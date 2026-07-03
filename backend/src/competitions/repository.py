"""Competition data access layer."""

from datetime import datetime, timedelta
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from src.competitions.models import Competition, Round, CompetitionMapping
from src.clubs.models import Team, Club
from src.games.models import Game


async def get_all_competitions(db: AsyncSession) -> list[dict]:
    """Filter all competitions with team and round counts."""
    stmt = (
        select(
            Competition.id,
            Competition.name,
            Competition.external_id,
            Competition.competition_mapping_id,
            CompetitionMapping.parent_competition,
            CompetitionMapping.division,
            CompetitionMapping.grade,
            func.count(func.distinct(Team.id)).label("team_count"),
            func.count(func.distinct(Round.id)).label("round_count"),
            func.count(func.distinct(Club.id)).label("club_count"),
            func.string_agg(func.distinct(Club.name), ", ").label("club_names"),
        )
        .outerjoin(Team, Team.competition_id == Competition.id)
        .outerjoin(Club, Team.club_id == Club.id)
        .outerjoin(Round, Round.competition_id == Competition.id)
        .outerjoin(
            CompetitionMapping,
            Competition.competition_mapping_id == CompetitionMapping.id,
        )
        .group_by(
            Competition.id,
            Competition.name,
            Competition.external_id,
            Competition.competition_mapping_id,
            CompetitionMapping.parent_competition,
            CompetitionMapping.division,
            CompetitionMapping.grade,
        )
        .order_by(Competition.name)
    )
    result = await db.execute(stmt)
    return [row._asdict() for row in result.all()]


async def get_competition_by_id(db: AsyncSession, competition_id: int) -> dict | None:
    """Fetch a single competition with its rounds and game counts."""
    # Get competition
    stmt = select(Competition).where(Competition.id == competition_id)
    result = await db.execute(stmt)
    comp = result.scalar_one_or_none()
    if not comp:
        return None

    # Fetch all db rounds
    rounds_stmt = (
        select(Round)
        .where(Round.competition_id == competition_id)
        .order_by(Round.number.nulls_last(), Round.id)
    )
    rounds_result = await db.execute(rounds_stmt)
    all_db_rounds = rounds_result.scalars().all()

    # Fetch all games for this competition
    games_stmt = (
        select(
            Game.id,
            Game.game_date,
            Game.status,
            Game.round_id,
            Round.number.label("round_number"),
            Round.name.label("round_name"),
            Round.external_id.label("round_external_id"),
        )
        .join(Round, Game.round_id == Round.id)
        .where(Round.competition_id == competition_id)
        .order_by(Game.game_date)
    )
    games_result = await db.execute(games_stmt)
    all_games = [row._asdict() for row in games_result.all()]

    # Reconstruct display rounds list
    def get_sat_date(dt):
        wd = dt.weekday()
        return (dt.date() + timedelta(days=(5 - wd))).strftime("%Y-%m-%d")

    game_groups = {}  # (round_id, date_str) -> list of games
    for g in all_games:
        rid = g["round_id"]
        sat = get_sat_date(g["game_date"])
        key = (rid, sat)
        if key not in game_groups:
            game_groups[key] = []
        game_groups[key].append(g)

    # Find expected date for each round number
    expected_dates = {}  # round_number -> date_str
    start_date = None
    r1_games = [g for g in all_games if g["round_number"] == 1]
    if r1_games:
        start_date = min(g["game_date"] for g in r1_games).date()
        start_date = start_date + timedelta(days=(5 - start_date.weekday()))
    elif all_games:
        start_date = min(g["game_date"] for g in all_games).date()
        start_date = start_date + timedelta(days=(5 - start_date.weekday()))

    if start_date:
        current_date = start_date
        sorted_rounds = sorted(
            [r for r in all_db_rounds if r.number is not None],
            key=lambda x: x.number,
        )
        for r in sorted_rounds:
            expected_dates[r.number] = current_date.strftime("%Y-%m-%d")

            # Advance current_date to next Saturday
            next_sat = current_date + timedelta(days=7)
            next_next_sat = current_date + timedelta(days=14)
            has_games_next = any(
                abs(
                    (
                        (
                            g["game_date"].date()
                            + timedelta(days=(5 - g["game_date"].weekday()))
                        )
                        - next_sat
                    ).days
                )
                <= 3
                for g in all_games
            )
            has_games_next_next = any(
                abs(
                    (
                        (
                            g["game_date"].date()
                            + timedelta(days=(5 - g["game_date"].weekday()))
                        )
                        - next_next_sat
                    ).days
                )
                <= 3
                for g in all_games
            )

            if not has_games_next and has_games_next_next:
                current_date = next_next_sat
            else:
                current_date = next_sat

    display_rounds = []

    for r in all_db_rounds:
        r_keys = [k for k in game_groups.keys() if k[0] == r.id]

        if not r_keys:
            exp_date = expected_dates.get(r.number)
            display_rounds.append(
                {
                    "id": f"{r.id}-original",
                    "round_id": r.id,
                    "name": r.name,
                    "number": r.number,
                    "external_id": r.external_id,
                    "game_count": 0,
                    "completed_game_count": 0,
                    "latest_game_date": (
                        datetime.strptime(exp_date, "%Y-%m-%d") if exp_date else None
                    ),
                    "is_rescheduled_empty": False,
                    "date_filter": None,
                }
            )
            continue

        exp_date = expected_dates.get(r.number)
        exp_dt = datetime.strptime(exp_date, "%Y-%m-%d").date() if exp_date else None
        has_games_on_exp_date = any(k[1] == exp_date for k in r_keys)

        now_date = datetime.now().date()

        if not has_games_on_exp_date and exp_dt and exp_dt <= now_date:
            display_rounds.append(
                {
                    "id": f"{r.id}-original",
                    "round_id": r.id,
                    "name": r.name,
                    "number": r.number,
                    "external_id": r.external_id,
                    "game_count": 0,
                    "completed_game_count": 0,
                    "latest_game_date": datetime.combine(exp_dt, datetime.min.time()),
                    "is_rescheduled_empty": True,
                    "date_filter": None,
                }
            )

        for k in sorted(r_keys, key=lambda x: x[1]):
            date_str = k[1]
            games_in_group = game_groups[k]
            game_count = len(games_in_group)
            completed_count = sum(
                1 for g in games_in_group if g["status"] == "completed"
            )

            is_resched_slot = date_str != exp_date and exp_dt and exp_dt <= now_date
            name = f"{r.name} (Resched)" if is_resched_slot else r.name

            display_rounds.append(
                {
                    "id": f"{r.id}-{date_str}",
                    "round_id": r.id,
                    "name": name,
                    "number": r.number,
                    "external_id": r.external_id,
                    "game_count": game_count,
                    "completed_game_count": completed_count,
                    "latest_game_date": datetime.strptime(date_str, "%Y-%m-%d"),
                    "is_rescheduled_empty": False,
                    "date_filter": date_str,
                }
            )

    def get_sort_key(dr):
        dt = dr["latest_game_date"]
        if not dt:
            return (1, dr["number"] or 99, dr["id"])
        dt_str = dt.strftime("%Y-%m-%d")
        return (0, dt_str, dr["number"] or 99, dr["id"])

    display_rounds = sorted(display_rounds, key=get_sort_key)

    # Get team count
    team_stmt = select(func.count(Team.id)).where(Team.competition_id == competition_id)
    team_count = (await db.execute(team_stmt)).scalar()

    return {
        "id": comp.id,
        "name": comp.name,
        "external_id": comp.external_id,
        "rounds": display_rounds,
        "team_count": team_count,
    }
