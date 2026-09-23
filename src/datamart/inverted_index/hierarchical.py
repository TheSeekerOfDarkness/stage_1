"""Hierarchical Folder Structure Inverted Index (datamarts/inverted_index/{A..Z}/{term}.txt)."""

import os
from pathlib import Path
from typing import Any
from src.config import INVERTED_INDEX_DIR_PATH
from src.datamart.inverted_index.base import BaseInvertedIndex
from src.datamart.tokenizer import TextTokenizer


class HierarchicalInvertedIndex(BaseInvertedIndex):
    """Stores each term as an individual .txt file grouped in subdirectories by first character."""

    def __init__(
        self,
        base_dir: Path = INVERTED_INDEX_DIR_PATH,
        tokenizer: TextTokenizer | None = None,
        track_positions: bool = False,
    ):
        super().__init__(tokenizer=tokenizer, track_positions=track_positions)
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_term_path(self, term: str) -> Path:
        clean_term = term.strip().lower()
        if not clean_term:
            folder = "_"
        else:
            first_char = clean_term[0].upper()
            folder = first_char if first_char.isalnum() else "_"
        return self.base_dir / folder / f"{clean_term}.txt"

    def add_document(self, book_id: int | str, text: str) -> None:
        bid = int(book_id)

        if self.track_positions:
            term_positions = self.tokenizer.extract_terms_with_positions(text)
            for term, positions in term_positions.items():
                term_path = self._get_term_path(term)
                term_path.parent.mkdir(parents=True, exist_ok=True)

                existing_postings: dict[str, list[int]] = {}
                if term_path.exists():
                    for line in term_path.read_text(encoding="utf-8").splitlines():
                        if ":" in line:
                            doc, pos_str = line.split(":", 1)
                            pos_list = [int(p) for p in pos_str.split(",") if p]
                            existing_postings[doc] = pos_list

                existing_postings[str(bid)] = positions
                # Write back sorted
                lines = [
                    f"{doc}:{','.join(str(p) for p in existing_postings[doc])}"
                    for doc in sorted(existing_postings.keys(), key=lambda x: int(x))
                ]
                term_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        else:
            tokens = set(self.tokenizer.tokenize(text))
            for term in tokens:
                term_path = self._get_term_path(term)
                term_path.parent.mkdir(parents=True, exist_ok=True)

                existing_ids = set()
                if term_path.exists():
                    for line in term_path.read_text(encoding="utf-8").splitlines():
                        clean_line = line.strip()
                        if clean_line:
                            existing_ids.add(int(clean_line))

                existing_ids.add(bid)
                sorted_ids = sorted(existing_ids)
                content = "\n".join(str(doc_id) for doc_id in sorted_ids) + "\n"
                term_path.write_text(content, encoding="utf-8")

    def lookup(self, term: str) -> list[int] | dict[str, list[int]]:
        clean_term = term.strip().lower()
        term_path = self._get_term_path(clean_term)
        if not term_path.exists():
            return {} if self.track_positions else []

        lines = term_path.read_text(encoding="utf-8").splitlines()
        if self.track_positions:
            res: dict[str, list[int]] = {}
            for line in lines:
                if ":" in line:
                    doc, pos_str = line.split(":", 1)
                    res[doc] = [int(p) for p in pos_str.split(",") if p]
            return res
        else:
            return [int(line.strip()) for line in lines if line.strip().isdigit()]

    def save(self) -> None:
        """Individual files are written incrementally in add_document."""
        pass

    def load(self) -> None:
        """Filesystem acts as index."""
        pass

    def clear(self) -> None:
        """Delete all generated term files and subfolders."""
        if self.base_dir.exists():
            for root, dirs, files in os.walk(self.base_dir, topdown=False):
                for f in files:
                    os.unlink(os.path.join(root, f))
                for d in dirs:
                    os.rmdir(os.path.join(root, d))

    def get_terms_count(self) -> int:
        count = 0
        if self.base_dir.exists():
            for _ in self.base_dir.glob("*/*.txt"):
                count += 1
        return count

    def get_storage_size_bytes(self) -> int:
        total = 0
        if self.base_dir.exists():
            for p in self.base_dir.glob("*/*.txt"):
                total += p.stat().st_size
        return total
