#!/usr/bin/env python3
"""CLI interface for Stage 1: Search Engine Ingestion Pipeline."""

import argparse
import json
import sys
from src.pipeline import IngestionPipeline


def main():
    parser = argparse.ArgumentParser(
        description="Search Engine Stage 1 - Datalake Ingestion Pipeline (ULPGC Big Data)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Ingest subcommand
    ingest_parser = subparsers.add_parser("ingest", help="Ingest one or more books into the datalake")
    ingest_parser.add_argument(
        "--book-id",
        type=int,
        nargs="+",
        required=True,
        help="One or more Project Gutenberg Book IDs (e.g. 1342 for Pride and Prejudice)",
    )
    ingest_parser.add_argument(
        "--force",
        action="store_true",
        help="Force download and overwrite even if already marked as downloaded in control layer",
    )
    ingest_parser.add_argument(
        "--datalake",
        choices=["time_based", "book_based", "batch_based"],
        default="time_based",
        help="Datalake organization hierarchy (default: time_based)",
    )

    # Index subcommand
    index_parser = subparsers.add_parser("index", help="Index downloaded books into Datamarts")
    index_parser.add_argument(
        "--book-id",
        type=int,
        nargs="*",
        help="Specific book ID(s) to index (defaults to all pending downloaded books)",
    )
    index_parser.add_argument(
        "--indexer",
        choices=["monolithic", "hierarchical", "database"],
        default="monolithic",
        help="Inverted index storage architecture (default: monolithic)",
    )
    index_parser.add_argument(
        "--datalake",
        choices=["time_based", "book_based", "batch_based"],
        default="time_based",
        help="Datalake layout to read books from (default: time_based)",
    )

    # Search subcommand
    search_parser = subparsers.add_parser("search", help="Search the inverted index")
    search_parser.add_argument("query", type=str, help="Search query keywords")
    search_parser.add_argument(
        "--indexer",
        choices=["monolithic", "hierarchical", "database"],
        default="monolithic",
        help="Inverted index storage architecture to query",
    )

    # Run subcommand
    run_parser = subparsers.add_parser("run", help="Run control layer steps (index pending or download new)")
    run_parser.add_argument("--steps", type=int, default=1, help="Number of steps to run (default: 1)")
    run_parser.add_argument(
        "--indexer",
        choices=["monolithic", "hierarchical", "database"],
        default="monolithic",
        help="Inverted index used for indexing steps (default: monolithic)",
    )

    # Status subcommand
    status_parser = subparsers.add_parser("status", help="Show datalake and control layer status")
    status_parser.add_argument(
        "--datalake",
        choices=["time_based", "book_based", "batch_based"],
        default="time_based",
        help="Datalake organization hierarchy to inspect (default: time_based)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    dl_type = getattr(args, "datalake", "time_based")
    pipeline = IngestionPipeline(datalake_type=dl_type)

    if args.command == "ingest":
        results = pipeline.ingest_batch(args.book_id, force=args.force)
        print("\n=== Ingestion Summary ===")
        for res in results:
            print(json.dumps(res, indent=2))
        all_success = all(r.get("status") in ("success", "skipped") for r in results)
        sys.exit(0 if all_success else 1)

    elif args.command == "index":
        if args.book_id:
            results = pipeline.index_batch(args.book_id, indexer_type=args.indexer)
        else:
            results = pipeline.index_pending(indexer_type=args.indexer)
        print(f"\n=== Indexing Summary ({args.indexer}) ===")
        for res in results:
            print(json.dumps(res, indent=2))
        sys.exit(0)

    elif args.command == "search":
        result = pipeline.search(args.query, indexer_type=args.indexer)
        print(f"\n=== Search Results for: '{args.query}' ({args.indexer}) ===")
        print(f"Total matching books: {result['total_hits']}")
        for hit in result["results"]:
            print(f"  - [{hit['book_id']}] {hit['title']} by {hit['author']}")
        sys.exit(0)

    elif args.command == "run":
        for step in range(1, args.steps + 1):
            try:
                res = pipeline.run_step(indexer_type=args.indexer)
            except Exception as exc:
                res = {"status": "failed", "error": str(exc)}
            print(f"[CONTROL] Step {step}/{args.steps}: {res.get('status')} {res.get('book_id', '')}")
        sys.exit(0)

    elif args.command == "status":
        status = pipeline.get_status()
        print("\n=== Data Layer Status ===")
        print(f"Downloaded books recorded in control: {status['total_downloaded_in_control']}")
        print(f"Indexed books recorded in control:    {status['total_indexed_in_control']}")
        print(f"Pending for indexing:                {status['pending_indexing']}")
        print(f"Total book entries in datalake:       {status['total_books_in_datalake']}")
        if status["datalake_books"]:
            print("\nDatalake contents:")
            for b in status["datalake_books"]:
                location = f"(Date: {b['date']}, Hour: {b['hour']}) " if "date" in b else ""
                print(
                    f"  - Book ID: {b['book_id']} {location}"
                    f"[Header: {b['header_size_bytes']} bytes, Body: {b['body_size_bytes']} bytes]"
                )


if __name__ == "__main__":
    main()
