from __future__ import annotations

from datetime import UTC, datetime

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies import current_user
from app.models import RefreshSession, User, as_utc
from app.schemas import RefreshRequest, TokenPair, UserCreate, UserRead
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    token_hash,
    verify_password,
)

router = APIRouter(prefix="/api/v1", tags=["authentication"])


async def issue_pair(session: AsyncSession, user: User) -> TokenPair:
    access = create_access_token(user.id)
    refresh, expires = create_refresh_token(user.id)
    session.add(RefreshSession(user_id=user.id, token_hash=token_hash(refresh), expires_at=expires))
    await session.commit()
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/auth/login", response_model=TokenPair)
async def login(
    form: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_db)
) -> TokenPair:
    user = await session.scalar(select(User).where(User.username == form.username))
    if user is None or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    return await issue_pair(session, user)


@router.post("/auth/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, session: AsyncSession = Depends(get_db)) -> TokenPair:
    raw = payload.refresh_token.get_secret_value()
    try:
        user_id = decode_token(raw, "refresh")
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token") from None
    record = await session.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == token_hash(raw))
    )
    now = datetime.now(UTC)
    if record is None or record.revoked_at is not None or as_utc(record.expires_at) <= now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token is expired or revoked")
    record.revoked_at = now
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User is disabled")
    return await issue_pair(session, user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshRequest,
    _: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    record = await session.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == token_hash(payload.refresh_token.get_secret_value())
        )
    )
    if record is not None and record.revoked_at is None:
        record.revoked_at = datetime.now(UTC)
        await session.commit()


@router.get("/users/me", response_model=UserRead)
async def me(user: User = Depends(current_user)) -> User:
    return user


@router.get("/users", response_model=list[UserRead])
async def list_users(
    _: User = Depends(current_user), session: AsyncSession = Depends(get_db)
) -> list[User]:
    return list((await session.scalars(select(User).order_by(User.username))).all())


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    _: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> User:
    if await session.scalar(
        select(func.count()).select_from(User).where(User.username == payload.username)
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already exists")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password.get_secret_value()),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disable_user(
    user_id: str,
    actor: User = Depends(current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == actor.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "An administrator cannot disable itself")
    user.is_active = False
    await session.commit()
