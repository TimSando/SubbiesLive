"""Database upsert helpers for the ingestion pipeline.

All functions accept a synchronous SQLAlchemy session and use raw SQL
via text() for performance. Each function is idempotent — safe to call
multiple times with the same data.
"""

import logging
from sqlalchemy import text
from src.ingestion.transformers import extract_round_number

logger = logging.getLogger("ingestion")


def upsert_club(
    session, club_name: str, logo_url: str = None, competition_id: int = None
) -> int | None:
    if not club_name:
        return None

    result = session.execute(
        text("SELECT id, competition_mapping_id FROM clubs WHERE name = :name"),
        {"name": club_name},
    )
    row = result.fetchone()

    mapping_id = None
    if competition_id:
        comp_res = session.execute(
            text("SELECT competition_mapping_id FROM competitions WHERE id = :cid"),
            {"cid": competition_id},
        )
        mapping_id = comp_res.scalar()

    if row:
        club_id = row[0]
        if mapping_id and not row[1]:
            session.execute(
                text("UPDATE clubs SET competition_mapping_id = :mid WHERE id = :id"),
                {"mid": mapping_id, "id": club_id},
            )
            session.commit()
        return club_id

    result = session.execute(
        text(
            "INSERT INTO clubs (name, short_name, logo_url, competition_mapping_id) VALUES (:name, :short_name, :logo_url, :mid) RETURNING id"
        ),
        {
            "name": club_name,
            "short_name": club_name,
            "logo_url": logo_url,
            "mid": mapping_id,
        },
    )
    session.commit()
    return result.fetchone()[0]


def upsert_competition(session, external_id: int, name: str) -> int:
    result = session.execute(
        text("SELECT id FROM competitions WHERE external_id = :eid"),
        {"eid": external_id},
    )
    row = result.fetchone()
    if row:
        return row[0]

    # Try to find a mapping
    mapping_res = session.execute(
        text("SELECT id FROM competition_mapping WHERE name = :name"), {"name": name}
    )
    mapping_row = mapping_res.fetchone()
    mapping_id = mapping_row[0] if mapping_row else None

    result = session.execute(
        text(
            "INSERT INTO competitions (name, external_id, competition_mapping_id) VALUES (:name, :eid, :mid) RETURNING id"
        ),
        {"name": name, "eid": external_id, "mid": mapping_id},
    )
    session.commit()
    return result.fetchone()[0]


def upsert_round(session, competition_id: int, external_id: int, name: str) -> int:
    result = session.execute(
        text("SELECT id FROM rounds WHERE external_id = :eid"), {"eid": external_id}
    )
    row = result.fetchone()
    if row:
        return row[0]

    number = extract_round_number(name)
    result = session.execute(
        text("""INSERT INTO rounds (competition_id, name, number, external_id) 
                VALUES (:cid, :name, :number, :eid) RETURNING id"""),
        {"cid": competition_id, "name": name, "number": number, "eid": external_id},
    )
    session.commit()
    return result.fetchone()[0]


def upsert_team(
    session,
    external_id: int,
    name: str,
    club_name: str,
    competition_id: int,
    logo_url: str = None,
) -> int:
    result = session.execute(
        text("SELECT id FROM teams WHERE external_id = :eid"), {"eid": external_id}
    )
    row = result.fetchone()
    if row:
        return row[0]

    club_id = upsert_club(session, club_name, logo_url, competition_id)
    if not club_id:
        logger.debug(
            f"Skipping team {name} ({external_id}) as no valid club could be determined"
        )
        return None
    result = session.execute(
        text("""INSERT INTO teams (club_id, competition_id, name, external_id) 
                VALUES (:club_id, :comp_id, :name, :eid) RETURNING id"""),
        {
            "club_id": club_id,
            "comp_id": competition_id,
            "name": name,
            "eid": external_id,
        },
    )
    session.commit()
    return result.fetchone()[0]


def upsert_game(
    session, round_id: int, game_data: dict, home_team_id: int, away_team_id: int
) -> int:
    result = session.execute(
        text(
            "SELECT id, home_score, away_score, status FROM games WHERE external_id = :eid"
        ),
        {"eid": game_data["external_id"]},
    )
    row = result.fetchone()

    if row:
        stored_id, stored_hs, stored_as, stored_status = row
        # Check if anything changed: status, home_score, or away_score
        if (
            game_data["status"] != stored_status
            or game_data["home_score"] != stored_hs
            or game_data["away_score"] != stored_as
        ):
            session.execute(
                text(
                    """UPDATE games SET home_score = :hs, away_score = :as_, status = :status 
                        WHERE id = :id"""
                ),
                {
                    "hs": game_data["home_score"],
                    "as_": game_data["away_score"],
                    "status": game_data["status"],
                    "id": stored_id,
                },
            )
            session.commit()
            logger.info(
                f"Updated game {game_data['external_id']} (status: {stored_status} -> {game_data['status']}, score: {stored_hs}-{stored_as} -> {game_data['home_score']}-{game_data['away_score']})"
            )

            # Dispatch target-filtered push notifications on update
            try:
                hs_str = (
                    str(game_data["home_score"])
                    if game_data["home_score"] is not None
                    else "0"
                )
                as_str = (
                    str(game_data["away_score"])
                    if game_data["away_score"] is not None
                    else "0"
                )

                from src.notifications.service import notify_game_update

                # 1. Match started (kick-off)
                if (
                    game_data["status"] == "in_progress"
                    and stored_status == "scheduled"
                ):
                    msg = f"Match started! Score: {hs_str} - {as_str}"
                    notify_game_update(session, stored_id, "event", msg)

                # 2. Match completed (full time)
                elif (
                    game_data["status"] == "completed" and stored_status != "completed"
                ):
                    msg = f"Full Time! Final Score: {hs_str} - {as_str}"
                    notify_game_update(session, stored_id, "outcome", msg)

                # 3. Simple live score update during play
                elif game_data["status"] == "in_progress" and (
                    game_data["home_score"] != stored_hs
                    or game_data["away_score"] != stored_as
                ):
                    msg = f"Score update: {hs_str} - {as_str}"
                    notify_game_update(session, stored_id, "event", msg)

            except Exception as e:
                logger.error(f"Failed to dispatch game update notifications: {e}")

        return stored_id

    result = session.execute(
        text("""INSERT INTO games (round_id, home_team_id, away_team_id, game_date, 
                location, home_score, away_score, status, external_id) 
                VALUES (:rid, :htid, :atid, :gd, :loc, :hs, :as_, :status, :eid) 
                RETURNING id"""),
        {
            "rid": round_id,
            "htid": home_team_id,
            "atid": away_team_id,
            "gd": game_data["game_date"],
            "loc": game_data["location"],
            "hs": game_data["home_score"],
            "as_": game_data["away_score"],
            "status": game_data["status"],
            "eid": game_data["external_id"],
        },
    )
    session.commit()
    return result.fetchone()[0]


def upsert_player(session, player_data: dict) -> int | None:
    if not player_data:
        return None

    result = session.execute(
        text("SELECT id FROM players WHERE external_id = :eid"),
        {"eid": player_data["external_id"]},
    )
    row = result.fetchone()
    if row:
        return row[0]

    dob = None
    if player_data.get("dob"):
        try:
            from dateutil import parser as dateparser

            dob = dateparser.parse(player_data["dob"]).date()
        except (ValueError, TypeError):
            pass

    result = session.execute(
        text("""INSERT INTO players (name, dob, image_url, thumbnail_url, external_id) 
                VALUES (:name, :dob, :img, :thumb, :eid) RETURNING id"""),
        {
            "name": player_data["name"],
            "dob": dob,
            "img": player_data.get("image_url"),
            "thumb": player_data.get("thumbnail_url"),
            "eid": player_data["external_id"],
        },
    )
    session.commit()
    return result.fetchone()[0]
