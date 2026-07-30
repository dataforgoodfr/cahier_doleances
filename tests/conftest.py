"""Shared fixtures for extraction tests."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from database.models import Base


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine


@pytest.fixture
def pdf_path() -> Path:
    return Path(__file__).parent / "data" / "Cahier_citoyen_test.pdf"


@pytest.fixture
def show_db(engine: Engine):
    def _show():
        with Session(engine) as session:
            for table in ["contribution", "extraction"]:
                rows = session.execute(text(f"SELECT * FROM {table}")).fetchall()
                print(f"\n--- {table} ---")
                for row in rows:
                    print(dict(row._mapping))

    return _show
