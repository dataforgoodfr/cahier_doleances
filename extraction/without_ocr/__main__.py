"""Extract all PDFs from PATH_TO_DATA and persist them page by page.

Displays a concise recap of each created Contribution and the total
extraction time.
"""

import sys

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tqdm import tqdm

from database.db import get_engine
from database.models import Contribution, PageExtraction
from extraction.without_ocr.discovery import list_pdfs, require_path_to_data
from extraction.without_ocr.extract_text import extract_pdf_pages
from extraction.without_ocr.settings import logger
from extraction.without_ocr.timing import timed


@timed
def main() -> int:
    """Extract and persist all PDFs found in PATH_TO_DATA.

    Returns:
        0 if all PDFs were processed successfully, 1 otherwise.
    """
    data_dir = require_path_to_data()
    pdf_paths = list_pdfs(data_dir)

    logger.info(f"Found {len(pdf_paths)} PDF(s) in {data_dir.resolve()}")

    engine = get_engine()
    failed: list[str] = []
    succeeded: list[int] = []

    with Session(engine) as session:
        for pdf_path in tqdm(pdf_paths, desc="Extracting PDFs"):
            logger.debug(f"\nSelected PDF: {pdf_path.name}")
            logger.debug(f"Full path: {pdf_path.resolve()}")

            try:
                contribution_id = extract_pdf_pages(pdf_path, engine=engine)
            except Exception:  # noqa: BLE001 - catch any per-PDF failure to keep the batch running
                logger.exception("Failed to extract %s", pdf_path.name)
                failed.append(pdf_path.name)
                continue

            contribution = session.get(Contribution, contribution_id)
            if contribution is None:
                logger.warning("Contribution id=%d not found in DB", contribution_id)
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

            logger.info("--- Contribution ---")
            logger.info(f"  id: {contribution.id}")
            logger.info(f"  pdf_file: {contribution.pdf_file}")
            logger.info(f"  city: {contribution.city or '(not set)'}")
            logger.info(f"  pages: {contribution.start_page}-{contribution.end_page}")
            logger.info(f"  page_extraction_rows: {page_count}")
            logger.info(f"  is_handwritten: {contribution.is_handwritten}")

            succeeded.append(contribution_id)

    logger.info("\n=== Summary ===")
    logger.info(f"  processed: {len(succeeded)}")
    logger.info(f"  failed: {len(failed)}")
    if failed:
        logger.info(f"  failed files: {', '.join(failed)}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
