"""Club data access layer."""

from sqlalchemy import select, func, case, and_, or_, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from src.clubs.models import Club, Team
from src.competitions.models import Competition, CompetitionMapping, Round
from src.games.models import Game


async def get_all_clubs(db: AsyncSession) -> list[dict]:
    """Fetch all clubs with team counts and season win/loss/draw record."""
    record_sub = (
        select(
            Team.club_id,
            func.sum(case(
                (and_(Game.home_team_id == Team.id, Game.home_score > Game.away_score), 1),
                (and_(Game.away_team_id == Team.id, Game.away_score > Game.home_score), 1),
                else_=0
            )).label("wins"),
            func.sum(case(
                (and_(Game.home_team_id == Team.id, Game.home_score < Game.away_score), 1),
                (and_(Game.away_team_id == Team.id, Game.away_score < Game.home_score), 1),
                else_=0
            )).label("losses"),
            func.sum(case(
                (Game.home_score == Game.away_score, 1),
                else_=0
            )).label("draws"),
        )
        .join(
            Game,
            and_(
                or_(Game.home_team_id == Team.id, Game.away_team_id == Team.id),
                Game.status == "completed",
            ),
        )
        .group_by(Team.club_id)
        .subquery("record_sub")
    )

    stmt = (
        select(
            Club.id,
            Club.name,
            Club.short_name,
            Club.logo_url,
            Club.home_ground_name,
            Club.home_ground_map_url,
            Club.has_womens_team,
            func.count(Team.id).label("team_count"),
            func.coalesce(record_sub.c.wins, 0).label("wins"),
            func.coalesce(record_sub.c.losses, 0).label("losses"),
            func.coalesce(record_sub.c.draws, 0).label("draws"),
            CompetitionMapping.id.label("mapping_id"),
            CompetitionMapping.parent_competition,
            CompetitionMapping.name.label("mapping_name"),
            CompetitionMapping.division,
            CompetitionMapping.grade,
        )
        .outerjoin(Team, Team.club_id == Club.id)
        .outerjoin(record_sub, record_sub.c.club_id == Club.id)
        .outerjoin(CompetitionMapping, Club.competition_mapping_id == CompetitionMapping.id)
        .group_by(
            Club.id, Club.name, Club.short_name, Club.logo_url,
            Club.home_ground_name, Club.home_ground_map_url, Club.has_womens_team,
            record_sub.c.wins, record_sub.c.losses, record_sub.c.draws,
            CompetitionMapping.id, CompetitionMapping.parent_competition,
            CompetitionMapping.name, CompetitionMapping.division, CompetitionMapping.grade,
        )
        .order_by(CompetitionMapping.parent_competition, CompetitionMapping.division, Club.name)
    )
    result = await db.execute(stmt)
    
    clubs = []
    for row in result.all():
        d = row._asdict()
        # Nest competition_mapping
        if d.get("mapping_id"):
            d["competition_mapping"] = {
                "id": d.pop("mapping_id"),
                "parent_competition": d.pop("parent_competition"),
                "name": d.pop("mapping_name"),
                "division": d.pop("division"),
                "grade": d.pop("grade"),
            }
        else:
            d["competition_mapping"] = None
            # Cleanup unwanted mapping fields if they are None
            for k in ["mapping_id", "parent_competition", "mapping_name", "division", "grade"]:
                if k in d: d.pop(k)
        clubs.append(d)
        
    return clubs


async def get_club_by_id(db: AsyncSession, club_id: int) -> dict | None:
    """Fetch a single club with its teams, records, fallbacks, and sorted fixtures."""
    stmt = (
        select(
            Club.id,
            Club.name,
            Club.short_name,
            Club.logo_url,
            Club.about_text,
            Club.division_info,
            Club.grades_count,
            Club.training_info,
            Club.has_womens_team,
            Club.home_ground_name,
            Club.home_ground_map_url,
            Club.website_url,
            Club.facebook_url,
            Club.instagram_url,
            Club.tiktok_url,
            CompetitionMapping.id.label("mapping_id"),
            CompetitionMapping.parent_competition,
            CompetitionMapping.name.label("mapping_name"),
            CompetitionMapping.division,
            CompetitionMapping.grade,
        )
        .outerjoin(CompetitionMapping, Club.competition_mapping_id == CompetitionMapping.id)
        .where(Club.id == club_id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        return None

    d = row._asdict()
    
    # Nest competition_mapping
    if d.get("mapping_id"):
        d["competition_mapping"] = {
            "id": d.pop("mapping_id"),
            "parent_competition": d.pop("parent_competition"),
            "name": d.pop("mapping_name"),
            "division": d.pop("division"),
            "grade": d.pop("grade"),
        }
    else:
        d["competition_mapping"] = None
        for k in ["mapping_id", "parent_competition", "mapping_name", "division", "grade"]:
            if k in d: d.pop(k)

    # 1. Calculate fallback Home Ground and Google Maps URL
    fallback_ground = None
    fallback_map_url = None

    if not d.get("home_ground_name"):
        ground_stmt = (
            select(Game.location, func.count(Game.id).label("cnt"))
            .join(Team, Team.id == Game.home_team_id)
            .where(and_(
                Team.club_id == club_id,
                Game.status == "completed",
                Game.location != None,
                Game.location != ""
            ))
            .group_by(Game.location)
            .order_by(literal_column("cnt").desc())
            .limit(1)
        )
        ground_res = await db.execute(ground_stmt)
        ground_row = ground_res.first()
        if ground_row:
            fallback_ground = ground_row[0]
            import urllib.parse
            q = urllib.parse.quote(f"{fallback_ground} rugby ground Sydney")
            fallback_map_url = f"https://www.google.com/maps/search/?api=1&query={q}"

    d["home_ground_name"] = d.get("home_ground_name") or fallback_ground
    d["home_ground_map_url"] = d.get("home_ground_map_url") or fallback_map_url

    # 2. Get teams with distinct W/L/D records
    record_sub = (
        select(
            Team.id.label("team_id"),
            func.sum(case(
                (and_(Game.home_team_id == Team.id, Game.home_score > Game.away_score), 1),
                (and_(Game.away_team_id == Team.id, Game.away_score > Game.home_score), 1),
                else_=0
            )).label("wins"),
            func.sum(case(
                (and_(Game.home_team_id == Team.id, Game.home_score < Game.away_score), 1),
                (and_(Game.away_team_id == Team.id, Game.away_score < Game.home_score), 1),
                else_=0
            )).label("losses"),
            func.sum(case(
                (Game.home_score == Game.away_score, 1),
                else_=0
            )).label("draws"),
        )
        .select_from(Team)
        .join(
            Game,
            and_(
                or_(Game.home_team_id == Team.id, Game.away_team_id == Team.id),
                Game.status == "completed",
            ),
            isouter=True
        )
        .where(Team.club_id == club_id)
        .group_by(Team.id)
        .subquery("record_sub")
    )

    teams_stmt = (
        select(
            Team.id,
            Team.name,
            Team.external_id,
            Competition.name.label("competition_name"),
            func.coalesce(record_sub.c.wins, 0).label("wins"),
            func.coalesce(record_sub.c.losses, 0).label("losses"),
            func.coalesce(record_sub.c.draws, 0).label("draws"),
        )
        .join(Competition, Competition.id == Team.competition_id)
        .outerjoin(record_sub, record_sub.c.team_id == Team.id)
        .where(Team.club_id == club_id)
        .order_by(Competition.name)
    )
    teams_result = await db.execute(teams_stmt)
    d["teams"] = [row._asdict() for row in teams_result.all()]

    # 3. Fetch recent & upcoming fixtures sorted by user-defined grade rank
    async def get_fixtures(status_filter, order_desc=True, limit_count=30):
        from sqlalchemy import desc
        from sqlalchemy.orm import aliased

        home_team = aliased(Team, name="home_team")
        away_team = aliased(Team, name="away_team")
        home_club = aliased(Club, name="home_club")
        away_club = aliased(Club, name="away_club")

        stmt_fix = (
            select(
                Game.id,
                Game.home_score,
                Game.away_score,
                Game.game_date,
                Game.location,
                Game.status,
                Game.external_id,
                Round.name.label("round_name"),
                Competition.name.label("competition_name"),
                Competition.id.label("competition_id"),
                home_team.id.label("home_team_id"),
                home_team.name.label("home_team_name"),
                home_club.name.label("home_club_name"),
                home_club.id.label("home_club_id"),
                away_team.id.label("away_team_id"),
                away_team.name.label("away_team_name"),
                away_club.name.label("away_club_name"),
                away_club.id.label("away_club_id"),
            )
            .select_from(Game)
            .join(Round, Round.id == Game.round_id)
            .join(Competition, Competition.id == Round.competition_id)
            .join(home_team, home_team.id == Game.home_team_id)
            .join(away_team, away_team.id == Game.away_team_id)
            .join(home_club, home_club.id == home_team.club_id)
            .join(away_club, away_club.id == away_team.club_id)
            .where(
                and_(
                    or_(
                        home_team.club_id == club_id,
                        away_team.club_id == club_id
                    ),
                    Game.status == "completed" if status_filter == "completed" else Game.status != "completed"
                )
            )
        )
        if order_desc:
            stmt_fix = stmt_fix.order_by(desc(Game.game_date))
        else:
            stmt_fix = stmt_fix.order_by(Game.game_date)
            
        res_fix = await db.execute(stmt_fix.limit(limit_count))
        games_list = []
        for r_fix in res_fix.all():
            g = r_fix._asdict()
            games_list.append({
                "id": g["id"],
                "round_name": g["round_name"],
                "competition_name": g["competition_name"],
                "competition_id": g["competition_id"],
                "home_team": {
                    "id": g["home_team_id"],
                    "name": g["home_team_name"],
                    "club_name": g["home_club_name"],
                    "club_id": g["home_club_id"]
                },
                "away_team": {
                    "id": g["away_team_id"],
                    "name": g["away_team_name"],
                    "club_name": g["away_club_name"],
                    "club_id": g["away_club_id"]
                },
                "home_score": g["home_score"],
                "away_score": g["away_score"],
                "game_date": g["game_date"],
                "location": g["location"],
                "status": g["status"],
                "external_id": g["external_id"]
            })
        return games_list

    def get_game_grade_rank(game):
        our_team = game["home_team"] if game["home_team"]["club_id"] == club_id else game["away_team"]
        name = our_team["name"].lower()
        
        if "1st grade" in name or "1st xv" in name or "first grade" in name:
            return 10
        if "2nd grade" in name or "second grade" in name:
            return 20
        if "1st colts" in name or ("colts" in name and "2nd" not in name and "3rd" not in name and "4th" not in name):
            return 30
        if "3rd grade" in name or "third grade" in name:
            return 40
        if "colts" in name:
            if "2nd" in name:
                return 50
            if "3rd" in name:
                return 51
            return 52
        if "4th grade" in name or "fourth grade" in name or "4ths" in name:
            return 60
        if "5th grade" in name or "fifth grade" in name or "5ths" in name:
            return 70
        return 99

    recent_games = await get_fixtures("completed", order_desc=True, limit_count=40)
    upcoming_games = await get_fixtures("scheduled", order_desc=False, limit_count=40)

    recent_games.sort(key=lambda g: (get_game_grade_rank(g), -g["game_date"].timestamp()))
    upcoming_games.sort(key=lambda g: (get_game_grade_rank(g), g["game_date"].timestamp()))

    d["recent_fixtures"] = recent_games[:15]
    d["upcoming_fixtures"] = upcoming_games[:15]

    return d
