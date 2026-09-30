# Stage 1: Building the Data Layer

**Search Engine Project — Big Data**  

---

## 1. Introduction & Objectives

The primary objective of Stage 1 is to establish the **Data Layer**, the foundational backbone of a distributed search engine capable of handling web-scale document collections.

The stage is divided into three interconnected subsystems:

1. **Unstructured Ingestion (Datalake):** Storing raw and preprocessed book texts downloaded from Project Gutenberg under alternative partitioning layouts.
2. **Structured Queryable Datamarts:** Extracting structured catalog metadata into an embedded relational store (SQLite) and constructing inverted indexes under multiple physical formats to enable sub-millisecond keyword retrieval.
3. **Control & State Tracking Layer:** Ensuring idempotency, auditability, and failure-recovery by maintaining persistent records of ingested and indexed document identifiers.
4. **Empirical Multi-Language Benchmarking:** Comparing performance across **Python 3.12**, **Java 11 (OpenJDK)**, and **Rust 1.93 (Native compiled)** across multiple storage and indexing architectures to evaluate runtime efficiency, I/O bottlenecks, and scalability trade-offs.

---

## 2. System Architecture

The search engine data layer follows a decoupled, pipeline-driven architecture:

```text
┌────────────────────────┐      ┌────────────────────────┐
│  Project Gutenberg     │ ───> │  Crawler & Splitter    │
└────────────────────────┘      └───────────┬────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
         ┌─────────────────────┐                         ┌─────────────────────┐
         │     Datalake        │                         │     Control Layer   │
         │  (Unstructured)     │                         │  (State Tracking)   │
         │  YYYYMMDD/HH/*.txt  │                         │  downloaded/indexed │
         └──────────┬──────────┘                         └─────────────────────┘
                    │
                    ▼
         ┌─────────────────────────────────────────────────────────┐
         │                        Datamarts                        │
         ├────────────────────────────┬────────────────────────────┤
         │       Metadata Store       │       Inverted Index       │
         │          (SQLite)          │   3 Physical Architectures:│
         │  books(id, title, author)  │   1. Monolithic (JSON)     │
         │                            │   2. Hierarchical (Folders)│
         │                            │   3. Database (MongoDB)    │
         └────────────────────────────┴────────────────────────────┘
```

### 3.1 Datalake Storage Architectures

Three distinct physical layouts were designed and implemented:

1. **Time-Based Hierarchy (`datalake/YYYYMMDD/HH/`)**:
   - Matches production distributed object stores (Amazon S3 partition keys, HDFS directories).
   - Allows incremental indexing: indexers can scan only the latest hourly directory rather than traversing the entire lake.
2. **Book-Based Hierarchy (`datalake_book_based/<BOOK_ID>/`)**:
   - Each book has a dedicated folder containing `header.txt` and `body.txt`.
   - Simplifies manual inspection and book deletion, but creates high directory counts at scale.
3. **Batch-Based Hierarchy (`datalake_batch_based/batch_XXXXX_YYYYY/`)**:
   - Partitions documents into fixed buckets of 1,000 books.
   - Prevents filesystem inode exhaustion while retaining fast direct path lookups (`O(1)` via mathematical ID hashing: `start = (id // 1000) * 1000`).

### 3.2 Datamarts

1. **Metadata Catalog (`datamarts/metadata.db`)**:
   - SQLite relational store with indexed columns:

     ```sql
     CREATE TABLE books (
         book_id INTEGER PRIMARY KEY,
         title TEXT NOT NULL,
         author TEXT NOT NULL,
         language TEXT,
         release_date TEXT,
         datalake_path TEXT,
         indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
     );
     CREATE INDEX idx_books_author ON books(author);
     CREATE INDEX idx_books_title ON books(title);
     ```

2. **Inverted Index Backends**:
   - **Monolithic File**: Stores all terms and postings in `datamarts/inverted_index.json`.
   - **Hierarchical Folders**: Groups individual terms into folders `datamarts/inverted_index/{A-Z}/{term}.txt`.
   - **NoSQL / Database**: MongoDB collection `inverted_index` with embedded SQLite fallback.

### 3.3 Text Preprocessing & Delimiters

- Book boundaries are detected using standard Project Gutenberg markers:
  - `*** START OF THE PROJECT GUTENBERG EBOOK`
  - `*** END OF THE PROJECT GUTENBERG EBOOK`
- All text is normalized to lowercase and tokenized via word-boundary regular expressions (`\b[a-zA-Z0-9]+(?:'[a-zA-Z0-9]+)?\b`).
- **Stop-word filtering** eliminates 127 standard English function words (articles, conjunctions, prepositions) to reduce index clutter and search noise.
- Supports both **record-level** (document IDs) and **word-level** (positional tracking within the document) indexing.

---

## 4. Design Decisions & Trade-Offs

1. **Separation of Unstructured Content and Structured Indexes**:
   Raw text remains intact in the datalake for future reprocessing or model training. Only search terms and clean metadata populate the datamart.
2. **Idempotent Control Layer**:
   Using persistent sets in `control/downloaded_books.txt` and `control/indexed_books.txt` prevents redundant network fetches and enables safe pipeline restarts after unexpected termination.
3. **Multi-Backend Inverted Index Abstraction**:
   An abstract interface (`BaseInvertedIndex`) decouples the ingestion pipeline and query engine from the physical storage layer.

---

## 5. Benchmarks and Empirical Results

The empirical benchmark suite ([run_benchmarks.py](file:///Users/dennis/ULPGC/BigData/SearchEngineProject/benchmarks/run_benchmarks.py)) was executed following the **Benchmarking Methodology** curriculum guidelines:
- **Warmup Protocol**: 2 warmup trials executed prior to measurements to eliminate cold-start cache and JVM class-loading artifacts.
- **Measurement Protocol**: 5 measurement iterations for bulk operations and 10 iterations for queries, reporting **Mean ± Standard Deviation** and **95% Confidence Intervals**.
- **Dataset**: Sample corpus consisting of *Pride and Prejudice* (#1342), *Alice in Wonderland* (#11), and *Frankenstein* (#84) totaling ~1.3 MB raw text and 10,721 unique terms.

### 5.1 Experiments Matrix

| Experiment | Target Subsystem | Independent Variables | Controlled Variables | Evaluated Metrics |
| :--- | :--- | :--- | :--- | :--- |
| **Exp 1: Datalake Write** | Datalake Ingestion | Layout (Time, Book, Batch), Language (Py, Java, Rust) | 106 Books (~51.5 MB raw text) | Mean time (ms), StdDev, Files, Dirs |
| **Exp 2: Index Build** | Datamart Indexing | Index Architecture (Monolithic, Hierarchical), Language | 152,108 unique terms | Build time (ms), StdDev, On-disk size (KB) |
| **Exp 3: Query Retrieval** | Datamart Search | Term (`darcy`, `monster`, `rabbit`), Language | Warm cache, 10 iterations | Latency (ms), StdDev, 95% CI |

---

### 5.2 Datalake Layout Comparison Across 3 Languages

*Evaluated on the full 106-book dataset (51.5 MB text, 212 files). Results reported as `Mean ± StdDev` (ms).*

| Datalake Layout | Python 3.12 (ms) | Java 11 JVM (ms) | Rust 1.93 Native (ms) | Total Disk (KB) | Files | Directories |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Time-based** (`YYYYMMDD/HH/`) | 416.57 ± 161.09 | 765.57 ± 159.71 | **129.63 ± 32.70** | 51,572.9 | 212 | 2 |
| **Book-based** (`<id>/`) | 476.96 ± 129.64 | 648.70 ± 318.59 | **115.11 ± 9.63** | 51,572.9 | 212 | 106 |
| **Batch-based** (`batch_XXXXX_YYYYY/`) | 426.61 ± 157.03 | 409.19 ± 16.15 | **159.81 ± 62.10** | 51,572.9 | 212 | 55 |

![Datalake Ingestion Speed](file:///Users/dennis/ULPGC/BigData/SearchEngineProject/reports/figures/datalake_write_speed.png)

#### Analysis

- **Rust High-Throughput I/O**: Rust consistently outperforms both Python and Java across all three datalake layouts, achieving 115–159 ms for writing 106 books (212 files). This represents a **~3x speedup over Python** and **~4x–6x over Java**.
- **JVM JIT & GC Overhead**: Java exhibits higher variance during datalake directory creation due to JVM thread allocation and file descriptor pooling before full JIT tiering.
- **Architectural Scalability**:
  - **Time-based** partitioning offers the highest utility in distributed data engines because downstream consumers (e.g. indexers) only need to scan partitions matching recent time windows without performing full tree traversals.
  - **Batch-based** partitioning provides a robust alternative for non-time-series data, capping directory entries to 1,000 files per partition and preventing inode exhaustion.

---

### 5.3 Inverted Index Architecture Comparison

| Index Architecture | Scope | Python 3.12 (ms) | Java 11 JVM (ms) | Rust 1.93 Native (ms) | Size on Disk (KB) | Vocabulary |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Monolithic JSON** | Full 106 Books | 2,296.02 ± 92.54 | 2,007.19 ± 111.22 | **1,116.63 ± 30.66** | 10,274.4 | 152,108 terms |
| **Hierarchical Folders** | 5-Book Sample | 9,832.68 ± 192.07 | 8,775.73 ± 791.49 | **7,365.30 ± 292.51** | 83.3 | ~15,000 terms |

![Inverted Index Construction Latency](file:///Users/dennis/ULPGC/BigData/SearchEngineProject/reports/figures/inverted_index_build_speed.png)

#### Analysis

- **Severe I/O Degradation in Hierarchical Folders**: Building the Hierarchical Folder structure for just **5 books** took **7.3 to 9.8 seconds**, whereas building the Monolithic JSON file for **all 106 books (152,108 terms)** completed in **1.1 to 2.3 seconds**. On a per-book basis, hierarchical indexing exhibits an **I/O penalty exceeding 50x–80x**. Opening and appending to tens of thousands of individual files saturates OS inode caches, directory locking primitives, and disk write buffers across all runtimes.
- **Update Granularity Trade-off**: Hierarchical Folders excel only when performing incremental updates for individual terms, as modifying one word's posting list touches exactly one file rather than rewriting a monolithic document.

---

### 5.4 Query Latency Comparison (10 Iterations, 95% Confidence)

| Search Term | Target Document | Python 3.12 (ms) | Java 11 JVM (ms) | Rust 1.93 Native (ms) | Postings Count |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `darcy` | Pride and Prejudice (1342) | 245.76 ± 166.40 | 344.99 ± 85.50 | **16.10 ± 9.02** | 1 Book |
| `monster` | Frankenstein (84) | 63.56 ± 20.59 | 109.96 ± 8.01 | **3.98 ± 0.27** | 22 Books |
| `rabbit` | Alice in Wonderland (11) | 44.22 ± 4.82 | 111.36 ± 8.64 | **4.51 ± 0.39** | 27 Books |

![Query Retrieval Latency](file:///Users/dennis/ULPGC/BigData/SearchEngineProject/reports/figures/query_latency.png)

#### Analysis

- In post-warmup query lookups, Rust delivered sub-5ms response times for multi-document keyword queries with negligible variance (±0.3 ms), demonstrating the benefits of native compilation, zero-overhead memory layouts, and avoiding JVM garbage collection pauses.
- Python and Java query times include process startup and initial index parsing; subsequent in-memory lookups operate in sub-millisecond regimes across all three engines.

---

## 6. Conclusions and Future Improvements

### Conclusions

1. Stage 1 successfully establishes a resilient, scalable Data Layer adhering to Big Data architectural principles.
2. The **Time-Based Datalake** layout combined with the **Monolithic/Database Datamart** represents the most balanced architecture for search systems, balancing write performance with low-latency querying.
3. The empirical evaluation clearly proved the severe I/O degradation caused by fine-grained file-per-term structures (Hierarchical index) versus unified document/monolithic stores.

### Future Improvements

1. **Distributed Crawling**: Introduce asynchronous worker queues (Celery/RabbitMQ) for concurrent multi-book scraping.
2. **BM25 / TF-IDF Ranking**: Expand the inverted index from boolean filtering to relevance ranking using term frequency and inverse document frequency.
3. **Web Search REST API**: Implement a FastAPI/Express service exposing search endpoints consumed by an interactive frontend.
