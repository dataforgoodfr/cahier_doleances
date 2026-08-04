"""Extract all PDFs from PATH_TO_DATA and persist them page by page.

Displays a concise recap of each created Contribution and the total
extraction time.
"""

import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tqdm import tqdm

from cahier_doleances.database.db import get_engine
from cahier_doleances.database.models import Contribution, PageExtraction
from cahier_doleances.extraction.discovery import list_pdfs, require_path_to_data
from cahier_doleances.extraction.extract_text import extract_pdf_pages
from cahier_doleances.utils.timing import timed
from cahier_doleances.config import logger

@timed
def main() -> int:
    """Extract and persist all PDFs found in PATH_TO_DATA.

    Returns:
        0 if all PDFs were processed successfully, 1 otherwise.
    """
    data_dir = require_path_to_data()
    pdf_paths = list_pdfs(data_dir)

    print(f"Found {len(pdf_paths)} PDF(s) in {data_dir.resolve()}")

    engine = get_engine()
    failed: list[str] = []
    succeeded: list[int] = []

    with Session(engine) as session:
        for pdf_path in tqdm(pdf_paths, desc="Extracting PDFs"):
            print(f"\nSelected PDF: {pdf_path.name}")
            print(f"Full path: {pdf_path.resolve()}")

            try:
                contribution_id = extract_pdf_pages(pdf_path)
            except Exception as exc:  # noqa: BLE001 - catch any per-PDF failure to keep the batch running
                print(
                    f"Failed to extract {pdf_path.name}: {exc}",
                    file=sys.stderr,
                )
                failed.append(pdf_path.name)
                continue

            contribution = session.get(Contribution, contribution_id)
            if contribution is None:
                print(
                    f"Contribution id={contribution_id} not found in DB",
                    file=sys.stderr,
                )
                failed.append(pdf_path.name)
                continue

            page_count = (
                session.execute(
                    select(func.count(PageExtraction.id)).where(
                        PageExtraction.contribution_id == contribution_id
                    )
                ).scalar()
                or 0
            )

            print("--- Contribution ---")
            print(f"  id: {contribution.id}")
            print(f"  pdf_file: {contribution.pdf_file}")
            print(f"  city: {contribution.city or '(not set)'}")
            print(f"  pages: {contribution.start_page}-{contribution.end_page}")
            print(f"  page_extraction_rows: {page_count}")
            print(f"  is_handwritten: {contribution.is_handwritten}")

            succeeded.append(contribution_id)

    print("\n=== Summary ===")
    print(f"  processed: {len(succeeded)}")
    print(f"  failed: {len(failed)}")
    if failed:
        print(f"  failed files: {', '.join(failed)}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
