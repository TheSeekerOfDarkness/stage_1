"""Single Monolithic File Inverted Index (JSON-based)."""

import json
from pathlib import Path
from typing import Any
from src.config import INVERTED_INDEX_JSON_PATH
from src.datamart.inverted_index.base import BaseInvertedIndex
from src.datamart.tokenizer import TextTokenizer


class MonolithicInvertedIndex(BaseInvertedIndex):
    """Stores all terms and postings in a single JSON file (datamarts/inverted_index.json)."""

    def __init__(
        self,
        file_path: Path = INVERTED_INDEX_JSON_PATH,
        tokenizer: TextTokenizer | None = None,
        track_positions: bool = False,
    ):
        super().__init__(tokenizer=tokenizer, track_positions=track_positions)
        self.file_path = Path(file_path)
        self.index: dict[str, Any] = {}
        if self.file_path.exists():
            self.load()

    def add_document(self, book_id: int | str, text: str) -> None:
        bid = int(book_id)

        if self.track_positions:
            term_positions = self.tokenizer.extract_terms_with_positions(text)
            for term, positions in term_positions.items():
                if term not in self.index:
                    self.index[term] = {}
                self.index[term][str(bid)] = positions
        else:
            tokens = set(self.tokenizer.tokenize(text))
            for term in tokens:
                if term not in self.index:
                    self.index[term] = []
                if bid not in self.index[term]:
                    self.index[term].append(bid)
                    self.index[term].sort()

    def lookup(self, term: str) -> list[int] | dict[str, list[int]]:
        clean_term = term.strip().lower()
        if self.track_positions:
            return self.index.get(clean_term, {})
        return self.index.get(clean_term, [])

    def save(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.index, f, indent=2, sort_keys=True)

    def load(self) -> None:
        if self.file_path.exists():
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.index = json.load(f)
        else:
            self.index = {}

    def clear(self) -> None:
        self.index = {}
        if self.file_path.exists():
            self.file_path.unlink()

    def get_terms_count(self) -> int:
        return len(self.index)

    def get_storage_size_bytes(self) -> int:
        if self.file_path.exists():
            return self.file_path.stat().st_size
        return 0
