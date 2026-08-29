from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from app.actions import ACTIONS
from app.ssh import CommandResult, SSHClient, parse_output, redact


def test_recursive_redaction_of_real_bitrix_shapes() -> None:
    source = {
        "params": {
            "server": {
                "host_vars": {"host_pass": "generated-password"},
                "DBPassword": "database-password",
                "ip": "192.168.0.56",
            }
        }
    }
    result = redact(source)
    assert result["params"]["server"]["host_vars"]["host_pass"] == "********"
    assert result["params"]["server"]["DBPassword"] == "********"
    assert result["params"]["server"]["ip"] == "192.168.0.56"


def test_json_output_is_normalized() -> None:
    result = parse_output('{"params":{"status":"finished","token":"x"}}', "", 0)
    assert result["exit_status"] == 0
    assert result["data"]["params"]["status"] == "finished"
    assert result["data"]["params"]["token"] == "********"


def test_plain_task_output_extracts_remote_id() -> None:
    result = parse_output("info:process:memcached_123:456:0:0:running\n", "", 0)
    assert result["remote_task_id"] == "memcached_123"


def test_plain_error_is_redacted() -> None:
    result = parse_output("error:auth\npassword=visible", "", 1)
    assert "visible" not in result["stdout"]


def test_action_identifier_ending_in_password_is_not_redacted() -> None:
    source = {"actions": {"mysql.change_password": {"available": True}}}
    assert redact(source) == source


async def test_background_action_defers_secret_cleanup_until_worker_finishes(
    monkeypatch: Any,
) -> None:
    client = object.__new__(SSHClient)
    removed: list[dict[str, str]] = []
    connection = object()

    @asynccontextmanager
    async def connect():
        yield connection

    async def upload_secrets(_connection: object, _values: dict[str, str]) -> dict[str, str]:
        return {"password": "/opt/webdir/tmp/controller_secret"}

    async def remove_files(_connection: object, paths: dict[str, str]) -> None:
        removed.append(paths)

    async def run_argv(
        _connection: object, _argv: tuple[str, ...], **_kwargs: Any
    ) -> CommandResult:
        return CommandResult(0, "info:process:mysql_123:456:0:0:running\n", "")

    monkeypatch.setattr(client, "connect", connect)
    monkeypatch.setattr(client, "upload_secrets", upload_secrets)
    monkeypatch.setattr(client, "remove_files", remove_files)
    monkeypatch.setattr(client, "run_argv", run_argv)

    spec = ACTIONS["mysql.change_password"]
    values = spec.normalize({"host": "db1.example.com", "password": "super-secret"})
    _results, task_id, _disconnected, deferred = await client.execute_action(spec, values)

    assert task_id == "mysql_123"
    assert deferred == {"password": "/opt/webdir/tmp/controller_secret"}
    assert removed == []

    await client.cleanup_secret_files(deferred)
    assert removed == [deferred]
