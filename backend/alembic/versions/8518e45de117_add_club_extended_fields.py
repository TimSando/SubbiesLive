"""add_club_extended_fields

Revision ID: 8518e45de117
Revises: dcbea83b06f6
Create Date: 2026-05-17 23:44:18.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8518e45de117"
down_revision: Union[str, None] = "dcbea83b06f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns. Use execute check or just add them safely since they will be upgraded.
    # To handle cases where columns might already exist in the target database from a previous run:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col["name"] for col in inspector.get_columns("clubs")]

    if "about_text" not in columns:
        op.add_column(
            "clubs", sa.Column("about_text", sa.String(length=5000), nullable=True)
        )
    if "division_info" not in columns:
        op.add_column(
            "clubs", sa.Column("division_info", sa.String(length=200), nullable=True)
        )
    if "grades_count" not in columns:
        op.add_column("clubs", sa.Column("grades_count", sa.Integer(), nullable=True))
    if "training_info" not in columns:
        op.add_column(
            "clubs", sa.Column("training_info", sa.String(length=500), nullable=True)
        )
    if "has_womens_team" not in columns:
        op.add_column(
            "clubs", sa.Column("has_womens_team", sa.Boolean(), nullable=True)
        )
    if "home_ground_name" not in columns:
        op.add_column(
            "clubs", sa.Column("home_ground_name", sa.String(length=250), nullable=True)
        )
    if "home_ground_map_url" not in columns:
        op.add_column(
            "clubs",
            sa.Column("home_ground_map_url", sa.String(length=500), nullable=True),
        )
    if "website_url" not in columns:
        op.add_column(
            "clubs", sa.Column("website_url", sa.String(length=500), nullable=True)
        )


def downgrade() -> None:
    op.drop_column("clubs", "website_url")
    op.drop_column("clubs", "home_ground_map_url")
    op.drop_column("clubs", "home_ground_name")
    op.drop_column("clubs", "has_womens_team")
    op.drop_column("clubs", "training_info")
    op.drop_column("clubs", "grades_count")
    op.drop_column("clubs", "division_info")
    op.drop_column("clubs", "about_text")
