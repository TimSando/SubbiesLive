"""Pydantic schemas for Player API responses."""

from datetime import date
from pydantic import BaseModel


class PlayerStatSummary(BaseModel):
    """Aggregated stats for a player."""
    total_tries: int = 0
    total_conversions: int = 0
    total_penalty_goals: int = 0
    total_drop_goals: int = 0
    total_yellow_cards: int = 0
    total_red_cards: int = 0
    total_points: int = 0
    games_played: int = 0


class PlayerTeamInfo(BaseModel):
    """Team association for a player."""
    team_id: int
    team_name: str
    club_name: str = ""
    competition_name: str = ""

    class Config:
        from_attributes = True


class PlayerBrief(BaseModel):
    """Player summary for list views."""
    id: int
    name: str
    external_id: int
    thumbnail_url: str | None = None
    current_team: str | None = None

    class Config:
        from_attributes = True


class PlayerDetail(BaseModel):
    """Full player detail with stats and team history."""
    id: int
    name: str
    dob: date | None = None
    image_url: str | None = None
    thumbnail_url: str | None = None
    external_id: int
    teams: list[PlayerTeamInfo] = []
    stats: PlayerStatSummary = PlayerStatSummary()

    class Config:
        from_attributes = True
