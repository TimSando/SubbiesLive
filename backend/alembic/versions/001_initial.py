"""Initial schema — all core tables

Revision ID: 001_initial
Revises: None
Create Date: 2026-05-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Competition Mapping ---
    op.create_table(
        "competition_mapping",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("parent_competition", sa.String(150), nullable=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("division", sa.String(50), nullable=True),
        sa.Column("grade", sa.String(50), nullable=True),
    )

    # --- Competitions ---
    op.create_table(
        "competitions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "competition_mapping_id",
            sa.Integer(),
            sa.ForeignKey("competition_mapping.id"),
            nullable=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("external_id", sa.Integer(), nullable=False, unique=True),
    )
    op.create_index("ix_competitions_external_id", "competitions", ["external_id"])

    # --- Rounds ---
    op.create_table(
        "rounds",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "competition_id",
            sa.Integer(),
            sa.ForeignKey("competitions.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("external_id", sa.Integer(), nullable=False, unique=True),
    )
    op.create_index("ix_rounds_competition_id", "rounds", ["competition_id"])
    op.create_index("ix_rounds_external_id", "rounds", ["external_id"])

    # --- Clubs ---
    op.create_table(
        "clubs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "competition_mapping_id",
            sa.Integer(),
            sa.ForeignKey("competition_mapping.id"),
            nullable=True,
        ),
        sa.Column("name", sa.String(150), nullable=False, unique=True),
        sa.Column("short_name", sa.String(50), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
    )

    # --- Teams ---
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("club_id", sa.Integer(), sa.ForeignKey("clubs.id"), nullable=False),
        sa.Column(
            "competition_id",
            sa.Integer(),
            sa.ForeignKey("competitions.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("external_id", sa.Integer(), nullable=False, unique=True),
    )
    op.create_index("ix_teams_club_id", "teams", ["club_id"])
    op.create_index("ix_teams_competition_id", "teams", ["competition_id"])
    op.create_index("ix_teams_external_id", "teams", ["external_id"])

    # --- Players ---
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("dob", sa.Date(), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("external_id", sa.Integer(), nullable=False, unique=True),
    )
    op.create_index("ix_players_name", "players", ["name"])
    op.create_index("ix_players_external_id", "players", ["external_id"])

    # --- Games ---
    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("round_id", sa.Integer(), sa.ForeignKey("rounds.id"), nullable=False),
        sa.Column(
            "home_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False
        ),
        sa.Column(
            "away_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False
        ),
        sa.Column("game_date", sa.DateTime(), nullable=False),
        sa.Column("location", sa.String(300), nullable=True),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="scheduled"),
        sa.Column("external_id", sa.Integer(), nullable=False, unique=True),
    )
    op.create_index("ix_games_round_id", "games", ["round_id"])
    op.create_index("ix_games_home_team_id", "games", ["home_team_id"])
    op.create_index("ix_games_away_team_id", "games", ["away_team_id"])
    op.create_index("ix_games_game_date", "games", ["game_date"])
    op.create_index("ix_games_external_id", "games", ["external_id"])

    # --- Game Events ---
    op.create_table(
        "game_events",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column(
            "player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("player_number", sa.Integer(), nullable=True),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(100), nullable=True, unique=True),
    )
    op.create_index("ix_game_events_game_id", "game_events", ["game_id"])
    op.create_index("ix_game_events_team_id", "game_events", ["team_id"])
    op.create_index("ix_game_events_player_id", "game_events", ["player_id"])
    op.create_index("ix_game_events_event_type", "game_events", ["event_type"])

    # --- Player Team History ---
    op.create_table(
        "player_team_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False
        ),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
    )
    op.create_index(
        "ix_player_team_history_player_id", "player_team_history", ["player_id"]
    )
    op.create_index(
        "ix_player_team_history_team_id", "player_team_history", ["team_id"]
    )


def downgrade() -> None:
    op.drop_table("player_team_history")
    op.drop_table("game_events")
    op.drop_table("games")
    op.drop_table("players")
    op.drop_table("teams")
    op.drop_table("clubs")
    op.drop_table("rounds")
    op.drop_table("competitions")
    op.drop_table("competition_mapping")
