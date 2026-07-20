"""ORM models for team ratings and odds system."""

from datetime import datetime
from sqlalchemy import ForeignKey, Integer, Float, Boolean, DateTime, func, String, UniqueConstraint
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


class GameSquad(Base):
    """Named squad rosters for upcoming games before they are played."""

    __tablename__ = "game_squads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"), nullable=False, index=True
    )
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"), nullable=False, index=True
    )
    player_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("game_id", "team_id", "player_id", name="uq_game_squads_game_team_player"),
    )

    # Relationships
    game: Mapped["Game"] = relationship("Game")
    team: Mapped["Team"] = relationship("Team")
    player: Mapped["Player"] = relationship("Player")

    def __repr__(self) -> str:
        return f"<GameSquad(game_id={self.game_id}, team_id={self.team_id}, player_id={self.player_id})>"


class PlayerImpactScore(Base):
    """Calculated impact score for a player within a team, either career or per-season."""

    __tablename__ = "player_impact_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"), nullable=False, index=True
    )
    club_id: Mapped[int] = mapped_column(
        ForeignKey("clubs.id"), nullable=False, index=True
    )
    competition_mapping_id: Mapped[int | None] = mapped_column(
        ForeignKey("competition_mapping.id"), nullable=True, index=True
    )
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # Core metrics
    impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    games_with: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    games_without: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    win_rate_with: Mapped[float | None] = mapped_column(Float, nullable=True)
    win_rate_without: Mapped[float | None] = mapped_column(Float, nullable=True)
    margin_diff: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Metadata
    confidence: Mapped[str] = mapped_column(String, nullable=False, default="low")
    last_calculated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("player_id", "team_id", "year", name="uq_player_impact_scores_player_team_year"),
    )

    # Relationships
    player: Mapped["Player"] = relationship("Player")
    team: Mapped["Team"] = relationship("Team")
    club: Mapped["Club"] = relationship("Club")
    competition_mapping: Mapped["CompetitionMapping"] = relationship("CompetitionMapping")

    def __repr__(self) -> str:
        return f"<PlayerImpactScore(player_id={self.player_id}, team_id={self.team_id}, year={self.year}, impact_score={self.impact_score})>"
