#!/usr/bin/env python3
"""Unified Automated Benchmarking Suite for Stage 1 Search Engine.

Implements rigorous benchmarking methodology according to course guidelines:
- Warmup iterations (avoiding "cold" JVM / interpreter / cache effects)
- Multiple measurement trials with statistical indicators:
  Mean, Standard Deviation (StdDev), Min, Max, and 95% Confidence Interval
- Evaluates 3 Languages (Python, Java, Rust) across:
  1. Datalake Layouts: write, lookup, incremental detection, storage overhead, recovery
  2. Inverted Index Layouts: build, query, update, memory, disk, scalability
  3. Metadata store (SQLite): insertion and queries
"""

import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

DATALAKE_DIR = BASE_DIR / "datalake"
BENCHMARK_DIR = BASE_DIR / "benchmarks"
BENCH_RUNNER = BENCHMARK_DIR / "bench_runner.py"
RESULTS_JSON = BENCHMARK_DIR / "results.json"
REPORT_MD = BENCHMARK_DIR / "BENCHMARK_REPORT.md"
TMP_DIR = BENCHMARK_DIR / "tmp"

JAVA_BUILD_DIR = BASE_DIR / "languages" / "java" / "build"
RUST_BIN = BASE_DIR / "languages" / "rust" / "target" / "release" / "searchengine_rust"

LANGUAGES = ["python", "java", "rust"]
COMMANDS = {
    "python": [sys.executable, str(BENCH_RUNNER)],
    "java": ["java", "-cp", str(JAVA_BUILD_DIR), "searchengine.Main"],
    "rust": [str(RUST_BIN)],
}
LAYOUTS = ["time_based", "book_based", "batch_based"]
QUERY_TERMS = ["rabbit", "monster", "science"]
MONOLITHIC_SIZES = [25, 50, 106]
HIERARCHICAL_SIZES = [5, 10, 20]
DATABASE_SIZE = 5

from src.control.tracker import ControlTracker
from src.datalake import BatchBasedDatalake, BookBasedDatalake, TimeBasedDatalake
from src.datamart.metadata import MetadataStore
from src.pipeline import IngestionPipeline
from benchmarks.report_template import render_benchmark_markdown_report


def get_dir_size_and_count(dir_path: Path) -> tuple[int, int, int]:
    """Return (total_bytes, file_count, dir_count)."""
    total_bytes = 0
    file_count = 0
    dir_count = 0
    if not dir_path.exists():
        return 0, 0, 0
    for root, dirs, files in os.walk(dir_path):
        dir_count += len(dirs)
        file_count += len(files)
        for f in files:
            p = os.path.join(root, f)
            if not os.path.islink(p):
                total_bytes += os.path.getsize(p)
    return total_bytes, file_count, dir_count


def sorted_body_files() -> list[Path]:
    bodies = list(DATALAKE_DIR.glob("*/*/*.body.txt"))
    return sorted(bodies, key=lambda p: int(p.name.replace(".body.txt", "")))


def make_books_dir(target_dir: Path, start: int, end: int) -> None:
    """Copy book bodies number start..end-1 (sorted by ID) into a flat directory."""
    shutil.rmtree(target_dir, ignore_errors=True)
    target_dir.mkdir(parents=True)
    for body in sorted_body_files()[start:end]:
        shutil.copy(body, target_dir / body.name)


def prepare_sample_books_dir(target_dir: Path) -> list[int]:
    """Collect all available book bodies from datalake into a flat directory for benchmark tests."""
    target_dir.mkdir(parents=True, exist_ok=True)
    book_ids = []
    for body in DATALAKE_DIR.glob("*/*/*.body.txt"):
        bid = int(body.name.replace(".body.txt", ""))
        book_ids.append(bid)
        shutil.copy(body, target_dir / f"{bid}.txt")
    return sorted(book_ids)


def restore_dir(source: Path, target: Path) -> None:
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(source, target)


def restore_file(source: Path, target: Path) -> None:
    shutil.copy(source, target)


def run_benchmark_trials(
    cmd: list[str],
    warmups: int = 2,
    iterations: int = 5,
    cleanup_fn=None,
) -> dict:
    """Execute warmup iterations followed by measurement iterations (wall-clock time of the process).

    Calculates: mean, stddev, min, max, and margin of error at 95% confidence.
    """
    for _ in range(warmups):
        if cleanup_fn:
            cleanup_fn()
        subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, check=True)

    times_ms = []
    last_stdout = ""
    for _ in range(iterations):
        if cleanup_fn:
            cleanup_fn()
        t0 = time.perf_counter()
        res = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, check=True)
        t_ms = (time.perf_counter() - t0) * 1000
        times_ms.append(t_ms)
        last_stdout = res.stdout.strip()

    mean_val = statistics.mean(times_ms)
    stddev_val = statistics.stdev(times_ms) if len(times_ms) > 1 else 0.0
    min_val = min(times_ms)
    max_val = max(times_ms)

    t_crit = 2.776 if iterations == 5 else 2.0
    ci_margin = (t_crit * stddev_val / math.sqrt(iterations)) if iterations > 1 else 0.0

    return {
        "mean_ms": round(mean_val, 2),
        "stddev_ms": round(stddev_val, 2),
        "min_ms": round(min_val, 2),
        "max_ms": round(max_val, 2),
        "ci95_margin": round(ci_margin, 2),
        "iterations": iterations,
        "warmups": warmups,
        "raw_times_ms": [round(t, 2) for t in times_ms],
        "stdout": last_stdout,
    }


def run_internal_trials(cmd: list[str], warmups: int = 2, iterations: int = 5) -> dict:
    """Run a command several times and use the time it measures itself ("time_us"), without process startup."""
    for _ in range(warmups):
        subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, check=True)

    times_us = []
    for _ in range(iterations):
        res = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, check=True)
        output = json.loads(res.stdout.strip().splitlines()[-1])
        times_us.append(output["time_us"])

    return {
        "mean_us": round(statistics.mean(times_us), 3),
        "stddev_us": round(statistics.stdev(times_us), 3),
        "min_us": round(min(times_us), 3),
        "max_us": round(max(times_us), 3),
        "iterations": iterations,
        "warmups": warmups,
        "raw_times_us": [round(t, 3) for t in times_us],
    }


def measure_peak_memory_mb(cmd: list[str], cleanup_fn=None) -> float:
    """Run a command once and return the highest memory (RSS) seen while it runs, in MB."""
    if cleanup_fn:
        cleanup_fn()
    process = subprocess.Popen(cmd, cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ps_process = psutil.Process(process.pid)
    peak = 0
    while process.poll() is None:
        try:
            rss = ps_process.memory_info().rss
            if rss > peak:
                peak = rss
        except psutil.Error:
            break
        time.sleep(0.01)
    process.wait()
    return round(peak / (1024 * 1024), 1)


def compile_engines() -> None:
    java_srcs = [str(p) for p in (BASE_DIR / "languages" / "java" / "src" / "searchengine").glob("*.java")]
    subprocess.run(["javac", "-d", str(JAVA_BUILD_DIR)] + java_srcs, check=True)
    subprocess.run(["cargo", "build", "--release", "--manifest-path", str(BASE_DIR / "languages" / "rust" / "Cargo.toml")], check=True)


def benchmark_datalake(sample_dir: Path, book_ids: list[int]):
    print("\n=== Running Datalake Architecture Benchmarks ===")
    results = []
    lookup_id = str(book_ids[len(book_ids) // 2])
    indexed_file = TMP_DIR / "indexed_books.txt"
    with open(indexed_file, "w", encoding="utf-8") as f:
        for bid in book_ids[: len(book_ids) // 2]:
            f.write(f"{bid}\n")

    for layout in LAYOUTS:
        print(f"Testing layout: {layout}...")
        entry = {"layout": layout, "lookup": {}, "detect_new": {}}
        for lang in LANGUAGES:
            out_lake = TMP_DIR / f"{lang}_{layout}"
            cmd = COMMANDS[lang] + ["benchmark-datalake", layout, str(sample_dir), str(out_lake)]
            entry[lang] = run_benchmark_trials(cmd, cleanup_fn=lambda: shutil.rmtree(out_lake, ignore_errors=True))

            cmd = COMMANDS[lang] + ["lookup-datalake", layout, str(out_lake), lookup_id]
            entry["lookup"][lang] = run_internal_trials(cmd)

            cmd = COMMANDS[lang] + ["detect-new", str(out_lake), str(indexed_file)]
            entry["detect_new"][lang] = run_internal_trials(cmd)

        size, files, dirs = get_dir_size_and_count(TMP_DIR / f"python_{layout}")
        entry["disk_bytes"] = size
        entry["file_count"] = files
        entry["dir_count"] = dirs
        results.append(entry)
        print(f"  -> write ms: Py {entry['python']['mean_ms']} | Java {entry['java']['mean_ms']} | Rust {entry['rust']['mean_ms']}")
    return results


def benchmark_index_scalability():
    print("\n=== Running Inverted Index Build Benchmarks (scalability) ===")
    results = []
    for structure, sizes, command, warmups, iterations in [
        ("monolithic_json", MONOLITHIC_SIZES, "index-monolithic", 2, 5),
        ("hierarchical_folders", HIERARCHICAL_SIZES, "index-hierarchical", 1, 2),
    ]:
        for size in sizes:
            print(f"Testing {structure} build with {size} books...")
            books_dir = TMP_DIR / f"books_{size}"
            make_books_dir(books_dir, 0, size)
            entry = {"structure": structure, "books": size}
            for lang in LANGUAGES:
                if structure == "monolithic_json":
                    out = TMP_DIR / f"{lang}_mono_{size}.json"
                    cleanup = lambda: out.unlink(missing_ok=True)
                else:
                    out = TMP_DIR / f"{lang}_hier_{size}"
                    cleanup = lambda: shutil.rmtree(out, ignore_errors=True)
                cmd = COMMANDS[lang] + [command, str(books_dir), str(out)]
                entry[lang] = run_benchmark_trials(cmd, warmups=warmups, iterations=iterations, cleanup_fn=cleanup)
            results.append(entry)
            print(f"  -> Py {entry['python']['mean_ms']} | Java {entry['java']['mean_ms']} | Rust {entry['rust']['mean_ms']} ms")
    return results


def benchmark_index_main(scalability):
    """Build-time, memory and disk for the main configurations (monolithic with all books, hierarchical with 5)."""
    print("\n=== Measuring memory and disk of the main index configurations ===")
    results = []
    for entry in scalability:
        is_main_mono = entry["structure"] == "monolithic_json" and entry["books"] == MONOLITHIC_SIZES[-1]
        is_main_hier = entry["structure"] == "hierarchical_folders" and entry["books"] == HIERARCHICAL_SIZES[0]
        if not (is_main_mono or is_main_hier):
            continue
        size = entry["books"]
        books_dir = TMP_DIR / f"books_{size}"
        main_entry = {
            "structure": entry["structure"],
            "books": size,
            "python": entry["python"],
            "java": entry["java"],
            "rust": entry["rust"],
            "memory_mb": {},
        }
        for lang in LANGUAGES:
            if is_main_mono:
                out = TMP_DIR / f"{lang}_mono_{size}.json"
                cmd = COMMANDS[lang] + ["index-monolithic", str(books_dir), str(out)]
                main_entry["memory_mb"][lang] = measure_peak_memory_mb(cmd, cleanup_fn=lambda: out.unlink(missing_ok=True))
            else:
                out = TMP_DIR / f"{lang}_hier_{size}"
                cmd = COMMANDS[lang] + ["index-hierarchical", str(books_dir), str(out)]
                main_entry["memory_mb"][lang] = measure_peak_memory_mb(cmd, cleanup_fn=lambda: shutil.rmtree(out, ignore_errors=True))
        if is_main_mono:
            main_entry["size_bytes"] = (TMP_DIR / f"python_mono_{size}.json").stat().st_size
        else:
            size_bytes, files, dirs = get_dir_size_and_count(TMP_DIR / f"python_hier_{size}")
            main_entry["size_bytes"] = size_bytes
            main_entry["files_count"] = files
        results.append(main_entry)
        print(f"  -> {entry['structure']} memory MB: {main_entry['memory_mb']}")
    return results


def benchmark_queries():
    print("\n=== Running Query Benchmarks (lookup time only, no process startup) ===")
    results = []
    mono_size = MONOLITHIC_SIZES[-1]
    hier_size = HIERARCHICAL_SIZES[0]
    for term in QUERY_TERMS:
        for structure in ["monolithic_json", "hierarchical_folders"]:
            entry = {"structure": structure, "term": term}
            for lang in LANGUAGES:
                if structure == "monolithic_json":
                    cmd = COMMANDS[lang] + ["query-monolithic", str(TMP_DIR / f"{lang}_mono_{mono_size}.json"), term]
                else:
                    cmd = COMMANDS[lang] + ["query-hierarchical", str(TMP_DIR / f"{lang}_hier_{hier_size}"), term]
                entry[lang] = run_internal_trials(cmd)
            results.append(entry)
            print(f"  -> {structure} '{term}': Py {entry['python']['mean_us']} | Java {entry['java']['mean_us']} | Rust {entry['rust']['mean_us']} us")
    return results


def benchmark_updates():
    print("\n=== Running Index Update Benchmarks (add new books to an existing index) ===")
    results = []

    total = len(sorted_body_files())
    new_mono = TMP_DIR / "new_mono"
    make_books_dir(new_mono, total - 5, total)
    base_books = TMP_DIR / "base_mono_books"
    make_books_dir(base_books, 0, total - 5)
    base_mono = TMP_DIR / "base_mono.json"
    subprocess.run(COMMANDS["python"] + ["index-monolithic", str(base_books), str(base_mono)], cwd=BASE_DIR, check=True, capture_output=True)

    entry = {"structure": "monolithic_json", "base_books": total - 5, "new_books": 5}
    for lang in LANGUAGES:
        work = TMP_DIR / f"{lang}_update_mono.json"
        cmd = COMMANDS[lang] + ["update-monolithic", str(work), str(new_mono)]
        entry[lang] = run_benchmark_trials(cmd, cleanup_fn=lambda: restore_file(base_mono, work))
    results.append(entry)
    print(f"  -> monolithic: Py {entry['python']['mean_ms']} | Java {entry['java']['mean_ms']} | Rust {entry['rust']['mean_ms']} ms")

    hier_size = HIERARCHICAL_SIZES[0]
    new_hier = TMP_DIR / "new_hier"
    make_books_dir(new_hier, hier_size, hier_size + 1)
    base_hier = TMP_DIR / f"python_hier_{hier_size}"

    entry = {"structure": "hierarchical_folders", "base_books": hier_size, "new_books": 1}
    for lang in LANGUAGES:
        work = TMP_DIR / f"{lang}_update_hier"
        cmd = COMMANDS[lang] + ["index-hierarchical", str(new_hier), str(work)]
        entry[lang] = run_benchmark_trials(cmd, warmups=1, iterations=2, cleanup_fn=lambda: restore_dir(base_hier, work))
    results.append(entry)
    print(f"  -> hierarchical: Py {entry['python']['mean_ms']} | Java {entry['java']['mean_ms']} | Rust {entry['rust']['mean_ms']} ms")
    return results


def benchmark_database():
    """MongoDB inverted index (Python only). Requires MongoDB running: docker compose up -d"""
    print("\n=== Running MongoDB Inverted Index Benchmarks (Python) ===")
    books_dir = TMP_DIR / f"books_{DATABASE_SIZE}"
    make_books_dir(books_dir, 0, DATABASE_SIZE)
    cmd = COMMANDS["python"] + ["index-database", str(books_dir)]
    build = run_benchmark_trials(cmd, warmups=0, iterations=2)
    output = json.loads(build["stdout"].splitlines()[-1])
    memory = measure_peak_memory_mb(cmd)

    queries = []
    for term in QUERY_TERMS:
        stat = run_internal_trials(COMMANDS["python"] + ["query-database", term])
        queries.append({"term": term, "python": stat})
        print(f"  -> mongodb '{term}': Py {stat['mean_us']} us")

    print(f"  -> mongodb build: {build['mean_ms']} ms, memory {memory} MB")
    return {
        "books": DATABASE_SIZE,
        "build": build,
        "memory_mb": memory,
        "size_bytes": output["size_bytes"],
        "terms": output["terms"],
        "queries": queries,
    }


def benchmark_metadata():
    """SQLite metadata store (Python): insertion time and query time for different numbers of books."""
    print("\n=== Running Metadata Benchmarks (SQLite) ===")
    headers = []
    for body in sorted_body_files():
        book_id = int(body.name.replace(".body.txt", ""))
        header_path = body.parent / f"{book_id}.header.txt"
        headers.append((book_id, header_path.read_text(encoding="utf-8")))

    results = []
    for size in MONOLITHIC_SIZES:
        store = MetadataStore(db_path=TMP_DIR / f"metadata_{size}.db")

        t0 = time.perf_counter()
        for book_id, text in headers[:size]:
            store.ingest_header_text(book_id, text)
        insert_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        for _ in range(100):
            store.find_by_author("Carroll")
        author_us = (time.perf_counter() - t0) * 1_000_000 / 100

        t0 = time.perf_counter()
        for _ in range(100):
            store.get_book(headers[0][0])
        id_us = (time.perf_counter() - t0) * 1_000_000 / 100

        results.append({
            "books": size,
            "insert_ms": round(insert_ms, 2),
            "query_author_us": round(author_us, 2),
            "query_id_us": round(id_us, 2),
        })
        print(f"  -> {size} books: insert {round(insert_ms, 2)} ms, by author {round(author_us, 2)} us, by id {round(id_us, 2)} us")
    return results


def fake_download(book_id: int) -> str:
    """Rebuild a Gutenberg-like text from the local datalake, so the recovery test does not need internet."""
    header_path, body_path = TimeBasedDatalake(base_dir=DATALAKE_DIR).find_book(book_id)
    header = header_path.read_text(encoding="utf-8")
    body = body_path.read_text(encoding="utf-8")
    return (
        header
        + "\n*** START OF THE PROJECT GUTENBERG EBOOK TEST ***\n"
        + body
        + "\n*** END OF THE PROJECT GUTENBERG EBOOK TEST ***\n"
    )


def recovery_test(book_ids: list[int]):
    """Simulate a crash after a book is written but before the control file is updated, then resume."""
    print("\n=== Running Recovery Test ===")
    books = book_ids[:10]
    results = []
    for layout in LAYOUTS:
        test_dir = TMP_DIR / f"recovery_{layout}"
        shutil.rmtree(test_dir, ignore_errors=True)
        if layout == "time_based":
            datalake = TimeBasedDatalake(base_dir=test_dir / "lake")
        elif layout == "book_based":
            datalake = BookBasedDatalake(base_dir=test_dir / "lake")
        else:
            datalake = BatchBasedDatalake(base_dir=test_dir / "lake")
        control = ControlTracker(control_dir=test_dir / "control")
        pipeline = IngestionPipeline(datalake=datalake, control=control)
        pipeline.downloader.download_text = fake_download

        pipeline.ingest_batch(books[:4])
        header, body, footer = pipeline.downloader.split_book_text(fake_download(books[4]))
        datalake.save_book(books[4], header, body, timestamp=datetime(2000, 1, 1, 0))

        pipeline.ingest_batch(books)

        lake_ids = []
        for book in datalake.list_books():
            lake_ids.append(str(book["book_id"]))
        unique_ids = set(lake_ids)
        entry = {
            "layout": layout,
            "books_expected": len(books),
            "books_in_control": len(control.get_downloaded_ids()),
            "copies_in_datalake": len(lake_ids),
            "duplicates": len(lake_ids) - len(unique_ids),
            "lost": len(books) - len(unique_ids),
        }
        results.append(entry)
        print(f"  -> {layout}: {entry}")
    return results


def generate_markdown_report(full_results, books_count):
    content = render_benchmark_markdown_report(full_results, books_count=books_count)
    REPORT_MD.write_text(content, encoding="utf-8")
    print(f"\nSaved statistical benchmark markdown report to: {REPORT_MD}")


def main():
    shutil.rmtree(TMP_DIR, ignore_errors=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    compile_engines()

    sample_dir = TMP_DIR / "sample_books"
    books = prepare_sample_books_dir(sample_dir)
    print(f"Prepared {len(books)} sample benchmarking books in {sample_dir}")

    dl_res = benchmark_datalake(sample_dir, books)
    scalability = benchmark_index_scalability()
    idx_res = benchmark_index_main(scalability)
    q_res = benchmark_queries()
    update_res = benchmark_updates()
    db_res = benchmark_database()
    meta_res = benchmark_metadata()
    recovery_res = recovery_test(books)

    full_results = {
        "timestamp": time.time(),
        "methodology": "warmup=2, iterations=5 (hierarchical: warmup=1, iterations=2), statistical indicators: mean, stddev, min, max, ci95",
        "datalake_benchmarks": dl_res,
        "inverted_index_benchmarks": idx_res,
        "query_benchmarks": q_res,
        "scalability_benchmarks": scalability,
        "update_benchmarks": update_res,
        "database_benchmarks": db_res,
        "metadata_benchmarks": meta_res,
        "recovery_test": recovery_res,
    }

    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(full_results, f, indent=2)
    print(f"Saved raw statistical results to: {RESULTS_JSON}")

    generate_markdown_report(full_results, len(books))
    shutil.rmtree(TMP_DIR, ignore_errors=True)

    print("\nGenerating publication-quality comparison charts...")
    from benchmarks.generate_plots import main as generate_all_plots
    generate_all_plots()

    print("\nStatistical Benchmarking Complete!")


if __name__ == "__main__":
    main()
