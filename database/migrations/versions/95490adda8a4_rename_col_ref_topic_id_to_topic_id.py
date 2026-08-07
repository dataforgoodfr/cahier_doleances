"""rename col ref_topic_id to topic_id

Revision ID: 95490adda8a4
Revises: 5eb701b42e7a
Create Date: 2026-07-18 17:40:50.552482

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "95490adda8a4"
down_revision: str | Sequence[str] | None = "5eb701b42e7a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # La colonne est actuellement dans 'instance' (l'ancienne table 'topic')
    op.alter_column("instance", "ref_topic_id", new_column_name="topic_id")


def downgrade() -> None:
    # Retour en arrière en cas de rollback
    op.alter_column("instance", "topic_id", new_column_name="ref_topic_id")
