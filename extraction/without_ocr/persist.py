"""Database persistence for extracted PDF text."""

from typing import cast

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from database.db import get_engine
from database.models import Contribution, Extraction, PageExtraction
from extraction.without_ocr.settings import logger


def save_page_extractions(
    pdf_name: str,
    city: str,
    pages: list[dict],
    *,
    engine: Engine | None = None,
) -> list[int]:
    """Persist one contribution per page, with optional extraction for clean pages.

    For each page in ``pages``:
    - Creates a ``Contribution`` (start_page = end_page = page_number,
      is_handwritten = needs_ocr).
    - Creates a ``PageExtraction`` (raw text + quality_score + needs_ocr).
    - If ``needs_ocr`` is False, also creates an ``Extraction`` with the
      cleaned text and computed word/line counts.

    If page extractions for this PDF already exist in the database, the import
    is skipped and an error is logged (delete the existing rows first to
    re-extract).

    Args:
        pdf_name: PDF file name.
        city: City extracted from the metadata pages (empty if not found).
        pages: List of dicts ``(page_number, text, quality_score, needs_ocr)``
            representing the pages to persist.
        engine: Optional SQLAlchemy engine.

    Returns:
        List of IDs of the created ``Contribution`` rows (one per page).
    """
    if engine is None:
        engine = get_engine()

    with Session(engine) as session:
        existing_page = (
            session.query(PageExtraction).filter_by(pdf_name=pdf_name).first()
        )
        if existing_page is not None:
            existing_ids = [
                r[0]
                for r in session.query(Contribution.id)
                .filter(Contribution.pdf_file == pdf_name)
                .all()
            ]
            logger.error(
                "PDF already extracted: %s (%d contributions) — skipping. "
                "Delete the existing rows to re-extract.",
                pdf_name,
                len(existing_ids),
            )
            return existing_ids

        contribution_ids: list[int] = []

        for p in pages:
            page_number = p["page_number"]
            needs_ocr = bool(p.get("needs_ocr"))
            text = p["text"]

            contribution = Contribution(
                city=city,
                pdf_file=pdf_name,
                start_page=page_number,
                end_page=page_number,
                is_handwritten=needs_ocr,
            )
            session.add(contribution)
            session.flush()

            session.add(
                PageExtraction(
                    contribution_id=contribution.id,
                    pdf_name=pdf_name,
                    page_number=page_number,
                    text=text,
                    quality_score=p["quality_score"],
                    needs_ocr=needs_ocr,
                    city=city,
                )
            )

            if not needs_ocr:
                session.add(
                    Extraction(
                        contribution_id=contribution.id,
                        ocr="pymupdf",
                        text=text,
                        num_words=len(text.split()),
                        num_lines=text.count("\n") + 1,
                    )
                )

            contribution_ids.append(cast(int, contribution.id))

        session.commit()

        logger.debug(
            "Persisted %d pages as %d contributions (city=%s)",
            len(pages),
            len(contribution_ids),
            city or "(none)",
        )

    return contribution_ids
