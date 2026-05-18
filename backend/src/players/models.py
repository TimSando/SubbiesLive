"""Player domain ORM models."""

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class Player(Base):
    """A registered player."""

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    dob: Mapped[str | None] = mapped_column(Date, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    external_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)

    # Relationships
    events: Mapped[list["GameEvent"]] = relationship("GameEvent", back_populates="player")

    def __repr__(self) -> str:
        return f"<Player(id={self.id}, name='{self.name}')>"
