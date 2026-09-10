from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.actions import ACTIONS
from app.config import get_settings
from app.db import get_db
from app.dependencies import current_user
from app.models import Server, ServerProbe, User, as_utc
from app.schemas import (
    CapabilityRead,
    LogRequest,
    LogResponse,
    LogServiceInfo,
    ProbeCreate,
    ProbeRead,
    ServerCreate,
    ServerRead,
    ServerUpdate,
)
from app.security import SecretBox
from app.ssh import (
    SSHClient,
    SSHError,
    generate_ssh_keypair,
    probe_host_key,
    validate_log_file_path,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/servers", tags=["servers"])
POOL_HOST_PATTERN = re.compile(r"[A-Za-z0-9_.-]{1,253}")


async def get_server_or_404(server_id: uuid.UUID, session: AsyncSession) -> Server:
    server = await session.get(Server, server_id)
    if server is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Server not found")
    return server


@router.post("/probes", response_model=ProbeRead, status_code=status.HTTP_201_CREATED)
async def create_probe(
    payload: ProbeCreate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> ProbeRead:
    try:
        host_key, fingerprint, algorithm = await probe_host_key(
            payload.address, payload.port, get_settings().ssh_connect_timeout
        )
    except SSHError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    probe = ServerProbe(
        address=payload.address,
        port=payload.port,
        host_key=host_key,
        fingerprint=fingerprint,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
        created_by=user.id,
    )
    session.add(probe)
    await session.commit()
    await session.refresh(probe)
    return ProbeRead(
        id=probe.id,
        address=probe.address,
        port=probe.port,
        fingerprint=probe.fingerprint,
        host_key_algorithm=algorithm,
        expires_at=probe.expires_at,
    )


@router.post("", response_model=ServerRead, status_code=status.HTTP_201_CREATED)
async def create_server(
    payload: ServerCreate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> Server:
    probe = await session.get(ServerProbe, payload.probe_id)
    now = datetime.now(UTC)
    if probe is None or probe.created_by != user.id or as_utc(probe.expires_at) <= now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Probe is missing or expired")
    if payload.confirmed_fingerprint != probe.fingerprint:
        raise HTTPException(status.HTTP_409_CONFLICT, "SSH fingerprint was not confirmed")
    try:
        material = payload.credential.material()
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    if payload.credential.type == "password":
        bootstrap_server = Server(
            name=payload.name,
            address=probe.address,
            port=probe.port,
            username=payload.username,
            credential_type="password",
            credentials_encrypted=SecretBox.configured().encrypt_json(material),
            host_key=probe.host_key,
            host_key_fingerprint=probe.fingerprint,
        )
        try:
            private_key_pem, public_key = generate_ssh_keypair(
                comment=f"admin-bitrixvm-{payload.name}"
            )
            bootstrap_client = SSHClient(bootstrap_server)
            await bootstrap_client.install_authorized_key(public_key)
        except SSHError as exc:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY, f"SSH key setup via password failed: {exc}"
            ) from exc

        server = Server(
            name=payload.name,
            address=probe.address,
            port=probe.port,
            username=payload.username,
            credential_type="private_key",
            credentials_encrypted=SecretBox.configured().encrypt_json(
                {"private_key": private_key_pem}
            ),
            host_key=probe.host_key,
            host_key_fingerprint=probe.fingerprint,
        )
    else:
        server = Server(
            name=payload.name,
            address=probe.address,
            port=probe.port,
            username=payload.username,
            credential_type=payload.credential.type,
            credentials_encrypted=SecretBox.configured().encrypt_json(material),
            host_key=probe.host_key,
            host_key_fingerprint=probe.fingerprint,
        )
    # Verify authentication and compatibility before persisting the target.
    try:
        server.capabilities = await SSHClient(server).discovery()
        server.capabilities_checked_at = now
    except SSHError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    session.add(server)
    await session.delete(probe)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Server name already exists") from None
    await session.refresh(server)
    return server


@router.get("", response_model=list[ServerRead])
async def list_servers(
    _: User = Depends(current_user), session: AsyncSession = Depends(get_db)
) -> list[Server]:
    return list((await session.scalars(select(Server).order_by(Server.name))).all())


LOG_SERVICES: dict[str, dict[str, Any]] = {
    "nginx": {
        "name": "Nginx (HTTP/HTTPS)",
        "journal_unit": "nginx",
        "files": [
            "/var/log/nginx/error.log",
            "/var/log/nginx/access.log",
        ],
    },
    "httpd": {
        "name": "Apache (httpd / PHP)",
        "journal_unit": "httpd",
        "files": [
            "/var/log/httpd/error_log",
            "/var/log/httpd/access_log",
        ],
    },
    "bitrix-manager": {
        "name": "BitrixVM Управление",
        "journal_unit": None,
        "files": [
            "/opt/webdir/logs/wrapper.log",
            "/opt/webdir/logs/bvat.log",
            "/opt/webdir/logs/bxSiteNew.debug",
            "/opt/webdir/logs/pool_manage.debug",
            "/opt/webdir/logs/bxMysql.debug",
            "/opt/webdir/logs/install-9.0.10.log",
        ],
    },
    "push-server": {
        "name": "Bitrix Push Server (RTC)",
        "journal_unit": "push-server",
        "files": [
            "/var/log/push-server/error.log",
            "/var/log/push-server/info.log",
        ],
    },
    "mysql": {
        "name": "MySQL / Percona / MariaDB",
        "journal_unit": "mysqld",
        "files": [
            "/var/log/mysqld.log",
            "/var/log/mysql/error.log",
            "/var/log/mariadb/mariadb.log",
        ],
    },
    "redis": {
        "name": "Redis",
        "journal_unit": "redis",
        "files": [
            "/var/log/redis/redis.log",
        ],
    },
    "memcached": {
        "name": "Memcached",
        "journal_unit": "memcached",
        "files": [],
    },
    "cron": {
        "name": "Cron (Задачи Bitrix)",
        "journal_unit": "crond",
        "files": [
            "/var/log/cron",
        ],
    },
    "bvat": {
        "name": "Bitrix-Env Auto-tuning (BVAT)",
        "journal_unit": "bvat",
        "files": [
            "/opt/webdir/logs/bvat.log",
        ],
    },
    "php-fpm": {
        "name": "PHP-FPM",
        "journal_unit": "php-fpm",
        "files": [
            "/var/log/php-fpm/www-error.log",
        ],
    },
    "mail": {
        "name": "Почта (msmtp / maillog)",
        "journal_unit": None,
        "files": [
            "/var/log/maillog",
        ],
    },
    "system": {
        "name": "Система (syslog / auth)",
        "journal_unit": "_system",
        "files": [
            "/var/log/messages",
            "/var/log/secure",
            "/var/log/dnf.log",
        ],
    },
    "custom": {
        "name": "Пользовательский файл",
        "journal_unit": None,
        "files": [],
    },
}

SERVICE_ALIASES: dict[str, str] = {
    "bitrix-pool": "bitrix-manager",
    "bitrix-sites": "bitrix-manager",
    "bitrix-process": "bitrix-manager",
    "bitrix-sphinx": "bitrix-manager",
}


def get_default_log_services() -> list[dict[str, Any]]:
    return [
        {
            "id": key,
            "name": value["name"],
            "journal_unit": value["journal_unit"],
            "files": value["files"],
            "active": None,
        }
        for key, value in LOG_SERVICES.items()
    ]


@router.get("/log-services", response_model=list[LogServiceInfo])
async def list_log_services(
    _: User = Depends(current_user),
) -> list[dict[str, Any]]:
    return get_default_log_services()


@router.get("/{server_id}", response_model=ServerRead)
async def get_server(
    server_id: uuid.UUID,
    _: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> Server:
    return await get_server_or_404(server_id, session)


@router.patch("/{server_id}", response_model=ServerRead)
async def update_server(
    server_id: uuid.UUID,
    payload: ServerUpdate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> Server:
    server = await get_server_or_404(server_id, session)

    if payload.name is not None and payload.name != server.name:
        server.name = payload.name
    if payload.enabled is not None:
        server.enabled = payload.enabled

    address_changed = payload.address is not None and payload.address != server.address
    port_changed = payload.port is not None and payload.port != server.port

    if address_changed or port_changed:
        new_address = payload.address if payload.address is not None else server.address
        new_port = payload.port if payload.port is not None else server.port
        now = datetime.now(UTC)
        try:
            host_key, fingerprint, _algo = await probe_host_key(
                new_address, new_port, get_settings().ssh_connect_timeout
            )
        except SSHError as exc:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"Не удалось получить SSH-ключ по адресу {new_address}:{new_port}: {exc}",
            ) from exc

        server.address = new_address
        server.port = new_port
        server.host_key = host_key
        server.host_key_fingerprint = fingerprint

        try:
            server.capabilities = await SSHClient(server).discovery()
            server.capabilities_checked_at = now
        except SSHError as exc:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"Проверка подключения по адресу {new_address}:{new_port} не удалась: {exc}",
            ) from exc

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Server name already exists") from None

    await session.refresh(server)
    return server


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: uuid.UUID,
    _: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    server = await get_server_or_404(server_id, session)
    await session.delete(server)
    await session.commit()


@router.post("/{server_id}/capabilities/refresh", response_model=list[CapabilityRead])
async def refresh_capabilities(
    server_id: uuid.UUID,
    _: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CapabilityRead]:
    server = await get_server_or_404(server_id, session)
    try:
        server.capabilities = await SSHClient(server).discovery()
    except SSHError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    server.capabilities_checked_at = datetime.now(UTC)
    await session.commit()
    return capability_models(server)


def pool_hostnames(value: Any) -> list[str]:
    """Extract hostnames from normalized wrapper_ansible_conf status output."""
    result: set[str] = set()

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if (
                    str(key).lower() in {"host", "hostname", "server"}
                    and isinstance(child, str)
                    and POOL_HOST_PATTERN.fullmatch(child)
                ):
                    result.add(child)
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return sorted(result)


def request_schema_with_options(server: Server, action: str) -> dict[str, Any]:
    schema = ACTIONS[action].request_schema()
    options = pool_hostnames(server.capabilities.get("pool"))
    if not options:
        return schema
    for definition in schema.get("properties", {}).values():
        if definition.get("x-options-source") == "pool_hosts":
            definition["x-options"] = options
    return schema


def capability_models(server: Server) -> list[CapabilityRead]:
    discovered = server.capabilities.get("actions", {})
    return [
        CapabilityRead(
            action=name,
            summary=spec.summary,
            available=bool(discovered.get(name, {}).get("available", False)),
            reason=discovered.get(name, {}).get("reason"),
            risk=spec.risk,
            category=spec.category,
            request_schema=request_schema_with_options(server, name),
        )
        for name, spec in sorted(ACTIONS.items())
    ]


@router.get("/{server_id}/capabilities", response_model=list[CapabilityRead])
async def capabilities(
    server_id: uuid.UUID,
    _: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CapabilityRead]:
    return capability_models(await get_server_or_404(server_id, session))


@router.get("/{server_id}/snapshot", response_model=dict[str, Any])
async def snapshot(
    server_id: uuid.UUID,
    _: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    server = await get_server_or_404(server_id, session)
    try:
        return await SSHClient(server).snapshot()
    except SSHError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc


@router.get("/{server_id}/services-status", response_model=dict[str, str])
async def get_server_services_status(
    server_id: uuid.UUID,
    _: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    server = await get_server_or_404(server_id, session)
    try:
        statuses = await SSHClient(server).get_service_statuses()
        if statuses:
            caps = dict(server.capabilities or {})
            caps["services"] = statuses
            server.capabilities = caps
            await session.commit()
            return statuses
    except Exception as exc:
        logger.warning("Failed to query service statuses for %s: %s", server_id, exc)

    if server.capabilities and "services" in server.capabilities:
        return dict(server.capabilities["services"])

    return {
        "nginx": "unknown",
        "httpd": "unknown",
        "mysql": "unknown",
        "php_fpm": "unknown",
        "memcached": "unknown",
        "redis": "unknown",
        "push_server": "unknown",
        "cron": "unknown",
        "bvat": "unknown",
    }


@router.get("/{server_id}/log-services", response_model=list[LogServiceInfo])
async def list_server_log_services(
    server_id: uuid.UUID,
    _: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    server = await get_server_or_404(server_id, session)
    try:
        discovered = await SSHClient(server).discover_log_services()
        if discovered:
            return discovered
    except Exception as exc:
        logger.warning("Dynamic log discovery failed for server %s: %s", server_id, exc)
    return get_default_log_services()


@router.post("/{server_id}/logs", response_model=LogResponse)
async def read_server_logs(
    server_id: uuid.UUID,
    payload: LogRequest,
    _: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> LogResponse:
    server = await get_server_or_404(server_id, session)

    service_id = SERVICE_ALIASES.get(payload.service, payload.service)
    service_config = LOG_SERVICES.get(service_id)

    if service_id == "custom":
        if payload.source != "file":
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Custom log source only supports file reading",
            )
        if not payload.file_path:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "file_path is required for custom log source",
            )
        try:
            validated_path = validate_log_file_path(payload.file_path)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
        effective_service = "custom"
        effective_file_path = validated_path
    elif service_config is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Unknown service: {payload.service}",
        )
    else:
        if payload.source == "journal":
            if service_config.get("journal_unit") is None:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    f"Service '{payload.service}' does not support journalctl",
                )
            effective_service = service_config["journal_unit"]
            effective_file_path = None
        elif payload.source == "file":
            effective_file_path = payload.file_path
            if not effective_file_path:
                if service_config.get("files"):
                    effective_file_path = service_config["files"][0]
                else:
                    raise HTTPException(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        f"Service '{payload.service}' has no default log files",
                    )
            try:
                effective_file_path = validate_log_file_path(effective_file_path)
            except ValueError as exc:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
            effective_service = service_id
        else:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Unsupported source: {payload.source}",
            )

    request = LogRequest(
        service=effective_service,
        source=payload.source,
        date_from=payload.date_from,
        date_to=payload.date_to,
        file_path=effective_file_path,
        limit=payload.limit,
        grep=payload.grep,
    )

    try:
        lines, source_used = await SSHClient(server).read_logs(request)
    except SSHError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc

    truncated = len(lines) >= payload.limit
    return LogResponse(
        lines=lines,
        total=len(lines),
        truncated=truncated,
        source_used=source_used,
    )
