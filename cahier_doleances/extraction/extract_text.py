"""PDF text extraction."""

from pathlib import Path

import fitz
from sqlalchemy import Engine

from cahier_doleances.extraction.persist import save_extraction
from cahier_doleances.extraction.settings import logger
from cahier_doleances.utils.timing import timed


def text_quality_score(text: str) -> float:
    """Estimate the quality of extracted text.

    Score is the product of printable-character ratio and alphabetic-character
    ratio over non-whitespace characters.  Returns 0.0 for empty input.

    Args:
        text: The extracted text to evaluate.

    Returns:
        A float between 0.0 (garbage) and 1.0 (clean text).
    """
    if not text:
        return 0.0

    chars = [c for c in text if not c.isspace()]
    if not chars:
        return 0.0

    printable_ratio = sum(c.isprintable() for c in chars) / len(chars)
    alpha_ratio = sum(c.isalpha() for c in chars) / len(chars)
    return printable_ratio * alpha_ratio


@timed
def extract_pdf(filepath: str | Path, engine: Engine | None = None) -> int:
    """Extract text from a PDF and persist it to the database.

    Args:
        filepath: Path to the PDF file to process.
        engine: Optional SQLAlchemy engine (uses default DB engine if omitted).

    Returns:
        The primary key of the newly created ``Extraction`` row.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    pdf_name = filepath.name
    logger.info("Opening PDF: %s", pdf_name)

    doc = fitz.open(filepath)
    page_count = doc.page_count
    logger.info("Pages: %d", page_count)

    full_text: list[str] = []
    for i in range(page_count):
        page = doc[i]
        page_text = page.get_text()
        full_text.append(page_text)
        logger.debug("Page %d extracted (%d chars)", i + 1, len(page_text))

    doc.close()

    text = "\n".join(full_text)
    quality = text_quality_score(text)
    logger.info("Extracted text quality: %.4f", quality)

    if quality < 0.1:
        logger.warning(
            "Very low quality text (%.4f) — continuing anyway", quality
        )

    city = ""

    return save_extraction(
        pdf_name=pdf_name,
        city=city,
        page_count=page_count,
        text=text,
        ocr="pymupdf",
        engine=engine,
    )
