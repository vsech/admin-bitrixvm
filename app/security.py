from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher

try:
    from argon2.exceptions import InvalidHashError, VerifyMismatchError
except ImportError:
    from argon2.exceptions import InvalidHash as InvalidHashError
    from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import Settings, get_settings

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hasher.verify(encoded, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


class SecretBox:
    def __init__(self, key_material: bytes):
        self._cipher = AESGCM(hashlib.sha256(key_material).digest())

    @classmethod
    def configured(cls) -> SecretBox:
        return cls(get_settings().master_key_bytes)

    def encrypt_json(self, value: dict[str, Any]) -> bytes:
        nonce = os.urandom(12)
        raw = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode()
        return nonce + self._cipher.encrypt(nonce, raw, b"bitrixvm-controller-v1")

    def decrypt_json(self, value: bytes) -> dict[str, Any]:
        nonce, encrypted = value[:12], value[12:]
        raw = self._cipher.decrypt(nonce, encrypted, b"bitrixvm-controller-v1")
        decoded = json.loads(raw)
        if not isinstance(decoded, dict):
            raise ValueError("encrypted payload is not an object")
        return decoded


def create_access_token(user_id: uuid.UUID, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, settings.jwt_secret_bytes, algorithm="HS256")


def create_refresh_token(
    user_id: uuid.UUID, settings: Settings | None = None
) -> tuple[str, datetime]:
    settings = settings or get_settings()
    now = datetime.now(UTC)
    expires = now + timedelta(days=settings.refresh_token_days)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": now,
        "exp": expires,
        "jti": secrets.token_hex(32),
    }
    return jwt.encode(payload, settings.jwt_secret_bytes, algorithm="HS256"), expires


def decode_token(token: str, expected_type: str, settings: Settings | None = None) -> uuid.UUID:
    settings = settings or get_settings()
    payload = jwt.decode(token, settings.jwt_secret_bytes, algorithms=["HS256"])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("unexpected token type")
    return uuid.UUID(str(payload["sub"]))


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def opaque_token() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()
