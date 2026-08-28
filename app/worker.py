from __future__ import annotations

import asyncio
import logging
import os
import socket
import uuid
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import select

from app.actions import get_action
from app.config import get_settings
from app.db import SessionLocal
from app.models import AuditEvent, Operation, OperationEvent, Server
from app.security import SecretBox
from app.ssh import SSHClient, SSHError, parse_output, redact

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
TERMINAL_REMOTE = {"finished", "error", "stopped", "failed", "canceled", "interrupt"}


def worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


def find_status(value: Any) -> str | None:
    if isinstance(value, dict):
        if isinstance(value.get("status"), str):
            return cast(str, value["status"]).lower()
        for child in value.values():
            found = find_status(child)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = find_status(child)
            if found:
                return found
    return None


def remote_status_succeeded(action: str, status: str) -> bool:
    return status == "finished" or (action == "host.reboot" and status == "interrupt")


async def add_event(operation: Operation, event: str, message: str, **data: Any) -> None:
    async with SessionLocal() as session:
        session.add(
            OperationEvent(
                operation_id=operation.id,
                event=event,
                message=message,
                data=redact(data),
            )
        )
        await session.commit()


async def set_status(
    operation_id: uuid.UUID,
    status: str,
    *,
    result: dict[str, Any] | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    remote_task_id: str | None = None,
) -> Operation:
    async with SessionLocal() as session:
        operation = await session.get(Operation, operation_id)
        if operation is None:
            raise RuntimeError("operation disappeared")
        operation.status = status
        operation.updated_at = datetime.now(UTC)
        if status == "preparing" and operation.started_at is None:
            operation.started_at = datetime.now(UTC)
        if status in {"succeeded", "failed", "canceled", "unknown"}:
            operation.finished_at = datetime.now(UTC)
        if result is not None:
            operation.result = redact(result)
        if error_code is not None:
            operation.error_code = error_code
        if error_message is not None:
            operation.error_message = str(redact(error_message))
        if remote_task_id is not None:
            operation.remote_task_id = remote_task_id
        await session.commit()
        await session.refresh(operation)
        return operation


async def claim_next(identity: str) -> uuid.UUID | None:
    async with SessionLocal() as session:
        async with session.begin():
            query = (
                select(Operation)
                .where(Operation.status == "queued")
                .order_by(Operation.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            operation = await session.scalar(query)
            if operation is None:
                return None
            conflict = await session.scalar(
                select(Operation.id).where(
                    Operation.server_id == operation.server_id,
                    Operation.category == operation.category,
                    Operation.status.in_(("preparing", "running", "reconnecting")),
                )
            )
            if conflict is not None:
                return None
            operation.status = "preparing"
            operation.claimed_by = identity
            operation.started_at = datetime.now(UTC)
            session.add(
                OperationEvent(
                    operation_id=operation.id,
                    event="claimed",
                    message="Operation was claimed by a worker",
                    data={},
                )
            )
            return operation.id


async def poll_remote_task(
    client: SSHClient, operation: Operation, task_id: str, timeout_seconds: float = 7200
) -> dict[str, Any]:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    last_status: str | None = None
    while asyncio.get_running_loop().time() < deadline:
        try:
            async with client.connect() as connection:
                result = await client.run_argv(
                    connection,
                    (
                        "/opt/webdir/bin/bx-process",
                        "-a",
                        "status",
                        "-t",
                        task_id,
                        "-o",
                        "json",
                    ),
                    timeout=30,
                )
        except SSHError:
            if operation.action != "host.reboot":
                raise
            await add_event(
                operation,
                "reconnecting",
                "SSH is unavailable while the target host reboots",
                remote_task_id=task_id,
            )
            await asyncio.sleep(5)
            continue
        parsed = parse_output(result.stdout, result.stderr, result.exit_status)
        status_value = find_status(parsed)
        if status_value != last_status:
            await add_event(
                operation,
                "remote_status",
                f"Remote task status: {status_value or 'unknown'}",
                remote_task_id=task_id,
                status=status_value,
            )
            last_status = status_value
        if status_value in TERMINAL_REMOTE:
            if remote_status_succeeded(operation.action, status_value):
                return parsed
            raise SSHError(f"remote task {task_id} completed with status {status_value}")
        await asyncio.sleep(2)
    raise SSHError(f"remote task {task_id} timed out")


async def wait_for_reconnect(client: SSHClient, timeout_seconds: float = 300) -> bool:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        try:
            async with client.connect() as connection:
                result = await client.run_argv(connection, ("/usr/bin/true",), timeout=10)
                return result.exit_status == 0
        except SSHError:
            await asyncio.sleep(5)
    return False


async def process_operation(operation_id: uuid.UUID) -> None:
    async with SessionLocal() as session:
        operation = await session.get(Operation, operation_id)
        if operation is None:
            return
        server = await session.get(Server, operation.server_id)
        if server is None:
            await set_status(
                operation_id,
                "failed",
                error_code="server_missing",
                error_message="Target server was deleted",
            )
            return
        parameters = SecretBox.configured().decrypt_json(operation.args_encrypted)
        spec = get_action(operation.action)

    client = SSHClient(server)
    operation = await set_status(operation_id, "running")
    await add_event(operation, "started", f"Started {spec.name}", category=spec.category)
    try:
        results, task_id, disconnected = await client.execute_action(spec, parameters)
        if task_id:
            operation = await set_status(operation_id, "running", remote_task_id=task_id)
            await add_event(
                operation,
                "remote_task",
                "BitrixVM accepted a background task",
                remote_task_id=task_id,
            )
            remote_result = await poll_remote_task(client, operation, task_id)
            results.append({"remote_task": remote_result})
        if disconnected:
            operation = await set_status(operation_id, "reconnecting", result={"commands": results})
            await add_event(
                operation,
                "disconnected",
                "SSH disconnected as expected; waiting for the server",
            )
            if spec.name == "local.halt":
                operation = await set_status(
                    operation_id,
                    "unknown",
                    result={"commands": results, "reason": "server powered off"},
                )
                await add_event(operation, "complete", "Server powered off; final state is unknown")
                return
            if not await wait_for_reconnect(client):
                raise SSHError("server did not reconnect before timeout")
        operation = await set_status(operation_id, "succeeded", result={"commands": results})
        await add_event(operation, "complete", "Operation completed successfully")
        async with SessionLocal() as session:
            session.add(
                AuditEvent(
                    user_id=operation.user_id,
                    server_id=operation.server_id,
                    action=operation.action,
                    outcome="succeeded",
                    data={"operation_id": str(operation.id)},
                )
            )
            await session.commit()
    except Exception as exc:
        logger.exception("operation failed", extra={"operation_id": str(operation_id)})
        operation = await set_status(
            operation_id,
            "failed",
            error_code=type(exc).__name__,
            error_message=str(exc),
        )
        await add_event(operation, "failed", "Operation failed", error=str(exc))
        async with SessionLocal() as session:
            session.add(
                AuditEvent(
                    user_id=operation.user_id,
                    server_id=operation.server_id,
                    action=operation.action,
                    outcome="failed",
                    data={"operation_id": str(operation.id), "error": str(redact(str(exc)))},
                )
            )
            await session.commit()


async def run_worker() -> None:
    identity = worker_id()
    settings = get_settings()
    logger.info("worker started", extra={"worker_id": identity})
    while True:
        try:
            operation_id = await claim_next(identity)
            if operation_id is None:
                await asyncio.sleep(settings.worker_poll_seconds)
                continue
            await process_operation(operation_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("worker loop failure")
            await asyncio.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    asyncio.run(run_worker())
