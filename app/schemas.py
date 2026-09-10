from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenPair(ApiModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class RefreshRequest(ApiModel):
    refresh_token: SecretStr


class UserCreate(ApiModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: SecretStr = Field(min_length=12, max_length=256)


class UserRead(ApiModel):
    id: uuid.UUID
    username: str
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.\-]+$")
    current_password: SecretStr = Field(min_length=12, max_length=256)


class ChangePassword(BaseModel):
    current_password: SecretStr = Field(min_length=12, max_length=256)
    new_password: SecretStr = Field(min_length=12, max_length=256)
    confirm_password: SecretStr = Field(min_length=12, max_length=256)


class ProbeCreate(ApiModel):
    address: str = Field(min_length=1, max_length=255)
    port: int = Field(default=22, ge=1, le=65535)


class ProbeRead(ApiModel):
    id: uuid.UUID
    address: str
    port: int
    fingerprint: str
    host_key_algorithm: str
    expires_at: datetime


class Credential(ApiModel):
    type: Literal["password", "private_key"]
    password: SecretStr | None = None
    private_key: SecretStr | None = None
    passphrase: SecretStr | None = None

    @field_validator("passphrase")
    @classmethod
    def passphrase_length(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value()) > 1024:
            raise ValueError("passphrase is too long")
        return value

    def material(self) -> dict[str, str]:
        if self.type == "password":
            if self.password is None or not self.password.get_secret_value():
                raise ValueError("password is required")
            return {"password": self.password.get_secret_value()}
        if self.private_key is None or not self.private_key.get_secret_value():
            raise ValueError("private_key is required")
        result = {"private_key": self.private_key.get_secret_value()}
        if self.passphrase is not None:
            result["passphrase"] = self.passphrase.get_secret_value()
        return result


class ServerCreate(ApiModel):
    name: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")
    probe_id: uuid.UUID
    confirmed_fingerprint: str = Field(min_length=8, max_length=255)
    username: Literal["root"] = "root"
    credential: Credential


class ServerUpdate(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")
    address: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    enabled: bool | None = None


class ServerRead(ApiModel):
    id: uuid.UUID
    name: str
    address: str
    port: int
    username: str
    credential_type: str
    host_key_fingerprint: str
    enabled: bool
    capabilities: dict[str, Any]
    capabilities_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CapabilityRead(ApiModel):
    action: str
    summary: str
    available: bool
    reason: str | None = None
    risk: str
    category: str
    request_schema: dict[str, Any]


class ActionRequest(ApiModel):
    parameters: dict[str, Any] = Field(default_factory=dict)
    confirmation_token: str | None = None


class PreviewRequest(ApiModel):
    parameters: dict[str, Any] = Field(default_factory=dict)


class PreviewRead(ApiModel):
    action: str
    risk: str
    summary: str
    warnings: list[str]
    normalized_parameters: dict[str, Any]
    confirmation_token: str
    expires_at: datetime


class OperationRead(ApiModel):
    id: uuid.UUID
    server_id: uuid.UUID
    user_id: uuid.UUID
    action: str
    category: str
    risk: str
    status: str
    args_redacted: dict[str, Any]
    idempotency_key: str
    remote_task_id: str | None
    result: dict[str, Any] | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    updated_at: datetime


class OperationEventRead(ApiModel):
    id: uuid.UUID
    operation_id: uuid.UUID
    level: str
    event: str
    message: str
    data: dict[str, Any]
    created_at: datetime


class Page(ApiModel):
    items: list[Any]
    total: int
    limit: int
    offset: int


class LogServiceInfo(ApiModel):
    id: str
    name: str
    journal_unit: str | None = None
    files: list[str] = Field(default_factory=list)
    active: bool | None = None


class LogRequest(ApiModel):
    service: str = Field(min_length=1, max_length=128)
    source: Literal["journal", "file"] = "journal"
    date_from: datetime | None = None
    date_to: datetime | None = None
    file_path: str | None = Field(default=None, max_length=1024)
    limit: int = Field(default=5000, ge=1, le=50000)
    grep: str | None = Field(default=None, max_length=512)


class LogResponse(ApiModel):
    lines: list[str]
    total: int
    truncated: bool
    source_used: str


class ProblemDetail(ApiModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    code: str
    request_id: str | None = None
