"""PWA push notification subscriptions router."""

import logging
from fastapi import APIRouter, status, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete

from src.core.config import get_settings
from src.core.dependencies import DbSession
from src.notifications.models import PwaSubscription, PwaSubscriptionTopic
from src.clubs.models import Club
from src.competitions.models import Competition
from src.games.models import Game

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionInput(BaseModel):
    endpoint: str
    keys: PushKeys


class MySubscriptionsInput(BaseModel):
    endpoint: str


class ToggleTopicInput(BaseModel):
    endpoint: str
    topic_type: str  # 'club', 'competition', 'game'
    topic_id: int
    subscribe: bool
    notify_outcome: bool = True
    notify_events: bool = False


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


@router.post("/my-subscriptions")
async def get_my_subscriptions(db: DbSession, payload: MySubscriptionsInput):
    """Fetch all subscription topics registered for a given device endpoint."""
    stmt = select(PwaSubscription).where(PwaSubscription.endpoint == payload.endpoint)
    res = await db.execute(stmt)
    sub = res.scalars().first()
    if not sub:
        return {"subscriptions": []}

    topic_stmt = select(PwaSubscriptionTopic).where(PwaSubscriptionTopic.subscription_id == sub.id)
    topic_res = await db.execute(topic_stmt)
    topics = topic_res.scalars().all()

    result = []
    for t in topics:
        topic_name = "Unknown"
        if t.topic_type == "club":
            club_res = await db.execute(select(Club.name).where(Club.id == t.topic_id))
            topic_name = club_res.scalar() or "Unknown Club"
        elif t.topic_type == "competition":
            comp_res = await db.execute(select(Competition.name).where(Competition.id == t.topic_id))
            topic_name = comp_res.scalar() or "Unknown Competition"
        elif t.topic_type == "game":
            from sqlalchemy.orm import aliased
            from src.clubs.models import Team
            HomeTeam = aliased(Team)
            AwayTeam = aliased(Team)
            game_stmt = (
                select(HomeTeam.name, AwayTeam.name)
                .select_from(Game)
                .join(HomeTeam, Game.home_team_id == HomeTeam.id)
                .join(AwayTeam, Game.away_team_id == AwayTeam.id)
                .where(Game.id == t.topic_id)
            )
            game_res = await db.execute(game_stmt)
            game_row = game_res.fetchone()
            if game_row:
                home_team, away_team = game_row
                topic_name = f"{home_team} vs {away_team}"
            else:
                topic_name = "Unknown Match"

        result.append({
            "topic_type": t.topic_type,
            "topic_id": t.topic_id,
            "topic_name": topic_name,
            "notify_outcome": t.notify_outcome,
            "notify_events": t.notify_events
        })

    return {"subscriptions": result}


@router.post("/toggle-topic")
async def toggle_topic(db: DbSession, payload: ToggleTopicInput):
    """Subscribe or unsubscribe a device to/from a specific topic."""
    stmt = select(PwaSubscription).where(PwaSubscription.endpoint == payload.endpoint)
    res = await db.execute(stmt)
    sub = res.scalars().first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Push subscription not found. Please enable push notifications on your device first."
        )

    if payload.subscribe:
        topic_stmt = select(PwaSubscriptionTopic).where(
            PwaSubscriptionTopic.subscription_id == sub.id,
            PwaSubscriptionTopic.topic_type == payload.topic_type,
            PwaSubscriptionTopic.topic_id == payload.topic_id
        )
        topic_res = await db.execute(topic_stmt)
        existing_topic = topic_res.scalars().first()

        if existing_topic:
            existing_topic.notify_outcome = payload.notify_outcome
            existing_topic.notify_events = payload.notify_events
        else:
            new_topic = PwaSubscriptionTopic(
                subscription_id=sub.id,
                topic_type=payload.topic_type,
                topic_id=payload.topic_id,
                notify_outcome=payload.notify_outcome,
                notify_events=payload.notify_events
            )
            db.add(new_topic)
        await db.commit()
    else:
        delete_stmt = delete(PwaSubscriptionTopic).where(
            PwaSubscriptionTopic.subscription_id == sub.id,
            PwaSubscriptionTopic.topic_type == payload.topic_type,
            PwaSubscriptionTopic.topic_id == payload.topic_id
        )
        await db.execute(delete_stmt)
        await db.commit()

    return {"status": "success"}
