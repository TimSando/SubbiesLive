"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from environment variables or .env file."""

    # Environment
    environment: str = "development"

    # Database
    database_url: str = "postgresql+asyncpg://subbiesstats:subbiesstats_dev_2026@db:5432/subbiesstats"

    # App metadata
    app_name: str = "SubbiesStats API"
    app_version: str = "0.1.0"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
