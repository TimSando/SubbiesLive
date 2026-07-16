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
    current_season_year: int = 2026

    # Ingestion Schedule
    ingestion_interval_minutes: int = 15

    # Cookie security
    cookie_secure: Optional[bool] = None

    # PWA Web Push
    vapid_public_key: str
    vapid_private_key: str
    vapid_mailto: str

    # Google Maps API Key
    google_maps_api_key: Optional[str] = None

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
