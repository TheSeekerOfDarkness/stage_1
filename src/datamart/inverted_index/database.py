"""Database Inverted Index implementation (MongoDB with embedded SQLite fallback)."""

import json
from pathlib import Path
import sqlite3
from typing import Any
from src.config import DATAMARTS_DIR
from src.datamart.inverted_index.base import BaseInvertedIndex
from src.datamart.tokenizer import TextTokenizer


class SQLiteBackend:
    """Embedded database backend for inverted index storing terms and JSON postings."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS inverted_index (
                    term TEXT PRIMARY KEY,
                    postings_json TEXT NOT NULL
                );
                """
            )
            conn.commit()

    def get_term(self, term: str) -> Any | None:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT postings_json FROM inverted_index WHERE term = ?", (term,))
            row = cur.fetchone()
            return json.loads(row[0]) if row else None

    def upsert_term(self, term: str, postings: Any) -> None:
        payload = json.dumps(postings)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO inverted_index (term, postings_json)
                VALUES (?, ?)
                """,
                (term, payload),
            )
            conn.commit()

    def clear(self) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM inverted_index")
            conn.commit()

    def count(self) -> int:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM inverted_index")
            return cur.fetchone()[0]

    def size_bytes(self) -> int:
        return self.db_path.stat().st_size if self.db_path.exists() else 0


class MongoBackend:
    """MongoDB backend for inverted index storing terms as documents."""

    def __init__(self, mongo_uri: str = "mongodb://localhost:27017", db_name: str = "search_engine"):
        import pymongo
        self.client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        # Test connection
        self.client.admin.command("ping")
        self.db = self.client[db_name]
        self.collection = self.db["inverted_index"]
        self.collection.create_index("term", unique=True)

    def get_term(self, term: str) -> Any | None:
        doc = self.collection.find_one({"term": term})
        return doc.get("postings") if doc else None

    def upsert_term(self, term: str, postings: Any) -> None:
        self.collection.update_one(
            {"term": term},
            {"$set": {"term": term, "postings": postings}},
            upsert=True,
        )

    def clear(self) -> None:
        self.collection.delete_many({})

    def count(self) -> int:
        return self.collection.count_documents({})

    def size_bytes(self) -> int:
        stats = self.db.command("collStats", "inverted_index")
        return stats.get("size", 0)


class DatabaseInvertedIndex(BaseInvertedIndex):
    """Database-backed Inverted Index.

    Uses MongoDB if available/specified; otherwise seamlessly falls back to
    an embedded SQLite document store at `datamarts/inverted_index.db`.
    """

    def __init__(
        self,
        mongo_uri: str | None = None,
        db_path: Path | None = None,
        tokenizer: TextTokenizer | None = None,
        track_positions: bool = False,
    ):
        super().__init__(tokenizer=tokenizer, track_positions=track_positions)
        self.backend_type = "sqlite"

        # Attempt MongoDB if explicit URI or default requested
        if mongo_uri:
            try:
                self.backend = MongoBackend(mongo_uri=mongo_uri)
                self.backend_type = "mongodb"
            except Exception:
                # Fallback to SQLite
                fallback_path = db_path or (DATAMARTS_DIR / "inverted_index.db")
                self.backend = SQLiteBackend(fallback_path)
                self.backend_type = "sqlite"
        else:
            default_path = db_path or (DATAMARTS_DIR / "inverted_index.db")
            self.backend = SQLiteBackend(default_path)

    def add_document(self, book_id: int | str, text: str) -> None:
        bid = int(book_id)

        if self.track_positions:
            term_positions = self.tokenizer.extract_terms_with_positions(text)
            for term, positions in term_positions.items():
                existing = self.backend.get_term(term) or {}
                existing[str(bid)] = positions
                self.backend.upsert_term(term, existing)
        else:
            tokens = set(self.tokenizer.tokenize(text))
            for term in tokens:
                existing = self.backend.get_term(term) or []
                if bid not in existing:
                    existing.append(bid)
                    existing.sort()
                self.backend.upsert_term(term, existing)

    def lookup(self, term: str) -> list[int] | dict[str, list[int]]:
        clean_term = term.strip().lower()
        postings = self.backend.get_term(clean_term)
        if postings is None:
            return {} if self.track_positions else []
        return postings

    def save(self) -> None:
        pass

    def load(self) -> None:
        pass

    def clear(self) -> None:
        self.backend.clear()

    def get_terms_count(self) -> int:
        return self.backend.count()

    def get_storage_size_bytes(self) -> int:
        return self.backend.size_bytes()
