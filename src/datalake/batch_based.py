"""Batch or Range-based Datalake storage implementation (datalake_batch/batch_0000_0999/<BOOK_ID>.body.txt)."""

from pathlib import Path
from src.config import BASE_DIR

DEFAULT_BATCH_BASED_DIR = BASE_DIR / "datalake_batch_based"


class BatchBasedDatalake:
    """Manages storage of books grouped into batch/range folders of a fixed size."""

    def __init__(self, base_dir: Path = DEFAULT_BATCH_BASED_DIR, batch_size: int = 1000):
        self.base_dir = Path(base_dir)
        self.batch_size = batch_size
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_batch_folder_name(self, book_id: int | str) -> str:
        bid = int(book_id)
        start = (bid // self.batch_size) * self.batch_size
        end = start + self.batch_size - 1
        return f"batch_{start:05d}_{end:05d}"

    def save_book(
        self,
        book_id: int | str,
        header: str,
        body: str,
        **kwargs,
    ) -> tuple[Path, Path]:
        """Save a book's header and body into its corresponding batch folder.

        Layout:
            base_dir / batch_XXXXX_YYYYY / <BOOK_ID>.header.txt
            base_dir / batch_XXXXX_YYYYY / <BOOK_ID>.body.txt
        """
        batch_folder = self._get_batch_folder_name(book_id)
        target_dir = self.base_dir / batch_folder
        target_dir.mkdir(parents=True, exist_ok=True)

        header_path = target_dir / f"{book_id}.header.txt"
        body_path = target_dir / f"{book_id}.body.txt"

        header_path.write_text(header.strip(), encoding="utf-8")
        body_path.write_text(body.strip(), encoding="utf-8")

        return header_path, body_path

    def find_book(self, book_id: int | str) -> tuple[Path | None, Path | None]:
        """Find the header and body paths for a given book ID in the batch datalake."""
        batch_folder = self._get_batch_folder_name(book_id)
        target_dir = self.base_dir / batch_folder
        header_path = target_dir / f"{book_id}.header.txt"
        body_path = target_dir / f"{book_id}.body.txt"

        return (
            header_path if header_path.exists() else None,
            body_path if body_path.exists() else None,
        )

    def list_books(self) -> list[dict]:
        """List all books stored in the batch-based datalake."""
        books = []
        if not self.base_dir.exists():
            return books

        for body_path in sorted(self.base_dir.glob("batch_*/*.body.txt")):
            book_id = body_path.name.replace(".body.txt", "")
            header_path = body_path.parent / f"{book_id}.header.txt"
            batch_folder = body_path.parent.name
            books.append({
                "book_id": book_id,
                "batch": batch_folder,
                "header_path": header_path,
                "body_path": body_path,
                "header_size_bytes": header_path.stat().st_size if header_path.exists() else 0,
                "body_size_bytes": body_path.stat().st_size,
            })
        return books
