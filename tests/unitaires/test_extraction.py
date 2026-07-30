"""Unit tests for PDF text extraction (no real PDF file)."""

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from cahier_doleances.extraction.extract_text import text_quality_score
from cahier_doleances.extraction.persist import save_extraction
from database.models import Contribution, Extraction


def test_text_quality_score_empty():
    assert text_quality_score("") == 0.0


def test_text_quality_score_only_whitespace():
    assert text_quality_score("   \n\t  ") == 0.0


def test_text_quality_score_clean():
    score = text_quality_score("Hello world. This is clean text.")
    assert score > 0.9


def test_text_quality_score_garbage():
    score = text_quality_score("\x00\x01\x02\x03\x04")
    assert score < 0.5


def test_text_quality_score_mixed():
    score = text_quality_score("Hello\x00world\x01test")
    assert 0.0 < score < 1.0


def test_save_extraction_creates_contribution_and_extraction(engine: Engine):
    extraction_id = save_extraction(
        pdf_name="test.pdf",
        city="01000",
        page_count=5,
        text="Hello world",
        ocr="pymupdf",
        engine=engine,
    )

    with Session(engine) as session:
        extraction = session.get(Extraction, extraction_id)
        assert extraction is not None
        assert extraction.ocr == "pymupdf"
        assert extraction.num_words == 2
        assert extraction.num_lines == 1

        contribution = session.get(Contribution, extraction.contribution_id)
        assert contribution is not None
        assert contribution.pdf_file == "test.pdf"
        assert contribution.city == "01000"
        assert contribution.start_page == 1
        assert contribution.end_page == 5


def test_save_extraction_reuses_existing_contribution(engine: Engine):
    id1 = save_extraction(
        pdf_name="dup.pdf",
        city="01000",
        page_count=3,
        text="First extraction",
        engine=engine,
    )
    id2 = save_extraction(
        pdf_name="dup.pdf",
        city="99999",
        page_count=10,
        text="Second extraction",
        engine=engine,
    )

    with Session(engine) as session:
        ext1 = session.get(Extraction, id1)
        ext2 = session.get(Extraction, id2)
        assert ext1 is not None and ext2 is not None
        assert ext1.contribution_id == ext2.contribution_id

        contributions = session.query(Contribution).all()
        assert len(contributions) == 1
        assert contributions[0].city == "01000"
        assert contributions[0].end_page == 3
