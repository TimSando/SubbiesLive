"""Games API router."""

from fastapi import APIRouter, HTTPException, Query

from src.core.dependencies import DbSession
from src.games import service
from src.games.schemas import GameBrief, GameDetail

router = APIRouter()


@router.get("", response_model=list[GameBrief])
async def list_games(
    db: DbSession,
    competition_id: int | None = Query(None, description="Filter by competition"),
    round_id: int | None = Query(None, description="Filter by round"),
    team_id: int | None = Query(None, description="Filter by team"),
    status: str | None = Query(None, description="Filter by status (scheduled/completed)"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """List games with optional filters."""
    return await service.list_games(
        db, competition_id=competition_id, round_id=round_id,
        team_id=team_id, status=status, limit=limit, offset=offset
    )


@router.get("/{game_id}", response_model=GameDetail)
async def get_game(game_id: int, db: DbSession):
    """Get a single game with full scoring events."""
    result = await service.get_game(db, game_id)
    if not result:
        raise HTTPException(status_code=404, detail="Game not found")
    return result
