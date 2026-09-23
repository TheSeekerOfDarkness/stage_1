"""Control layer tracking state for the ingestion and indexing pipeline."""

from pathlib import Path
from src.config import CONTROL_DIR, DOWNLOADED_BOOKS_FILE, INDEXED_BOOKS_FILE


class ControlTracker:
    """Manages tracking files (downloaded_books.txt, indexed_books.txt)."""

    def __init__(
        self,
        control_dir: Path = CONTROL_DIR,
        downloaded_file: Path | None = None,
        indexed_file: Path | None = None,
    ):
        self.control_dir = Path(control_dir)
        self.downloaded_file = downloaded_file or (self.control_dir / "downloaded_books.txt")
        self.indexed_file = indexed_file or (self.control_dir / "indexed_books.txt")
        self.control_dir.mkdir(parents=True, exist_ok=True)

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

    def get_indexed_ids(self) -> set[str]:
        """Return set of all indexed book IDs."""
        return self._read_ids(self.indexed_file)

    def is_downloaded(self, book_id: int | str) -> bool:
        """Check if a book ID has already been recorded as downloaded."""
        return str(book_id) in self.get_downloaded_ids()

    def is_indexed(self, book_id: int | str) -> bool:
        """Check if a book ID has already been recorded as indexed."""
        return str(book_id) in self.get_indexed_ids()

    def mark_downloaded(self, book_id: int | str) -> None:
        """Record a book ID as downloaded."""
        self._append_id(self.downloaded_file, str(book_id))

    def mark_indexed(self, book_id: int | str) -> None:
        """Record a book ID as indexed."""
        self._append_id(self.indexed_file, str(book_id))

    def get_pending_indexing(self) -> set[str]:
        """Return books downloaded but not yet indexed."""
        return self.get_downloaded_ids() - self.get_indexed_ids()
