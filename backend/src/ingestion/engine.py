"""Synchronous SQLAlchemy engine factory for ingestion background thread."""

from sqlalchemy import create_engine
from src.core.config import get_settings


def get_sync_engine():
    """Create a synchronous SQLAlchemy engine for ingestion.

    Uses psycopg2 (not asyncpg) because ingestion runs in a background
    thread outside the async FastAPI event loop.
    """
    settings = get_settings()
    return create_engine(settings.database_url_sync, echo=False, pool_pre_ping=True)
