"""Engine and session factory for the cahiers Postgres database.

The connection string is read from the ``DATABASE_URL`` environment variable
and falls back to a local Postgres instance. Override it, e.g.:

    export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/cahiers"

Schema changes are managed by Alembic (see ``db_schema/migrations``), so this module
deliberately does *not* call ``create_all`` — run ``alembic upgrade head``
instead.
"""

import os

from sqlmodel import Session, create_engine

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://localhost:5432/cahiers",
)

engine = create_engine(DATABASE_URL, echo=False)


def get_session() -> Session:
    """Return a new SQLModel session bound to the engine."""
    return Session(engine)
