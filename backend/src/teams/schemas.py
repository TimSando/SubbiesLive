from pydantic import BaseModel, model_validator
from typing import Optional


class TeamStats(BaseModel):
    games_played: int
    wins: int
    losses: int
    draws: int
    points_for: int
    points_against: int
    total_tries: int
    total_conversions: int
    total_penalty_goals: int
    total_drop_goals: int
    total_yellow_cards: int
    total_red_cards: int


class TeamDetail(BaseModel):
    id: int
    name: str
    external_id: int
    club_id: int
    club_name: str
    club_logo_url: Optional[str] = None
    competition_id: int
    competition_name: str
    year: int
    stats: TeamStats

    @model_validator(mode="after")
    def rewrite_logo(self) -> "TeamDetail":
        if self.club_logo_url and not self.club_logo_url.startswith("/api/"):
            self.club_logo_url = f"/api/clubs/{self.club_id}/logo"
        return self
