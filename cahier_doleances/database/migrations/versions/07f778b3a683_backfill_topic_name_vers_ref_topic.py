"""backfill: topic.name vers ref_topic

Revision ID: 07f778b3a683
Revises: fd5a99be52e1
Create Date: 2026-07-14 23:17:51.603943

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "07f778b3a683"
down_revision: str | Sequence[str] | None = "fd5a99be52e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Mettre les valeurs déjà en base dans la nouvelle table
    op.execute("""
        INSERT INTO ref_topic (name)
        SELECT DISTINCT name FROM topic WHERE name IS NOT NULL
    """)
    op.execute("""
        UPDATE topic SET ref_topic_id = r.id
        FROM ref_topic r WHERE topic.name = r.name
    """)


def downgrade() -> None:
    op.execute("UPDATE topic SET ref_topic_id = NULL")
    op.execute("DELETE FROM ref_topic")
