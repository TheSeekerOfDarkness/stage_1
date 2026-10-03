"""Markdown report generator for benchmark results."""


def ms(stat: dict) -> str:
    return f"{stat['mean_ms']} ± {stat['stddev_ms']}"


def us(stat: dict) -> str:
    return f"{stat['mean_us']} ± {stat['stddev_us']}"


def render_benchmark_markdown_report(results: dict, books_count: int = 106) -> str:
    """Generate GitHub-flavored Markdown tables from results.json."""
    content = f"""# Empirical Benchmark Report
**Search Engine Project — Big Data (ULPGC)**

*Dataset: {books_count} Project Gutenberg books. Methodology: {results['methodology']}.*
*Times marked "ms" are wall-clock times of the whole process (includes startup). Times marked "µs" are measured inside each program (no startup), averaged over 100 repetitions.*

---

## 1. Datalake

### 1.1 Write time ({books_count} books, ms)

| Layout | Python | Java | Rust | Size (KB) | Files | Dirs |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for d in results["datalake_benchmarks"]:
        size_kb = round(d["disk_bytes"] / 1024, 1)
        content += f"| {d['layout']} | {ms(d['python'])} | {ms(d['java'])} | {ms(d['rust'])} | {size_kb} | {d['file_count']} | {d['dir_count']} |\n"

    content += """
### 1.2 Lookup cost: locate one book (µs)

| Layout | Python | Java | Rust |
| :--- | :---: | :---: | :---: |
"""
    for d in results["datalake_benchmarks"]:
        content += f"| {d['layout']} | {us(d['lookup']['python'])} | {us(d['lookup']['java'])} | {us(d['lookup']['rust'])} |\n"

    content += """
### 1.3 Incremental processing: detect books not yet indexed (µs)

| Layout | Python | Java | Rust |
| :--- | :---: | :---: | :---: |
"""
    for d in results["datalake_benchmarks"]:
        content += f"| {d['layout']} | {us(d['detect_new']['python'])} | {us(d['detect_new']['java'])} | {us(d['detect_new']['rust'])} |\n"

    content += """
### 1.4 Recovery after an interruption

A crash is simulated after a book is written to the datalake but before the control file is updated. The pipeline is then run again over all the books.

| Layout | Books expected | Books in control | Copies in datalake | Duplicates | Lost |
| :--- | :---: | :---: | :---: | :---: | :---: |
"""
    for r in results["recovery_test"]:
        content += f"| {r['layout']} | {r['books_expected']} | {r['books_in_control']} | {r['copies_in_datalake']} | {r['duplicates']} | {r['lost']} |\n"

    content += """
---

## 2. Inverted Index

### 2.1 Build time, memory and disk

| Structure | Books | Python (ms) | Java (ms) | Rust (ms) | Memory Py / Java / Rust (MB) | Size on disk (KB) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for i in results["inverted_index_benchmarks"]:
        mem = i["memory_mb"]
        size_kb = round(i["size_bytes"] / 1024, 1)
        content += f"| {i['structure']} | {i['books']} | {ms(i['python'])} | {ms(i['java'])} | {ms(i['rust'])} | {mem['python']} / {mem['java']} / {mem['rust']} | {size_kb} |\n"

    db = results["database_benchmarks"]
    content += f"| mongodb (Python only) | {db['books']} | {ms(db['build'])} | - | - | {db['memory_mb']} / - / - | {round(db['size_bytes'] / 1024, 1)} |\n"

    content += """
### 2.2 Query time (µs)

| Structure | Term | Python | Java | Rust |
| :--- | :--- | :---: | :---: | :---: |
"""
    for q in results["query_benchmarks"]:
        content += f"| {q['structure']} | `{q['term']}` | {us(q['python'])} | {us(q['java'])} | {us(q['rust'])} |\n"
    for q in db["queries"]:
        content += f"| mongodb | `{q['term']}` | {us(q['python'])} | - | - |\n"

    content += """
### 2.3 Update: add new books to an existing index (ms)

| Structure | Books already indexed | New books | Python | Java | Rust |
| :--- | :---: | :---: | :---: | :---: | :---: |
"""
    for u in results["update_benchmarks"]:
        content += f"| {u['structure']} | {u['base_books']} | {u['new_books']} | {ms(u['python'])} | {ms(u['java'])} | {ms(u['rust'])} |\n"

    content += """
### 2.4 Scalability: build time vs number of books (ms)

| Structure | Books | Python | Java | Rust |
| :--- | :---: | :---: | :---: | :---: |
"""
    for s in results["scalability_benchmarks"]:
        content += f"| {s['structure']} | {s['books']} | {ms(s['python'])} | {ms(s['java'])} | {ms(s['rust'])} |\n"

    content += """
---

## 3. Metadata Store (SQLite, Python)

| Books | Insert all (ms) | Query by author (µs) | Query by ID (µs) |
| :---: | :---: | :---: | :---: |
"""
    for m in results["metadata_benchmarks"]:
        content += f"| {m['books']} | {m['insert_ms']} | {m['query_author_us']} | {m['query_id_us']} |\n"

    return content
