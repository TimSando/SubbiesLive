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
                    "auth": subscription["auth"]
                }
            },
            data=json.dumps(payload),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={
                "sub": settings.vapid_mailto
            }
        )
        logger.debug(f"Successfully sent push notification to {subscription['endpoint'][:30]}...")
    except WebPushException as ex:
        # 404 or 410 indicates the subscription has expired or is invalid
        if ex.response is not None and ex.response.status_code in [404, 410]:
            logger.info(f"Removing expired/invalid subscription: {subscription['endpoint'][:30]}...")
            # We open a separate database connection to delete the subscription
            from src.ingestion.engine import get_sync_engine
            engine = get_sync_engine()
            with engine.begin() as conn:
                conn.execute(
                    text("DELETE FROM pwa_subscriptions WHERE endpoint = :endpoint"),
                    {"endpoint": subscription["endpoint"]}
                )
        else:
            logger.error(f"WebPushException sending to {subscription['endpoint'][:30]}: {ex}")
    except Exception as e:
        logger.error(f"Error sending push notification to {subscription['endpoint'][:30]}: {e}")


def dispatch_push_notifications(title: str, body: str, url: str = "/"):
    """Fetch all PWA subscriptions and dispatch push notifications in a background thread."""
    from src.ingestion.engine import get_sync_engine
    engine = get_sync_engine()

    # Load all active subscriptions
    with engine.connect() as conn:
        result = conn.execute(text("SELECT endpoint, p256dh, auth FROM pwa_subscriptions"))
        subscriptions = [dict(row) for row in result.mappings()]

    if not subscriptions:
        logger.debug("No PWA push subscriptions registered. Skipping dispatch.")
        return

    logger.info(f"Dispatching push notifications to {len(subscriptions)} devices...")

    payload = {
        "title": title,
        "body": body,
        "url": url
    }

    # Dispatch to all devices in background threads to avoid blocking the ingestion process
    for sub in subscriptions:
        thread = threading.Thread(target=_send_webpush_sync, args=(engine, sub, payload), daemon=True)
        thread.start()


def notify_game_update(session, game_id: int, update_type: str, detail_message: str):
    """Notify users who subscribed to a game, its clubs, or its competition.
    
    Args:
        session: Synchronous DB session
        game_id: Internal game ID
        update_type: 'outcome' or 'event'
        detail_message: Body text for the push notification
    """
    # 1. Fetch game details: competition_id, home_club_id, away_club_id, team names, parent comp, division
    game_query = text("""
        SELECT 
            g.id,
            r.competition_id,
            ht.club_id AS home_club_id,
            at.club_id AS away_club_id,
            ht.name AS home_team_name,
            at.name AS away_team_name,
            m.parent_competition,
            m.division
        FROM games g
        JOIN rounds r ON g.round_id = r.id
        JOIN competitions c ON r.competition_id = c.id
        LEFT JOIN competition_mapping m ON c.competition_mapping_id = m.id
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE g.id = :gid
    """)
    res = session.execute(game_query, {"gid": game_id})
    row = res.fetchone()
    if not row:
        logger.warning(f"Could not notify update for game {game_id}: game not found in DB")
        return
        
    _, competition_id, home_club_id, away_club_id, home_team_name, away_team_name, parent_competition, division = row
    
    # 2. Query all unique subscriptions matching the topic rules
    sub_query = text("""
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
    """)
    
    params = {
        "game_id": game_id,
        "home_club_id": home_club_id,
        "away_club_id": away_club_id,
        "comp_id": competition_id,
        "utype": update_type
    }
    
    sub_res = session.execute(sub_query, params)
    subscriptions = [dict(r) for r in sub_res.mappings()]
    
    if not subscriptions:
        logger.debug(f"No subscribers for game {game_id} (update_type: {update_type}). Skipping dispatch.")
        return
        
    logger.info(f"Dispatching game update notifications to {len(subscriptions)} devices...")
    
    title = f"🏉 Update: {home_team_name} vs {away_team_name}"
    if update_type == "outcome":
        title = f"🏉 Full Time: {home_team_name} vs {away_team_name}"
        
    payload = {
        "title": title,
        "body": detail_message,
        "url": f"/games/{game_id}",
        "tag": f"game-{game_id}"  # To collapse notifications for the same game
    }
    
    from src.ingestion.engine import get_sync_engine
    engine = get_sync_engine()
    
    for sub in subscriptions:
        thread = threading.Thread(target=_send_webpush_sync, args=(engine, sub, payload), daemon=True)
        thread.start()

