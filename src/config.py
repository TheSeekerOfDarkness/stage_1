"""Configuration and path constants for Stage 1 Data Layer."""

from datetime import datetime
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATALAKE_DIR = BASE_DIR / "datalake"
DATAMARTS_DIR = BASE_DIR / "datamarts"
CONTROL_DIR = BASE_DIR / "control"

# Metadata and datamarts files
METADATA_DB_PATH = DATAMARTS_DIR / "metadata.db"
INVERTED_INDEX_JSON_PATH = DATAMARTS_DIR / "inverted_index.json"
INVERTED_INDEX_DIR_PATH = DATAMARTS_DIR / "inverted_index"

# Control files
DOWNLOADED_BOOKS_FILE = CONTROL_DIR / "downloaded_books.txt"
INDEXED_BOOKS_FILE = CONTROL_DIR / "indexed_books.txt"

# Project Gutenberg configuration
GUTENBERG_URL_TEMPLATE = "https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
START_MARKER = "*** START OF THE PROJECT GUTENBERG EBOOK"
END_MARKER = "*** END OF THE PROJECT GUTENBERG EBOOK"

DEFAULT_USER_AGENT = (
    "ULPGC-BigData-Bot/1.0 (Educational Search Engine; https://github.com/dataexplorers/stage_1)"
)


def get_time_hierarchy(dt: datetime | None = None) -> tuple[str, str]:
    """Return (YYYYMMDD, HH) strings for the time-based hierarchy."""
    if dt is None:
        dt = datetime.now()
    date_str = dt.strftime("%Y%m%d")
    hour_str = dt.strftime("%H")
    return date_str, hour_str
