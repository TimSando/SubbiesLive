from pydantic import BaseModel

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
    image_url: str | None = None

class ClubStatRow(BaseModel):
    rank: int
    club_id: int
    club_name: str
    tries: int
    conversions: int
    penalties: int
    total_points: int
    yellow_cards: int
    red_cards: int
    logo_url: str | None = None

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
