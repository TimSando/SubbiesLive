"""Pydantic schemas for Game API responses."""

from datetime import datetime
from pydantic import BaseModel


class TeamInGame(BaseModel):
    """Team info as shown within a game context."""
    id: int
    name: str
    club_name: str = ""
    club_id: int | None = None
    logo_url: str | None = None

    class Config:
        from_attributes = True


class GameEventSchema(BaseModel):
    """A scoring or disciplinary event within a game."""
    id: str
    event_type: str
    team_id: int
    team_name: str = ""
    player_id: int | None = None
    player_name: str | None = None
    player_number: int | None = None
    points: int = 0
    text: str | None = None
    external_created_at: datetime | None = None

    class Config:
        from_attributes = True


class GameBrief(BaseModel):
    """Game summary for list views."""
    id: int
    round_name: str = ""
    competition_name: str = ""
    competition_id: int | None = None
    home_team: TeamInGame
    away_team: TeamInGame
    home_score: int | None = None
    away_score: int | None = None
    game_date: datetime
    location: str | None = None
    status: str
    external_id: int
    video_url: str | None = None
    video_url_needs_review: bool = False

    class Config:
        from_attributes = True


class GameDetail(BaseModel):
    """Full game detail with events."""
    id: int
    round_name: str = ""
    competition_name: str = ""
    competition_id: int | None = None
    home_team: TeamInGame
    away_team: TeamInGame
    home_score: int | None = None
    away_score: int | None = None
    game_date: datetime
    location: str | None = None
    status: str
    external_id: int
    video_url: str | None = None
    video_url_needs_review: bool = False
    events: list[GameEventSchema] = []

    class Config:
        from_attributes = True

