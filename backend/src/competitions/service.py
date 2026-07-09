"""Competition business logic."""

from sqlalchemy.ext.asyncio import AsyncSession
from src.competitions import repository


async def list_competitions(db: AsyncSession, year: int | None = None) -> list[dict]:
    """Get all competitions with summary counts."""
    return await repository.get_all_competitions(db, year=year)


async def get_competition(db: AsyncSession, competition_id: int) -> dict | None:
    """Get a single competition with rounds."""
    return await repository.get_competition_by_id(db, competition_id)
