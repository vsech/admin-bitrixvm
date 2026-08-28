from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.actions import ActionSpec, ActionValidationError, get_action
from app.api.servers import get_server_or_404
from app.config import get_settings
from app.db import SessionLocal, get_db
from app.dependencies import current_user
from app.models import AuditEvent, Confirmation, Operation, OperationEvent, User, as_utc
from app.schemas import (
    ActionRequest,
    OperationEventRead,
    OperationRead,
    PreviewRead,
    PreviewRequest,
)
from app.security import SecretBox, opaque_token, stable_hash, token_hash

router = APIRouter(prefix="/api/v1", tags=["operations"])


def validate_action_parameters(
    action: str, parameters: dict[str, object]
) -> tuple[ActionSpec, dict[str, object]]:
    try:
        spec = get_action(action)
        normalized = spec.normalize(parameters)
    except ActionValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return spec, normalized


def ensure_available(server: object, action: str) -> None:
    capability = getattr(server, "capabilities", {}).get("actions", {}).get(action, {})
    if not capability.get("available", False):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            capability.get("reason") or "Action is unavailable on this server",
        )


@router.post(
    "/servers/{server_id}/actions/{action}/preview",
    response_model=PreviewRead,
)
async def preview_action(
    server_id: uuid.UUID,
    action: str,
    payload: PreviewRequest,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> PreviewRead:
    server = await get_server_or_404(server_id, session)
    spec, normalized = validate_action_parameters(action, payload.parameters)
    ensure_available(server, action)
    raw_token = opaque_token()
    expires = datetime.now(UTC) + timedelta(minutes=get_settings().confirmation_minutes)
    state_fingerprint = stable_hash(
        {"capabilities": server.capabilities, "updated_at": server.updated_at}
    )
    session.add(
        Confirmation(
            token_hash=token_hash(raw_token),
            user_id=user.id,
            server_id=server.id,
            action=action,
            payload_hash=stable_hash(normalized),
            state_fingerprint=state_fingerprint,
            expires_at=expires,
        )
    )
    await session.commit()
    return PreviewRead(
        action=action,
        risk=spec.risk,
        summary=spec.summary,
        warnings=list(spec.warnings),
        normalized_parameters=spec.redact(normalized),
        confirmation_token=raw_token,
        expires_at=expires,
    )


@router.post(
    "/servers/{server_id}/actions/{action}",
    response_model=OperationRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def execute_action(
    server_id: uuid.UUID,
    action: str,
    payload: ActionRequest,
    request: Request,
    idempotency_key: str = Header(min_length=8, max_length=128, alias="Idempotency-Key"),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> Operation:
    server = await get_server_or_404(server_id, session)
    spec, normalized = validate_action_parameters(action, payload.parameters)
    ensure_available(server, action)

    existing = await session.scalar(
        select(Operation).where(
            Operation.server_id == server.id,
            Operation.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return existing

    if spec.confirmation_required:
        if not payload.confirmation_token:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "A preview confirmation token is required"
            )
        confirmation = await session.scalar(
            select(Confirmation).where(
                Confirmation.token_hash == token_hash(payload.confirmation_token),
                Confirmation.user_id == user.id,
                Confirmation.server_id == server.id,
                Confirmation.action == action,
            )
        )
        now = datetime.now(UTC)
        expected_state = stable_hash(
            {"capabilities": server.capabilities, "updated_at": server.updated_at}
        )
        if (
            confirmation is None
            or confirmation.consumed_at is not None
            or as_utc(confirmation.expires_at) <= now
            or confirmation.payload_hash != stable_hash(normalized)
            or confirmation.state_fingerprint != expected_state
        ):
            raise HTTPException(status.HTTP_409_CONFLICT, "Confirmation is expired or stale")
        confirmation.consumed_at = now

    operation = Operation(
        server_id=server.id,
        user_id=user.id,
        action=action,
        category=spec.category,
        risk=spec.risk,
        args_redacted=spec.redact(normalized),
        args_encrypted=SecretBox.configured().encrypt_json(normalized),
        idempotency_key=idempotency_key,
    )
    session.add(operation)
    session.add(
        AuditEvent(
            user_id=user.id,
            server_id=server.id,
            action=action,
            outcome="queued",
            request_id=getattr(request.state, "request_id", None),
            remote_addr=request.client.host if request.client else None,
            data={"parameters": spec.redact(normalized), "idempotency_key": idempotency_key},
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(
            select(Operation).where(
                Operation.server_id == server.id,
                Operation.idempotency_key == idempotency_key,
            )
        )
        if existing is None:
            raise
            return existing
    await session.refresh(operation)
    return operation


@router.get("/operations", response_model=list[OperationRead])
async def list_operations(
    limit: int = 100,
    offset: int = 0,
    _: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> list[Operation]:
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    query = select(Operation).order_by(Operation.created_at.desc()).limit(limit).offset(offset)
    return list((await session.scalars(query)).all())


@router.get("/operations/{operation_id}", response_model=OperationRead)
async def get_operation(
    operation_id: uuid.UUID,
    _: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> Operation:
    operation = await session.get(Operation, operation_id)
    if operation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Operation not found")
    return operation


@router.get("/operations/{operation_id}/events", response_model=list[OperationEventRead])
async def get_events(
    operation_id: uuid.UUID,
    _: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> list[OperationEvent]:
    if await session.get(Operation, operation_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Operation not found")
    query = (
        select(OperationEvent)
        .where(OperationEvent.operation_id == operation_id)
        .order_by(OperationEvent.created_at)
    )
    return list((await session.scalars(query)).all())


@router.get("/operations/{operation_id}/events/stream")
async def stream_events(
    operation_id: uuid.UUID,
    _: User = Depends(current_user),
) -> StreamingResponse:
    async def generate() -> AsyncIterator[str]:
        seen: set[str] = set()
        terminal = {"succeeded", "failed", "canceled", "unknown"}
        while True:
            async with SessionLocal() as session:
                operation = await session.get(Operation, operation_id)
                if operation is None:
                    yield 'event: error\ndata: {"detail":"operation not found"}\n\n'
                    return
                events = list(
                    (
                        await session.scalars(
                            select(OperationEvent)
                            .where(OperationEvent.operation_id == operation_id)
                            .order_by(OperationEvent.created_at)
                        )
                    ).all()
                )
                for event in events:
                    key = str(event.id)
                    if key in seen:
                        continue
                    seen.add(key)
                    data = OperationEventRead.model_validate(event).model_dump(mode="json")
                    yield f"event: {event.event}\ndata: {json.dumps(data)}\n\n"
                if operation.status in terminal:
                    yield f"event: complete\ndata: {json.dumps({'status': operation.status})}\n\n"
                    return
            await asyncio.sleep(1)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/operations/{operation_id}/cancel", response_model=OperationRead)
async def cancel_operation(
    operation_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> Operation:
    operation = await session.get(Operation, operation_id)
    if operation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Operation not found")
    if operation.status != "queued":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Only queued controller operations can be canceled; use tasks.stop for a remote task",
        )
    operation.status = "canceled"
    operation.finished_at = datetime.now(UTC)
    session.add(
        AuditEvent(
            user_id=user.id,
            server_id=operation.server_id,
            action="operation.cancel",
            outcome="succeeded",
            data={"operation_id": str(operation.id)},
        )
    )
    await session.commit()
    await session.refresh(operation)
    return operation
