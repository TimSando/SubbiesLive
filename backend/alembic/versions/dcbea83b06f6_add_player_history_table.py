"""add player history table

Revision ID: dcbea83b06f6
Revises: d1d5dda21139
Create Date: 2026-05-15 16:34:02.496869
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "dcbea83b06f6"
down_revision: Union[str, None] = "d1d5dda21139"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "player_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("position_id", sa.Integer(), nullable=True),
        sa.Column("player_number", sa.Integer(), nullable=True),
        sa.Column("points", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tries", sa.Integer(), server_default="0", nullable=False),
        sa.Column("conversions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("penalty_goals", sa.Integer(), server_default="0", nullable=False),
        sa.Column("drop_goals", sa.Integer(), server_default="0", nullable=False),
        sa.Column("yellow_cards", sa.Integer(), server_default="0", nullable=False),
        sa.Column("red_cards", sa.Integer(), server_default="0", nullable=False),
        sa.Column("blue_cards", sa.Integer(), server_default="0", nullable=False),
        sa.Column("medal_points_1", sa.Integer(), server_default="0", nullable=False),
        sa.Column("medal_points_2", sa.Integer(), server_default="0", nullable=False),
        sa.Column("medal_points_3", sa.Integer(), server_default="0", nullable=False),
        sa.Column("coach_points_1", sa.Integer(), server_default="0", nullable=False),
        sa.Column("coach_points_2", sa.Integer(), server_default="0", nullable=False),
        sa.Column("coach_points_3", sa.Integer(), server_default="0", nullable=False),
        sa.Column("card_text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "game_id", "team_id"),
    )
    op.create_index(
        op.f("ix_player_history_game_id"), "player_history", ["game_id"], unique=False
    )
    op.create_index(
        op.f("ix_player_history_player_id"),
        "player_history",
        ["player_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_player_history_team_id"), "player_history", ["team_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_player_history_team_id"), table_name="player_history")
    op.drop_index(op.f("ix_player_history_player_id"), table_name="player_history")
    op.drop_index(op.f("ix_player_history_game_id"), table_name="player_history")
    op.drop_table("player_history")
