"""Pydantic schemas for Club API responses."""

from pydantic import BaseModel


from src.competitions.schemas import CompetitionMappingBrief


class TeamBrief(BaseModel):
    """Brief team info for club listings."""
    id: int
    name: str
    competition_name: str = ""
    external_id: int

    class Config:
        from_attributes = True


class ClubBrief(BaseModel):
    """Club summary for list views."""
    id: int
    name: str
    short_name: str | None = None
    logo_url: str | None = None
    competition_mapping: CompetitionMappingBrief | None = None
    team_count: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0

    class Config:
        from_attributes = True


class ClubDetail(BaseModel):
    """Full club detail with teams across competitions."""
    id: int
    name: str
    short_name: str | None = None
    logo_url: str | None = None
    competition_mapping: CompetitionMappingBrief | None = None
    teams: list[TeamBrief] = []

    class Config:
        from_attributes = True
