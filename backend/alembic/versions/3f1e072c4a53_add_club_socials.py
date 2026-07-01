"""add_club_socials

Revision ID: 3f1e072c4a53
Revises: 8518e45de117
Create Date: 2026-05-18 11:19:27.327298
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3f1e072c4a53"
down_revision: Union[str, None] = "8518e45de117"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [col["name"] for col in inspector.get_columns("clubs")]

    if "facebook_url" not in columns:
        op.add_column(
            "clubs", sa.Column("facebook_url", sa.String(length=500), nullable=True)
        )
    if "instagram_url" not in columns:
        op.add_column(
            "clubs", sa.Column("instagram_url", sa.String(length=500), nullable=True)
        )
    if "tiktok_url" not in columns:
        op.add_column(
            "clubs", sa.Column("tiktok_url", sa.String(length=500), nullable=True)
        )


def downgrade() -> None:
    op.drop_column("clubs", "tiktok_url")
    op.drop_column("clubs", "instagram_url")
    op.drop_column("clubs", "facebook_url")
