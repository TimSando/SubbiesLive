"""Player business logic."""

from sqlalchemy.ext.asyncio import AsyncSession
from src.players import repository


async def list_players(
    db: AsyncSession,
    search: str | None = None,
    team_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Get players with optional search and team filter."""
    return await repository.get_players(
        db, search=search, team_id=team_id, limit=limit, offset=offset
    )


async def get_player(db: AsyncSession, player_id: int) -> dict | None:
    """Get a single player with stats and team history."""
    return await repository.get_player_by_id(db, player_id)
