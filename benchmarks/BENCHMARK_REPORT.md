# Empirical Benchmark Report
**Search Engine Project — Big Data (ULPGC)**

*Dataset: 106 Project Gutenberg books. Methodology: warmup=2, iterations=5 (hierarchical: warmup=1, iterations=2), statistical indicators: mean, stddev, min, max, ci95.*
*Times marked "ms" are wall-clock times of the whole process (includes startup). Times marked "µs" are measured inside each program (no startup), averaged over 100 repetitions.*

---

## 1. Datalake

### 1.1 Write time (106 books, ms)

| Layout | Python | Java | Rust | Size (KB) | Files | Dirs |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| time_based | 2684.75 ± 54.88 | 2312.94 ± 946.79 | 522.82 ± 21.61 | 53591.4 | 212 | 2 |
| book_based | 2683.14 ± 84.84 | 1397.8 ± 33.08 | 532.35 ± 24.21 | 53591.4 | 212 | 106 |
| batch_based | 2639.8 ± 27.0 | 1432.09 ± 58.58 | 533.0 ± 10.49 | 53591.4 | 212 | 55 |

### 1.2 Lookup cost: locate one book (µs)

| Layout | Python | Java | Rust |
| :--- | :---: | :---: | :---: |
| time_based | 3375.807 ± 84.168 | 2054.693 ± 62.438 | 11454.154 ± 190.13 |
| book_based | 296.627 ± 9.565 | 321.612 ± 13.801 | 100.694 ± 4.372 |
| batch_based | 302.516 ± 8.239 | 1051.13 ± 61.908 | 106.438 ± 6.216 |

### 1.3 Incremental processing: detect books not yet indexed (µs)

| Layout | Python | Java | Rust |
| :--- | :---: | :---: | :---: |
| time_based | 5832.58 ± 683.057 | 60347.7 ± 4210.943 | 28827.02 ± 1424.366 |
| book_based | 49025.88 ± 5719.505 | 89474.94 ± 2868.454 | 51536.24 ± 4191.067 |
| batch_based | 26215.7 ± 1209.238 | 73185.3 ± 2519.169 | 41441.88 ± 2260.302 |

### 1.4 Recovery after an interruption

A crash is simulated after a book is written to the datalake but before the control file is updated. The pipeline is then run again over all the books.

| Layout | Books expected | Books in control | Copies in datalake | Duplicates | Lost |
| :--- | :---: | :---: | :---: | :---: | :---: |
| time_based | 10 | 10 | 10 | 0 | 0 |
| book_based | 10 | 10 | 10 | 0 | 0 |
| batch_based | 10 | 10 | 10 | 0 | 0 |

---

## 2. Inverted Index

### 2.1 Build time, memory and disk

| Structure | Books | Python (ms) | Java (ms) | Rust (ms) | Memory Py / Java / Rust (MB) | Size on disk (KB) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| monolithic_json | 106 | 17119.64 ± 1273.13 | 6321.97 ± 352.16 | 18057.84 ± 657.59 | 263.7 / 577.8 / 108.6 | 11248.7 |
| hierarchical_folders | 5 | 46931.53 ± 9.82 | 39841.36 ± 564.39 | 34880.47 ± 42.25 | 60.4 / 198.7 / 10.2 | 103.8 |
| mongodb (Python only) | 5 | 78731.46 ± 146.64 | - | - | 68.0 / - / - | 842.1 |

### 2.2 Query time (µs)

| Structure | Term | Python | Java | Rust |
| :--- | :--- | :---: | :---: | :---: |
| monolithic_json | `rabbit` | 0.677 ± 0.042 | 10.864 ± 0.764 | 0.511 ± 0.067 |
| hierarchical_folders | `rabbit` | 397.048 ± 6.292 | 839.791 ± 11.2 | 233.684 ± 3.089 |
| monolithic_json | `monster` | 0.683 ± 0.04 | 13.891 ± 2.882 | 0.396 ± 0.085 |
| hierarchical_folders | `monster` | 425.125 ± 43.506 | 894.165 ± 34.018 | 228.208 ± 3.658 |
| monolithic_json | `science` | 0.665 ± 0.027 | 11.341 ± 1.096 | 0.583 ± 0.099 |
| hierarchical_folders | `science` | 395.077 ± 7.739 | 850.506 ± 11.205 | 232.556 ± 6.075 |
| mongodb | `rabbit` | 1737.119 ± 67.277 | - | - |
| mongodb | `monster` | 1798.093 ± 55.855 | - | - |
| mongodb | `science` | 1800.737 ± 121.0 | - | - |

### 2.3 Update: add new books to an existing index (ms)

| Structure | Books already indexed | New books | Python | Java | Rust |
| :--- | :---: | :---: | :---: | :---: | :---: |
| monolithic_json | 101 | 5 | 3410.61 ± 56.6 | 1438.52 ± 57.07 | 827.58 ± 21.75 |
| hierarchical_folders | 5 | 1 | 12138.96 ± 206.49 | 9883.33 ± 1.87 | 8382.23 ± 194.21 |

### 2.4 Scalability: build time vs number of books (ms)

| Structure | Books | Python | Java | Rust |
| :--- | :---: | :---: | :---: | :---: |
| monolithic_json | 25 | 6826.52 ± 100.23 | 2901.2 ± 170.85 | 7140.15 ± 199.68 |
| monolithic_json | 50 | 9446.99 ± 59.34 | 4035.11 ± 213.25 | 10367.66 ± 98.49 |
| monolithic_json | 106 | 17119.64 ± 1273.13 | 6321.97 ± 352.16 | 18057.84 ± 657.59 |
| hierarchical_folders | 5 | 46931.53 ± 9.82 | 39841.36 ± 564.39 | 34880.47 ± 42.25 |
| hierarchical_folders | 10 | 243419.23 ± 3735.63 | 181259.16 ± 30755.54 | 128490.35 ± 773.12 |
| hierarchical_folders | 20 | 274281.09 ± 3426.78 | 231303.88 ± 161.49 | 211704.79 ± 1983.08 |

---

## 3. Metadata Store (SQLite, Python)

| Books | Insert all (ms) | Query by author (µs) | Query by ID (µs) |
| :---: | :---: | :---: | :---: |
| 25 | 172.93 | 924.24 | 890.73 |
| 50 | 376.98 | 1536.67 | 1159.1 |
| 106 | 788.57 | 1023.94 | 872.83 |
