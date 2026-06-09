"""Pydantic schemas for Standings API responses."""

from pydantic import BaseModel


class StandingsRow(BaseModel):
    """A single row in the standings/ladder table."""

    position: int
    team_id: int
    team_name: str
    club_name: str = ""
    club_id: int | None = None
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    byes: int = 0
    points_for: int = 0
    points_against: int = 0
    points_diff: int = 0
    competition_points: int = 0


class StandingsResponse(BaseModel):
    """Full standings for a competition."""

    competition_id: int
    competition_name: str
    standings: list[StandingsRow] = []
