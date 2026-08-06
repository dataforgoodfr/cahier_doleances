"""Database persistence for extracted PDF text."""

from typing import cast

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from cahier_doleances.database.db import get_engine
from cahier_doleances.database.models import Contribution, PageExtraction
from cahier_doleances.settings import logger


def save_page_extractions(
    pdf_name: str,
    city: str,
    pages: list[dict],
    *,
    engine: Engine | None = None,
) -> int:
    """Persist page-by-page extractions into the ``page_extraction`` table.

    Creates or reuses a ``Contribution`` (key: ``pdf_file``), populates
    ``city`` and ``is_handwritten`` (True if at least one page is suspected
    handwritten), then inserts one ``PageExtraction`` row per provided page.

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
        The ID of the created/reused ``Contribution``.
    """
    if engine is None:
        engine = get_engine()

    with Session(engine) as session:
        existing_page = (
            session.query(PageExtraction).filter_by(pdf_name=pdf_name).first()
        )
        if existing_page is not None:
            logger.error(
                "PDF already extracted: %s (contribution id=%d) — skipping. "
                "Delete the existing rows to re-extract.",
                pdf_name,
                existing_page.contribution_id,
            )
            return cast(int, existing_page.contribution_id)

        contribution: Contribution | None = (
            session.query(Contribution).filter_by(pdf_file=pdf_name).first()
        )

        any_ocr = any(p.get("needs_ocr") for p in pages)

        if contribution is None:
            contribution = Contribution(
                city=city,
                pdf_file=pdf_name,
                start_page=pages[0]["page_number"] if pages else 1,
                end_page=pages[-1]["page_number"] if pages else 0,
                is_handwritten=any_ocr,
            )
            session.add(contribution)
            session.flush()
            logger.info(
                "Created contribution (id=%d, city=%s)", contribution.id, city or ""
            )
        else:
            contribution.city = city or contribution.city
            contribution.is_handwritten = any_ocr or bool(contribution.is_handwritten)
            if pages:
                contribution.start_page = pages[0]["page_number"]
                contribution.end_page = pages[-1]["page_number"]
            logger.info("Found existing contribution (id=%d)", contribution.id)

        for p in pages:
            session.add(
                PageExtraction(
                    contribution_id=contribution.id,
                    pdf_name=pdf_name,
                    page_number=p["page_number"],
                    text=p["text"],
                    quality_score=p["quality_score"],
                    needs_ocr=bool(p.get("needs_ocr")),
                    city=city,
                )
            )

        session.commit()

        logger.info(
            "Page extractions done: %d pages persisted (contribution id=%d)",
            len(pages),
            contribution.id,
        )

    return cast(int, contribution.id)
