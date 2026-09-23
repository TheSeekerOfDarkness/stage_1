"""Tests for metadata parser and SQLite metadata store."""

from pathlib import Path
from src.datamart.metadata import MetadataStore, parse_header

SAMPLE_HEADER = """The Project Gutenberg eBook of Pride and Prejudice
Title: Pride and Prejudice
Author: Jane Austen
Release date: June 1, 1998 [eBook #1342]
Language: English
"""


def test_parse_header_valid():
    meta = parse_header(SAMPLE_HEADER)
    assert meta["title"] == "Pride and Prejudice"
    assert meta["author"] == "Jane Austen"
    assert meta["language"] == "English"
    assert "June 1, 1998" in meta["release_date"]


def test_parse_header_missing_fields():
    meta = parse_header("Some generic header without clear fields")
    assert meta["title"] == "Unknown Title"
    assert meta["author"] == "Unknown Author"
    assert meta["language"] == "en"


def test_metadata_store_crud(tmp_path: Path):
    db_file = tmp_path / "test_metadata.db"
    store = MetadataStore(db_path=db_file)

    assert store.count_books() == 0

    # Ingest book header
    res = store.ingest_header_text(
        book_id=1342,
        header_text=SAMPLE_HEADER,
        datalake_path="datalake/20260916/13/1342.body.txt",
    )
    assert res["book_id"] == 1342
    assert store.count_books() == 1

    # Get by ID
    book = store.get_book(1342)
    assert book is not None
    assert book["title"] == "Pride and Prejudice"
    assert book["author"] == "Jane Austen"
    assert book["datalake_path"] == "datalake/20260916/13/1342.body.txt"

    # Search by author
    by_author = store.find_by_author("Austen")
    assert len(by_author) == 1
    assert by_author[0]["book_id"] == 1342

    # Search by title
    by_title = store.find_by_title("Prejudice")
    assert len(by_title) == 1
    assert by_title[0]["book_id"] == 1342

    # Insert another book
    store.insert_book(
        book_id=11,
        title="Alice's Adventures in Wonderland",
        author="Lewis Carroll",
        language="English",
    )
    assert store.count_books() == 2
    assert len(store.list_books()) == 2
