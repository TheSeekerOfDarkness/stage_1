"""Automated unit and integration tests for Stage 1 Datalake Ingestion."""

from datetime import datetime
from pathlib import Path
import pytest
from src.control.tracker import ControlTracker
from src.crawler.downloader import BookDownloader
from src.datalake.time_based import TimeBasedDatalake
from src.pipeline import IngestionPipeline

SAMPLE_BOOK_TEXT = """The Project Gutenberg eBook of Sample Book
Title: Sample Book
Author: Test Author
Language: English

*** START OF THE PROJECT GUTENBERG EBOOK SAMPLE BOOK ***

Chapter 1.
It was the best of times, it was the worst of times.

*** END OF THE PROJECT GUTENBERG EBOOK SAMPLE BOOK ***

Gutenberg License footer notes...
"""


def test_split_book_text_valid():
    downloader = BookDownloader()
    header, body, footer = downloader.split_book_text(SAMPLE_BOOK_TEXT)

    assert "Title: Sample Book" in header
    assert "Author: Test Author" in header
    assert "*** START" not in header
    assert "It was the best of times" in body
    assert "*** END" not in body
    assert "Gutenberg License footer" in footer


def test_split_book_text_missing_marker():
    downloader = BookDownloader()
    with pytest.raises(ValueError, match="delimiters"):
        downloader.split_book_text("Just some text without markers")


def test_time_based_datalake_save_and_find(tmp_path: Path):
    datalake = TimeBasedDatalake(base_dir=tmp_path)
    fixed_time = datetime(2026, 9, 16, 14, 30)

    header_path, body_path = datalake.save_book(
        book_id=9999,
        header="Header content",
        body="Body content",
        timestamp=fixed_time,
    )

    expected_dir = tmp_path / "20260916" / "14"
    assert header_path == expected_dir / "9999.header.txt"
    assert body_path == expected_dir / "9999.body.txt"
    assert header_path.exists()
    assert body_path.exists()
    assert header_path.read_text(encoding="utf-8") == "Header content"
    assert body_path.read_text(encoding="utf-8") == "Body content"

    # Test find_book
    found_header, found_body = datalake.find_book(9999)
    assert found_header == header_path
    assert found_body == body_path

    # Test list_books
    books = datalake.list_books()
    assert len(books) == 1
    assert books[0]["book_id"] == "9999"
    assert books[0]["date"] == "20260916"
    assert books[0]["hour"] == "14"


def test_control_tracker(tmp_path: Path):
    tracker = ControlTracker(control_dir=tmp_path)

    assert not tracker.is_downloaded("1234")
    assert not tracker.is_indexed("1234")

    tracker.mark_downloaded("1234")
    assert tracker.is_downloaded("1234")
    assert tracker.get_pending_indexing() == {"1234"}

    tracker.mark_indexed("1234")
    assert tracker.is_indexed("1234")
    assert tracker.get_pending_indexing() == set()


def test_pipeline_idempotence(tmp_path: Path, monkeypatch):
    test_control_dir = tmp_path / "control"
    test_datalake_dir = tmp_path / "datalake"

    tracker = ControlTracker(control_dir=test_control_dir)
    datalake = TimeBasedDatalake(base_dir=test_datalake_dir)
    downloader = BookDownloader()

    # Mock download_text to avoid network in unit test
    monkeypatch.setattr(downloader, "download_text", lambda book_id: SAMPLE_BOOK_TEXT)

    pipeline = IngestionPipeline(downloader=downloader, datalake=datalake, control=tracker)

    # First ingestion -> success
    res1 = pipeline.ingest_book(5555)
    assert res1["status"] == "success"
    assert tracker.is_downloaded("5555")

    # Second ingestion -> skipped (idempotent)
    res2 = pipeline.ingest_book(5555)
    assert res2["status"] == "skipped"
    assert res2["reason"] == "already_downloaded"

    # Force ingestion -> success again
    res3 = pipeline.ingest_book(5555, force=True)
    assert res3["status"] == "success"
