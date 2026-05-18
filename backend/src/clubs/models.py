"""Club and Team domain ORM models."""

from sqlalchemy import ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class Club(Base):
    """A rugby union club (e.g., Mosman, Randwick).

    A club is the organisation; it fields teams in different competitions.
    """

    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    short_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    competition_mapping_id: Mapped[int | None] = mapped_column(ForeignKey("competition_mapping.id"), nullable=True)
    
    about_text: Mapped[str | None] = mapped_column(String(5000), nullable=True)
    division_info: Mapped[str | None] = mapped_column(String(200), nullable=True)
    grades_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    training_info: Mapped[str | None] = mapped_column(String(500), nullable=True)
    has_womens_team: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)
    home_ground_name: Mapped[str | None] = mapped_column(String(250), nullable=True)
    home_ground_map_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    facebook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    instagram_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tiktok_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    competition_mapping: Mapped["CompetitionMapping | None"] = relationship("CompetitionMapping", back_populates="clubs")
    teams: Mapped[list["Team"]] = relationship("Team", back_populates="club", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Club(id={self.id}, name='{self.name}')>"


class Team(Base):
    """A team is a club's entry in a specific competition.

    e.g., "Mosman - Kentwell Cup" is a Team belonging to Club "Mosman"
    in Competition "Kentwell Cup".
    """

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), nullable=False, index=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    external_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)

    # Relationships
    club: Mapped["Club"] = relationship("Club", back_populates="teams")
    competition: Mapped["Competition"] = relationship("Competition", back_populates="teams")
    home_games: Mapped[list["Game"]] = relationship("Game", foreign_keys="Game.home_team_id", back_populates="home_team")
    away_games: Mapped[list["Game"]] = relationship("Game", foreign_keys="Game.away_team_id", back_populates="away_team")

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name='{self.name}')>"
