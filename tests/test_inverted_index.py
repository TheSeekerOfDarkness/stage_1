"""Unit tests for the three physical inverted index implementations."""

from pathlib import Path
import pytest
from src.datamart.inverted_index.monolithic import MonolithicInvertedIndex
from src.datamart.inverted_index.hierarchical import HierarchicalInvertedIndex
from src.datamart.inverted_index.database import DatabaseInvertedIndex

SAMPLE_DOC_1 = "The car is nice and very fast"
SAMPLE_DOC_2 = "That car is mine and it is fast"
SAMPLE_DOC_3 = "The car is the best"


@pytest.mark.parametrize("index_cls", [
    MonolithicInvertedIndex,
    HierarchicalInvertedIndex,
    DatabaseInvertedIndex,
])
def test_inverted_index_implementations(index_cls, tmp_path: Path):
    if index_cls == MonolithicInvertedIndex:
        index = index_cls(file_path=tmp_path / "test_index.json")
    elif index_cls == HierarchicalInvertedIndex:
        index = index_cls(base_dir=tmp_path / "test_index_dir")
    else:
        index = index_cls(db_path=tmp_path / "test_index.db")

    # Add 3 documents
    index.add_document(1, SAMPLE_DOC_1)
    index.add_document(2, SAMPLE_DOC_2)
    index.add_document(3, SAMPLE_DOC_3)
    index.save()

    # Query 'car' -> should match documents 1, 2, and 3
    car_postings = index.lookup("car")
    assert sorted(car_postings) == [1, 2, 3]

    # Query 'nice' -> only doc 1
    nice_postings = index.lookup("nice")
    assert nice_postings == [1]

    # Query 'best' -> only doc 3
    best_postings = index.lookup("best")
    assert best_postings == [3]

    # Stop words like 'the' should not be indexed
    the_postings = index.lookup("the")
    assert the_postings == []

    # Non-existent term
    unknown_postings = index.lookup("submarine")
    assert unknown_postings == []

    # Terms count and storage size
    assert index.get_terms_count() >= 3
    assert index.get_storage_size_bytes() > 0


def test_positional_tracking(tmp_path: Path):
    index = MonolithicInvertedIndex(file_path=tmp_path / "pos_index.json", track_positions=True)
    index.add_document(1, "The car is fast and car is red")
    index.save()

    postings = index.lookup("car")
    # 'car' appears at position 1 and position 5 in raw tokens
    assert "1" in postings
    assert postings["1"] == [1, 5]
