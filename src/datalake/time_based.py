"""Time-based Datalake storage implementation (datalake/YYYYMMDD/HH/<BOOK_ID>.{header,body}.txt)."""

from datetime import datetime
from pathlib import Path
from src.config import DATALAKE_DIR, get_time_hierarchy


class TimeBasedDatalake:
    """Manages storage of raw book headers and bodies organized by download date and hour."""

    def __init__(self, base_dir: Path = DATALAKE_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_book(
        self,
        book_id: int | str,
        header: str,
        body: str,
        timestamp: datetime | None = None,
    ) -> tuple[Path, Path]:
        """Save a book's header and body into the time-based directory structure.

        Layout:
            base_dir / YYYYMMDD / HH / <BOOK_ID>.header.txt
            base_dir / YYYYMMDD / HH / <BOOK_ID>.body.txt

        Returns:
            Tuple of (header_path, body_path).
        """
        date_folder, hour_folder = get_time_hierarchy(timestamp)
        target_dir = self.base_dir / date_folder / hour_folder
        target_dir.mkdir(parents=True, exist_ok=True)

        header_path = target_dir / f"{book_id}.header.txt"
        body_path = target_dir / f"{book_id}.body.txt"

        header_path.write_text(header.strip(), encoding="utf-8")
        body_path.write_text(body.strip(), encoding="utf-8")

        return header_path, body_path

    def find_book(self, book_id: int | str) -> tuple[Path | None, Path | None]:
        """Find the header and body paths for a given book ID in the datalake."""
        header_pattern = f"**/{book_id}.header.txt"
        body_pattern = f"**/{book_id}.body.txt"

        headers = list(self.base_dir.glob(header_pattern))
        bodies = list(self.base_dir.glob(body_pattern))

        header_path = headers[0] if headers else None
        body_path = bodies[0] if bodies else None

        return header_path, body_path

    def list_books(self) -> list[dict]:
        """List all books currently stored in the datalake with path and metadata."""
        books = []
        for body_path in sorted(self.base_dir.glob("*/*/*.body.txt")):
            book_id = body_path.name.replace(".body.txt", "")
            header_path = body_path.parent / f"{book_id}.header.txt"
            date_folder = body_path.parent.parent.name
            hour_folder = body_path.parent.name
            books.append({
                "book_id": book_id,
                "date": date_folder,
                "hour": hour_folder,
                "header_path": header_path,
                "body_path": body_path,
                "header_size_bytes": header_path.stat().st_size if header_path.exists() else 0,
                "body_size_bytes": body_path.stat().st_size if body_path.exists() else 0,
            })
        return books
