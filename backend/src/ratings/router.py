"""FastAPI router for ratings and predictions."""

from fastapi import APIRouter, HTTPException, Query
from src.core.dependencies import DbSession
from src.ratings.schemas import PredictionResponse, TeamRatingHistoryEntry, PlayerImpactResponse
from src.ratings import repository

router = APIRouter()


@router.get("/predictions/{game_id}", response_model=PredictionResponse)
async def get_prediction_for_game(game_id: int, db: DbSession):
    """Get the win probability and odds prediction for an upcoming game."""
    result = await repository.get_prediction_for_game(db, game_id)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"Prediction for game {game_id} not found"
        )
    return result


@router.get("/history/{team_id}", response_model=list[TeamRatingHistoryEntry])
async def get_rating_history(team_id: int, db: DbSession, limit: int = 20):
    """Get rating history for a team."""
    result = await repository.get_rating_history(db, team_id, limit)
    return result


@router.get("/player-impact/{team_id}", response_model=PlayerImpactResponse)
async def get_team_impact_rankings(
    team_id: int,
    db: DbSession,
    year: int | None = Query(None, description="Filter by season year (e.g. 2025), career if not provided"),
):
    """Get player impact rankings for a team."""
    result = await repository.get_team_impact_rankings(db, team_id, year)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"Team {team_id} or player impact rankings not found"
        )
    return result
