from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(min_length=1)
    webhook_mode: bool = False
    webhook_secret: str = ""
    webhook_base_url: str = ""
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    database_url: str = "postgresql+asyncpg://avela:avela@localhost:5432/avela"
    jwt_secret: str = Field(min_length=32, default="dev-only-secret-change-me-0123456789")
    jwt_ttl_seconds: int = 7 * 24 * 3600

    # Worker напоминаний
    notifier_interval_seconds: int = 30

    # Публичный адрес Mini App — для кнопки «Приложение» в боте
    mini_app_url: str = ""

    # Строгий CORS: разрешённые frontend-домены через запятую.
    cors_origins: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def _validate_webhook(self) -> "Settings":
        if self.webhook_mode:
            if not self.webhook_secret:
                raise ValueError("WEBHOOK_MODE=true требует WEBHOOK_SECRET")
            if not self.webhook_base_url:
                raise ValueError("WEBHOOK_MODE=true требует WEBHOOK_BASE_URL")
        return self


def get_settings(**_overrides: Any) -> Settings:
    return Settings(**_overrides)
