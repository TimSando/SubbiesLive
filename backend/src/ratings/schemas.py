"""Pydantic schemas for ratings and prediction endpoints."""

from datetime import datetime
from pydantic import BaseModel


class PlayerInsight(BaseModel):
    """Contextual player impact insight for a single player."""

    player_id: int
    player_name: str
    impact_score: float
    impact_score_season: float | None = None
    confidence: str
    games_this_season: int
    last_played_round: str | None = None
    weeks_since_last_game: int | None = None

    class Config:
        from_attributes = True


class TeamPlayerInsights(BaseModel):
    """Player insights for a team, including key players and squad modifier."""

    key_players: list[PlayerInsight]
    squad_modifier: float | None = None
    squad_modifier_source: str

    class Config:
        from_attributes = True


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
    player_insights: dict[str, TeamPlayerInsights] | None = None

    class Config:
        from_attributes = True


class PlayerImpactEntry(BaseModel):
    """Summary of a player's impact calculation metrics."""

    player_id: int
    player_name: str
    impact_score: float
    impact_score_career: float
    confidence: str
    games_with: int
    games_without: int
    win_rate_with: float | None = None
    win_rate_without: float | None = None

    class Config:
        from_attributes = True


class PlayerImpactResponse(BaseModel):
    """Impact rankings response for a team."""

    team_id: int
    team_name: str
    year: int | None = None
    full_strength_baseline: float
    players: list[PlayerImpactEntry]
    available_years: list[int]

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
