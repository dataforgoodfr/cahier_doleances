"""rename : topic -> instance, ref_topic-> topic; parent sur topic

Revision ID: 5eb701b42e7a
Revises: 1064c8457a88
Create Date: 2026-07-18 13:58:18.854878

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5eb701b42e7a"
down_revision: str | Sequence[str] | None = "1064c8457a88"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Libérer le nom topic pour réattribution
    op.rename_table("topic", "instance")
    op.rename_table("ref_topic", "topic")
    op.add_column("topic", sa.Column("parent", sa.Text(), nullable=True))


def downgrade() -> None:
    # reverse du précédent schema
    op.drop_column("topic", "parent")
    op.rename_table("topic", "ref_topic")
    op.rename_table("instance", "topic")
