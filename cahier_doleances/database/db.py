"""Database engine and connection URL helpers."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def get_url() -> URL:
    """Build a PostgreSQL connection URL from environment variables.

    Expects ``DB_USER``, ``DB_PASSWORD``, ``DB_HOST``, ``DB_PORT`` and
    ``DB_NAME`` to be set (e.g. in a ``.env`` file).

    Returns:
        A fully-formed ``sqlalchemy.engine.URL`` for ``postgresql+psycopg2``.
    """
    return URL.create(
        drivername="postgresql+psycopg2",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_NAME"],
    )


def get_engine() -> Engine:
    """Create a SQLAlchemy engine with connection pooling.

    Returns:
        A configured ``Engine`` instance.
    """
    return create_engine(get_url(), pool_pre_ping=True)
