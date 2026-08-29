from __future__ import annotations

import uuid

import httpx
import pytest

from app.db import SessionLocal, engine
from app.main import app
from app.models import Base, Server, User
from app.security import SecretBox, hash_password


@pytest.fixture
async def api_client():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        user = User(username="admin", password_hash=hash_password("very-long-test-password"))
        server = Server(
            name="sandbox",
            address="192.168.0.56",
            port=22,
            username="root",
            credential_type="password",
            credentials_encrypted=SecretBox.configured().encrypt_json({"password": "not-used"}),
            host_key="ssh-rsa AAAATEST",
            host_key_fingerprint="SHA256:test",
            capabilities={
                "compatible": True,
                "pool": {
                    "exit_status": 0,
                    "data": {
                        "params": {
                            "bx02.example.test": {"hostname": "bx02.example.test"},
                            "bxcv.ru": {"hostname": "bxcv.ru"},
                        }
                    },
                },
                "actions": {
                    "host.reboot": {"available": True, "reason": None},
                    "memcached.update": {"available": True, "reason": None},
                },
            },
        )
        session.add_all((user, server))
        await session.commit()
        await session.refresh(server)
        server_id = server.id
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)
    async with httpx.AsyncClient(transport=transport, base_url="https://test") as client:
        yield client, server_id
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


async def authenticate(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "very-long-test-password"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_login_capabilities_preview_and_idempotent_enqueue(api_client) -> None:
    client, server_id = api_client
    headers = await authenticate(client)

    capabilities = await client.get(f"/api/v1/servers/{server_id}/capabilities", headers=headers)
    assert capabilities.status_code == 200
    assert len(capabilities.json()) == 83
    by_action = {item["action"]: item for item in capabilities.json()}
    assert by_action["host.reboot"]["request_schema"]["properties"]["host"][
        "x-options"
    ] == ["bx02.example.test", "bxcv.ru"]
    assert "x-options" not in by_action["host.rename"]["request_schema"]["properties"][
        "hostname"
    ]
    assert "x-options" not in by_action["local.hostname"]["request_schema"]["properties"][
        "hostname"
    ]

    missing_confirmation = await client.post(
        f"/api/v1/servers/{server_id}/actions/host.reboot",
        headers={**headers, "Idempotency-Key": "reboot-test-1"},
        json={"parameters": {"host": "bxcv.ru"}},
    )
    assert missing_confirmation.status_code == 409

    preview = await client.post(
        f"/api/v1/servers/{server_id}/actions/host.reboot/preview",
        headers=headers,
        json={"parameters": {"host": "bxcv.ru"}},
    )
    assert preview.status_code == 200, preview.text
    token = preview.json()["confirmation_token"]

    request = {
        "parameters": {"host": "bxcv.ru"},
        "confirmation_token": token,
    }
    first = await client.post(
        f"/api/v1/servers/{server_id}/actions/host.reboot",
        headers={**headers, "Idempotency-Key": "reboot-test-1"},
        json=request,
    )
    assert first.status_code == 202, first.text
    assert first.json()["status"] == "queued"
    assert first.json()["args_redacted"] == {"host": "bxcv.ru"}

    repeated = await client.post(
        f"/api/v1/servers/{server_id}/actions/host.reboot",
        headers={**headers, "Idempotency-Key": "reboot-test-1"},
        json=request,
    )
    assert repeated.status_code == 202
    assert repeated.json()["id"] == first.json()["id"]


async def test_low_risk_operation_does_not_need_preview(api_client) -> None:
    client, server_id = api_client
    headers = await authenticate(client)
    response = await client.post(
        f"/api/v1/servers/{server_id}/actions/memcached.update",
        headers={**headers, "Idempotency-Key": uuid.uuid4().hex},
        json={"parameters": {}},
    )
    assert response.status_code == 202, response.text
