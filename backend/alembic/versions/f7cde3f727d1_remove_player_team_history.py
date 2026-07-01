"""remove_player_team_history

Revision ID: f7cde3f727d1
Revises: 3f1e072c4a53
Create Date: 2026-05-18 14:00:30.362904
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7cde3f727d1"
down_revision: Union[str, None] = "3f1e072c4a53"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_player_team_history_team_id", table_name="player_team_history")
    op.drop_index("ix_player_team_history_player_id", table_name="player_team_history")
    op.drop_table("player_team_history")


def downgrade() -> None:
    op.create_table(
        "player_team_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "player_id",
            sa.Integer(),
            sa.ForeignKey("players.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            sa.Integer(),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_player_team_history_player_id", "player_team_history", ["player_id"]
    )
    op.create_index(
        "ix_player_team_history_team_id", "player_team_history", ["team_id"]
    )
