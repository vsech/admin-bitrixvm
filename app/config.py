from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BITRIXVM_", env_file=".env", extra="ignore", case_sensitive=False
    )

    app_name: str = "BitrixVM Controller"
    environment: str = "production"
    database_url: str = "postgresql+asyncpg://bitrixvm:bitrixvm@localhost:5432/bitrixvm"
    database_password_file: Path | None = None
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    confirmation_minutes: int = 5
    ssh_connect_timeout: float = 10
    ssh_command_timeout: float = 120
    worker_poll_seconds: float = 1
    output_limit_bytes: int = 1_000_000
    master_key: SecretStr | None = None
    master_key_file: Path | None = None
    jwt_secret: SecretStr | None = None
    jwt_secret_file: Path | None = None
    cors_origins: list[str] = Field(default_factory=list)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        if value not in {"development", "test", "production"}:
            raise ValueError("environment must be development, test, or production")
        return value

    def secret_bytes(self, direct: SecretStr | None, path: Path | None, name: str) -> bytes:
        if direct is not None:
            value = direct.get_secret_value().strip()
        elif path is not None and path.is_file():
            value = path.read_text(encoding="utf-8").strip()
        else:
            raise RuntimeError(f"{name} is not configured")
        if len(value) < 32:
            raise RuntimeError(f"{name} must contain at least 32 characters")
        return value.encode()

    @property
    def master_key_bytes(self) -> bytes:
        return self.secret_bytes(self.master_key, self.master_key_file, "master key")

    @property
    def jwt_secret_bytes(self) -> bytes:
        return self.secret_bytes(self.jwt_secret, self.jwt_secret_file, "JWT secret")

    @property
    def resolved_database_url(self) -> str:
        if "{PASSWORD}" not in self.database_url:
            return self.database_url
        if self.database_password_file is None or not self.database_password_file.is_file():
            raise RuntimeError("database password file is not configured")
        password = self.database_password_file.read_text(encoding="utf-8").strip()
        if not password:
            raise RuntimeError("database password file is empty")
        return self.database_url.replace("{PASSWORD}", quote_plus(password))


@lru_cache
def get_settings() -> Settings:
    return Settings()
