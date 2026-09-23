# Stage 1: Building the Data Layer - Search Engine Project
**Big Data — Grado en Ciencia e Ingeniería de Datos (ULPGC)**

## Overview

This repository implements **Stage 1 (Building the Data Layer)** of the Big Data Search Engine project. The data layer acts as the foundation of the search engine, providing a scalable, organized, and auditable repository for raw and cleaned text, alongside optimized structured datamarts for metadata querying and inverted index retrieval.

---

## Architecture

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

### 1. Datalake
Stores the raw and cleaned book content in an unstructured format:
- **Time-Based Hierarchy** (`YYYYMMDD/HH/`):
  - `<BOOK_ID>.header.txt`: Metadata, title, author, release notes.
  - `<BOOK_ID>.body.txt`: Cleaned body text delimited between Gutenberg markers.

### 2. Control Layer
Maintains state files in `control/` for pipeline auditability and deduplication:
- `control/downloaded_books.txt`: Ingested book IDs.
- `control/indexed_books.txt`: Indexed book IDs.

### 3. Datamarts
Structured, queryable data stores:
- **Metadata Store (`datamarts/metadata.db`)**: SQLite database storing parsed metadata (`book_id`, `title`, `author`, `language`, `release_date`, `datalake_path`).
- **Inverted Index (3 Implementations)**:
  1. **Single Monolithic File**: `datamarts/inverted_index.json`
  2. **Hierarchical Folder Structure**: `datamarts/inverted_index/{A..Z}/{term}.txt`
  3. **NoSQL Database**: MongoDB (`inverted_index` collection) with embedded SQLite fallback (`datamarts/inverted_index.db`).
- **Text Processing & Stop Words**: Includes a standard stop-word filter (Lucene/NLTK) and positional tracking for phrase searching.

---

## Directory Structure

```text
.
├── control/
│   ├── downloaded_books.txt        # State tracking of ingested books
│   └── indexed_books.txt           # State tracking of indexed books
├── datalake/
│   └── 20260916/
│       └── 13/
│           ├── 1342.body.txt       # Pride and Prejudice (Jane Austen)
│           └── 1342.header.txt
├── datamarts/
│   ├── metadata.db                 # SQLite metadata catalog (auto-generated)
│   ├── inverted_index.json         # Monolithic index (auto-generated)
│   └── inverted_index/             # Hierarchical folder index (auto-generated)
├── src/
│   ├── __init__.py
│   ├── config.py                   # Global constants and path configurations
│   ├── control/
│   │   ├── __init__.py
│   │   └── tracker.py              # Control layer state management
│   ├── crawler/
│   │   ├── __init__.py
│   │   └── downloader.py           # HTTP Gutenberg fetcher and text splitter
│   ├── datalake/
│   │   ├── __init__.py
│   │   └── time_based.py           # Time-based datalake storage
│   ├── datamart/
│   │   ├── __init__.py
│   │   ├── metadata.py             # Header parser & SQLite metadata store
│   │   ├── tokenizer.py            # Tokenizer with stop-word filter & positions
│   │   └── inverted_index/
│   │       ├── __init__.py
│   │       ├── base.py             # Inverted index abstract base class
│   │       ├── monolithic.py       # Monolithic JSON implementation
│   │       ├── hierarchical.py     # Hierarchical folder implementation
│   │       └── database.py         # MongoDB / SQLite document store
│   └── pipeline.py                 # End-to-end pipeline orchestrator
├── tests/
│   ├── test_ingestion.py           # Datalake and ingestion tests
│   ├── test_metadata.py            # Metadata extraction and SQLite tests
│   ├── test_tokenizer.py           # Tokenizer and stop words tests
│   └── test_inverted_index.py      # All 3 inverted index backends tests
├── docker-compose.yml              # Local MongoDB 7 service
├── main.py                         # CLI entry point (ingest, index, search, status)
├── requirements.txt
└── README.md
```

---

## Setup & Installation

### Requirements
- Python 3.10+
- Optional: Docker (for MongoDB backend)

### Install Dependencies
```bash
pip install -r requirements.txt
```

### (Optional) Start MongoDB for NoSQL Indexer
```bash
docker compose up -d
```
*(If MongoDB is not running, the database indexer will transparently use an embedded SQLite document store at `datamarts/inverted_index.db`)*.

---

## Usage

### 1. Ingesting Books
Download and save a book to the datalake:
```bash
# Ingest single book (e.g. Pride and Prejudice, ID 1342)
python main.py ingest --book-id 1342

# Ingest multiple books
python main.py ingest --book-id 1342 11 84
```

### 2. Indexing Books into Datamarts
Extract metadata to SQLite and build inverted index:
```bash
# Index pending books using Monolithic JSON backend
python main.py index --indexer monolithic

# Index using Hierarchical Folder backend
python main.py index --indexer hierarchical

# Index using Database backend (MongoDB / SQLite)
python main.py index --indexer database
```

### 3. Searching the Datamarts
Search terms across the inverted index and resolve book metadata:
```bash
python main.py search "Darcy Elizabeth" --indexer monolithic
python main.py search "adventure island" --indexer hierarchical
```

### 4. Inspect Pipeline Status
View ingestion counts, indexed records, pending queue, and datalake entries:
```bash
python main.py status
```

---

## Running Tests

Run the full automated test suite with pytest:
```bash
pytest tests/ -v
```
