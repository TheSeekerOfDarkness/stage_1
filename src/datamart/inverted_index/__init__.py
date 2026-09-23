"""Inverted index implementations: Monolithic, Hierarchical, and Database."""

from src.datamart.inverted_index.base import BaseInvertedIndex
from src.datamart.inverted_index.monolithic import MonolithicInvertedIndex
from src.datamart.inverted_index.hierarchical import HierarchicalInvertedIndex
from src.datamart.inverted_index.database import DatabaseInvertedIndex

__all__ = [
    "BaseInvertedIndex",
    "MonolithicInvertedIndex",
    "HierarchicalInvertedIndex",
    "DatabaseInvertedIndex",
]
