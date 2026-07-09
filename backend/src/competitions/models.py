"""Competition domain ORM models."""

from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class CompetitionMapping(Base):
    """Lookup table for mapping competitions to parent competitions and divisions."""

    __tablename__ = "competition_mapping"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_competition: Mapped[str | None] = mapped_column(String(150), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    division: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    competitions: Mapped[list["Competition"]] = relationship(
        "Competition", back_populates="competition_mapping"
    )
    clubs: Mapped[list["Club"]] = relationship(
        "Club", back_populates="competition_mapping"
    )

    def __repr__(self) -> str:
        return f"<CompetitionMapping(id={self.id}, name='{self.name}')>"


class Competition(Base):
    """A rugby union competition (e.g., Kentwell Cup, Shute Shield)."""

    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competition_mapping_id: Mapped[int | None] = mapped_column(
        ForeignKey("competition_mapping.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    external_id: Mapped[int] = mapped_column(
        Integer, unique=True, nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False, default=2026, index=True)
    season_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships (use string references to avoid circular imports)
    competition_mapping: Mapped["CompetitionMapping | None"] = relationship(
        "CompetitionMapping", back_populates="competitions"
    )
    rounds: Mapped[list["Round"]] = relationship(
        "Round", back_populates="competition", cascade="all, delete-orphan"
    )
    teams: Mapped[list["Team"]] = relationship("Team", back_populates="competition")

    def __repr__(self) -> str:
        return f"<Competition(id={self.id}, name='{self.name}')>"


class Round(Base):
    """A round within a competition (e.g., Round 1, Semi Final)."""

    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_id: Mapped[int] = mapped_column(
        Integer, unique=True, nullable=False, index=True
    )

    # Relationships
    competition: Mapped["Competition"] = relationship(
        "Competition", back_populates="rounds"
    )
    games: Mapped[list["Game"]] = relationship(
        "Game", back_populates="round", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Round(id={self.id}, name='{self.name}', competition_id={self.competition_id})>"
