"""Competitions API router."""

from fastapi import APIRouter, HTTPException

from src.core.dependencies import DbSession
from src.competitions import service
from src.competitions.schemas import CompetitionBrief, CompetitionDetail

router = APIRouter()


@router.get("", response_model=list[CompetitionBrief])
async def list_competitions(db: DbSession):
    """List all competitions with team and round counts."""
    return await service.list_competitions(db)


@router.get("/{competition_id}", response_model=CompetitionDetail)
async def get_competition(competition_id: int, db: DbSession):
    """Get a single competition with its rounds."""
    result = await service.get_competition(db, competition_id)
    if not result:
        raise HTTPException(status_code=404, detail="Competition not found")
    return result
