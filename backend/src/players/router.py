"""Players API router."""

from fastapi import APIRouter, HTTPException, Query

from src.core.dependencies import DbSession
from src.players import service
from src.players.schemas import PlayerBrief, PlayerDetail

router = APIRouter()


@router.get("", response_model=list[PlayerBrief])
async def list_players(
    db: DbSession,
    search: str | None = Query(None, description="Search by player name"),
    team_id: int | None = Query(None, description="Filter by team"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Search and list players."""
    return await service.list_players(
        db, search=search, team_id=team_id, limit=limit, offset=offset
    )


@router.get("/{player_id}", response_model=PlayerDetail)
async def get_player(
    player_id: int,
    db: DbSession,
    year: int | None = Query(None, description="Filter stats by year"),
):
    """Get a single player with stats history."""
    result = await service.get_player(db, player_id, year)
    if not result:
        raise HTTPException(status_code=404, detail="Player not found")
    return result
