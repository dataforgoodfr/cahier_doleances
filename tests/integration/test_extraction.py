"""Integration tests for PDF text extraction (uses the real PDF file)."""

from typing import cast

import fitz
import pytest
from sqlalchemy.orm import Session

from cahier_doleances.extraction.extract_text import (
    extract_pdf,
    text_quality_score,
)
from database.models import Contribution, Extraction

MIN_VALID_PAGE_CHARS = 50
MAX_EMPTY_PAGE_CHARS = 50


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("num_words", None),
        ("num_lines", None),
        ("ocr", "pymupdf"),
        ("pdf_file", "Cahier_citoyen_test.pdf"),
        ("city", ""),
    ],
)
def test_extraction_db_row_fields(engine, pdf_path, show_db, field, expected):
    """Each persisted field of the Extraction/Contribution rows matches expectations."""
    extraction_id = extract_pdf(pdf_path, engine=engine)
    show_db()

    with Session(engine) as session:
        extraction = session.get(Extraction, extraction_id)
        assert extraction is not None

        if field in {"num_words", "num_lines"}:
            assert getattr(extraction, field) > 0
        elif field == "ocr":
            assert extraction.ocr == expected
        else:
            contribution = session.get(Contribution, extraction.contribution_id)
            assert contribution is not None
            assert getattr(contribution, field) == expected


def test_extraction_db_row_end_page_positive(engine, pdf_path):
    """The contribution end_page must be a positive integer."""
    extraction_id = extract_pdf(pdf_path, engine=engine)

    with Session(engine) as session:
        extraction = session.get(Extraction, extraction_id)
        assert extraction is not None
        contribution = session.get(Contribution, extraction.contribution_id)
        assert contribution is not None
        assert contribution.end_page > 0


@pytest.mark.parametrize("threshold", [0.1, 0.3, 0.5])
def test_full_text_quality_above_threshold(engine, pdf_path, threshold):
    """Quality score of the concatenated extracted text stays above given thresholds."""
    extract_pdf(pdf_path, engine=engine)

    with Session(engine) as session:
        extraction = session.query(Extraction).first()
        assert extraction is not None
        text = cast(str, extraction.text)
        quality = text_quality_score(text)
        assert quality > threshold, f"Quality {quality:.4f} <= {threshold}"


@pytest.mark.parametrize(
    "phrase",
    [
        "cahier d'expression citoyenne",
        "Je suis une habitante du revennont",
        "Vous trouverez joint à ce courrier le cahier d'expression citoyenne",
        "Je suis une habitante du revennont je ,suis 100 pour 100 pour l'écologie.",
    ],
)
def test_extracted_text_contains_phrase(engine, pdf_path, phrase):
    """The concatenated extracted text contains each expected phrase."""
    extract_pdf(pdf_path, engine=engine)

    with Session(engine) as session:
        extraction = session.query(Extraction).first()
        assert extraction is not None
        text = cast(str, extraction.text)
        assert phrase in text, f"Missing phrase: {phrase!r}"


@pytest.mark.parametrize(
    ("page_index", "snippet"),
    [
        (0, "Le grand\ndébat national\nCahier citoyen"),
        (2, "Le 21 février 2019"),
        (8, "Je suis une habitante du revennont"),
        (49, "gilets jaunes, on dit que les revendications"),
        (126, "SUGGESTIONS\n1/MORALISATION"),
        (247, "Monsieur Tomislav MILINKOVIC"),
        (262, "une douleur maximale au réveil"),
    ],
    ids=lambda v: f"p{v}" if isinstance(v, int) else v,
)
def test_valid_page_extracted_text(pdf_path, page_index, snippet):
    """Typed pages yield text long enough and containing the expected snippet.

    Uses only the first occurrence for ids stability.
    """
    doc = fitz.open(pdf_path)
    try:
        page_text = doc[page_index].get_text()
    finally:
        doc.close()

    assert len(page_text) >= MIN_VALID_PAGE_CHARS, (
        f"Page {page_index} too short: {len(page_text)} chars"
    )
    assert snippet in page_text, (
        f"Page {page_index} missing snippet {snippet[:60]!r}\nGot: {page_text[:120]!r}"
    )


@pytest.mark.parametrize("page_index", [5, 7, 81, 119, 125, 284])
def test_empty_page_has_no_extracted_text(pdf_path, page_index):
    """Blank/whitespace-only pages yield (almost) no extractable text."""
    doc = fitz.open(pdf_path)
    try:
        page_text = doc[page_index].get_text()
    finally:
        doc.close()

    assert len(page_text) < MAX_EMPTY_PAGE_CHARS, (
        f"Page {page_index} expected empty but got {len(page_text)} chars: "
        f"{page_text!r}"
    )


@pytest.mark.parametrize(
    ("page_index", "snippet"),
    [
        (1, "Cahier citoyen"),
        (83, "Contributions reçues"),
        (88, "gilets jaunes"),
        (93, "Bourg en Bresse"),
        (131, "MORALISATION"),
    ],
    ids=lambda v: f"p{v}" if isinstance(v, int) else v,
)
def test_ocr_garbage_page_does_not_contain_typed_snippet(pdf_path, page_index, snippet):
    """Handwritten pages produce unusable OCR output: the typed snippet is absent."""
    doc = fitz.open(pdf_path)
    try:
        page_text = doc[page_index].get_text()
    finally:
        doc.close()

    assert snippet not in page_text, (
        f"Page {page_index} unexpectedly contains typed snippet {snippet!r}; "
        f"OCR may have succeeded where garbage was expected."
    )
