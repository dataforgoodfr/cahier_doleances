"""Database persistence for extracted PDF text."""

from typing import cast

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from cahier_doleances.database.db import get_engine
from cahier_doleances.database.models import Contribution, Extraction
from cahier_doleances.extraction.settings import logger


def save_extraction(
    pdf_name: str,
    city: str,
    page_count: int,
    text: str,
    *,
    ocr: str = "pymupdf",
    engine: Engine | None = None,
) -> int:
    """Persist an extraction to the database.

    Creates a ``Contribution`` row if one does not already exist for this PDF,
    then creates an ``Extraction`` row linked to it.

    Args:
        pdf_name: Filename of the PDF (used to look up an existing contribution).
        city: City or department code associated with the contribution.
        page_count: Number of pages in the PDF.
        text: Extracted text content.
        ocr: OCR engine identifier (default ``"pymupdf"``).

    Returns:
        The primary key of the newly created ``Extraction`` row.
    """
    if engine is None:
        engine = get_engine()

    with Session(engine) as session:
        contribution: Contribution | None = (
            session.query(Contribution).filter_by(pdf_file=pdf_name).first()
        )

        if contribution is None:
            contribution = Contribution(
                city=city,
                pdf_file=pdf_name,
                start_page=1,
                end_page=page_count,
                is_handwritten=False,
            )
            session.add(contribution)
            session.flush()
            logger.info("Created contribution (id=%d, city=%s)", contribution.id, city)
        else:
            logger.info("Found existing contribution (id=%d)", contribution.id)

        extraction = Extraction(
            contribution_id=contribution.id,
            ocr=ocr,
            text=text,
            num_words=len(text.split()),
            num_lines=text.count("\n") + 1,
        )
        session.add(extraction)
        session.commit()

        extraction_id = cast(int, extraction.id)
        logger.info(
            "Extraction done: %d words, %d lines (extraction id=%d)",
            extraction.num_words,
            extraction.num_lines,
            extraction.id,
        )

    return extraction_id
