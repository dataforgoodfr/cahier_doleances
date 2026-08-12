"""expand topic et instance pour la livraison analyse

Ajout purement additif : aucune colonne existante n'est touchée, tout est
nullable, donc les lignes déjà en base restent valides.

`topic.parent` (le nom du parent en Text) est conservée pour l'instant ;
elle sera supprimée par une migration contract quand `parent_id` sera en service.

Les contraintes sont nommées explicitement : l'autogenerate les crée avec le
nom `None`, ce qui rend le downgrade inapplicable.

Revision ID: 770ed9d30389
Revises: a1b2c3d4e5f6
Create Date: 2026-08-11 16:39:27.555313

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "770ed9d30389"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UQ_TOPIC_EXTERNAL = "uq_topic_external_id"
FK_TOPIC_PARENT = "fk_topic_parent_id_topic"


def upgrade() -> None:
    """Ajoute les colonnes de la livraison analyse sur topic et instance."""
    op.add_column("topic", sa.Column("external_id", sa.String(), nullable=True))
    op.add_column("topic", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("topic", sa.Column("level", sa.Integer(), nullable=True))
    op.add_column("topic", sa.Column("validated", sa.Boolean(), nullable=True))
    op.add_column("topic", sa.Column("parent_id", sa.Integer(), nullable=True))
    op.create_unique_constraint(UQ_TOPIC_EXTERNAL, "topic", ["external_id"])
    op.create_foreign_key(FK_TOPIC_PARENT, "topic", "topic", ["parent_id"], ["id"])

    op.add_column("instance", sa.Column("external_doc_id", sa.String(), nullable=True))


def downgrade() -> None:
    """Retire ces colonnes ; les données qu'elles portaient sont perdues."""
    op.drop_column("instance", "external_doc_id")

    op.drop_constraint(FK_TOPIC_PARENT, "topic", type_="foreignkey")
    op.drop_constraint(UQ_TOPIC_EXTERNAL, "topic", type_="unique")
    op.drop_column("topic", "parent_id")
    op.drop_column("topic", "validated")
    op.drop_column("topic", "level")
    op.drop_column("topic", "description")
    op.drop_column("topic", "external_id")
