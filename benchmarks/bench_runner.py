#!/usr/bin/env python3
"""Standardized CLI entry point for Python benchmark operations.

Mirrors the CLI signature of searchengine.Main (Java) and searchengine_rust (Rust)
to ensure identical process execution semantics across all three languages.
"""

import sys
import time
from pathlib import Path

# Ensure project root is importable
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.datalake import BatchBasedDatalake, BookBasedDatalake, TimeBasedDatalake
from src.datamart.inverted_index.hierarchical import HierarchicalInvertedIndex
from src.datamart.inverted_index.monolithic import MonolithicInvertedIndex


def walk_body_files(lake_dir: Path) -> list[tuple[int, str]]:
    """Recursively collect book ID and body content from datalake directory."""
    docs = []
    body_files = list(lake_dir.rglob("*.body.txt"))
    if not body_files:
        body_files = list(lake_dir.rglob("*.txt"))
    for p in body_files:
        stem = p.name.replace(".body.txt", "").replace(".txt", "")
        if stem.isdigit():
            docs.append((int(stem), p.read_text(encoding="utf-8", errors="replace")))
    return docs


def run_benchmark_datalake(layout: str, sample_dir: str, out_lake: str):
    inp = Path(sample_dir)
    out = Path(out_lake)

    if layout == "time_based":
        dl = TimeBasedDatalake(base_dir=out)
    elif layout == "book_based":
        dl = BookBasedDatalake(base_dir=out)
    elif layout == "batch_based":
        dl = BatchBasedDatalake(base_dir=out)
    else:
        raise ValueError(f"Unknown datalake layout: {layout}")

    count = 0
    t0 = time.perf_counter()
    for p in sorted(inp.glob("*.txt")):
        bid = int(p.stem)
        content = p.read_text(encoding="utf-8")
        dl.save_book(bid, f"Header {bid}", content)
        count += 1
    elapsed_ms = (time.perf_counter() - t0) * 1000
    print(f'{{"status": "success", "layout": "{layout}", "books": {count}, "time_ms": {elapsed_ms:.2f}}}')


def run_index_monolithic(lake_dir_str: str, out_json_str: str):
    lake_dir = Path(lake_dir_str)
    out_json = Path(out_json_str)

    t0 = time.perf_counter()
    idx = MonolithicInvertedIndex(file_path=out_json)
    idx.clear()

    docs = walk_body_files(lake_dir)
    for bid, body in docs:
        idx.add_document(bid, body)
    idx.save()

    elapsed_ms = (time.perf_counter() - t0) * 1000
    print(f'{{"status": "success", "time_ms": {elapsed_ms:.2f}, "terms": {len(idx.index)}, "output": "{out_json}"}}')


def run_index_hierarchical(lake_dir_str: str, out_dir_str: str):
    lake_dir = Path(lake_dir_str)
    out_dir = Path(out_dir_str)

    t0 = time.perf_counter()
    idx = HierarchicalInvertedIndex(base_dir=out_dir)
    idx.clear()

    docs = walk_body_files(lake_dir)
    for bid, body in docs:
        idx.add_document(bid, body)

    elapsed_ms = (time.perf_counter() - t0) * 1000
    print(f'{{"status": "success", "time_ms": {elapsed_ms:.2f}, "output": "{out_dir}"}}')


def run_query_hierarchical(index_dir_str: str, term: str):
    index_dir = Path(index_dir_str)
    idx = HierarchicalInvertedIndex(base_dir=index_dir)

    t0 = time.perf_counter()
    postings = idx.lookup(term)
    elapsed_us = (time.perf_counter() - t0) * 1_000_000
    print(f'{{"term": "{term}", "time_us": {elapsed_us:.2f}, "postings": {postings}}}')


def main():
    if len(sys.argv) < 2:
        print("Usage: python benchmarks/bench_runner.py <command> [args...]", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "benchmark-datalake":
        run_benchmark_datalake(sys.argv[2], sys.argv[3], sys.argv[4])
    elif command == "index-monolithic":
        run_index_monolithic(sys.argv[2], sys.argv[3])
    elif command == "index-hierarchical":
        run_index_hierarchical(sys.argv[2], sys.argv[3])
    elif command == "query-hierarchical":
        run_query_hierarchical(sys.argv[2], sys.argv[3])
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
