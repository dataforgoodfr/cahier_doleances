"""PDF discovery helpers for the data directory."""

import re
from pathlib import Path

from cahier_doleances.settings import logger, settings


def _natural_sort_key(path: Path) -> list[str | int]:
    """Return a sort key that mixes alphabetical and numeric ordering.

    Splits the filename into alternating text and integer chunks so that
    ``page_2.pdf`` sorts before ``page_10.pdf``.
    """
    parts = re.split(r"(\d+)", path.name)
    return [int(part) if part.isdigit() else part for part in parts]


def list_pdfs(path: str | Path) -> list[Path]:
    """List PDF files in a directory, sorted in natural order.

    Args:
        path: Directory containing the PDFs.

    Returns:
        A list of ``Path`` objects pointing to ``*.pdf`` files.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        NotADirectoryError: If ``path`` is not a directory.
        ValueError: If no PDF is found.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"PATH_TO_DATA directory not found: {p}")
    if not p.is_dir():
        raise NotADirectoryError(f"PATH_TO_DATA is not a directory: {p}")

    pdfs = sorted(p.glob("*.pdf"), key=_natural_sort_key)
    if not pdfs:
        raise ValueError(f"No PDF found in {p}")

    logger.info("Found %d PDF(s) in %s", len(pdfs), p)
    return pdfs


def first_pdf(path: str | Path) -> Path:
    """Return the first PDF from the data directory.

    Thin wrapper around :func:`list_pdfs` for the common single-file case.

    Args:
        path: Directory containing the PDFs.

    Returns:
        The first PDF path (sorted in natural order).
    """
    return list_pdfs(path)[0]


def require_path_to_data() -> Path:
    """Read ``path_to_data`` from settings and ensure it is configured.

    Returns:
        The configured data directory as a ``Path``.

    Raises:
        ValueError: If ``PATH_TO_DATA`` is empty or not configured.
    """
    raw = settings.path_to_data
    if not raw:
        raise ValueError(
            "PATH_TO_DATA is not set. Add it to your .env file "
            "(`PATH_TO_DATA=/path/to/pdfs`)."
        )
    return Path(raw)
