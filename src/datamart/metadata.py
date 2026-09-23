"""Metadata extraction and SQLite storage layer for Project Gutenberg books."""

import re
import sqlite3
from pathlib import Path
from src.config import METADATA_DB_PATH


def parse_header(header_text: str) -> dict:
    """Parse key metadata fields from a Project Gutenberg book header.

    Extracts title, author, language, and release date using robust regex patterns.
    """
    metadata = {
        "title": "Unknown Title",
        "author": "Unknown Author",
        "language": "en",
        "release_date": None,
    }

    # Match Title
    title_match = re.search(r"^Title:\s*(.+)$", header_text, re.MULTILINE | re.IGNORECASE)
    if title_match:
        metadata["title"] = title_match.group(1).strip()

    # Match Author
    author_match = re.search(r"^Author:\s*(.+)$", header_text, re.MULTILINE | re.IGNORECASE)
    if author_match:
        metadata["author"] = author_match.group(1).strip()

    # Match Language
    lang_match = re.search(r"^Language:\s*(.+)$", header_text, re.MULTILINE | re.IGNORECASE)
    if lang_match:
        metadata["language"] = lang_match.group(1).strip()

    # Match Release date
    date_match = re.search(r"^Release [Dd]ate:\s*(.+)$", header_text, re.MULTILINE)
    if date_match:
        # Strip trailing notes like '[eBook #1342]'
        raw_date = date_match.group(1).strip()
        cleaned_date = re.sub(r"\[.*?\]", "", raw_date).strip()
        metadata["release_date"] = cleaned_date or raw_date

    return metadata


class MetadataStore:
    """SQLite-backed metadata store for book details."""

    def __init__(self, db_path: Path = METADATA_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create the books table and necessary search indexes."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS books (
                    book_id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    language TEXT,
                    release_date TEXT,
                    datalake_path TEXT,
                    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);")
            conn.commit()

    def insert_book(
        self,
        book_id: int,
        title: str,
        author: str,
        language: str = "en",
        release_date: str | None = None,
        datalake_path: str | None = None,
    ) -> None:
        """Insert or replace book metadata."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO books (book_id, title, author, language, release_date, datalake_path)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (int(book_id), title, author, language, release_date, datalake_path),
            )
            conn.commit()

    def ingest_header_text(
        self,
        book_id: int,
        header_text: str,
        datalake_path: str | None = None,
    ) -> dict:
        """Parse header and insert parsed metadata into the database."""
        parsed = parse_header(header_text)
        self.insert_book(
            book_id=book_id,
            title=parsed["title"],
            author=parsed["author"],
            language=parsed["language"],
            release_date=parsed["release_date"],
            datalake_path=datalake_path,
        )
        return {
            "book_id": int(book_id),
            "title": parsed["title"],
            "author": parsed["author"],
            "language": parsed["language"],
            "release_date": parsed["release_date"],
            "datalake_path": datalake_path,
        }

    def get_book(self, book_id: int) -> dict | None:
        """Retrieve book record by ID."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM books WHERE book_id = ?", (int(book_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    def find_by_author(self, author_query: str) -> list[dict]:
        """Search books by author name (case-insensitive substring match)."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM books WHERE author LIKE ? ORDER BY book_id ASC",
                (f"%{author_query}%",),
            )
            return [dict(row) for row in cur.fetchall()]

    def find_by_title(self, title_query: str) -> list[dict]:
        """Search books by title (case-insensitive substring match)."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM books WHERE title LIKE ? ORDER BY book_id ASC",
                (f"%{title_query}%",),
            )
            return [dict(row) for row in cur.fetchall()]

    def list_books(self) -> list[dict]:
        """Return all books stored in the metadata catalog."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM books ORDER BY book_id ASC")
            return [dict(row) for row in cur.fetchall()]

    def count_books(self) -> int:
        """Return total number of books in metadata catalog."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM books")
            return cur.fetchone()[0]
