from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from app.db import SessionLocal, engine
from app.main import app
from app.models import Base, Server, ServerProbe, User
from app.security import SecretBox, hash_password
from app.ssh import SSHClient, SSHError


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


async def test_update_username(api_client) -> None:
    client, _ = api_client
    headers = await authenticate(client)

    me = await client.get("/api/v1/users/me", headers=headers)
    user_id = me.json()["id"]

    response = await client.patch(
        f"/api/v1/users/{user_id}",
        headers=headers,
        json={"username": "newadmin", "current_password": "very-long-test-password"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["username"] == "newadmin"


async def test_update_username_wrong_password(api_client) -> None:
    client, _ = api_client
    headers = await authenticate(client)

    me = await client.get("/api/v1/users/me", headers=headers)
    user_id = me.json()["id"]

    response = await client.patch(
        f"/api/v1/users/{user_id}",
        headers=headers,
        json={"username": "newadmin", "current_password": "wrong-password-123"},
    )
    assert response.status_code == 401


async def test_update_username_unique_conflict(api_client) -> None:
    client, _ = api_client
    headers = await authenticate(client)

    await client.post(
        "/api/v1/users",
        headers=headers,
        json={"username": "existing", "password": "very-long-password-123"},
    )

    me = await client.get("/api/v1/users/me", headers=headers)
    user_id = me.json()["id"]

    response = await client.patch(
        f"/api/v1/users/{user_id}",
        headers=headers,
        json={"username": "existing", "current_password": "very-long-test-password"},
    )
    assert response.status_code == 409


async def test_change_password(api_client) -> None:
    client, _ = api_client
    headers = await authenticate(client)

    me = await client.get("/api/v1/users/me", headers=headers)
    user_id = me.json()["id"]

    response = await client.post(
        f"/api/v1/users/{user_id}/password",
        headers=headers,
        json={
            "current_password": "very-long-test-password",
            "new_password": "brand-new-password-123",
            "confirm_password": "brand-new-password-123",
        },
    )
    assert response.status_code == 204

    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "brand-new-password-123"},
    )
    assert login.status_code == 200


async def test_change_password_mismatch(api_client) -> None:
    client, _ = api_client
    headers = await authenticate(client)

    me = await client.get("/api/v1/users/me", headers=headers)
    user_id = me.json()["id"]

    response = await client.post(
        f"/api/v1/users/{user_id}/password",
        headers=headers,
        json={
            "current_password": "very-long-test-password",
            "new_password": "brand-new-password-123",
            "confirm_password": "different-password-123",
        },
    )
    assert response.status_code == 400


async def test_change_password_wrong_current(api_client) -> None:
    client, _ = api_client
    headers = await authenticate(client)

    me = await client.get("/api/v1/users/me", headers=headers)
    user_id = me.json()["id"]

    response = await client.post(
        f"/api/v1/users/{user_id}/password",
        headers=headers,
        json={
            "current_password": "wrong-current-password-123",
            "new_password": "brand-new-password-123",
            "confirm_password": "brand-new-password-123",
        },
    )
    assert response.status_code == 401


async def test_delete_server(api_client) -> None:
    client, server_id = api_client
    headers = await authenticate(client)

    delete_resp = await client.delete(f"/api/v1/servers/{server_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/servers/{server_id}/capabilities", headers=headers)
    assert get_resp.status_code == 404


async def test_create_server_password_bootstraps_key(api_client, monkeypatch: Any) -> None:
    client, _ = api_client
    headers = await authenticate(client)

    me = await client.get("/api/v1/users/me", headers=headers)
    user_id = uuid.UUID(me.json()["id"])

    probe_id = uuid.uuid4()
    async with SessionLocal() as session:
        probe = ServerProbe(
            id=probe_id,
            address="192.168.1.100",
            port=22,
            host_key="ssh-ed25519 AAAAC3TEST",
            fingerprint="SHA256:testfingerprint",
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
            created_by=user_id,
        )
        session.add(probe)
        await session.commit()

    installed_keys: list[str] = []

    async def mock_install_authorized_key(self, public_key: str, connection=None):
        installed_keys.append(public_key)

    async def mock_discovery(self):
        return {"compatible": True, "actions": {}}

    monkeypatch.setattr(SSHClient, "install_authorized_key", mock_install_authorized_key)
    monkeypatch.setattr(SSHClient, "discovery", mock_discovery)

    response = await client.post(
        "/api/v1/servers",
        headers=headers,
        json={
            "name": "new-server",
            "probe_id": str(probe_id),
            "confirmed_fingerprint": "SHA256:testfingerprint",
            "username": "root",
            "credential": {
                "type": "password",
                "password": "initial-secret-password",
            },
        },
    )
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["name"] == "new-server"
    assert created["credential_type"] == "private_key"
    assert len(installed_keys) == 1
    assert "admin-bitrixvm-new-server" in installed_keys[0]

    async with SessionLocal() as session:
        server = await session.get(Server, uuid.UUID(created["id"]))
        assert server is not None
        assert server.credential_type == "private_key"
        creds = SecretBox.configured().decrypt_json(server.credentials_encrypted)
        assert "private_key" in creds
        assert "password" not in creds


async def test_update_server_name(api_client) -> None:
    client, server_id = api_client
    headers = await authenticate(client)

    response = await client.patch(
        f"/api/v1/servers/{server_id}",
        headers=headers,
        json={"name": "renamed-sandbox"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "renamed-sandbox"

    async with SessionLocal() as session:
        server = await session.get(Server, server_id)
        assert server is not None
        assert server.name == "renamed-sandbox"


async def test_update_server_address_and_port(api_client, monkeypatch: Any) -> None:
    client, server_id = api_client
    headers = await authenticate(client)

    probed: list[tuple[str, int]] = []

    async def mock_probe_host_key(address: str, port: int, timeout: float = 10):
        probed.append((address, port))
        return "ssh-ed25519 AAAANEWKEY", "SHA256:newfingerprint", "ssh-ed25519"

    async def mock_discovery(self):
        return {"compatible": True, "actions": {}}

    monkeypatch.setattr("app.api.servers.probe_host_key", mock_probe_host_key)
    monkeypatch.setattr(SSHClient, "discovery", mock_discovery)

    response = await client.patch(
        f"/api/v1/servers/{server_id}",
        headers=headers,
        json={"address": "192.168.0.99", "port": 2222},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["address"] == "192.168.0.99"
    assert data["port"] == 2222
    assert probed == [("192.168.0.99", 2222)]

    async with SessionLocal() as session:
        server = await session.get(Server, server_id)
        assert server is not None
        assert server.address == "192.168.0.99"
        assert server.port == 2222
        assert server.host_key == "ssh-ed25519 AAAANEWKEY"


async def test_update_server_address_unreachable(api_client, monkeypatch: Any) -> None:
    client, server_id = api_client
    headers = await authenticate(client)

    async def mock_probe_host_key_fail(address: str, port: int, timeout: float = 10):
        raise SSHError("Connection timed out")

    monkeypatch.setattr("app.api.servers.probe_host_key", mock_probe_host_key_fail)

    response = await client.patch(
        f"/api/v1/servers/{server_id}",
        headers=headers,
        json={"address": "192.168.0.250"},
    )
    assert response.status_code == 502, response.text

    # Old address should remain intact in DB
    async with SessionLocal() as session:
        server = await session.get(Server, server_id)
        assert server is not None
        assert server.address == "192.168.0.56"


