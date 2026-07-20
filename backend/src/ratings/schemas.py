"""Pydantic schemas for ratings and prediction endpoints."""

from datetime import datetime
from pydantic import BaseModel


class PredictionResponse(BaseModel):
    """Win probability and odds prediction response for an upcoming game."""

    game_id: int
    home_win_probability: float
    away_win_probability: float
    draw_probability: float
    home_odds_display: str
    away_odds_display: str
    confidence: str  # e.g., 'high', 'medium', 'low'
    rating_diff: float

    class Config:
        from_attributes = True


class TeamRatingHistoryEntry(BaseModel):
    """Individual entry in a team's rating history."""

    team_id: int
    game_id: int | None = None
    rating_before: float
    rating_after: float
    opponent_rating: float
    expected_result: float
    actual_result: float
    created_at: datetime

    class Config:
        from_attributes = True
