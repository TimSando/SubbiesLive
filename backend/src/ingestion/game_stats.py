"""Game statistics, events, and player history ingestion.

Fetches score sheets and game events, mapping them to local player
and team IDs before inserting or updating them in the database.
"""

import logging
from sqlalchemy import text
from src.ingestion.fusesport import get_game_info, get_score_sheet
from src.ingestion.transformers import transform_game_event
from src.ingestion.upserts import upsert_player

logger = logging.getLogger("ingestion")


def ingest_game_events(
    session,
    game_id: int,
    game_external_id: int,
    team_id_map: dict,
    game_info: dict | None = None,
):
    """Fetch and ingest game events for a completed/in-progress game.

    Accepts an optional pre-fetched game_info dict to avoid a redundant HTTP call
    when called alongside ingest_player_history_for_game.

    For completed games whose events are already fully ingested, skips the network
    call entirely so startup re-syncs stay fast.
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

    if status == "completed":
        existing_count = session.execute(
            text("SELECT COUNT(*) FROM game_events WHERE game_id = :gid"),
            {"gid": game_id},
        ).scalar()
        if existing_count > 0:
            logger.debug(
                f"  Skipping game_events fetch for game {game_external_id} — already ingested ({existing_count} events)"
            )
            return

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

                msg = event_data.get("text")
                if not msg:
                    msg = f"Game Event: {event_data['event_type'].replace('_', ' ').title()}"

                # Fetch current scores to append to the message body
                score_row = session.execute(
                    text("SELECT home_score, away_score FROM games WHERE id = :gid"),
                    {"gid": game_id},
                ).fetchone()
                if score_row:
                    hs, as_ = score_row
                    hs_val = hs if hs is not None else 0
                    as_val = as_ if as_ is not None else 0
                    msg += f" (Score: {hs_val} - {as_val})"

                notify_game_update(session, game_id, "event", msg)
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
            text("""
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
            """),
            {
                "pid": player_id,
                "gid": game_id,
                "tid": db_team_id,
                "pos": record.get("position_id"),
                "pnum": record.get("player_number"),
                "pts": record.get("points", 0),
                "tries": record.get("rugby_union_try", 0),
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
):
    """Fetch game details to get score sheet IDs and ingest history.

    Accepts an optional pre-fetched game_info dict to avoid a redundant HTTP call
    when called alongside ingest_game_events.

    For completed games whose player_history rows are already fully ingested for
    both teams, skips the network call entirely.
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

    if status == "completed":
        # Skip if both score sheets are already recorded in player_history.
        existing_sheets = session.execute(
            text(
                "SELECT COUNT(DISTINCT team_id) FROM player_history WHERE game_id = :gid"
            ),
            {"gid": game_id},
        ).scalar()
        if existing_sheets >= 2:
            logger.debug(
                f"  Skipping player_history fetch for game {game_external_id} — both score sheets already ingested"
            )
            return

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
