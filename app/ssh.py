from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import shlex
import tempfile
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import asyncssh

from app.actions import ACTIONS, BIN, ActionSpec, RemoteCommand
from app.config import Settings, get_settings
from app.models import Server
from app.schemas import LogRequest
from app.security import SecretBox

logger = logging.getLogger(__name__)
SENSITIVE_KEY = re.compile(
    r"(?:pass(?:word)?|secret|token|private.?key|host_pass|dbpassword|smtppassword)", re.I
)
MASK = "********"


def is_sensitive_key(key: object) -> bool:
    text = str(key)
    # Dotted keys are action identifiers, e.g. mysql.change_password.
    return "." not in text and bool(SENSITIVE_KEY.search(text))


class SSHError(RuntimeError):
    pass


@dataclass(frozen=True)
class CommandResult:
    exit_status: int
    stdout: str
    stderr: str
    disconnected: bool = False


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: MASK if is_sensitive_key(key) else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        value = re.sub(
            r"(?i)(password|secret|token|host_pass)(\s*[:=]\s*)([^\s,}\]]+)",
            rf"\1\2{MASK}",
            value,
        )
    return value


def parse_output(stdout: str, stderr: str, exit_status: int) -> dict[str, Any]:
    cleaned_stdout = stdout.strip()
    cleaned_stderr = stderr.strip()
    parsed: Any = None
    if cleaned_stdout.startswith(("{", "[")):
        try:
            parsed = json.loads(cleaned_stdout)
        except json.JSONDecodeError:
            parsed = None
    if parsed is not None:
        safe = redact(parsed)
        if isinstance(safe, dict):
            return {"exit_status": exit_status, "data": safe, "stderr": redact(cleaned_stderr)}
        return {"exit_status": exit_status, "data": safe, "stderr": redact(cleaned_stderr)}

    task_match = re.search(r"^info:([^\n]+)$", cleaned_stdout, re.MULTILINE)
    task_id = None
    if task_match:
        fields = task_match.group(1).split(":")
        task_id = fields[1] if len(fields) > 1 else fields[0]
    return {
        "exit_status": exit_status,
        "stdout": redact(cleaned_stdout),
        "stderr": redact(cleaned_stderr),
        "remote_task_id": task_id,
    }


async def probe_host_key(address: str, port: int, timeout: float = 10) -> tuple[str, str, str]:
    try:
        key = await asyncio.wait_for(asyncssh.get_server_host_key(address, port), timeout=timeout)
    except (TimeoutError, OSError, asyncssh.Error) as exc:
        raise SSHError(f"unable to retrieve SSH host key: {exc}") from exc
    if key is None:
        raise SSHError("SSH server did not present a host key")
    exported = key.export_public_key("openssh").decode().strip()
    fingerprint = key.get_fingerprint("sha256")
    return exported, fingerprint, key.get_algorithm()


def generate_ssh_keypair(comment: str = "") -> tuple[str, str]:
    key = asyncssh.generate_private_key("ssh-ed25519")
    priv = key.export_private_key("openssh").decode("utf-8")
    pub = key.export_public_key("openssh").decode("utf-8").strip()
    if comment:
        pub = f"{pub} {comment}"
    return priv, pub


ALLOWED_LOG_PREFIXES = (
    "/var/log/",
    "/opt/webdir/logs/",
    "/home/bitrix/",
    "/tmp/php_sessions/",
    "/tmp/php_upload/",
)

FORBIDDEN_FILE_SUBSTRINGS = (
    "/etc/",
    "/proc/",
    "/sys/",
    "/dev/",
    "/root/",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "id_dsa",
    "authorized_keys",
    "known_hosts",
    "shadow",
    "master_key",
)


def validate_log_file_path(file_path: str) -> str:
    if not file_path or not isinstance(file_path, str):
        raise ValueError("file_path is required for file source")
    path = file_path.strip()
    if "\x00" in path:
        raise ValueError("Invalid file path")
    normalized = os.path.normpath(path)
    if not normalized.startswith("/"):
        raise ValueError("file_path must be an absolute path")
    if not any(normalized.startswith(prefix) for prefix in ALLOWED_LOG_PREFIXES):
        raise ValueError(
            f"Access denied: file must be located in allowed directories ({', '.join(ALLOWED_LOG_PREFIXES)})"
        )
    for forbidden in FORBIDDEN_FILE_SUBSTRINGS:
        if forbidden in normalized:
            raise ValueError(f"Access to sensitive file path containing '{forbidden}' is forbidden")
    return normalized


def is_active_log_file(file_path: str) -> bool:
    name = file_path.rsplit("/", 1)[-1]
    if not name:
        return False
    if name.endswith((".gz", ".xz", ".bz2", ".zip", ".rpmnew", ".rpmsave", "~")):
        return False
    if re.search(r"[-._]\d{6,}$", name):
        return False
    if re.search(r"\.\d+$", name):
        return False
    return True


class SSHClient:
    def __init__(self, server: Server, settings: Settings | None = None):
        self.server = server
        self.settings = settings or get_settings()
        self.credentials = SecretBox.configured().decrypt_json(server.credentials_encrypted)

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[asyncssh.SSHClientConnection]:
        host_pattern = (
            self.server.address
            if self.server.port == 22
            else f"[{self.server.address}]:{self.server.port}"
        )
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", prefix="known_hosts_") as known:
            known.write(f"{host_pattern} {self.server.host_key}\n")
            known.flush()
            kwargs: dict[str, Any] = {
                "host": self.server.address,
                "port": self.server.port,
                "username": self.server.username,
                "known_hosts": known.name,
                "connect_timeout": self.settings.ssh_connect_timeout,
                "keepalive_interval": 15,
                "keepalive_count_max": 3,
            }
            if self.server.credential_type == "password":
                kwargs["password"] = self.credentials["password"]
                kwargs["client_keys"] = None
            else:
                key = asyncssh.import_private_key(
                    self.credentials["private_key"], self.credentials.get("passphrase")
                )
                kwargs["client_keys"] = [key]
            try:
                async with asyncssh.connect(**kwargs) as connection:
                    yield connection
            except asyncssh.HostKeyNotVerifiable as exc:
                raise SSHError("SSH host key does not match the approved fingerprint") from exc
            except (OSError, asyncssh.Error) as exc:
                raise SSHError(f"SSH connection failed: {exc}") from exc

    async def run_argv(
        self,
        connection: asyncssh.SSHClientConnection,
        argv: tuple[str, ...],
        *,
        expect_disconnect: bool = False,
        timeout: float | None = None,
    ) -> CommandResult:
        command = shlex.join(argv)
        try:
            result = await asyncio.wait_for(
                connection.run(command, check=False, encoding="utf-8"),
                timeout=timeout or self.settings.ssh_command_timeout,
            )
        except (TimeoutError, asyncssh.ConnectionLost) as exc:
            if expect_disconnect:
                return CommandResult(0, "", "", disconnected=True)
            raise SSHError(f"remote command did not complete: {exc}") from exc
        stdout = str(result.stdout)[: self.settings.output_limit_bytes]
        stderr = str(result.stderr)[: self.settings.output_limit_bytes]
        return CommandResult(
            result.exit_status if result.exit_status is not None else -1, stdout, stderr
        )

    async def upload_secrets(
        self, connection: asyncssh.SSHClientConnection, values: dict[str, str]
    ) -> dict[str, str]:
        if not values:
            return {}
        paths: dict[str, str] = {}
        sftp = await connection.start_sftp_client()
        for name, value in values.items():
            remote = f"/opt/webdir/tmp/controller_{uuid.uuid4().hex}"
            async with sftp.open(remote, "w") as handle:
                await handle.write(value)
            await sftp.chmod(remote, 0o600)
            paths[name] = remote
        return paths

    async def remove_files(
        self, connection: asyncssh.SSHClientConnection, paths: dict[str, str]
    ) -> None:
        if not paths:
            return
        try:
            sftp = await connection.start_sftp_client()
            for path in paths.values():
                try:
                    await sftp.remove(path)
                except (OSError, asyncssh.SFTPError):
                    logger.warning(
                        "failed to remove remote secret file",
                        extra={"path_hash": hashlib.sha256(path.encode()).hexdigest()},
                    )
        except (OSError, asyncssh.Error):
            logger.warning("unable to start SFTP for secret cleanup")

    async def install_authorized_key(
        self, public_key: str, connection: asyncssh.SSHClientConnection | None = None
    ) -> None:
        cleaned_key = public_key.strip()
        if not cleaned_key:
            raise SSHError("cannot install empty public key")
        script = (
            "set -e\n"
            "mkdir -p -m 700 /root/.ssh\n"
            "chmod 700 /root/.ssh\n"
            "touch /root/.ssh/authorized_keys\n"
            "chmod 600 /root/.ssh/authorized_keys\n"
            f"if ! grep -qxF {shlex.quote(cleaned_key)} /root/.ssh/authorized_keys; then\n"
            f"    printf '%s\\n' {shlex.quote(cleaned_key)} >> /root/.ssh/authorized_keys\n"
            "fi\n"
            "if command -v restorecon >/dev/null 2>&1; then restorecon -R /root/.ssh; fi\n"
        )
        if connection is not None:
            result = await self.run_argv(connection, ("/bin/sh", "-c", script))
            if result.exit_status != 0:
                raise SSHError(
                    f"failed to install SSH public key: {result.stderr.strip() or result.stdout.strip()}"
                )
        else:
            async with self.connect() as conn:
                result = await self.run_argv(conn, ("/bin/sh", "-c", script))
                if result.exit_status != 0:
                    raise SSHError(
                        f"failed to install SSH public key: {result.stderr.strip() or result.stdout.strip()}"
                    )

    async def cleanup_secret_files(self, paths: dict[str, str]) -> None:
        if not paths:
            return
        try:
            async with self.connect() as connection:
                await self.remove_files(connection, paths)
        except SSHError:
            logger.warning("unable to reconnect for remote secret cleanup")

    async def execute(
        self, commands: tuple[RemoteCommand, ...], secret_values: dict[str, str]
    ) -> tuple[list[dict[str, Any]], str | None, bool]:
        results: list[dict[str, Any]] = []
        task_id: str | None = None
        disconnected = False
        async with self.connect() as connection:
            secret_paths = await self.upload_secrets(connection, secret_values)
            try:
                for command in commands:
                    result = await self.run_argv(
                        connection,
                        command.argv,
                        expect_disconnect=command.expect_disconnect,
                    )
                    disconnected = disconnected or result.disconnected
                    parsed = parse_output(result.stdout, result.stderr, result.exit_status)
                    results.append(parsed)
                    task_id = parsed.get("remote_task_id") or task_id
                    if result.exit_status != 0 and not result.disconnected:
                        raise SSHError(
                            f"remote command failed with exit status {result.exit_status}: "
                            f"{redact(result.stderr.strip())}"
                        )
            finally:
                if not disconnected:
                    await self.remove_files(connection, secret_paths)
        return results, task_id, disconnected

    async def execute_action(
        self, spec: ActionSpec, values: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], str | None, bool, dict[str, str]]:
        secret_values = {
            name: str(values[name])
            for name, param in spec.params.items()
            if param.kind == "secret" and values.get(name)
        }
        results: list[dict[str, Any]] = []
        task_id: str | None = None
        disconnected = False
        defer_secret_cleanup = False
        async with self.connect() as connection:
            secret_paths = await self.upload_secrets(connection, secret_values)
            commands = spec.builder(values, secret_paths)
            try:
                for command in commands:
                    result = await self.run_argv(
                        connection,
                        command.argv,
                        expect_disconnect=command.expect_disconnect,
                    )
                    disconnected = disconnected or result.disconnected
                    parsed = parse_output(result.stdout, result.stderr, result.exit_status)
                    results.append(parsed)
                    task_id = parsed.get("remote_task_id") or task_id
                    if result.exit_status != 0 and not result.disconnected:
                        raise SSHError(
                            f"remote command failed with exit status {result.exit_status}: "
                            f"{redact(result.stderr.strip())}"
                        )
                defer_secret_cleanup = task_id is not None and not disconnected
            finally:
                if not disconnected and not defer_secret_cleanup:
                    await self.remove_files(connection, secret_paths)
        deferred_paths = secret_paths if defer_secret_cleanup else {}
        return results, task_id, disconnected, deferred_paths

    async def discovery(self) -> dict[str, Any]:
        checks = {
            "os_release": ("/usr/bin/cat", "/etc/os-release"),
            "bitrix_env": ("/usr/bin/rpm", "-q", "bitrix-env"),
            "pool": (f"{BIN}/wrapper_ansible_conf", "-a", "status", "-o", "json"),
        }
        output: dict[str, Any] = {}
        async with self.connect() as connection:
            for key, argv in checks.items():
                result = await self.run_argv(connection, argv, timeout=30)
                output[key] = parse_output(result.stdout, result.stderr, result.exit_status)
            required = sorted(
                {command for spec in ACTIONS.values() for command in spec.required_commands}
            )
            available: dict[str, bool] = {}
            for command in required:
                result = await self.run_argv(
                    connection, ("/usr/bin/test", "-x", command), timeout=5
                )
                available[command] = result.exit_status == 0
            output["commands"] = available
            output["services"] = await self.get_service_statuses(connection=connection)
        rpm_text = json.dumps(output.get("bitrix_env", {}))
        compatible = bool(re.search(r"bitrix-env-9\.", rpm_text))
        output["compatible"] = compatible
        action_capabilities: dict[str, dict[str, Any]] = {}
        for name, spec in ACTIONS.items():
            missing = [cmd for cmd in spec.required_commands if not available.get(cmd, False)]
            reason = None
            if not compatible:
                reason = "BitrixEnv 9.x on EL9 is required"
            elif spec.disabled_reason:
                reason = spec.disabled_reason
            elif missing:
                reason = f"Required executable is missing: {', '.join(missing)}"
            action_capabilities[name] = {"available": reason is None, "reason": reason}
        output["actions"] = action_capabilities
        return cast(dict[str, Any], redact(output))

    async def get_service_statuses(self, connection: Any = None) -> dict[str, str]:
        cmd = (
            "for s in nginx httpd mysqld mariadb redis memcached push-server crond php-fpm bvat; "
            "do echo \"$s:$(systemctl is-active $s 2>/dev/null || echo unknown)\"; done"
        )
        raw = ""
        try:
            if connection is not None:
                svc_res = await connection.run(cmd, check=False, encoding="utf-8")
                raw = str(svc_res.stdout)
            else:
                async with self.connect() as conn:
                    svc_res = await conn.run(cmd, check=False, encoding="utf-8")
                    raw = str(svc_res.stdout)
        except SSHError as exc:
            logger.warning("Failed to query service statuses: %s", exc)
            return {}

        services: dict[str, str] = {}
        for line in raw.splitlines():
            line = line.strip()
            if ":" in line:
                unit, _, state = line.partition(":")
                services[unit.strip()] = state.strip()

        db_state = "inactive"
        if services.get("mysqld") == "active" or services.get("mariadb") == "active":
            db_state = "active"
        elif services.get("mysqld") == "failed" or services.get("mariadb") == "failed":
            db_state = "failed"
        elif "active" in (services.get("mysqld", ""), services.get("mariadb", "")):
            db_state = "active"
        else:
            db_state = services.get("mysqld") or services.get("mariadb") or "inactive"

        return {
            "nginx": services.get("nginx", "unknown"),
            "httpd": services.get("httpd", "unknown"),
            "mysql": db_state,
            "php_fpm": services.get("php-fpm", "unknown"),
            "memcached": services.get("memcached", "unknown"),
            "redis": services.get("redis", "unknown"),
            "push_server": services.get("push-server", "unknown"),
            "cron": services.get("crond", "unknown"),
            "bvat": services.get("bvat", "unknown"),
        }

    async def snapshot(self) -> dict[str, Any]:
        commands = {
            "pool": (f"{BIN}/wrapper_ansible_conf", "-a", "status", "-o", "json"),
            "tasks": (f"{BIN}/bx-process", "-a", "list", "-o", "json"),
            "sites": (f"{BIN}/bx-sites", "-a", "list", "-o", "json"),
            "mysql": (f"{BIN}/bx-mysql", "-a", "list", "-o", "json"),
            "memcached": (f"{BIN}/bx-mc", "-a", "list", "-o", "json"),
            "sphinx": (f"{BIN}/bx-sphinx", "-a", "list", "-o", "json"),
            "monitoring": (f"{BIN}/bx-monitor", "-a", "status", "-o", "json"),
            "network": (f"{BIN}/bx-node", "-a", "list", "-o", "json"),
        }
        snapshot: dict[str, Any] = {}
        async with self.connect() as connection:
            for name, argv in commands.items():
                try:
                    result = await self.run_argv(connection, argv, timeout=30)
                    snapshot[name] = parse_output(result.stdout, result.stderr, result.exit_status)
                except SSHError as exc:
                    snapshot[name] = {"error": str(exc)}
        return cast(dict[str, Any], redact(snapshot))

    async def discover_log_services(self) -> list[dict[str, Any]]:
        find_cmd = (
            "/usr/bin/find /var/log/nginx /var/log/httpd /var/log/push-server "
            "/var/log/redis /opt/webdir/logs /var/log/mysql -maxdepth 1 -type f 2>/dev/null ; "
            "echo '---SERVICES---' ; "
            "/usr/bin/systemctl is-active httpd nginx mysqld redis memcached push-server bvat crond php-fpm 2>/dev/null"
        )
        try:
            async with self.connect() as connection:
                result = await connection.run(find_cmd, check=False, encoding="utf-8")
                raw = str(result.stdout)
        except SSHError:
            return []

        files_part, _, services_part = raw.partition("---SERVICES---")
        raw_files = [f.strip() for f in files_part.splitlines() if f.strip()]
        active_files = [f for f in raw_files if is_active_log_file(f)]

        service_states = [s.strip() for s in services_part.splitlines() if s.strip()]
        service_names = [
            "httpd", "nginx", "mysqld", "redis", "memcached", "push-server", "bvat", "crond", "php-fpm"
        ]
        active_map = {
            name: (service_states[i] == "active" if i < len(service_states) else None)
            for i, name in enumerate(service_names)
        }

        nginx_files = [f for f in active_files if f.startswith("/var/log/nginx/")]
        nginx_files.sort(key=lambda x: (0 if "error.log" in x else (1 if "access.log" in x else 2), x))

        httpd_files = [f for f in active_files if f.startswith("/var/log/httpd/")]
        httpd_files.sort(key=lambda x: (0 if "error_log" in x else (1 if "access_log" in x else 2), x))

        push_files = [f for f in active_files if f.startswith("/var/log/push-server/")]
        push_files.sort(key=lambda x: (0 if "error.log" in x else 1, x))

        redis_files = [f for f in active_files if f.startswith("/var/log/redis/")]

        webdir_files = [f for f in active_files if f.startswith("/opt/webdir/logs/")]
        webdir_files.sort(key=lambda x: (0 if "wrapper.log" in x else (1 if "bvat.log" in x else 2), x))

        mysql_files = [f for f in active_files if f.startswith("/var/log/mysql/")]

        return [
            {
                "id": "nginx",
                "name": "Nginx (HTTP/HTTPS)",
                "journal_unit": "nginx",
                "files": nginx_files or ["/var/log/nginx/error.log", "/var/log/nginx/access.log"],
                "active": active_map.get("nginx"),
            },
            {
                "id": "httpd",
                "name": "Apache (httpd / PHP)",
                "journal_unit": "httpd",
                "files": httpd_files or ["/var/log/httpd/error_log", "/var/log/httpd/access_log"],
                "active": active_map.get("httpd"),
            },
            {
                "id": "bitrix-manager",
                "name": "BitrixVM Управление",
                "journal_unit": None,
                "files": webdir_files or ["/opt/webdir/logs/wrapper.log", "/opt/webdir/logs/bvat.log"],
                "active": True,
            },
            {
                "id": "push-server",
                "name": "Bitrix Push Server (RTC)",
                "journal_unit": "push-server",
                "files": push_files or ["/var/log/push-server/error.log", "/var/log/push-server/info.log"],
                "active": active_map.get("push-server"),
            },
            {
                "id": "mysql",
                "name": "MySQL / Percona / MariaDB",
                "journal_unit": "mysqld",
                "files": mysql_files or ["/var/log/mysqld.log", "/var/log/mysql/error.log"],
                "active": active_map.get("mysqld"),
            },
            {
                "id": "redis",
                "name": "Redis",
                "journal_unit": "redis",
                "files": redis_files or ["/var/log/redis/redis.log"],
                "active": active_map.get("redis"),
            },
            {
                "id": "memcached",
                "name": "Memcached",
                "journal_unit": "memcached",
                "files": [],
                "active": active_map.get("memcached"),
            },
            {
                "id": "cron",
                "name": "Cron (Задачи Bitrix)",
                "journal_unit": "crond",
                "files": ["/var/log/cron"],
                "active": active_map.get("crond"),
            },
            {
                "id": "bvat",
                "name": "Bitrix-Env Auto-tuning (BVAT)",
                "journal_unit": "bvat",
                "files": ["/opt/webdir/logs/bvat.log"],
                "active": active_map.get("bvat"),
            },
            {
                "id": "php-fpm",
                "name": "PHP-FPM",
                "journal_unit": "php-fpm",
                "files": ["/var/log/php-fpm/www-error.log"],
                "active": active_map.get("php-fpm"),
            },
            {
                "id": "mail",
                "name": "Почта (msmtp / maillog)",
                "journal_unit": None,
                "files": ["/var/log/maillog"],
                "active": None,
            },
            {
                "id": "system",
                "name": "Система (syslog / auth)",
                "journal_unit": "_system",
                "files": ["/var/log/messages", "/var/log/secure", "/var/log/dnf.log"],
                "active": None,
            },
            {
                "id": "custom",
                "name": "Пользовательский файл",
                "journal_unit": None,
                "files": [],
                "active": None,
            },
        ]

    async def read_logs(self, request: LogRequest) -> tuple[list[str], str]:
        now = datetime.now(UTC)
        d_from = request.date_from or (now - timedelta(hours=24))
        d_to = request.date_to or now

        if d_from.tzinfo is not None:
            date_from = d_from.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        else:
            date_from = d_from.strftime("%Y-%m-%d %H:%M:%S")

        if d_to.tzinfo is not None:
            date_to = d_to.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        else:
            date_to = d_to.strftime("%Y-%m-%d %H:%M:%S")

        async with self.connect() as connection:
            if request.source == "journal":
                return await self._read_journal_logs(
                    connection, request.service, date_from, date_to, request.limit, request.grep
                )
            return await self._read_file_logs(
                connection, request.file_path or "", date_from, date_to, request.limit,
                request.grep,
            )

    async def _read_journal_logs(
        self,
        connection: asyncssh.SSHClientConnection,
        service: str | None,
        date_from: str,
        date_to: str,
        limit: int,
        grep: str | None = None,
    ) -> tuple[list[str], str]:
        argv: list[str] = [
            "/usr/bin/journalctl",
            "--since",
            date_from,
            "--until",
            date_to,
            "--no-pager",
            "-n",
            str(limit),
            "--output",
            "short-iso",
        ]
        if service and service not in {"_system", "system"}:
            argv.extend(["-u", service])
        if grep:
            argv.extend(["-g", grep])

        result = await self.run_argv(connection, tuple(argv), timeout=60)
        if result.exit_status not in (0, 1) and not result.stdout.strip():
            raise SSHError(
                f"journalctl failed (exit {result.exit_status}): {result.stderr.strip()}"
            )
        lines = [
            line for line in result.stdout.splitlines()
            if line.strip() and not line.strip().startswith("-- No entries --")
        ]
        return lines, "journal"

    async def _read_file_logs(
        self,
        connection: asyncssh.SSHClientConnection,
        file_path: str,
        date_from: str,
        date_to: str,
        limit: int,
        grep: str | None,
    ) -> tuple[list[str], str]:
        if not file_path:
            raise SSHError("file_path is required for file source")

        try:
            validated_path = validate_log_file_path(file_path)
        except ValueError as exc:
            raise SSHError(str(exc)) from exc

        test = await self.run_argv(connection, ("/usr/bin/test", "-r", validated_path), timeout=5)
        if test.exit_status != 0:
            raise SSHError(f"Log file not found or not readable: {validated_path}")

        if grep:
            argv = ("/usr/bin/grep", "-E", grep, validated_path)
            result = await self.run_argv(connection, argv, timeout=60)
            if result.exit_status not in (0, 1):
                raise SSHError(
                    f"grep failed (exit {result.exit_status}): {result.stderr.strip()}"
                )
            if result.exit_status == 1 and not result.stdout.strip():
                return [], "file"
            lines = [line for line in result.stdout.splitlines() if line.strip()]
            if len(lines) > limit:
                lines = lines[-limit:]
            return lines, "file"
        else:
            argv = ("/usr/bin/tail", "-n", str(limit), validated_path)
            result = await self.run_argv(connection, argv, timeout=60)
            if result.exit_status != 0 and not result.stdout.strip():
                raise SSHError(
                    f"Failed to read log file (exit {result.exit_status}): {result.stderr.strip()}"
                )
            lines = [line for line in result.stdout.splitlines() if line.strip()]
            return lines, "file"
