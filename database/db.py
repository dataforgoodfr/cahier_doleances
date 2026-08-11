"""Database engine and connection URL helpers."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def get_url() -> URL:
    """Build a SQLAlchemy connection URL from environment variables.

    If ``DATABASE_URL`` is set (e.g. ``sqlite:///./cahier.db``), it is used
    directly — convenient for local SQLite development without Postgres.
    Otherwise, builds a ``postgresql+psycopg2`` URL from ``DB_USER``,
    ``DB_PASSWORD``, ``DB_HOST``, ``DB_PORT`` and ``DB_NAME``.

    Returns:
        A fully-formed ``sqlalchemy.engine.URL``.
    """
    raw = os.environ.get("DATABASE_URL")
    if raw:
        return make_url(raw)
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
