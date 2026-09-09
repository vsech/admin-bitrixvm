from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.db import SessionLocal, engine
from app.main import app
from app.models import Base, Server, User
from app.security import SecretBox, hash_password
from app.ssh import (
    CommandResult,
    SSHClient,
    is_active_log_file,
    validate_log_file_path,
)


def make_test_server() -> Server:
    return Server(
        name="test-server",
        address="192.0.2.10",
        port=22,
        username="root",
        credential_type="password",
        credentials_encrypted=SecretBox.configured().encrypt_json({"password": "not-used"}),
        host_key="ssh-rsa AAAATEST",
        host_key_fingerprint="SHA256:test",
        capabilities={"compatible": True},
    )


def test_validate_log_file_path():
    assert validate_log_file_path("/var/log/nginx/access.log") == "/var/log/nginx/access.log"
    assert validate_log_file_path("/opt/webdir/logs/wrapper.log") == "/opt/webdir/logs/wrapper.log"
    assert validate_log_file_path("/home/bitrix/www/index.php") == "/home/bitrix/www/index.php"

    with pytest.raises(ValueError, match="must be an absolute path"):
        validate_log_file_path("var/log/nginx/access.log")

    with pytest.raises(ValueError, match="Access denied"):
        validate_log_file_path("/etc/shadow")

    with pytest.raises(ValueError, match="sensitive file path"):
        validate_log_file_path("/var/log/something_id_rsa")

    with pytest.raises(ValueError, match="Access denied"):
        validate_log_file_path("/var/log/../../etc/passwd")


def test_is_active_log_file():
    assert is_active_log_file("/var/log/nginx/access.log") is True
    assert is_active_log_file("/var/log/httpd/error_log") is True
    assert is_active_log_file("/var/log/push-server/error.log") is True
    assert is_active_log_file("/opt/webdir/logs/wrapper.log") is True

    # Rotated or compressed
    assert is_active_log_file("/var/log/nginx/access.log-20260909") is False
    assert is_active_log_file("/var/log/nginx/access.log-20260901.gz") is False
    assert is_active_log_file("/var/log/redis/redis.log-20260705.gz") is False
    assert is_active_log_file("/opt/webdir/logs/bvat.log.1784093122") is False
    assert is_active_log_file("/var/log/dnf.log.1") is False


@pytest.mark.asyncio
async def test_ssh_client_read_journal_logs_success():
    server = make_test_server()
    client = SSHClient(server)
    mock_conn = AsyncMock()

    with patch.object(client, "run_argv", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = CommandResult(exit_status=0, stdout="line 1\nline 2\n", stderr="")
        lines, source = await client._read_journal_logs(
            mock_conn, "nginx", "2026-09-08 00:00:00", "2026-09-09 00:00:00", 100, grep="test"
        )
        assert lines == ["line 1", "line 2"]
        assert source == "journal"
        call_argv = mock_run.call_args[0][1]
        assert "-u" in call_argv and "nginx" in call_argv
        assert "-g" in call_argv and "test" in call_argv


@pytest.mark.asyncio
async def test_ssh_client_read_journal_logs_no_entries():
    server = make_test_server()
    client = SSHClient(server)
    mock_conn = AsyncMock()

    with patch.object(client, "run_argv", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = CommandResult(exit_status=1, stdout="-- No entries --\n", stderr="")
        lines, source = await client._read_journal_logs(
            mock_conn, "nginx", "2026-09-08 00:00:00", "2026-09-09 00:00:00", 100
        )
        assert lines == []
        assert source == "journal"


@pytest.mark.asyncio
async def test_ssh_client_read_journal_logs_system():
    server = make_test_server()
    client = SSHClient(server)
    mock_conn = AsyncMock()

    with patch.object(client, "run_argv", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = CommandResult(exit_status=0, stdout="kernel log\n", stderr="")
        lines, source = await client._read_journal_logs(
            mock_conn, "_system", "2026-09-08 00:00:00", "2026-09-09 00:00:00", 100
        )
        assert lines == ["kernel log"]
        call_argv = mock_run.call_args[0][1]
        assert "-u" not in call_argv


@pytest.mark.asyncio
async def test_ssh_client_read_file_logs_tail():
    server = make_test_server()
    client = SSHClient(server)
    mock_conn = AsyncMock()

    with patch.object(client, "run_argv", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = [
            CommandResult(exit_status=0, stdout="", stderr=""),
            CommandResult(exit_status=0, stdout="line a\nline b\n", stderr=""),
        ]
        lines, source = await client._read_file_logs(
            mock_conn, "/var/log/httpd/error_log", "from", "to", 100, grep=None
        )
        assert lines == ["line a", "line b"]
        assert source == "file"


@pytest.mark.asyncio
async def test_ssh_client_read_file_logs_grep_empty():
    server = make_test_server()
    client = SSHClient(server)
    mock_conn = AsyncMock()

    with patch.object(client, "run_argv", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = [
            CommandResult(exit_status=0, stdout="", stderr=""),
            CommandResult(exit_status=1, stdout="", stderr=""),
        ]
        lines, source = await client._read_file_logs(
            mock_conn, "/var/log/httpd/error_log", "from", "to", 100, grep="pattern"
        )
        assert lines == []
        assert source == "file"


@pytest.mark.asyncio
async def test_ssh_client_discover_log_services():
    server = make_test_server()
    client = SSHClient(server)
    mock_conn = AsyncMock()

    fake_output = (
        "/var/log/nginx/access.log\n"
        "/var/log/nginx/access.log-20260909.gz\n"
        "/var/log/nginx/test_site_access.log\n"
        "/var/log/httpd/error_log\n"
        "/var/log/httpd/test_site_error_log\n"
        "/opt/webdir/logs/wrapper.log\n"
        "/opt/webdir/logs/bvat.log.1234567\n"
        "---SERVICES---\n"
        "active\n"
        "active\n"
        "active\n"
        "active\n"
        "active\n"
        "active\n"
        "active\n"
        "active\n"
        "inactive\n"
    )
    mock_res = AsyncMock()
    mock_res.stdout = fake_output
    mock_conn.run = AsyncMock(return_value=mock_res)

    with patch.object(client, "connect") as mock_connect:
        mock_connect.return_value.__aenter__.return_value = mock_conn
        services = await client.discover_log_services()

        nginx = next(s for s in services if s["id"] == "nginx")
        assert nginx["active"] is True
        assert "/var/log/nginx/access.log" in nginx["files"]
        assert "/var/log/nginx/test_site_access.log" in nginx["files"]
        assert "/var/log/nginx/access.log-20260909.gz" not in nginx["files"]

        httpd = next(s for s in services if s["id"] == "httpd")
        assert httpd["active"] is True
        assert "/var/log/httpd/test_site_error_log" in httpd["files"]

        php = next(s for s in services if s["id"] == "php-fpm")
        assert php["active"] is False


@pytest.fixture
async def api_client():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        user = User(username="admin", password_hash=hash_password("very-long-test-password"))
        server = make_test_server()
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
    return {"Authorization": f"Bearer {response.json()["access_token"]}"}


async def test_get_log_services_catalog(api_client):
    client, server_id = api_client
    headers = await authenticate(client)

    response = await client.get("/api/v1/servers/log-services", headers=headers)
    assert response.status_code == 200
    services = response.json()
    service_ids = {s["id"] for s in services}
    assert {"nginx", "httpd", "bitrix-manager", "push-server", "mysql", "redis", "cron", "bvat", "system", "custom"}.issubset(service_ids)

    httpd = next(s for s in services if s["id"] == "httpd")
    assert "/var/log/httpd/error_log" in httpd["files"]
    assert httpd["journal_unit"] == "httpd"


async def test_get_server_specific_log_services(api_client):
    client, server_id = api_client
    headers = await authenticate(client)

    with patch("app.ssh.SSHClient.discover_log_services", new_callable=AsyncMock) as mock_disc:
        mock_disc.return_value = [
            {"id": "nginx", "name": "Nginx", "journal_unit": "nginx", "files": ["/var/log/nginx/test_site_error.log"], "active": True}
        ]
        response = await client.get(f"/api/v1/servers/{server_id}/log-services", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["files"] == ["/var/log/nginx/test_site_error.log"]
        assert data[0]["active"] is True


async def test_read_server_logs_file_mode(api_client):
    client, server_id = api_client
    headers = await authenticate(client)

    with patch("app.ssh.SSHClient.read_logs", new_callable=AsyncMock) as mock_read:
        mock_read.return_value = (["line 1", "line 2"], "file")
        response = await client.post(
            f"/api/v1/servers/{server_id}/logs",
            headers=headers,
            json={
                "service": "httpd",
                "source": "file",
                "file_path": "/var/log/httpd/error_log",
                "limit": 100,
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert result["lines"] == ["line 1", "line 2"]
        assert result["total"] == 2
        assert result["source_used"] == "file"


async def test_read_server_logs_alias_compatibility(api_client):
    client, server_id = api_client
    headers = await authenticate(client)

    with patch("app.ssh.SSHClient.read_logs", new_callable=AsyncMock) as mock_read:
        mock_read.return_value = (["wrapper log line"], "file")
        response = await client.post(
            f"/api/v1/servers/{server_id}/logs",
            headers=headers,
            json={
                "service": "bitrix-pool",
                "source": "file",
                "file_path": "/opt/webdir/logs/wrapper.log",
            },
        )
        assert response.status_code == 200
        assert response.json()["lines"] == ["wrapper log line"]


async def test_read_server_logs_rejects_path_traversal(api_client):
    client, server_id = api_client
    headers = await authenticate(client)

    response = await client.post(
        f"/api/v1/servers/{server_id}/logs",
        headers=headers,
        json={
            "service": "nginx",
            "source": "file",
            "file_path": "/etc/shadow",
        },
    )
    assert response.status_code == 422


async def test_get_service_statuses_parsing():
    client = object.__new__(SSHClient)

    mock_conn = MagicMock()
    mock_conn.run = AsyncMock(
        return_value=CommandResult(
            stdout=(
                "nginx:active\n"
                "httpd:active\n"
                "mysqld:active\n"
                "mariadb:inactive\n"
                "redis:inactive\n"
                "memcached:active\n"
                "push-server:active\n"
                "crond:active\n"
                "php-fpm:inactive\n"
                "bvat:active\n"
            ),
            stderr="",
            exit_status=0,
        )
    )

    statuses = await client.get_service_statuses(connection=mock_conn)
    assert statuses["nginx"] == "active"
    assert statuses["httpd"] == "active"
    assert statuses["mysql"] == "active"
    assert statuses["memcached"] == "active"
    assert statuses["redis"] == "inactive"
    assert statuses["push_server"] == "active"
    assert statuses["cron"] == "active"
    assert statuses["php_fpm"] == "inactive"


async def test_server_services_status_api(api_client):
    client, server_id = api_client
    headers = await authenticate(client)

    with patch("app.ssh.SSHClient.get_service_statuses", new_callable=AsyncMock) as mock_statuses:
        mock_statuses.return_value = {
            "nginx": "active",
            "httpd": "active",
            "mysql": "active",
            "php_fpm": "inactive",
            "memcached": "active",
            "redis": "inactive",
            "push_server": "active",
            "cron": "active",
            "bvat": "active",
        }
        response = await client.get(
            f"/api/v1/servers/{server_id}/services-status",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nginx"] == "active"
        assert data["mysql"] == "active"
        assert data["httpd"] == "active"
        assert data["cron"] == "active"

