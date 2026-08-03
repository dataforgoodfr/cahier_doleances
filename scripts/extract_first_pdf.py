"""Extract the first PDF from PATH_TO_DATA and persist it page by page.

Displays a recap of the created Contribution and its PageExtraction rows.
"""

# %%
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from cahier_doleances.database.db import get_engine
from cahier_doleances.database.models import Contribution, PageExtraction
from cahier_doleances.extraction.discovery import first_pdf, require_path_to_data
from cahier_doleances.extraction.extract_text import extract_pdf_pages


def main() -> int:
    """Extract and persist the first PDF found in PATH_TO_DATA.

    Returns:
        0 on success, 1 on error.
    """
    data_dir = require_path_to_data()
    pdf_path = first_pdf(data_dir)

    print(f"Selected PDF: {pdf_path.name}")
    print(f"Full path: {pdf_path.resolve()}")

    contribution_id = extract_pdf_pages(pdf_path)

    engine = get_engine()
    with Session(engine) as session:
        contribution = session.get(Contribution, contribution_id)
        if contribution is None:
            print(
                f"Contribution id={contribution_id} not found in DB",
                file=sys.stderr,
            )
            return 1

        page_rows = (
            session.execute(
                select(PageExtraction)
                .where(PageExtraction.contribution_id == contribution_id)
                .order_by(PageExtraction.page_number)
            )
            .scalars()
            .all()
        )

        print("\n--- Contribution ---")
        print(f"  id: {contribution.id}")
        print(f"  pdf_file: {contribution.pdf_file}")
        print(f"  city: {contribution.city or '(not set)'}")
        print(f"  pages: {contribution.start_page}-{contribution.end_page}")
        print(f"  is_handwritten: {contribution.is_handwritten}")

        print(f"\n--- PageExtraction ({len(page_rows)} rows) ---")
        for row in page_rows:
            preview = (row.text or "").replace("\n", " ")[:60]
            print(
                f"  p{row.page_number}: score={row.quality_score:.4f} "
                f"needs_ocr={'Y' if row.needs_ocr else 'N'} "
                f"chars={len(row.text or '')} | {preview}..."
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())

# %%
