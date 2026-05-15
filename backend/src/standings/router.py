"""Standings API router."""

from fastapi import APIRouter, HTTPException

from src.core.dependencies import DbSession
from src.standings import service
from src.standings.schemas import StandingsResponse

router = APIRouter()


@router.get("/{competition_id}", response_model=StandingsResponse)
async def get_standings(competition_id: int, db: DbSession):
    """Get current standings/ladder for a competition, calculated from results."""
    result = await service.get_standings(db, competition_id)
    if not result:
        raise HTTPException(status_code=404, detail="Competition not found")
    return result
