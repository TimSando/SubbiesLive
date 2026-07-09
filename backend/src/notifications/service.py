"""Service functions for sending PWA push notifications."""

import json
import logging
import threading
from sqlalchemy import text
from pywebpush import webpush, WebPushException

from src.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _send_webpush_sync(session_factory, subscription, payload):
    """Perform the synchronous webpush post and handle errors/expiry."""
    try:
        webpush(
            subscription_info={
                "endpoint": subscription["endpoint"],
                "keys": {
                    "p256dh": subscription["p256dh"],
                    "auth": subscription["auth"],
                },
            },
            data=json.dumps(payload),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_mailto},
        )
        logger.debug(
            f"Successfully sent push notification to {subscription['endpoint'][:30]}..."
        )
    except WebPushException as ex:
        # 404 or 410 indicates the subscription has expired or is invalid.
        # 400 Bad Request with VapidPkHashMismatch indicates VAPID public key mismatch (e.g., keys changed).
        is_expired = ex.response is not None and ex.response.status_code in [404, 410]
        is_mismatch = (
            ex.response is not None
            and ex.response.status_code == 400
            and "VapidPkHashMismatch" in (ex.response.text or "")
        )

        if is_expired or is_mismatch:
            reason = "expired/invalid" if is_expired else "mismatched VAPID keys"
            logger.info(
                f"Removing {reason} subscription: {subscription['endpoint'][:30]}..."
            )
            # We open a separate database connection to delete the subscription
            from src.ingestion.engine import get_sync_engine

            engine = get_sync_engine()
            with engine.begin() as conn:
                conn.execute(
                    text("DELETE FROM pwa_subscriptions WHERE endpoint = :endpoint"),
                    {"endpoint": subscription["endpoint"]},
                )
        else:
            logger.error(
                f"WebPushException sending to {subscription['endpoint'][:30]}: {ex}"
            )
    except Exception as e:
        logger.error(
            f"Error sending push notification to {subscription['endpoint'][:30]}: {e}"
        )


def dispatch_push_notifications(title: str, body: str, url: str = "/"):
    """Fetch all PWA subscriptions and dispatch push notifications in a background thread."""
    from src.ingestion.engine import get_sync_engine

    engine = get_sync_engine()

    # Load all active subscriptions
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT endpoint, p256dh, auth FROM pwa_subscriptions")
        )
        subscriptions = [dict(row) for row in result.mappings()]

    if not subscriptions:
        logger.debug("No PWA push subscriptions registered. Skipping dispatch.")
        return

    logger.info(f"Dispatching push notifications to {len(subscriptions)} devices...")

    payload = {"title": title, "body": body, "url": url}

    # Dispatch to all devices in background threads to avoid blocking the ingestion process
    for sub in subscriptions:
        thread = threading.Thread(
            target=_send_webpush_sync, args=(engine, sub, payload), daemon=True
        )
        thread.start()


def notify_game_update(
    session,
    game_id: int,
    update_type: str,
    detail_message: str,
    event_club_name: str = "",
):
    """Notify users who subscribed to a game, its clubs, or its competition.

    Args:
        session: Synchronous DB session
        game_id: Internal game ID
        update_type: Type of update (e.g. 'Try', 'Yellow Card', 'Full Time')
        detail_message: Specific details (e.g. try scorer, card text)
        event_club_name: Club responsible for the event
    """
    # 1. Fetch game details including club names and scores
    game_query = text(
        """
        SELECT 
            g.id,
            g.home_score,
            g.away_score,
            r.competition_id,
            c.name AS competition_name,
            ht.club_id AS home_club_id,
            at.club_id AS away_club_id,
            ht.name AS home_team_name,
            at.name AS away_team_name,
            hc.name AS home_club_name,
            hc.short_name AS home_club_short_name,
            ac.name AS away_club_name,
            ac.short_name AS away_club_short_name,
            m.parent_competition,
            m.division
        FROM games g
        JOIN rounds r ON g.round_id = r.id
        JOIN competitions c ON r.competition_id = c.id
        LEFT JOIN competition_mapping m ON c.competition_mapping_id = m.id
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        LEFT JOIN clubs hc ON ht.club_id = hc.id
        LEFT JOIN clubs ac ON at.club_id = ac.id
        WHERE g.id = :gid
    """
    )
    res = session.execute(game_query, {"gid": game_id})
    row = res.fetchone()
    if not row:
        logger.warning(
            f"Could not notify update for game {game_id}: game not found in DB"
        )
        return

    home_score = row.home_score if row.home_score is not None else 0
    away_score = row.away_score if row.away_score is not None else 0
    home_name = row.home_club_short_name or row.home_club_name or row.home_team_name
    away_name = row.away_club_short_name or row.away_club_name or row.away_team_name
    competition_name = row.competition_name

    # 2. Query all unique subscriptions matching the topic rules
    sub_query = text(
        """
        SELECT DISTINCT s.endpoint, s.p256dh, s.auth
        FROM pwa_subscriptions s
        JOIN pwa_subscription_topics t ON s.id = t.subscription_id
        WHERE (
            (t.topic_type = 'game' AND t.topic_id = :game_id)
            OR (t.topic_type = 'club' AND t.topic_id IN (:home_club_id, :away_club_id))
            OR (t.topic_type = 'competition' AND t.topic_id = :comp_id)
        )
        AND (
            (:utype = 'outcome' AND t.notify_outcome = TRUE)
            OR (:utype = 'event' AND t.notify_events = TRUE)
        )
    """
    )

    db_utype = "outcome" if update_type.lower() in ("outcome", "full time") else "event"

    params = {
        "game_id": game_id,
        "home_club_id": row.home_club_id,
        "away_club_id": row.away_club_id,
        "comp_id": row.competition_id,
        "utype": db_utype,
    }

    sub_res = session.execute(sub_query, params)
    subscriptions = [dict(r) for r in sub_res.mappings()]

    if not subscriptions:
        logger.debug(
            f"No subscribers for game {game_id} (update_type: {update_type}). Skipping dispatch."
        )
        return

    logger.info(
        f"Dispatching game update notifications to {len(subscriptions)} devices..."
    )

    # 3. Build the Smartwatch-Optimized Title
    title = f"{home_name} {home_score} - {away_score} {away_name}"

    # 4. Build the Contextual Body
    if event_club_name and detail_message:
        body = f"{competition_name} • {event_club_name} {update_type} {detail_message}"
    elif event_club_name:
        body = f"{competition_name} • {event_club_name} {update_type}"
    elif detail_message:
        body = f"{competition_name} • {update_type} {detail_message}"
    else:
        body = f"{competition_name} • {update_type}"

    payload = {
        "title": title,
        "body": body,
        "url": f"/games/{game_id}",
        "tag": f"game-{game_id}",  # To collapse notifications for the same game
    }

    from src.ingestion.engine import get_sync_engine

    engine = get_sync_engine()

    for sub in subscriptions:
        thread = threading.Thread(
            target=_send_webpush_sync, args=(engine, sub, payload), daemon=True
        )
        thread.start()
