"""Book-based Datalake storage implementation (datalake/<BOOK_ID>/header.txt, body.txt)."""

from pathlib import Path
from src.config import BASE_DIR

DEFAULT_BOOK_BASED_DIR = BASE_DIR / "datalake_book_based"


class BookBasedDatalake:
    """Manages storage of books where each book has its own dedicated directory."""

    def __init__(self, base_dir: Path = DEFAULT_BOOK_BASED_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_book(
        self,
        book_id: int | str,
        header: str,
        body: str,
        **kwargs,
    ) -> tuple[Path, Path]:
        """Save a book's header and body into its own directory.

        Layout:
            base_dir / <BOOK_ID> / header.txt
            base_dir / <BOOK_ID> / body.txt
        """
        target_dir = self.base_dir / str(book_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        header_path = target_dir / "header.txt"
        body_path = target_dir / "body.txt"

        header_path.write_text(header.strip(), encoding="utf-8")
        body_path.write_text(body.strip(), encoding="utf-8")

        return header_path, body_path

    def find_book(self, book_id: int | str) -> tuple[Path | None, Path | None]:
        """Find the header and body paths for a given book ID in the datalake."""
        target_dir = self.base_dir / str(book_id)
        header_path = target_dir / "header.txt"
        body_path = target_dir / "body.txt"

        return (
            header_path if header_path.exists() else None,
            body_path if body_path.exists() else None,
        )

    def list_books(self) -> list[dict]:
        """List all books stored in the book-based datalake."""
        books = []
        if not self.base_dir.exists():
            return books

        for book_dir in sorted(self.base_dir.iterdir()):
            if book_dir.is_dir():
                book_id = book_dir.name
                header_path = book_dir / "header.txt"
                body_path = book_dir / "body.txt"
                if body_path.exists():
                    books.append({
                        "book_id": book_id,
                        "header_path": header_path,
                        "body_path": body_path,
                        "header_size_bytes": header_path.stat().st_size if header_path.exists() else 0,
                        "body_size_bytes": body_path.stat().st_size,
                    })
        return books
