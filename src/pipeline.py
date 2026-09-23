"""Ingestion pipeline orchestrating Crawler, Datalake, and Control layers."""

import logging
from pathlib import Path
from src.control.tracker import ControlTracker
from src.crawler.downloader import BookDownloader
from src.datalake.time_based import TimeBasedDatalake

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates loading and ingesting books into the time-based datalake."""

    def __init__(
        self,
        downloader: BookDownloader | None = None,
        datalake: TimeBasedDatalake | None = None,
        control: ControlTracker | None = None,
    ):
        self.downloader = downloader or BookDownloader()
        self.datalake = datalake or TimeBasedDatalake()
        self.control = control or ControlTracker()

    def ingest_book(self, book_id: int | str, force: bool = False) -> dict:
        """Ingest a single book by ID.

        Workflow:
        1. Check control layer state (prevent duplicate downloads unless force=True).
        2. Fetch raw book text from Project Gutenberg.
        3. Split into header and body.
        4. Save into the time-based datalake hierarchy.
        5. Update the control layer state.

        Returns:
            Dictionary with execution summary.
        """
        book_id_str = str(book_id)

        if not force and self.control.is_downloaded(book_id_str):
            header_path, body_path = self.datalake.find_book(book_id_str)
            logger.info("Book %s has already been downloaded. Skipping.", book_id_str)
            return {
                "book_id": book_id_str,
                "status": "skipped",
                "reason": "already_downloaded",
                "header_path": str(header_path) if header_path else None,
                "body_path": str(body_path) if body_path else None,
            }

        logger.info("Downloading book %s from Project Gutenberg...", book_id_str)
        raw_text = self.downloader.download_text(int(book_id_str))

        logger.info("Parsing and splitting text for book %s...", book_id_str)
        header, body, _ = self.downloader.split_book_text(raw_text)

        logger.info("Saving book %s into time-based datalake...", book_id_str)
        header_path, body_path = self.datalake.save_book(book_id_str, header, body)

        logger.info("Updating control layer state...")
        self.control.mark_downloaded(book_id_str)

        logger.info(
            "Successfully ingested book %s into %s and %s",
            book_id_str,
            header_path,
            body_path,
        )

        return {
            "book_id": book_id_str,
            "status": "success",
            "header_path": str(header_path),
            "body_path": str(body_path),
            "header_size_chars": len(header),
            "body_size_chars": len(body),
        }

    def ingest_batch(self, book_ids: list[int | str], force: bool = False) -> list[dict]:
        """Ingest a batch of books."""
        results = []
        for bid in book_ids:
            try:
                res = self.ingest_book(bid, force=force)
                results.append(res)
            except Exception as exc:
                logger.error("Failed to ingest book %s: %s", bid, exc)
                results.append({"book_id": str(bid), "status": "failed", "error": str(exc)})
        return results

    def get_status(self) -> dict:
        """Return the current status of the datalake and control layer."""
        downloaded = self.control.get_downloaded_ids()
        indexed = self.control.get_indexed_ids()
        pending = self.control.get_pending_indexing()
        datalake_books = self.datalake.list_books()

        return {
            "total_downloaded_in_control": len(downloaded),
            "total_indexed_in_control": len(indexed),
            "pending_indexing": sorted(list(pending)),
            "total_books_in_datalake": len(datalake_books),
            "datalake_books": datalake_books,
        }
