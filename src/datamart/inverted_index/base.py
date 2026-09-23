"""Abstract base class for Inverted Index implementations."""

from abc import ABC, abstractmethod
from typing import Any
from src.datamart.tokenizer import TextTokenizer


class BaseInvertedIndex(ABC):
    """Uniform interface for all Inverted Index storage structures."""

    def __init__(self, tokenizer: TextTokenizer | None = None, track_positions: bool = False):
        self.tokenizer = tokenizer or TextTokenizer()
        self.track_positions = track_positions

    @abstractmethod
    def add_document(self, book_id: int | str, text: str) -> None:
        """Process document body text and update the index with its terms and postings."""
        pass

    @abstractmethod
    def lookup(self, term: str) -> list[int] | dict[str, list[int]]:
        """Lookup posting list (and optional positions) for a term.

        Returns:
            - If track_positions=False: list of book_ids [5, 12, 42]
            - If track_positions=True: dict mapping book_id to list of positions {"5": [12, 45]}
        """
        pass

    @abstractmethod
    def save(self) -> None:
        """Persist index state to disk or database."""
        pass

    @abstractmethod
    def load(self) -> None:
        """Load index state from disk or database."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Wipe the index contents."""
        pass

    @abstractmethod
    def get_terms_count(self) -> int:
        """Return the number of unique indexed terms."""
        pass

    @abstractmethod
    def get_storage_size_bytes(self) -> int:
        """Return total size in bytes occupied by the stored index."""
        pass
