"""Game business logic."""

from sqlalchemy.ext.asyncio import AsyncSession
from src.games import repository


async def list_games(
    db: AsyncSession,
    competition_id: int | None = None,
    round_id: int | None = None,
    team_id: int | None = None,
    club_id: int | None = None,
    status: str | None = None,
    player_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    game_date: str | None = None,
) -> list[dict]:
    """Get games with optional filters."""
    return await repository.get_games(
        db,
        competition_id=competition_id,
        round_id=round_id,
        team_id=team_id,
        club_id=club_id,
        status=status,
        player_id=player_id,
        limit=limit,
        offset=offset,
        game_date=game_date,
    )


async def get_game(db: AsyncSession, game_id: int) -> dict | None:
    """Get a single game with events."""
    return await repository.get_game_by_id(db, game_id)
