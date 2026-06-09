"""PWA push notification subscriptions ORM model."""

from datetime import datetime
from sqlalchemy import (
    Integer,
    String,
    DateTime,
    Text,
    func,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class PwaSubscription(Base):
    """PWA Push subscription details."""

    __tablename__ = "pwa_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    endpoint: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    p256dh: Mapped[str] = mapped_column(String(300), nullable=False)
    auth: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<PwaSubscription(id={self.id}, endpoint='{self.endpoint[:30]}...')>"


class PwaSubscriptionTopic(Base):
    """Anonymous subscription to a specific club, competition, or game."""

    __tablename__ = "pwa_subscription_topics"
    __table_args__ = (
        UniqueConstraint(
            "subscription_id", "topic_type", "topic_id", name="uq_subscription_topic"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("pwa_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'club', 'competition', 'game'
    topic_id: Mapped[int] = mapped_column(Integer, nullable=False)
    notify_outcome: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_events: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<PwaSubscriptionTopic(id={self.id}, subscription_id={self.subscription_id}, type='{self.topic_type}', topic_id={self.topic_id})>"
