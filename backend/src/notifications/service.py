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
