from pydantic import BaseModel, model_validator


class PlayerStatRow(BaseModel):
    rank: int
    player_id: int
    player_name: str
    club_name: str
    club_id: int
    tries: int
    conversions: int
    penalties: int
    drop_goals: int
    total_points: int
    yellow_cards: int
    red_cards: int
    games_played: int
    image_url: str | None = None


class ClubStatRow(BaseModel):
    rank: int
    club_id: int
    club_name: str
    tries: int
    conversions: int
    penalties: int
    drop_goals: int
    total_points: int
    yellow_cards: int
    red_cards: int
    games_played: int
    logo_url: str | None = None

    @model_validator(mode="after")
    def rewrite_logo(self) -> "ClubStatRow":
        if self.logo_url and not self.logo_url.startswith("/api/"):
            self.logo_url = f"/api/clubs/{self.club_id}/logo"
        return self


class SeasonOverview(BaseModel):
    total_tries: int
    total_conversions: int
    total_penalties: int
    total_yellow_cards: int
    total_red_cards: int
    top_scorer_name: str | None = None
    top_scorer_points: int = 0
    top_try_scorer_name: str | None = None
    top_try_scorer_tries: int = 0
    games_played: int
    club_count: int = 0
    player_count: int = 0


class ClubDepthRow(BaseModel):
    rank: int
    club_id: int
    club_name: str
    logo_url: str | None = None
    total_players: int
    core_players: int
    dedicated_players: int
    swing_players: int
    avg_games: float

    @model_validator(mode="after")
    def rewrite_logo(self) -> "ClubDepthRow":
        if self.logo_url and not self.logo_url.startswith("/api/"):
            self.logo_url = f"/api/clubs/{self.club_id}/logo"
        return self


class TeamFormStats(BaseModel):
    team_id: int
    games_played: int
    total_tries: int
    total_conversions: int
    total_yellow_cards: int
    total_red_cards: int
