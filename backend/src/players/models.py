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
    team_history: Mapped[list["PlayerTeamHistory"]] = relationship("PlayerTeamHistory", back_populates="player")

    def __repr__(self) -> str:
        return f"<Player(id={self.id}, name='{self.name}')>"


class PlayerTeamHistory(Base):
    """Tracks which team a player was part of for a given competition."""

    __tablename__ = "player_team_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False, index=True)

    # Relationships
    player: Mapped["Player"] = relationship("Player", back_populates="team_history")
    team: Mapped["Team"] = relationship("Team", back_populates="player_history")

    def __repr__(self) -> str:
        return f"<PlayerTeamHistory(player_id={self.player_id}, team_id={self.team_id})>"
