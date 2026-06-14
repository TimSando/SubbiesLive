"""Standings business logic — calculates ladder from game results.

Rugby union competition points:
- Win: 4 points
- Draw: 2 points
- Loss: 0 points
- Bonus point (scoring 4+ tries): 1 point
- Bonus point (losing by 7 or fewer): 1 point
Note: Bonus points require try-level data which we track, but for simplicity
in v1 we use the standard W/D/L point system without bonus points.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.competitions.models import Competition
from src.clubs.models import Club, Team
from src.games import repository as games_repo
from src.core.cache import ttl_cache

# Points allocation
WIN_POINTS = 4
DRAW_POINTS = 2
LOSS_POINTS = 0


@ttl_cache(ttl_seconds=300)
async def get_standings(db: AsyncSession, competition_id: int) -> dict | None:
    """Calculate standings for a competition from completed game results."""
    # Verify competition exists
    comp_stmt = select(Competition).where(Competition.id == competition_id)
    comp_result = await db.execute(comp_stmt)
    competition = comp_result.scalar_one_or_none()
    if not competition:
        return None

    # Get all teams in this competition
    teams_stmt = (
        select(
            Team.id,
            Team.name,
            Club.name.label("club_name"),
            Club.id.label("club_id"),
        )
        .join(Club, Club.id == Team.club_id)
        .where(Team.competition_id == competition_id)
        .order_by(Team.name)
    )
    teams_result = await db.execute(teams_stmt)
    teams = {row.id: row._asdict() for row in teams_result.all()}

    # Initialise standings
    standings = {}
    for team_id, team_info in teams.items():
        standings[team_id] = {
            "team_id": team_id,
            "team_name": team_info["name"],
            "club_name": team_info["club_name"],
            "club_id": team_info["club_id"],
            "played": 0,
            "won": 0,
            "drawn": 0,
            "lost": 0,
            "byes": 0,
            "points_for": 0,
            "points_against": 0,
            "points_diff": 0,
            "competition_points": 0,
        }

    # Process completed games
    games = await games_repo.get_games_by_competition(db, competition_id)

    for game in games:
        home_id = game["home_team_id"]
        away_id = game["away_team_id"]
        home_score = game["home_score"] or 0
        away_score = game["away_score"] or 0

        if home_id not in standings or away_id not in standings:
            continue

        # Update played count
        standings[home_id]["played"] += 1
        standings[away_id]["played"] += 1

        # Update scores
        standings[home_id]["points_for"] += home_score
        standings[home_id]["points_against"] += away_score
        standings[away_id]["points_for"] += away_score
        standings[away_id]["points_against"] += home_score

        # Determine result
        if home_score > away_score:
            standings[home_id]["won"] += 1
            standings[home_id]["competition_points"] += WIN_POINTS
            standings[away_id]["lost"] += 1
            standings[away_id]["competition_points"] += LOSS_POINTS
        elif away_score > home_score:
            standings[away_id]["won"] += 1
            standings[away_id]["competition_points"] += WIN_POINTS
            standings[home_id]["lost"] += 1
            standings[home_id]["competition_points"] += LOSS_POINTS
        else:
            standings[home_id]["drawn"] += 1
            standings[home_id]["competition_points"] += DRAW_POINTS
            standings[away_id]["drawn"] += 1
            standings[away_id]["competition_points"] += DRAW_POINTS

    # Calculate points differential
    for team_id in standings:
        standings[team_id]["points_diff"] = (
            standings[team_id]["points_for"] - standings[team_id]["points_against"]
        )

    # Sort by competition points (desc), then points diff (desc), then points for (desc)
    sorted_standings = sorted(
        standings.values(),
        key=lambda x: (x["competition_points"], x["points_diff"], x["points_for"]),
        reverse=True,
    )

    # Add position numbers
    for i, row in enumerate(sorted_standings, 1):
        row["position"] = i

    return {
        "competition_id": competition.id,
        "competition_name": competition.name,
        "standings": sorted_standings,
    }
