"""add page_extraction table

Revision ID: a1b2c3d4e5f6
Revises: 95490adda8a4
Create Date: 2026-07-30 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "95490adda8a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the page_extraction table."""
    op.create_table(
        "page_extraction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contribution_id", sa.Integer(), nullable=True),
        sa.Column("pdf_name", sa.String(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("needs_ocr", sa.Boolean(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["contribution_id"], ["contribution.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop the page_extraction table."""
    op.drop_table("page_extraction")
