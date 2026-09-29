"""Control layer tracking state for the ingestion and indexing pipeline."""

from pathlib import Path
from src.config import CONTROL_DIR


class ControlTracker:
    """Manages tracking files (downloaded_books_<datalake>.txt, indexed_books_<indexer>.txt)."""

    def __init__(self, control_dir: Path = CONTROL_DIR, datalake_type: str = "time_based"):
        self.control_dir = Path(control_dir)
        self.downloaded_file = self.control_dir / f"downloaded_books_{datalake_type}.txt"
        self.control_dir.mkdir(parents=True, exist_ok=True)

    def _indexed_file(self, indexer_type: str) -> Path:
        return self.control_dir / f"indexed_books_{indexer_type}.txt"

    def _read_ids(self, file_path: Path) -> set[str]:
        if not file_path.exists():
            return set()
        return {
            line.strip()
            for line in file_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }

    def _append_id(self, file_path: Path, book_id: str) -> None:
        existing = self._read_ids(file_path)
        if book_id not in existing:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"{book_id}\n")

    def get_downloaded_ids(self) -> set[str]:
        """Return set of all downloaded book IDs."""
        return self._read_ids(self.downloaded_file)

    def get_indexed_ids(self, indexer_type: str = "monolithic") -> set[str]:
        """Return set of all book IDs indexed by the given indexer."""
        return self._read_ids(self._indexed_file(indexer_type))

    def is_downloaded(self, book_id: int | str) -> bool:
        """Check if a book ID has already been recorded as downloaded."""
        return str(book_id) in self.get_downloaded_ids()

    def is_indexed(self, book_id: int | str, indexer_type: str = "monolithic") -> bool:
        """Check if a book ID has already been recorded as indexed by the given indexer."""
        return str(book_id) in self.get_indexed_ids(indexer_type)

    def mark_downloaded(self, book_id: int | str) -> None:
        """Record a book ID as downloaded."""
        self._append_id(self.downloaded_file, str(book_id))

    def mark_indexed(self, book_id: int | str, indexer_type: str = "monolithic") -> None:
        """Record a book ID as indexed by the given indexer."""
        self._append_id(self._indexed_file(indexer_type), str(book_id))

    def get_pending_indexing(self, indexer_type: str = "monolithic") -> set[str]:
        """Return books downloaded but not yet indexed by the given indexer."""
        return self.get_downloaded_ids() - self.get_indexed_ids(indexer_type)
