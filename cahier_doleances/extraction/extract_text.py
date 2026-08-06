"""PDF text extraction."""

import re
from pathlib import Path

import fitz
from sqlalchemy import Engine
from wordfreq import zipf_frequency

from cahier_doleances.extraction.extraction_config import (
    ExtractionConfig,
    city_regex,
)
from cahier_doleances.extraction.persist import save_page_extractions
from cahier_doleances.settings import logger
from cahier_doleances.utils.timing import timed


def wordfreq_quality_score(text: str) -> float:
    """Estimate OCR quality from the frequency of French words.

    Splits the text into words longer than 2 characters, strips non-letter
    characters from each token (so that OCR garbage like ``"'aj-v"`` does not
    accidentally match a real French word), then returns the ratio of "known"
    words (zipf frequency >= 2 in French). Returns 0.0 when there is no token
    long enough to evaluate.

    Args:
        text: The cleaned text to evaluate.

    Returns:
        A float between 0.0 (all words unknown / OCR garbage) and 1.0
        (every word is a common French word).
    """
    tokens = [w.lower() for w in text.split() if len(w) > 2]
    words = [re.sub(r"[^a-zà-ÿ]", "", w) for w in tokens]
    words = [w for w in words if len(w) > 2]
    if not words:
        return 0.0
    known_words = sum(1 for w in words if zipf_frequency(w, "fr") >= 2)
    return known_words / len(words)


def find_city(metadata_text: str) -> str | None:
    """Extract the city name from the metadata pages text.

    Expects a header format:
        Cahier citoyen
        BOURG-EN-BRESSE - 01053
        01000

    Args:
        metadata_text: Concatenated text of the first (metadata) pages.

    Returns:
        The city name in uppercase, or ``None`` if not found.
    """
    match = city_regex().search(metadata_text)
    if match is None:
        return None
    return match.group(1).strip().upper()


def find_end_page(pages: list[str]) -> int | None:
    """0-based index of the first page containing the end marker.

    Args:
        pages: List of page-extracted texts (0-based index).

    Returns:
        The index of the first marked page, or ``None`` if none.
    """
    marker = ExtractionConfig.END_MARKER.value
    for i, text in enumerate(pages):
        if marker in text:
            return i
    return None


def clean_page_text(text: str) -> str:
    """Clean the raw text extracted from a page.

    - Strip leading/trailing whitespace.
    - Normalize carriage returns.
    - Collapse multiple spaces (preserving newlines).

    Args:
        text: Raw text from PyMuPDF.

    Returns:
        The cleaned text.
    """
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in text.split("\n"):
        collapsed = " ".join(line.split())
        lines.append(collapsed)
    return "\n".join(lines).strip()


def needs_ocr_flag(text: str, wf_score: float) -> bool:
    """Decide whether a page should be flagged as handwritten (needs_ocr).

    Heuristic: non-empty page whose wordfreq quality score is below the
    configured threshold (few common French words among the extracted tokens).

    Args:
        text: Cleaned page text.
        wf_score: wordfreq quality score (``wordfreq_quality_score``).

    Returns:
        ``True`` if the page is suspected to be handwritten.
    """
    if not text.strip():
        return False
    return wf_score < ExtractionConfig.WORDFREQ_QUALITY_THRESHOLD.value


@timed
def extract_pdf_pages(filepath: str | Path, engine: Engine | None = None) -> int:
    """Extract text page-by-page and persist each page.

    Rules:
    - The first ``skip_first_n_pages`` pages are parsed only to extract the
      city name (no PageExtraction row created).
    - From the next page onward, each page is extracted, cleaned, scored and
      persisted (unless too short = noise).
    - Parsing stops at the first page containing the end marker (excluded).

    Args:
        filepath: Path of the PDF to process.
        engine: Optional SQLAlchemy engine (defaults to the global engine).

    Returns:
        The ID of the created/reused ``Contribution``.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    pdf_name = filepath.name
    logger.debug("Opening PDF: %s", pdf_name)

    doc = fitz.open(filepath)
    page_count = doc.page_count
    logger.debug("Pages: %d", page_count)

    raw_pages: list[str] = []
    for i in range(page_count):
        raw_pages.append(doc[i].get_text())
    doc.close()

    skip = ExtractionConfig.SKIP_FIRST_N_PAGES.value
    metadata_text = "\n".join(raw_pages[:skip])
    city = find_city(metadata_text) or ""
    logger.info("City extracted from metadata: %s", city or "(not found)")

    end_page = find_end_page(raw_pages)
    if end_page is not None:
        last_page = end_page  # exclusive
    else:
        last_page = page_count

    pages_data: list[dict] = []
    for i in range(skip, last_page):
        cleaned = clean_page_text(raw_pages[i])
        if len(cleaned) < ExtractionConfig.MIN_CHARS_FOR_PAGE.value:
            logger.debug("Page %d too short (%d chars) — skipped", i + 1, len(cleaned))
            continue
        score = wordfreq_quality_score(cleaned)
        ocr_flag = needs_ocr_flag(cleaned, score)
        pages_data.append(
            {
                "page_number": i + 1,
                "text": cleaned,
                "quality_score": score,
                "needs_ocr": ocr_flag,
            }
        )

    logger.info(
        "Extracted %d pages for persistence (city=%s)",
        len(pages_data),
        city or "(none)",
    )

    return save_page_extractions(
        pdf_name=pdf_name,
        city=city,
        pages=pages_data,
        engine=engine,
    )
