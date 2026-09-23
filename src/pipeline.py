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

    def get_index_backend(self, indexer_type: str = "monolithic"):
        """Factory for inverted index backend instances."""
        from src.datamart.inverted_index import (
            DatabaseInvertedIndex,
            HierarchicalInvertedIndex,
            MonolithicInvertedIndex,
        )
        if indexer_type == "hierarchical":
            return HierarchicalInvertedIndex()
        elif indexer_type in ("database", "mongodb", "sqlite"):
            return DatabaseInvertedIndex()
        return MonolithicInvertedIndex()

    def index_book(self, book_id: int | str, indexer_type: str = "monolithic") -> dict:
        """Index a downloaded book: extracts metadata to SQLite and indexes body text."""
        from src.datamart.metadata import MetadataStore
        book_id_str = str(book_id)
        header_path, body_path = self.datalake.find_book(book_id_str)

        if not header_path or not body_path or not header_path.exists() or not body_path.exists():
            raise FileNotFoundError(f"Book {book_id_str} files not found in datalake.")

        header_text = header_path.read_text(encoding="utf-8")
        body_text = body_path.read_text(encoding="utf-8")

        # 1. Feed Metadata store
        metadata_store = MetadataStore()
        meta = metadata_store.ingest_header_text(
            book_id=int(book_id_str),
            header_text=header_text,
            datalake_path=str(body_path),
        )

        # 2. Feed Inverted Index
        index = self.get_index_backend(indexer_type)
        index.add_document(int(book_id_str), body_text)
        index.save()

        # 3. Mark indexed in control layer
        self.control.mark_indexed(book_id_str)

        logger.info("Successfully indexed book %s using %s indexer.", book_id_str, indexer_type)
        return {
            "book_id": book_id_str,
            "status": "indexed",
            "indexer_type": indexer_type,
            "title": meta["title"],
            "author": meta["author"],
        }

    def index_pending(self, indexer_type: str = "monolithic") -> list[dict]:
        """Index all downloaded books that are marked pending in the control tracker."""
        pending = sorted(list(self.control.get_pending_indexing()), key=lambda x: int(x))
        results = []
        for bid in pending:
            try:
                res = self.index_book(bid, indexer_type=indexer_type)
                results.append(res)
            except Exception as exc:
                logger.error("Failed to index book %s: %s", bid, exc)
                results.append({"book_id": bid, "status": "failed", "error": str(exc)})
        return results

    def search(self, query: str, indexer_type: str = "monolithic") -> dict:
        """Execute a search query across the inverted index and resolve metadata."""
        from src.datamart.metadata import MetadataStore
        from src.datamart.tokenizer import TextTokenizer

        tokenizer = TextTokenizer()
        query_terms = tokenizer.tokenize(query)

        if not query_terms:
            return {"query": query, "terms": [], "results": []}

        index = self.get_index_backend(indexer_type)
        metadata_store = MetadataStore()

        # Boolean AND query for multiple terms
        candidate_ids = None
        for term in query_terms:
            postings = set(index.lookup(term))
            if candidate_ids is None:
                candidate_ids = postings
            else:
                candidate_ids &= postings

        doc_ids = sorted(list(candidate_ids or set()))
        hits = []
        for bid in doc_ids:
            meta = metadata_store.get_book(bid)
            if meta:
                hits.append(meta)
            else:
                hits.append({"book_id": bid, "title": "Unknown", "author": "Unknown"})

        return {
            "query": query,
            "terms": query_terms,
            "total_hits": len(hits),
            "results": hits,
        }
