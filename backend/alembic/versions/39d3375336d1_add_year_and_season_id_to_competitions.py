"""add_year_and_season_id_to_competitions

Revision ID: 39d3375336d1
Revises: dd8f46a15a42
Create Date: 2026-07-09 16:50:27.401627
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "39d3375336d1"
down_revision: Union[str, None] = "dd8f46a15a42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop existing unique index on external_id
    op.drop_index("ix_competitions_external_id", table_name="competitions")

    # Add columns year and season_id
    op.add_column(
        "competitions",
        sa.Column("year", sa.Integer(), nullable=False, server_default="2026"),
    )
    op.add_column("competitions", sa.Column("season_id", sa.Integer(), nullable=True))

    # Create index on year
    op.create_index("ix_competitions_year", "competitions", ["year"])

    # Remove the server default on year so future inserts require explicit year
    op.alter_column("competitions", "year", server_default=None)

    # Re-create index on external_id as non-unique (since we still query by it)
    op.create_index("ix_competitions_external_id", "competitions", ["external_id"])

    # Create new composite unique index on (external_id, year)
    op.create_index(
        "ix_competitions_external_id_year",
        "competitions",
        ["external_id", "year"],
        unique=True,
    )


def downgrade() -> None:
    # Drop composite unique index
    op.drop_index("ix_competitions_external_id_year", table_name="competitions")

    # Drop non-unique index on external_id
    op.drop_index("ix_competitions_external_id", table_name="competitions")

    # Drop year index
    op.drop_index("ix_competitions_year", table_name="competitions")

    # Drop columns
    op.drop_column("competitions", "season_id")
    op.drop_column("competitions", "year")

    # Re-create unique index on external_id
    op.create_index(
        "ix_competitions_external_id", "competitions", ["external_id"], unique=True
    )
