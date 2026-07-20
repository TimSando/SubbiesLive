"""Pure functions for computing Player Impact Ratings."""

from dataclasses import dataclass

MAX_PLAYER_IMPACT = 50.0  # Max Elo adjustment per player
MIN_GAMES_WITH = 5
MIN_GAMES_WITHOUT = 1


@dataclass
class PlayerImpactInput:
    games_with: int
    games_without: int
    win_rate_with: float  # 0.0 - 1.0
    win_rate_without: float  # 0.0 - 1.0
    avg_margin_with: float  # points
    avg_margin_without: float  # points


@dataclass
class PlayerImpactResult:
    impact_score: float  # Elo-point adjustment (-MAX to +MAX)
    confidence: str  # "low", "medium", "high"


def compute_impact(data: PlayerImpactInput) -> PlayerImpactResult:
    is_starter_all_games = data.games_without == 0 and data.games_with >= MIN_GAMES_WITH

    if data.games_with < MIN_GAMES_WITH or (
        data.games_without < MIN_GAMES_WITHOUT and not is_starter_all_games
    ):
        return PlayerImpactResult(impact_score=0.0, confidence="low")

    wr_diff = data.win_rate_with - data.win_rate_without
    margin_normalised = (data.avg_margin_with - data.avg_margin_without) / 30.0
    raw_score = (0.65 * wr_diff + 0.35 * margin_normalised) * MAX_PLAYER_IMPACT
    clamped = max(-MAX_PLAYER_IMPACT, min(MAX_PLAYER_IMPACT, raw_score))

    total_games = data.games_with + data.games_without
    if total_games >= 30:
        confidence = "high"
    elif total_games >= 15:
        confidence = "medium"
    else:
        confidence = "low"

    return PlayerImpactResult(impact_score=round(clamped, 1), confidence=confidence)


def compute_squad_modifier(
    named_squad: list[int],
    all_impact_scores: dict[int, float],
    full_strength_baseline: float,
) -> float:
    """Compute Elo adjustment based on squad composition vs full strength."""
    squad_impact = sum(all_impact_scores.get(pid, 0.0) for pid in named_squad)
    return squad_impact - full_strength_baseline
