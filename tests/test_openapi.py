from __future__ import annotations

from app.main import app


def test_openapi_contains_security_and_operation_flow() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/servers/probes" in paths
    assert "/api/v1/servers/{server_id}/actions/{action}/preview" in paths
    assert "/api/v1/servers/{server_id}/actions/{action}" in paths
    assert "/api/v1/operations/{operation_id}/events/stream" in paths
    assert "OAuth2PasswordBearer" in schema["components"]["securitySchemes"]
    assert "summary" in schema["components"]["schemas"]["CapabilityRead"]["required"]
