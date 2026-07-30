"""Extract the first PDF from PATH_TO_DATA and persist it to the database."""

import sys

from sqlalchemy.orm import Session

from cahier_doleances.database.db import get_engine
from cahier_doleances.database.models import Contribution, Extraction
from cahier_doleances.extraction.discovery import first_pdf, require_path_to_data
from cahier_doleances.extraction.extract_text import extract_pdf


def main() -> int:
    """Extract and persist the first PDF found in PATH_TO_DATA.

    Returns:
        0 on success, 1 on error.
    """
    data_dir = require_path_to_data()
    pdf_path = first_pdf(data_dir)

    print(f"Selected PDF: {pdf_path.name}")
    print(f"Full path: {pdf_path.resolve()}")

    extraction_id = extract_pdf(pdf_path)

    engine = get_engine()
    with Session(engine) as session:
        extraction = session.get(Extraction, extraction_id)
        if extraction is None:
            print(f"Extraction id={extraction_id} not found in DB", file=sys.stderr)
            return 1

        contribution = session.get(Contribution, extraction.contribution_id)
        if contribution is None:
            print(
                f"Contribution id={extraction.contribution_id} not found",
                file=sys.stderr,
            )
            return 1

        print("\n--- Contribution ---")
        print(f"  id: {contribution.id}")
        print(f"  pdf_file: {contribution.pdf_file}")
        print(f"  city: {contribution.city or '(not set)'}")
        print(f"  pages: {contribution.start_page}-{contribution.end_page}")
        print(f"  is_handwritten: {contribution.is_handwritten}")

        print("\n--- Extraction ---")
        print(f"  id: {extraction.id}")
        print(f"  ocr: {extraction.ocr}")
        print(f"  num_words: {extraction.num_words}")
        print(f"  num_lines: {extraction.num_lines}")

        preview = (extraction.text or "")[:500]
        print(f"\n--- Text preview (first 500 chars) ---\n{preview}\n---")

    return 0


if __name__ == "__main__":
    sys.exit(main())
