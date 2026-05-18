from datetime import datetime
from pydantic import BaseModel


class RoundBrief(BaseModel):
    """Brief round info for competition listings."""
    id: int
    name: str
    number: int | None = None
    external_id: int
    game_count: int = 0
    completed_game_count: int = 0
    latest_game_date: datetime | None = None

    class Config:
        from_attributes = True


class CompetitionMappingBrief(BaseModel):
    """Brief mapping info."""
    id: int
    parent_competition: str | None = None
    name: str
    division: str | None = None
    grade: str | None = None

    class Config:
        from_attributes = True


class CompetitionBrief(BaseModel):
    """Competition summary for list views."""
    id: int
    name: str
    external_id: int
    competition_mapping_id: int | None = None
    parent_competition: str | None = None
    division: str | None = None
    grade: str | None = None
    team_count: int = 0
    round_count: int = 0
    club_count: int = 0
    club_names: str | None = None

    class Config:
        from_attributes = True


class CompetitionDetail(BaseModel):
    """Full competition detail with rounds."""
    id: int
    name: str
    external_id: int
    rounds: list[RoundBrief] = []
    team_count: int = 0

    class Config:
        from_attributes = True
