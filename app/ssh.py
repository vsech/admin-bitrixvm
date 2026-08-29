from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import shlex
import tempfile
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, cast

import asyncssh

from app.actions import ACTIONS, BIN, ActionSpec, RemoteCommand
from app.config import Settings, get_settings
from app.models import Server
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
