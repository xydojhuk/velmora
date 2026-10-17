from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "/run/velmora/config/runtime.env"), env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Velmora API"
    environment: Literal["development", "production", "test"] = "development"
    api_prefix: str = "/api/v1"

    database_url: str = ""
    database_host: str = "127.0.0.1"
    database_port: int = Field(default=5432, ge=1, le=65535)
    database_user: str = "velmora"
    database_name: str = "velmora"
    database_password: str = ""
    database_password_file: str = ""
    database_sslmode: Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"] = "prefer"

    jwt_secret: str = ""
    jwt_secret_file: str = ""
    jwt_issuer: str = "velmora-api"
    jwt_audience: str = "velmora-admin"
    access_token_minutes: int = Field(default=15, ge=5, le=60)
    refresh_token_days: int = Field(default=14, ge=1, le=60)

    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_access_name: str = "velmora_access"
    cookie_refresh_name: str = "velmora_refresh"
    cookie_csrf_name: str = "velmora_csrf"

    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    allowed_hosts: list[str] = ["127.0.0.1", "localhost"]
    trust_proxy_headers: bool = False
    https_only: bool = False
    docs_enabled: bool = True

    max_request_body_bytes: int = Field(default=10_485_760, ge=65_536, le=16_777_216)
    media_root: str = "./media"
    media_url_prefix: str = "/media"
    product_image_max_bytes: int = Field(default=8_388_608, ge=262_144, le=10_485_760)
    product_image_max_pixels: int = Field(default=24_000_000, ge=1_000_000, le=48_000_000)
    product_image_max_count: int = Field(default=4, ge=1, le=8)
    product_image_webp_quality: int = Field(default=88, ge=70, le=95)
    icon_svg_max_bytes: int = Field(default=131_072, ge=16_384, le=524_288)
    icon_svg_max_elements: int = Field(default=300, ge=20, le=1000)
    icon_max_count: int = Field(default=200, ge=10, le=1000)

    login_max_failures_per_account: int = Field(default=5, ge=3, le=20)
    login_lock_minutes: int = Field(default=15, ge=1, le=120)
    login_ip_limit: int = Field(default=20, ge=5, le=200)
    login_ip_window_minutes: int = Field(default=15, ge=1, le=120)
    order_ip_limit: int = Field(default=8, ge=1, le=100)
    order_ip_window_minutes: int = Field(default=10, ge=1, le=120)
    visit_ip_limit: int = Field(default=60, ge=10, le=1000)
    visit_ip_window_minutes: int = Field(default=1, ge=1, le=60)

    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_password_file: str = ""
    smtp_from_email: str = ""
    smtp_starttls: bool = True
    telegram_bot_token: str = ""
    telegram_bot_token_file: str = ""

    @staticmethod
    def _read_secret(path: str) -> str:
        if not path:
            return ""
        try:
            return Path(path).read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ValueError(f"Could not read secret file: {path}") from exc

    @field_validator("cors_origins", "allowed_hosts")
    @classmethod
    def no_wildcards(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("Wildcard values are not allowed")
        return value

    @model_validator(mode="after")
    def resolve_secrets_and_database(self):
        if not self.jwt_secret and self.jwt_secret_file:
            self.jwt_secret = self._read_secret(self.jwt_secret_file)
        if not self.smtp_password and self.smtp_password_file:
            self.smtp_password = self._read_secret(self.smtp_password_file)
        if not self.telegram_bot_token and self.telegram_bot_token_file:
            self.telegram_bot_token = self._read_secret(self.telegram_bot_token_file)

        weak = {"change-me", "secret", "password", "your-secret-here"}
        if len(self.jwt_secret) < 64 or self.jwt_secret.lower().strip() in weak or len(set(self.jwt_secret)) < 12:
            raise ValueError("JWT_SECRET is missing or too weak")

        if not self.database_url:
            password = self.database_password or self._read_secret(self.database_password_file)
            if not password:
                raise ValueError("PostgreSQL password is not configured")
            user = quote(self.database_user, safe="")
            encoded_password = quote(password, safe="")
            database = quote(self.database_name, safe="")
            self.database_url = (
                f"postgresql+psycopg://{user}:{encoded_password}@"
                f"{self.database_host}:{self.database_port}/{database}?sslmode={self.database_sslmode}"
            )

        if self.is_production:
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production")
            if self.docs_enabled:
                raise ValueError("DOCS_ENABLED must be false in production")
            if self.cookie_samesite == "none" and not self.cookie_secure:
                raise ValueError("SameSite=None requires a Secure cookie")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
