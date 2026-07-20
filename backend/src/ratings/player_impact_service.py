"""Orchestration service for calculating and updating Player Impact Ratings."""

import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.ratings.player_impact import (
    compute_impact,
    PlayerImpactInput,
    PlayerImpactResult,
)
from src.ratings.models import PlayerImpactScore

logger = logging.getLogger("ingestion")


def calculate_player_impact(
    session: Session, player_id: int, team_id: int, year: int | None = None
) -> PlayerImpactResult:
    """Calculate the impact score for a player in a team.

    If year is None, calculates career impact restricted to the seasons (years)
    in which the player played at least one game for the team.
    """
    # 1. Get the years in which the player played at least one game for this team
    if year is not None:
        active_years = [year]
    else:
        active_years_query = session.execute(
            text(
                """
                SELECT DISTINCT EXTRACT(YEAR FROM g.game_date)::integer
                FROM player_history ph
                JOIN games g ON ph.game_id = g.id
                WHERE ph.player_id = :pid AND ph.team_id = :tid AND g.status = 'completed'
            """
            ),
            {"pid": player_id, "tid": team_id},
        ).fetchall()
        active_years = [r[0] for r in active_years_query if r[0] is not None]

    if not active_years:
        return PlayerImpactResult(impact_score=0.0, confidence="low")

    # 2. Get all completed games for the team in the active years
    games = session.execute(
        text(
            """
            SELECT 
                g.id,
                g.home_team_id,
                g.away_team_id,
                g.home_score,
                g.away_score,
                EXTRACT(YEAR FROM g.game_date)::integer as game_year
            FROM games g
            WHERE (g.home_team_id = :tid OR g.away_team_id = :tid)
              AND g.status = 'completed'
              AND EXTRACT(YEAR FROM g.game_date)::integer IN :years
        """
        ),
        {"tid": team_id, "years": tuple(active_years)},
    ).fetchall()

    if not games:
        return PlayerImpactResult(impact_score=0.0, confidence="low")

    # 3. Get all game IDs where the player actually played
    played_game_ids = set()
    played_query = session.execute(
        text(
            """
            SELECT game_id 
            FROM player_history 
            WHERE player_id = :pid AND team_id = :tid
        """
        ),
        {"pid": player_id, "tid": team_id},
    ).fetchall()
    for r in played_query:
        played_game_ids.add(r[0])

    # 4. Separate games into with and without player
    with_games = []
    without_games = []

    for g in games:
        game_id = g[0]
        home_team_id = g[1]
        home_score = g[3] or 0
        away_score = g[4] or 0

        is_home = home_team_id == team_id
        our_score = home_score if is_home else away_score
        opp_score = away_score if is_home else home_score

        margin = our_score - opp_score
        is_win = (
            1.0 if our_score > opp_score else (0.5 if our_score == opp_score else 0.0)
        )

        game_data = {"is_win": is_win, "margin": margin}

        if game_id in played_game_ids:
            with_games.append(game_data)
        else:
            without_games.append(game_data)

    games_with = len(with_games)
    games_without = len(without_games)

    if games_with == 0:
        return PlayerImpactResult(impact_score=0.0, confidence="low")

    win_rate_with = sum(g["is_win"] for g in with_games) / games_with
    avg_margin_with = sum(g["margin"] for g in with_games) / games_with

    win_rate_without = (
        sum(g["is_win"] for g in without_games) / games_without
        if games_without > 0
        else 0.5
    )
    avg_margin_without = (
        sum(g["margin"] for g in without_games) / games_without
        if games_without > 0
        else 0.0
    )

    impact_input = PlayerImpactInput(
        games_with=games_with,
        games_without=games_without,
        win_rate_with=win_rate_with,
        win_rate_without=win_rate_without,
        avg_margin_with=avg_margin_with,
        avg_margin_without=avg_margin_without,
    )

    return compute_impact(impact_input)


def recalculate_all_impacts(session_factory, current_year: int):
    """Recalculate player impact scores for career and the current season.

    Truncates the player_impact_scores table and does a full recalculation.
    """
    session = session_factory()
    try:
        logger.info("Recalculating all player impact scores...")

        # Find all unique player/team combinations from history with at least 5 appearances
        combinations = session.execute(
            text(
                """
                SELECT ph.player_id, ph.team_id, t.club_id, t.competition_id, c.competition_mapping_id
                FROM player_history ph
                JOIN teams t ON ph.team_id = t.id
                JOIN competitions c ON t.competition_id = c.id
                GROUP BY ph.player_id, ph.team_id, t.club_id, t.competition_id, c.competition_mapping_id
                HAVING COUNT(ph.id) >= 5
            """
            )
        ).fetchall()

        logger.info(f"Found {len(combinations)} player-team combinations to process.")

        # Truncate existing impact scores
        session.execute(text("TRUNCATE TABLE player_impact_scores RESTART IDENTITY"))
        session.commit()

        inserted_count = 0

        for row in combinations:
            player_id, team_id, club_id, competition_id, competition_mapping_id = row

            # Career impact (year = None)
            career_res = calculate_player_impact(session, player_id, team_id, year=None)

            # Determine win rates and margin differences
            # We compute it inside calculate_player_impact but return just the result.
            # Let's write them to the DB.
            # To fetch details for writing:
            career_details = _get_impact_metrics(session, player_id, team_id, year=None)
            if career_details:
                session.add(
                    PlayerImpactScore(
                        player_id=player_id,
                        team_id=team_id,
                        club_id=club_id,
                        competition_mapping_id=competition_mapping_id,
                        year=None,
                        impact_score=career_res.impact_score,
                        games_with=career_details["games_with"],
                        games_without=career_details["games_without"],
                        win_rate_with=career_details["win_rate_with"],
                        win_rate_without=career_details["win_rate_without"],
                        margin_diff=career_details["margin_diff"],
                        confidence=career_res.confidence,
                    )
                )
                inserted_count += 1

            # Current season impact (year = current_year)
            season_res = calculate_player_impact(
                session, player_id, team_id, year=current_year
            )
            season_details = _get_impact_metrics(
                session, player_id, team_id, year=current_year
            )
            if season_details and season_details["games_with"] > 0:
                session.add(
                    PlayerImpactScore(
                        player_id=player_id,
                        team_id=team_id,
                        club_id=club_id,
                        competition_mapping_id=competition_mapping_id,
                        year=current_year,
                        impact_score=season_res.impact_score,
                        games_with=season_details["games_with"],
                        games_without=season_details["games_without"],
                        win_rate_with=season_details["win_rate_with"],
                        win_rate_without=season_details["win_rate_without"],
                        margin_diff=season_details["margin_diff"],
                        confidence=season_res.confidence,
                    )
                )
                inserted_count += 1

            if inserted_count % 500 == 0 and inserted_count > 0:
                session.commit()
                logger.info(f"  Processed {inserted_count} impact score records...")

        session.commit()
        logger.info(
            f"Finished recalculating player impact scores. Total rows: {inserted_count}"
        )

    except Exception as e:
        session.rollback()
        logger.error(f"Failed to recalculate player impacts: {e}")
        raise e
    finally:
        session.close()


def _get_impact_metrics(
    session: Session, player_id: int, team_id: int, year: int | None = None
) -> dict | None:
    """Helper to return raw metrics for database insertion."""
    if year is not None:
        active_years = [year]
    else:
        active_years_query = session.execute(
            text(
                """
                SELECT DISTINCT EXTRACT(YEAR FROM g.game_date)::integer
                FROM player_history ph
                JOIN games g ON ph.game_id = g.id
                WHERE ph.player_id = :pid AND ph.team_id = :tid AND g.status = 'completed'
            """
            ),
            {"pid": player_id, "tid": team_id},
        ).fetchall()
        active_years = [r[0] for r in active_years_query if r[0] is not None]

    if not active_years:
        return None

    games = session.execute(
        text(
            """
            SELECT 
                g.id,
                g.home_team_id,
                g.home_score,
                g.away_score
            FROM games g
            WHERE (g.home_team_id = :tid OR g.away_team_id = :tid)
              AND g.status = 'completed'
              AND EXTRACT(YEAR FROM g.game_date)::integer IN :years
        """
        ),
        {"tid": team_id, "years": tuple(active_years)},
    ).fetchall()

    if not games:
        return None

    played_game_ids = set()
    played_query = session.execute(
        text(
            """
            SELECT game_id 
            FROM player_history 
            WHERE player_id = :pid AND team_id = :tid
        """
        ),
        {"pid": player_id, "tid": team_id},
    ).fetchall()
    for r in played_query:
        played_game_ids.add(r[0])

    with_games = []
    without_games = []

    for g in games:
        game_id = g[0]
        home_team_id = g[1]
        home_score = g[2] or 0
        away_score = g[3] or 0

        is_home = home_team_id == team_id
        our_score = home_score if is_home else away_score
        opp_score = away_score if is_home else home_score

        margin = our_score - opp_score
        is_win = (
            1.0 if our_score > opp_score else (0.5 if our_score == opp_score else 0.0)
        )

        game_data = {"is_win": is_win, "margin": margin}

        if game_id in played_game_ids:
            with_games.append(game_data)
        else:
            without_games.append(game_data)

    games_with = len(with_games)
    games_without = len(without_games)

    win_rate_with = (
        sum(g["is_win"] for g in with_games) / games_with if games_with > 0 else 0.0
    )
    avg_margin_with = (
        sum(g["margin"] for g in with_games) / games_with if games_with > 0 else 0.0
    )

    win_rate_without = (
        sum(g["is_win"] for g in without_games) / games_without
        if games_without > 0
        else 0.5
    )
    avg_margin_without = (
        sum(g["margin"] for g in without_games) / games_without
        if games_without > 0
        else 0.0
    )

    margin_diff = avg_margin_with - avg_margin_without

    return {
        "games_with": games_with,
        "games_without": games_without,
        "win_rate_with": win_rate_with,
        "win_rate_without": win_rate_without,
        "margin_diff": margin_diff,
    }
