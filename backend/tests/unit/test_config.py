import pytest
from src.core.config import Settings


def test_ingestion_interval_default():
    # Verify the field is present and defaults to an integer
    settings = Settings()
    assert hasattr(settings, "ingestion_interval_minutes")
    assert isinstance(settings.ingestion_interval_minutes, int)


def test_ingestion_interval_custom():
    settings = Settings(ingestion_interval_minutes=45)
    assert settings.ingestion_interval_minutes == 45
