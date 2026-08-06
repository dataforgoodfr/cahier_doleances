"""Integration tests for page-level PDF extraction (uses the real PDF file)."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from cahier_doleances.database.models import Contribution, PageExtraction
from cahier_doleances.extraction.extract_text import extract_pdf_pages
from cahier_doleances.extraction.extraction_config import ExtractionConfig


def test_extract_pages_persists_rows(engine, pdf_path):
    """extract_pdf_pages creates PageExtraction rows and a Contribution."""
    contribution_id = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        contribution = session.get(Contribution, contribution_id)
        assert contribution is not None

        rows = (
            session.execute(
                select(PageExtraction)
                .where(PageExtraction.contribution_id == contribution_id)
                .order_by(PageExtraction.page_number)
            )
            .scalars()
            .all()
        )
        assert len(rows) > 0

        first = rows[0]
        assert first.pdf_name == pdf_path.name
        assert first.city == "VILLE-TEST"
        assert first.page_number >= 3  # first two pages are metadata


def test_city_extracted_on_contribution(engine, pdf_path):
    """The city is populated on the Contribution."""
    contribution_id = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        contribution = session.get(Contribution, contribution_id)
        assert contribution is not None
        assert contribution.city == "VILLE-TEST"


def test_no_page_extraction_for_metadata_pages(engine, pdf_path):
    """No PageExtraction rows for pages 1 and 2 (metadata)."""
    contribution_id = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        metadata_rows = (
            session.execute(
                select(PageExtraction)
                .where(PageExtraction.contribution_id == contribution_id)
                .where(PageExtraction.page_number.in_([1, 2]))
            )
            .scalars()
            .all()
        )
        assert len(metadata_rows) == 0


def test_parsing_stops_at_end_marker(engine, pdf_path):
    """No page persisted beyond the 'Fin des pages écrites' marker."""
    contribution_id = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        rows = (
            session.execute(
                select(PageExtraction)
                .where(PageExtraction.contribution_id == contribution_id)
                .order_by(PageExtraction.page_number)
            )
            .scalars()
            .all()
        )
        # The marker is at page 7 (1-indexed) in the test PDF.
        assert all(r.page_number < 7 for r in rows), (
            "A page beyond the end marker was persisted"
        )
        assert rows[-1].page_number < 7


def test_needs_ocr_flag_on_handwritten_pages(engine, pdf_path):
    """needs_ocr flag reflects wordfreq quality: low-score pages are flagged.

    In this test PDF, page 5 (within the parsing range, before the
    'Fin des pages écrites' marker) is OCR garbage emulating a handwritten
    page. It must be flagged needs_ocr=True. Typed pages (high
    quality_score) must be flagged False.

    NB: pages located AFTER the end marker are not persisted (out of scope).
    """
    contribution_id = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        rows = (
            session.execute(
                select(PageExtraction).where(
                    PageExtraction.contribution_id == contribution_id
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) > 0

        threshold = ExtractionConfig.WORDFREQ_QUALITY_THRESHOLD.value
        by_page = {r.page_number: r for r in rows}

        known_handwritten = {5}
        for page_number in known_handwritten:
            assert page_number in by_page, f"Page {page_number} missing"
            r = by_page[page_number]
            assert r.needs_ocr is True, (
                f"Page {page_number} expected needs_ocr=True (score="
                f"{r.quality_score:.4f})"
            )

        for r in rows:
            if r.needs_ocr:
                assert r.quality_score < threshold, (
                    f"Page {r.page_number} flagged needs_ocr but score "
                    f"{r.quality_score:.4f} >= threshold {threshold}"
                )
            else:
                assert r.quality_score >= threshold, (
                    f"Page {r.page_number} not flagged but score "
                    f"{r.quality_score:.4f} < threshold {threshold}"
                )


def test_quality_score_in_range(engine, pdf_path):
    """Every PageExtraction has a quality_score between 0 and 1."""
    contribution_id = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        rows = (
            session.execute(
                select(PageExtraction).where(
                    PageExtraction.contribution_id == contribution_id
                )
            )
            .scalars()
            .all()
        )
        for r in rows:
            assert 0.0 <= r.quality_score <= 1.0


def test_short_pages_filtered(engine, pdf_path):
    """Near-empty pages are not persisted (noise filtering)."""
    contribution_id = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        rows = (
            session.execute(
                select(PageExtraction).where(
                    PageExtraction.contribution_id == contribution_id
                )
            )
            .scalars()
            .all()
        )
        for r in rows:
            assert len(r.text or "") >= 10  # min_chars_for_page


@pytest.mark.parametrize(
    "phrase",
    [
        "Je suis une habitante de la commune",
        "Notre commune doit renforcer ses politiques",
    ],
)
def test_extracted_text_contains_phrase(engine, pdf_path, phrase):
    """The concatenated text of persisted pages contains the expected phrases."""
    contribution_id = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        rows = (
            session.execute(
                select(PageExtraction).where(
                    PageExtraction.contribution_id == contribution_id
                )
            )
            .scalars()
            .all()
        )
        full = "\n".join(r.text or "" for r in rows)
        assert phrase in full, f"Missing phrase: {phrase!r}"


def test_duplicate_pdf_is_skipped(engine, pdf_path):
    """A second extraction of the same PDF does not duplicate rows."""
    contribution_id = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        first_count = (
            session.query(PageExtraction)
            .filter_by(contribution_id=contribution_id)
            .count()
        )

    second_contribution_id = extract_pdf_pages(pdf_path, engine=engine)

    assert second_contribution_id == contribution_id

    with Session(engine) as session:
        second_count = (
            session.query(PageExtraction)
            .filter_by(contribution_id=contribution_id)
            .count()
        )

    assert second_count == first_count, (
        f"Row count changed after re-extraction: {first_count} -> {second_count}"
    )
    assert first_count > 0
