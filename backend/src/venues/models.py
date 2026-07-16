"""Venue domain ORM model."""

from sqlalchemy import Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class Venue(Base):
    """A match venue / ground (e.g., Woollahra Oval, Forsyth Park)."""

    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    games: Mapped[list["Game"]] = relationship("Game", back_populates="venue")
    clubs: Mapped[list["Club"]] = relationship("Club", back_populates="primary_venue")

    def __repr__(self) -> str:
        return f"<Venue(id={self.id}, name='{self.name}')>"
