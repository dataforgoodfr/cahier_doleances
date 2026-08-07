"""Integration tests for page-level PDF extraction (uses the real PDF file)."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from cahier_doleances.database.models import Contribution, Extraction, PageExtraction
from cahier_doleances.extraction.extract_text import extract_pdf_pages
from cahier_doleances.extraction.extraction_config import ExtractionConfig


def test_extract_pages_persists_one_contribution_per_page(engine, pdf_path):
    """extract_pdf_pages creates one Contribution + one PageExtraction per page."""
    contribution_ids = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        assert len(contribution_ids) > 0

        contributions = (
            session.execute(
                select(Contribution)
                .where(Contribution.id.in_(contribution_ids))
                .order_by(Contribution.start_page)
            )
            .scalars()
            .all()
        )
        assert len(contributions) == len(contribution_ids)

        for c in contributions:
            assert c.pdf_file == pdf_path.name
            assert c.city == "VILLE-TEST"
            assert c.start_page == c.end_page
            assert c.start_page >= 3

        page_extractions = (
            session.execute(
                select(PageExtraction)
                .where(PageExtraction.contribution_id.in_(contribution_ids))
            )
            .scalars()
            .all()
        )
        assert len(page_extractions) == len(contributions)
        assert all(pe.pdf_name == pdf_path.name for pe in page_extractions)


def test_city_extracted_on_all_contributions(engine, pdf_path):
    """The city is populated on every Contribution."""
    contribution_ids = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        contributions = (
            session.execute(
                select(Contribution).where(Contribution.id.in_(contribution_ids))
            )
            .scalars()
            .all()
        )
        assert all(c.city == "VILLE-TEST" for c in contributions)


def test_no_page_extraction_for_metadata_pages(engine, pdf_path):
    """No Contribution for pages 1 and 2 (metadata)."""
    contribution_ids = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        metadata = (
            session.execute(
                select(Contribution)
                .where(Contribution.id.in_(contribution_ids))
                .where(Contribution.start_page.in_([1, 2]))
            )
            .scalars()
            .all()
        )
        assert len(metadata) == 0


def test_parsing_stops_at_end_marker(engine, pdf_path):
    """No contribution persisted beyond the 'Fin des pages écrites' marker."""
    contribution_ids = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        contributions = (
            session.execute(
                select(Contribution)
                .where(Contribution.id.in_(contribution_ids))
                .order_by(Contribution.start_page)
            )
            .scalars()
            .all()
        )
        # The marker is at page 7 (1-indexed) in the test PDF.
        assert all(c.start_page < 7 for c in contributions), (
            "A contribution beyond the end marker was persisted"
        )


def test_is_handwritten_matches_needs_ocr(engine, pdf_path):
    """Contribution.is_handwritten matches PageExtraction.needs_ocr per page."""
    contribution_ids = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        page_extractions = (
            session.execute(
                select(PageExtraction).where(
                    PageExtraction.contribution_id.in_(contribution_ids)
                )
            )
            .scalars()
            .all()
        )
        assert len(page_extractions) > 0

        threshold = ExtractionConfig.WORDFREQ_QUALITY_THRESHOLD.value
        by_page = {pe.page_number: pe for pe in page_extractions}

        known_handwritten = {5}
        for page_number in known_handwritten:
            assert page_number in by_page, f"Page {page_number} missing"
            pe = by_page[page_number]
            assert pe.needs_ocr is True
            contrib = session.get(Contribution, pe.contribution_id)
            assert contrib.is_handwritten is True

        for pe in page_extractions:
            contrib = session.get(Contribution, pe.contribution_id)
            assert contrib.is_handwritten == pe.needs_ocr
            if pe.needs_ocr:
                assert pe.quality_score < threshold
            else:
                assert pe.quality_score >= threshold


def test_quality_score_in_range(engine, pdf_path):
    """Every PageExtraction has a quality_score between 0 and 1."""
    contribution_ids = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        rows = (
            session.execute(
                select(PageExtraction).where(
                    PageExtraction.contribution_id.in_(contribution_ids)
                )
            )
            .scalars()
            .all()
        )
        for r in rows:
            assert 0.0 <= r.quality_score <= 1.0


def test_short_pages_filtered(engine, pdf_path):
    """Near-empty pages are not persisted (noise filtering)."""
    contribution_ids = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        rows = (
            session.execute(
                select(PageExtraction).where(
                    PageExtraction.contribution_id.in_(contribution_ids)
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
    """At least one page extraction contains the expected phrase."""
    contribution_ids = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        rows = (
            session.execute(
                select(PageExtraction).where(
                    PageExtraction.contribution_id.in_(contribution_ids)
                )
            )
            .scalars()
            .all()
        )
        full = "\n".join(r.text or "" for r in rows)
        assert phrase in full, f"Missing phrase: {phrase!r}"


def test_extraction_created_for_clean_pages_only(engine, pdf_path):
    """Extraction rows exist only for contributions with needs_ocr=False."""
    contribution_ids = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        extractions = (
            session.execute(
                select(Extraction).where(
                    Extraction.contribution_id.in_(contribution_ids)
                )
            )
            .scalars()
            .all()
        )
        for e in extractions:
            contrib = session.get(Contribution, e.contribution_id)
            assert contrib.is_handwritten is False
            assert e.ocr == "pdfplumber"
            assert e.text
            assert e.num_words == len(e.text.split())
            assert e.num_lines == e.text.count("\n") + 1

        assert len(extractions) > 0

        handwritten_contribs = (
            session.execute(
                select(Contribution)
                .where(Contribution.id.in_(contribution_ids))
                .where(Contribution.is_handwritten.is_(True))
            )
            .scalars()
            .all()
        )
        for c in handwritten_contribs:
            e = session.execute(
                select(Extraction).where(Extraction.contribution_id == c.id)
            ).scalar_one_or_none()
            assert e is None


def test_duplicate_pdf_is_skipped(engine, pdf_path):
    """A second extraction of the same PDF does not duplicate rows."""
    contribution_ids = extract_pdf_pages(pdf_path, engine=engine)

    with Session(engine) as session:
        first_count = (
            session.query(PageExtraction)
            .filter(PageExtraction.contribution_id.in_(contribution_ids))
            .count()
        )

    second_contribution_ids = extract_pdf_pages(pdf_path, engine=engine)

    assert second_contribution_ids == contribution_ids

    with Session(engine) as session:
        second_count = (
            session.query(PageExtraction)
            .filter(PageExtraction.contribution_id.in_(contribution_ids))
            .count()
        )

    assert second_count == first_count, (
        f"Row count changed after re-extraction: {first_count} -> {second_count}"
    )
    assert first_count > 0
