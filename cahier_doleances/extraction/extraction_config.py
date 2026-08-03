"""Configuration for PDF extraction (business parameters).

Distinct from ``settings.py`` (which holds secrets/connections): this module
centralizes parsing rules and quality thresholds as simple enum values.
"""

import enum
import re


class ExtractionConfig(enum.Enum):
    """Extraction parameters as simple constants.

    Each value may be a string, int or float; access via ``.value`` or the
    convenience module-level constants below.
    """

    # End marker for useful content (parsing stops beyond this page).
    END_MARKER = "Fin des pages écrites"

    # Number of first pages considered metadata (parsed for the city but not
    # persisted as PageExtraction rows).
    SKIP_FIRST_N_PAGES = 2

    # wordfreq quality score threshold below which a non-empty page is suspected
    # to be handwritten (needs_ocr=True). Typical values: clean French ~0.85,
    # OCR garbage ~0.0; 0.3 leaves a safety margin for informal text.
    WORDFREQ_QUALITY_THRESHOLD = 0.3

    # Minimum length (in characters) for a page to be persisted; shorter pages
    # are treated as noise.
    MIN_CHARS_FOR_PAGE = 10

    # Regex extracting the city name from the metadata page header.
    # Expected format:
    #   Cahier citoyen
    #   BOURG-EN-BRESSE - 01053
    #   01000
    CITY_PATTERN = (
        r"Cahier\s+citoyen\s*\n\s*"
        r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-\s]+?)\s*-\s*\d{5}\s*\n\s*\d{5}"
    )


def city_regex() -> re.Pattern[str]:
    """Compile the city pattern with case-insensitive flag.

    Returns:
        The compiled pattern (usable via ``.search``).
    """
    return re.compile(ExtractionConfig.CITY_PATTERN.value, re.IGNORECASE)
