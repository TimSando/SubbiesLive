"""PWA push notification subscriptions router."""

import logging
from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import select

from src.core.config import get_settings
from src.core.dependencies import DbSession
from src.notifications.models import PwaSubscription

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionInput(BaseModel):
    endpoint: str
    keys: PushKeys


@router.get("/vapid-public-key")
async def get_vapid_public_key():
    """Return the VAPID Public Key for client-side subscription initialization."""
    return {"publicKey": settings.vapid_public_key}


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe_user(db: DbSession, sub_input: PushSubscriptionInput):
    """Store an anonymous browser push subscription in the database."""
    # Check if subscription already exists
    stmt = select(PwaSubscription).where(PwaSubscription.endpoint == sub_input.endpoint)
    result = await db.execute(stmt)
    existing_sub = result.scalars().first()

    if existing_sub:
        logger.info(f"Subscription already registered: {sub_input.endpoint[:30]}...")
        # Update keys just in case they refreshed
        existing_sub.p256dh = sub_input.keys.p256dh
        existing_sub.auth = sub_input.keys.auth
        return {"status": "success", "message": "Subscription updated"}

    # Create new subscription
    new_sub = PwaSubscription(
        endpoint=sub_input.endpoint,
        p256dh=sub_input.keys.p256dh,
        auth=sub_input.keys.auth
    )
    db.add(new_sub)
    logger.info(f"Registered new PWA push subscription: {sub_input.endpoint[:30]}...")
    return {"status": "success", "message": "Subscription registered"}
