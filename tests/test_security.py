from __future__ import annotations

import uuid

import jwt
import pytest
from cryptography.exceptions import InvalidTag

from app.config import Settings
from app.security import (
    SecretBox,
    create_access_token,
    decode_token,
    hash_password,
    stable_hash,
    verify_password,
)


def test_password_hashing() -> None:
    encoded = hash_password("a sufficiently long password")
    assert "a sufficiently long password" not in encoded
    assert verify_password("a sufficiently long password", encoded)
    assert not verify_password("wrong", encoded)


def test_secret_box_round_trip_and_tamper_detection() -> None:
    box = SecretBox(b"master key material which is definitely long enough")
    encrypted = box.encrypt_json({"password": "secret", "private_key": "key"})
    assert b"secret" not in encrypted
    assert box.decrypt_json(encrypted) == {"password": "secret", "private_key": "key"}
    tampered = encrypted[:-1] + bytes([encrypted[-1] ^ 1])
    with pytest.raises(InvalidTag):
        box.decrypt_json(tampered)


def test_access_token_type_is_enforced() -> None:
    settings = Settings(
        environment="test",
        jwt_secret="jwt secret material which is definitely long enough",
        master_key="master key material which is definitely long enough",
    )
    user_id = uuid.uuid4()
    token = create_access_token(user_id, settings)
    assert decode_token(token, "access", settings) == user_id
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(token, "refresh", settings)


def test_stable_hash_is_order_independent() -> None:
    assert stable_hash({"a": 1, "b": 2}) == stable_hash({"b": 2, "a": 1})
