"""ORM models for team ratings and odds system."""

from datetime import datetime
from sqlalchemy import ForeignKey, Integer, Float, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class TeamRatingHistory(Base):
    """Historical record of a team's rating after each completed game."""

    __tablename__ = "team_rating_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"), nullable=False, index=True
    )
    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id"), nullable=False, index=True
    )
    competition_mapping_id: Mapped[int | None] = mapped_column(
        ForeignKey("competition_mapping.id"), nullable=True, index=True
    )
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id"), nullable=False, index=True
    )
    rating_before: Mapped[float] = mapped_column(Float, nullable=False)
    rating_after: Mapped[float] = mapped_column(Float, nullable=False)
    opponent_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"), nullable=False, index=True
    )
    opponent_rating: Mapped[float] = mapped_column(Float, nullable=False)
    expected_result: Mapped[float] = mapped_column(Float, nullable=False)
    actual_result: Mapped[float] = mapped_column(Float, nullable=False)
    home_advantage_applied: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationships
    team: Mapped["Team"] = relationship("Team", foreign_keys=[team_id])
    club: Mapped["Club"] = relationship("Club")
    game: Mapped["Game"] = relationship("Game", foreign_keys=[game_id])
    opponent_team: Mapped["Team"] = relationship(
        "Team", foreign_keys=[opponent_team_id]
    )

    def __repr__(self) -> str:
        return f"<TeamRatingHistory(team_id={self.team_id}, rating_after={self.rating_after}, game_id={self.game_id})>"
