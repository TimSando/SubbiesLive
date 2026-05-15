"""Game and GameEvent domain ORM models."""

import uuid

from datetime import datetime
from sqlalchemy import ForeignKey, Integer, String, DateTime, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class Game(Base):
    """A single match between two teams in a round."""

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"), nullable=False, index=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False, index=True)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False, index=True)
    game_date: Mapped[str] = mapped_column(DateTime, nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="scheduled")
    external_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)

    # Relationships
    round: Mapped["Round"] = relationship("Round", back_populates="games")
    home_team: Mapped["Team"] = relationship("Team", foreign_keys=[home_team_id], back_populates="home_games")
    away_team: Mapped["Team"] = relationship("Team", foreign_keys=[away_team_id], back_populates="away_games")
    events: Mapped[list["GameEvent"]] = relationship("GameEvent", back_populates="game", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Game(id={self.id}, external_id={self.external_id}, status='{self.status}')>"


class GameEvent(Base):
    """A scoring or disciplinary event within a game.

    Event types: try, conversion, penalty_goal, drop_goal, yellow_card, red_card
    """

    __tablename__ = "game_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False, index=True)
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    player_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)

    # Relationships
    game: Mapped["Game"] = relationship("Game", back_populates="events")
    team: Mapped["Team"] = relationship("Team")
    player: Mapped["Player | None"] = relationship("Player", back_populates="events")

    def __repr__(self) -> str:
        return f"<GameEvent(id={self.id}, type='{self.event_type}', points={self.points})>"
