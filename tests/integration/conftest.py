"""Fixtures for integration tests."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from cahier_doleances.database.models import Base


@pytest.fixture
def engine() -> Iterator[Engine]:
    """In-memory SQLite engine with the schema created."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine


@pytest.fixture
def pdf_path() -> Path:
    """Path to the reference test PDF."""
    return Path(__file__).resolve().parent.parent / "data" / "Cahier_citoyen_test.pdf"


@pytest.fixture
def show_db(engine: Engine):
    """Debug helper that prints every row of the contribution/extraction tables."""

    def _show():
        with Session(engine) as session:
            for table in ["contribution", "extraction"]:
                rows = session.execute(text(f"SELECT * FROM {table}")).fetchall()
                print(f"\n--- {table} ---")
                for row in rows:
                    print(dict(row._mapping))

    return _show


@pytest.fixture
def sample_pages() -> dict[str, list[tuple[int, str]]]:
    """Representative sample of PDF pages, grouped by extraction quality.

    Returns a mapping with three keys, each holding a list of
    ``(page_index, expected_snippet)`` tuples:

    - ``valid``: typed pages where PyMuPDF extracts clean text that
      must contain the snippet and exceed a minimal length.
    - ``empty``: pages with no extractable text (blank scans).
    - ``ocr_garbage``: handwritten pages whose OCR output is unusable;
      the expected snippet from the corresponding typed context must
      NOT be present in the extracted text.
    """
    return {
        "valid": [
            (0, "Cahier citoyen"),
            (2, "février 2019"),
            (4, "Contributions reçues"),
            (8, "habitant du revennont"),
            (9, "conteneurs flambants"),
            (49, "gilets jaunes"),
            (126, "MORALISATION"),
            (157, "TOMATIS"),
            (188, "Bourg en Bresse"),
            (247, "MILINKOVIC"),
            (262, "douleur maximale"),
        ],
        "empty": [
            (5, ""),
            (7, ""),
            (81, ""),
            (119, ""),
            (284, ""),
        ],
        "ocr_garbage": [
            (1, "Cahier citoyen"),
            (83, "Contributions reçues"),
            (88, "gilets jaunes"),
            (93, "Bourg en Bresse"),
            (131, "SUGGESTIONS"),
        ],
    }
