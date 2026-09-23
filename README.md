# Stage 1: Building the Data Layer - Search Engine Project
**Big Data — Grado en Ciencia e Ingeniería de Datos (ULPGC)**

## Overview

This repository implements **Stage 1 (Building the Data Layer)** of the Big Data Search Engine project. The data layer acts as the foundation of the search engine, providing a scalable, organized, and auditable repository for raw and cleaned text.

In this first milestone, the ingestion pipeline collects books from [Project Gutenberg](https://www.gutenberg.org/), extracts and validates headers and book bodies, stores them according to the **first recommended datalake layout** (time-based hierarchy), and tracks pipeline state through a dedicated **control layer**.

---

## Architecture

### 1. Datalake (Time-Based Hierarchy)
To ensure traceability, incremental processing, and scalability, files are grouped by download date (`YYYYMMDD`) and 24-hour download hour (`HH`):

```text
datalake/
└── YYYYMMDD/
    └── HH/
        ├── <BOOK_ID>.header.txt   # Metadata and licensing header
        └── <BOOK_ID>.body.txt     # Cleaned body text of the book
```

- **Traceability**: Easily determine when any document entered the system.
- **Incremental Processing**: Downstream indexers can scan only the latest hourly directories.
- **Scalability**: Avoids storing tens of thousands of files in a single flat directory, matching production distributed storage patterns (e.g. Amazon S3 prefixes, HDFS partitions).

### 2. Control Layer (State Tracking)
Located in `control/`:
- `control/downloaded_books.txt`: Set of book IDs successfully downloaded and stored in the datalake.
- `control/indexed_books.txt`: Set of book IDs successfully processed by the indexer (for future stages).

This prevents redundant downloads, supports seamless resume after interruption, and ensures pipeline idempotency.

### 3. Crawler & Splitter
Downloads the raw book text from `https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt` and separates:
- **Header**: All lines prior to `*** START OF THE PROJECT GUTENBERG EBOOK`
- **Body**: The text between the start and end markers `*** END OF THE PROJECT GUTENBERG EBOOK`
- **Footer**: Closing licensing and distributor notes (discarded from body)

---

## Directory Structure

```text
.
├── control/
│   ├── downloaded_books.txt      # State tracking of ingested books
│   └── indexed_books.txt         # State tracking of indexed books
├── datalake/
│   └── 20260916/
│       └── 13/
│           ├── 1342.body.txt     # Pride and Prejudice (Jane Austen)
│           └── 1342.header.txt
├── src/
│   ├── __init__.py
│   ├── config.py                 # Paths, URLs, delimiters, and settings
│   ├── control/
│   │   ├── __init__.py
│   │   └── tracker.py            # State tracking logic for control files
│   ├── crawler/
│   │   ├── __init__.py
│   │   └── downloader.py         # HTTP retrieval and marker-based splitting
│   ├── datalake/
│   │   ├── __init__.py
│   │   └── time_based.py         # Time-based datalake storage manager
│   └── pipeline.py               # Orchestrator combining control, crawler, and datalake
├── tests/
│   ├── __init__.py
│   └── test_ingestion.py         # Unit & integration tests
├── main.py                       # CLI entry point
├── requirements.txt              # Project dependencies
└── README.md
```

---

## Setup & Installation

### Requirements
- Python 3.10+
- `pip`

### Install Dependencies
```bash
pip install -r requirements.txt
```

---

## Usage

### Ingesting Books
To download and ingest a book into the datalake (e.g. *Pride and Prejudice*, ID `1342`):
```bash
python main.py ingest --book-id 1342
```

You can also pass multiple IDs:
```bash
python main.py ingest --book-id 1342 11 84
```

To force a re-download even if already tracked in `control/downloaded_books.txt`:
```bash
python main.py ingest --book-id 1342 --force
```

### Inspect Pipeline Status
To inspect the number of downloaded books, indexed books, pending indexing jobs, and datalake records:
```bash
python main.py status
```

---

## Running Tests

Run the full automated test suite with pytest:
```bash
pytest tests/ -v
```
