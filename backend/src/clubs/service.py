"""Club business logic."""

from sqlalchemy.ext.asyncio import AsyncSession
from src.clubs import repository


async def list_clubs(db: AsyncSession) -> list[dict]:
    """Get all clubs with summary counts."""
    return await repository.get_all_clubs(db)


async def get_club(db: AsyncSession, club_id: int) -> dict | None:
    """Get a single club with its teams."""
    return await repository.get_club_by_id(db, club_id)
