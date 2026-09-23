"""Unit tests for the three alternative datalake layouts."""

from pathlib import Path
import pytest
from src.datalake import (
    BatchBasedDatalake,
    BookBasedDatalake,
    TimeBasedDatalake,
)


@pytest.mark.parametrize("datalake_cls", [
    TimeBasedDatalake,
    BookBasedDatalake,
    BatchBasedDatalake,
])
def test_datalake_variants(datalake_cls, tmp_path: Path):
    dl = datalake_cls(base_dir=tmp_path / "lake")

    h_path, b_path = dl.save_book(
        book_id=1342,
        header="Header text",
        body="Body text",
    )

    assert h_path.exists()
    assert b_path.exists()
    assert h_path.read_text(encoding="utf-8") == "Header text"
    assert b_path.read_text(encoding="utf-8") == "Body text"

    # Find book
    found_h, found_b = dl.find_book(1342)
    assert found_h == h_path
    assert found_b == b_path

    # List books
    books = dl.list_books()
    assert len(books) == 1
    assert str(books[0]["book_id"]) == "1342"
