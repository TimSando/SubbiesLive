"""Game statistics, events, and player history ingestion.

Fetches score sheets and game events, mapping them to local player
and team IDs before inserting or updating them in the database.
"""

import logging
from datetime import datetime
from enum import Enum
from sqlalchemy import text
from src.ingestion.fusesport import get_game_info, get_score_sheet
from src.ingestion.transformers import transform_game_event
from src.ingestion.upserts import upsert_player

logger = logging.getLogger("ingestion")


class SyncMode(str, Enum):
    FAST = "fast"  # skip all completed games already in DB
    LIVE_ONLY = "live_only"  # only today's games
    RECENT = "recent"  # re-fetch if game_date within 14 days
    FULL = "full"  # re-fetch everything


def ingest_game_events(
    session,
    game_id: int,
    game_external_id: int,
    team_id_map: dict,
    game_info: dict | None = None,
    game_date: datetime | None = None,
    sync_mode: SyncMode = SyncMode.FAST,
):
    """Fetch and ingest game events for a completed/in-progress game.

    Accepts an optional pre-fetched game_info dict to avoid a redundant HTTP call
    when called alongside ingest_player_history_for_game.
    """
    # Fetch status of the game from the DB
    status = session.execute(
        text("SELECT status FROM games WHERE id = :gid"), {"gid": game_id}
    ).scalar()

    if status == "not_completed":
        logger.debug(
            f"  Skipping game_events fetch for game {game_external_id} — game status is not_completed"
        )
        return

    # In LIVE_ONLY mode, only process games played today
    if sync_mode == SyncMode.LIVE_ONLY:
        is_today = game_date is not None and game_date.date() == datetime.now().date()
        if not is_today:
            logger.debug(
                f"  Skipping game_events fetch for game {game_external_id} — not played today (LIVE_ONLY mode)"
            )
            return

    if status == "completed":
        existing_count = session.execute(
            text("SELECT COUNT(*) FROM game_events WHERE game_id = :gid"),
            {"gid": game_id},
        ).scalar()
        if existing_count > 0:
            if sync_mode == SyncMode.FAST:
                logger.debug(
                    f"  Skipping game_events fetch for game {game_external_id} — already ingested (FAST mode)"
                )
                return
            elif sync_mode == SyncMode.RECENT:
                is_recent = (
                    game_date is not None
                    and (datetime.now() - game_date.replace(tzinfo=None)).days <= 14
                )
                if not is_recent:
                    logger.debug(
                        f"  Skipping game_events fetch for game {game_external_id} "
                        f"— already ingested ({existing_count} events) and game is older than 14 days"
                    )
                    return
                logger.debug(
                    f"  Re-fetching game_events for recent game {game_external_id} "
                    f"({existing_count} events already stored) to pick up any corrections"
                )
            elif sync_mode == SyncMode.FULL:
                logger.debug(
                    f"  Re-fetching game_events for game {game_external_id} (FULL mode)"
                )

    if game_info is None:
        try:
            game_info = get_game_info(game_external_id)
        except Exception as e:
            logger.warning(f"Failed to fetch game {game_external_id} details: {e}")
            return

    events_ingested = 0
    for score_sheet_key in ["home_score_sheet", "away_score_sheet"]:
        score_sheet = game_info.get(score_sheet_key, {})
        if not score_sheet:
            continue

        sheet_team_ext_id = score_sheet.get("team_id")

        for raw_event in score_sheet.get("game_events", []):
            if raw_event.get("team_id") != sheet_team_ext_id:
                continue

            event_data = transform_game_event(raw_event, game_external_id)

            team_ext_id = event_data["team_external_id"]
            db_team_id = team_id_map.get(team_ext_id)
            if not db_team_id:
                continue

            player_id = upsert_player(session, event_data.get("player"))

            result = session.execute(
                text("SELECT id FROM game_events WHERE external_id = :eid"),
                {"eid": str(event_data["external_id"])},
            )
            if result.fetchone():
                continue

            session.execute(
                text(
                    """INSERT INTO game_events (game_id, team_id, player_id, event_type, 
                        player_number, points, text, external_created_at, external_id) 
                        VALUES (:gid, :tid, :pid, :et, :pn, :pts, :txt, :eca, :eid)"""
                ),
                {
                    "gid": game_id,
                    "tid": db_team_id,
                    "pid": player_id,
                    "et": event_data["event_type"],
                    "pn": event_data["player_number"],
                    "pts": event_data["points"],
                    "txt": event_data["text"],
                    "eca": event_data["external_created_at"],
                    "eid": str(event_data["external_id"]),
                },
            )
            events_ingested += 1

            # Notify of this live game event
            try:
                from src.notifications.service import notify_game_update

                home_team = game_info.get("home_team", {})
                away_team = game_info.get("away_team", {})
                event_team = (
                    home_team
                    if sheet_team_ext_id == home_team.get("external_id")
                    else away_team
                )
                event_club_name = event_team.get("club_name") or event_team.get(
                    "name", ""
                )

                event_type_str = event_data["event_type"].replace("_", " ").title()
                detail_msg = event_data.get("text") or ""

                notify_game_update(
                    session=session,
                    game_id=game_id,
                    update_type=event_type_str,
                    detail_message=detail_msg,
                    event_club_name=event_club_name,
                )
            except Exception as e:
                logger.error(f"Failed to dispatch notification for game event: {e}")

    session.commit()
    if events_ingested > 0:
        logger.info(f"  Ingested {events_ingested} events for game {game_external_id}")


def ingest_player_history(
    session, game_id: int, score_sheet_id: str, team_id_map: dict
):
    """Fetch a score sheet and upsert player_history records.

    Args:
        session:        SQLAlchemy session
        game_id:        Internal DB game ID
        score_sheet_id: FuseSport UUID for the score sheet
        team_id_map:    Dict mapping external team IDs -> internal team DB IDs
    """
    try:
        records = get_score_sheet(score_sheet_id)
    except Exception as e:
        logger.warning(f"Failed to fetch score sheet {score_sheet_id}: {e}")
        return

    if not records:
        return

    # Find the team ID represented by this score sheet to verify if we already ingested it
    db_team_id = None
    for record in records:
        team_ext_id = record.get("team_id")
        if team_ext_id:
            resolved_id = team_id_map.get(team_ext_id)
            if resolved_id:
                db_team_id = resolved_id
                break

    # Fetch status of the game from the DB
    status = session.execute(
        text("SELECT status FROM games WHERE id = :gid"), {"gid": game_id}
    ).scalar()

    if status == "not_completed":
        return

    if status == "completed" and db_team_id:
        existing = session.execute(
            text(
                "SELECT COUNT(*) FROM player_history WHERE game_id = :gid AND team_id = :tid"
            ),
            {"gid": game_id, "tid": db_team_id},
        ).scalar()
        if existing > 0:
            return  # Already processed this score sheet

    inserted = 0
    for record in records:
        member = record.get("member")
        if not member:
            continue  # Skip empty roster slots

        # Resolve player (upsert via existing helper)
        player_data = {
            "external_id": member["id"],
            "name": member["name"],
            "dob": member.get("dob"),
            "image_url": member.get("image"),
            "thumbnail_url": member.get("thumbnail"),
        }
        player_id = upsert_player(session, player_data)
        if not player_id:
            continue

        # Resolve internal team ID
        team_ext_id = record.get("team_id")
        db_team_id = team_id_map.get(team_ext_id)
        if not db_team_id:
            logger.debug(
                f"  Skipping player {member['name']}: unknown team ext_id {team_ext_id}"
            )
            continue

        # Upsert the player_history record
        session.execute(
            text(
                """
                INSERT INTO player_history (
                    player_id, game_id, team_id, position_id, player_number, points,
                    tries, conversions, penalty_goals, drop_goals,
                    yellow_cards, red_cards, blue_cards,
                    medal_points_1, medal_points_2, medal_points_3,
                    coach_points_1, coach_points_2, coach_points_3,
                    card_text
                ) VALUES (
                    :pid, :gid, :tid, :pos, :pnum, :pts,
                    :tries, :conv, :pen, :dg,
                    :yc, :rc, :bc,
                    :m1, :m2, :m3,
                    :c1, :c2, :c3,
                    :ctext
                )
                ON CONFLICT (player_id, game_id, team_id) DO UPDATE SET
                    points        = EXCLUDED.points,
                    tries         = EXCLUDED.tries,
                    conversions   = EXCLUDED.conversions,
                    penalty_goals = EXCLUDED.penalty_goals,
                    drop_goals    = EXCLUDED.drop_goals,
                    yellow_cards  = EXCLUDED.yellow_cards,
                    red_cards     = EXCLUDED.red_cards,
                    blue_cards    = EXCLUDED.blue_cards,
                    medal_points_1 = EXCLUDED.medal_points_1,
                    medal_points_2 = EXCLUDED.medal_points_2,
                    medal_points_3 = EXCLUDED.medal_points_3,
                    coach_points_1 = EXCLUDED.coach_points_1,
                    coach_points_2 = EXCLUDED.coach_points_2,
                    coach_points_3 = EXCLUDED.coach_points_3,
                    card_text     = EXCLUDED.card_text
            """
            ),
            {
                "pid": player_id,
                "gid": game_id,
                "tid": db_team_id,
                "pos": record.get("position_id"),
                "pnum": record.get("player_number"),
                "pts": record.get("points", 0),
                "tries": record.get("rugby_union_try", 0)
                + record.get("rugby_union_penalty_try", 0),
                "conv": record.get("rugby_union_conversion", 0),
                "pen": record.get("rugby_union_penalty_goal", 0),
                "dg": record.get("rugby_union_drop_goal", 0),
                "yc": record.get("rugby_union_yellow_card", 0),
                "rc": record.get("rugby_union_red_card", 0),
                "bc": record.get("rugby_union_blue_card", 0),
                "m1": record.get("rugby_union_medal_points_1", 0),
                "m2": record.get("rugby_union_medal_points_2", 0),
                "m3": record.get("rugby_union_medal_points_3", 0),
                "c1": record.get("rugby_union_coach_points_1", 0),
                "c2": record.get("rugby_union_coach_points_2", 0),
                "c3": record.get("rugby_union_coach_points_3", 0),
                "ctext": record.get("card_text") or None,
            },
        )
        inserted += 1

    session.commit()
    if inserted > 0:
        logger.info(
            f"  Ingested {inserted} player_history rows for score sheet {score_sheet_id}"
        )


def ingest_player_history_for_game(
    session,
    game_id: int,
    game_external_id: int,
    team_id_map: dict,
    game_info: dict | None = None,
    game_date: datetime | None = None,
    sync_mode: SyncMode = SyncMode.FAST,
):
    """Fetch game details to get score sheet IDs and ingest history.

    Accepts an optional pre-fetched game_info dict to avoid a redundant HTTP call
    when called alongside ingest_game_events.
    """
    # Fetch status of the game from the DB
    status = session.execute(
        text("SELECT status FROM games WHERE id = :gid"), {"gid": game_id}
    ).scalar()

    if status == "not_completed":
        logger.debug(
            f"  Skipping player_history fetch for game {game_external_id} — game status is not_completed"
        )
        return

    # In LIVE_ONLY mode, only process games played today
    if sync_mode == SyncMode.LIVE_ONLY:
        is_today = game_date is not None and game_date.date() == datetime.now().date()
        if not is_today:
            logger.debug(
                f"  Skipping player_history fetch for game {game_external_id} — not played today (LIVE_ONLY mode)"
            )
            return

    if status == "completed":
        # Skip check if we already ingested both sheets
        existing_sheets = session.execute(
            text(
                "SELECT COUNT(DISTINCT team_id) FROM player_history WHERE game_id = :gid"
            ),
            {"gid": game_id},
        ).scalar()
        if existing_sheets >= 2:
            if sync_mode == SyncMode.FAST:
                logger.debug(
                    f"  Skipping player_history fetch for game {game_external_id} — both score sheets already ingested (FAST mode)"
                )
                return
            elif sync_mode == SyncMode.RECENT:
                is_recent = (
                    game_date is not None
                    and (datetime.now() - game_date.replace(tzinfo=None)).days <= 14
                )
                if not is_recent:
                    logger.debug(
                        f"  Skipping player_history fetch for game {game_external_id} "
                        f"— both score sheets already ingested and game is older than 14 days"
                    )
                    return
                logger.debug(
                    f"  Re-fetching player_history for recent game {game_external_id} "
                    f"to pick up any corrections"
                )
            elif sync_mode == SyncMode.FULL:
                logger.debug(
                    f"  Re-fetching player_history for game {game_external_id} (FULL mode)"
                )

    if game_info is None:
        try:
            game_info = get_game_info(game_external_id)
        except Exception as e:
            logger.warning(
                f"Failed to fetch game {game_external_id} details for history: {e}"
            )
            return

    for sheet_key in ["home_score_sheet", "away_score_sheet"]:
        sheet = game_info.get(sheet_key, {})
        sheet_id = sheet.get("id")
        if sheet_id:
            ingest_player_history(session, game_id, sheet_id, team_id_map)


def ingest_game_squads(
    session,
    game_id: int,
    game_external_id: int,
    team_id_map: dict,
):
    """Fetch score sheets for a scheduled game and store the named squad.

    Only writes to game_squads (not player_history) — roster data only,
    no stats. Uses ON CONFLICT to handle re-runs cleanly.
    """
    try:
        game_info = get_game_info(game_external_id)
    except Exception as e:
        logger.debug(f"  No squad data available for scheduled game {game_external_id}: {e}")
        return

    for sheet_key in ["home_score_sheet", "away_score_sheet"]:
        sheet = game_info.get(sheet_key, {})
        sheet_id = sheet.get("id")
        if not sheet_id:
            continue

        try:
            records = get_score_sheet(sheet_id)
        except Exception:
            continue

        if not records:
            continue

        for record in records:
            member = record.get("member")
            if not member:
                continue

            player_id = upsert_player(session, {
                "external_id": member["id"],
                "name": member["name"],
                "dob": member.get("dob"),
                "image_url": member.get("image"),
                "thumbnail_url": member.get("thumbnail"),
            })
            if not player_id:
                continue

            team_ext_id = record.get("team_id")
            db_team_id = team_id_map.get(team_ext_id)
            if not db_team_id:
                continue

            session.execute(
                text("""
                    INSERT INTO game_squads (game_id, team_id, player_id, player_number, position_id)
                    VALUES (:gid, :tid, :pid, :pnum, :pos)
                    ON CONFLICT (game_id, team_id, player_id) DO UPDATE SET
                        player_number = EXCLUDED.player_number,
                        position_id = EXCLUDED.position_id
                """),
                {
                    "gid": game_id,
                    "tid": db_team_id,
                    "pid": player_id,
                    "pnum": record.get("player_number"),
                    "pos": record.get("position_id"),
                },
            )

    session.commit()
