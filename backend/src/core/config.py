"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from environment variables or .env file."""

    # Environment
    environment: str = "development"

    # Database
    database_url: str = (
        "postgresql+asyncpg://subbiesstats:subbiesstats_dev_2026@db:5432/subbiesstats"
    )
    database_url_sync: Optional[str] = None

    # App metadata
    app_name: str = "Subbies Live API"
    app_version: str = "0.1.0"

    # Ingestion Schedule
    ingestion_interval_minutes: int = 15

    # Cookie security
    cookie_secure: Optional[bool] = None

    # PWA Web Push
    vapid_public_key: str = "BI3OQJIP5CTGATc4ZKjIqce2uNgOIrjlHRrSmZRx4u5HY3ZJU_-QSt8Yq90ub3geXpVoDbO8dQDDaQeFyHXjkuE"
    vapid_private_key: str = "wiruot1guHaDvKd231NgPetRYI5x-jRuTKt-VFxLhKI"
    vapid_mailto: str = "mailto:admin@subbieslive.calypsolab.xyz"

    @model_validator(mode="after")
    def derive_sync_url(self) -> "Settings":
        if not self.database_url_sync:
            self.database_url_sync = self.database_url.replace("+asyncpg", "")
        if self.cookie_secure is None:
            self.cookie_secure = self.environment != "development"
        return self

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
