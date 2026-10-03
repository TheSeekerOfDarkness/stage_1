mod datalake;
mod inverted_index;
mod tokenizer;

use std::env;
use std::fs;
use std::path::Path;
use std::time::Instant;

fn walk_body_files(dir: &Path, files: &mut Vec<(u32, String)>) {
    if let Ok(entries) = fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                walk_body_files(&path, files);
            } else if path.file_name().unwrap_or_default().to_string_lossy().ends_with(".body.txt") {
                let name = path.file_name().unwrap().to_string_lossy();
                let id_str = name.replace(".body.txt", "");
                if let Ok(id) = id_str.parse::<u32>() {
                    if let Ok(body) = fs::read_to_string(&path) {
                        files.push((id, body));
                    }
                }
            }
        }
    }
}

fn list_book_ids(dir: &Path, ids: &mut Vec<String>) {
    if let Ok(entries) = fs::read_dir(dir) {
        for entry in entries {
            if let Ok(entry) = entry {
                let path = entry.path();
                let name = entry.file_name().to_string_lossy().to_string();
                if path.is_dir() {
                    list_book_ids(&path, ids);
                } else if name == "body.txt" {
                    let folder = path.parent().unwrap().file_name().unwrap();
                    ids.push(folder.to_string_lossy().to_string());
                } else if name.ends_with(".body.txt") {
                    ids.push(name.replace(".body.txt", ""));
                }
            }
        }
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: searchengine_rust <command> [args...]");
        std::process::exit(1);
    }

    let command = &args[1];

    if command == "index-monolithic" {
        let lake_dir = Path::new(&args[2]);
        let out_json = Path::new(&args[3]);

        let start = Instant::now();
        let mut index = inverted_index::MonolithicIndex::new();
        let mut docs = Vec::new();
        walk_body_files(lake_dir, &mut docs);

        for (id, body) in docs {
            index.add_document(id, &body);
        }

        index.save(out_json)?;
        let elapsed = start.elapsed();
        println!(
            "{{\"status\": \"success\", \"time_ms\": {}, \"terms\": {}, \"output\": \"{}\"}}",
            elapsed.as_millis(),
            index.terms_count(),
            out_json.display()
        );
    } else if command == "index-hierarchical" {
        let lake_dir = Path::new(&args[2]);
        let out_dir = Path::new(&args[3]);

        let start = Instant::now();
        let index = inverted_index::HierarchicalIndex::new(out_dir);
        let mut docs = Vec::new();
        walk_body_files(lake_dir, &mut docs);

        for (id, body) in docs {
            index.add_document(id, &body)?;
        }

        let elapsed = start.elapsed();
        println!(
            "{{\"status\": \"success\", \"time_ms\": {}, \"output\": \"{}\"}}",
            elapsed.as_millis(),
            out_dir.display()
        );
    } else if command == "query-hierarchical" {
        let index_dir = Path::new(&args[2]);
        let term = &args[3];

        let start = Instant::now();
        let index = inverted_index::HierarchicalIndex::new(index_dir);
        let mut postings = Vec::new();
        for _ in 0..100 {
            postings = index.lookup(term)?;
        }
        let elapsed_us = start.elapsed().as_secs_f64() * 1_000_000.0 / 100.0;

        println!(
            "{{\"term\": \"{}\", \"time_us\": {:.3}, \"postings\": {:?}}}",
            term, elapsed_us, postings
        );
    } else if command == "query-monolithic" {
        let index = inverted_index::MonolithicIndex::load(&args[2])?;
        let term = &args[3];

        let start = Instant::now();
        let mut postings = Vec::new();
        for _ in 0..100 {
            postings = index.lookup(term);
        }
        let elapsed_us = start.elapsed().as_secs_f64() * 1_000_000.0 / 100.0;

        println!(
            "{{\"term\": \"{}\", \"time_us\": {:.3}, \"postings\": {:?}}}",
            term, elapsed_us, postings
        );
    } else if command == "update-monolithic" {
        let index_file = Path::new(&args[2]);
        let new_books_dir = Path::new(&args[3]);

        let start = Instant::now();
        let mut index = inverted_index::MonolithicIndex::load(index_file)?;
        let mut docs = Vec::new();
        walk_body_files(new_books_dir, &mut docs);
        for (id, body) in docs {
            index.add_document(id, &body);
        }
        index.save(index_file)?;

        println!(
            "{{\"status\": \"success\", \"time_ms\": {}, \"terms\": {}}}",
            start.elapsed().as_millis(),
            index.terms_count()
        );
    } else if command == "lookup-datalake" {
        let layout = &args[2];
        let lake_dir = Path::new(&args[3]);
        let book_id: u32 = args[4].parse()?;

        let start = Instant::now();
        let mut found = None;
        for _ in 0..100 {
            if layout == "time_based" {
                found = datalake::TimeBasedDatalake::new(lake_dir).find_book(book_id);
            } else if layout == "book_based" {
                found = datalake::BookBasedDatalake::new(lake_dir).find_book(book_id);
            } else {
                found = datalake::BatchBasedDatalake::new(lake_dir, 1000).find_book(book_id);
            }
        }
        let elapsed_us = start.elapsed().as_secs_f64() * 1_000_000.0 / 100.0;

        println!(
            "{{\"time_us\": {:.3}, \"found\": {}}}",
            elapsed_us,
            found.is_some()
        );
    } else if command == "detect-new" {
        let lake_dir = Path::new(&args[2]);
        let indexed_file = Path::new(&args[3]);

        let start = Instant::now();
        let mut indexed = std::collections::HashSet::new();
        for line in fs::read_to_string(indexed_file)?.lines() {
            indexed.insert(line.trim().to_string());
        }
        let mut ids = Vec::new();
        list_book_ids(lake_dir, &mut ids);
        let mut new_count = 0;
        for id in &ids {
            if !indexed.contains(id) {
                new_count += 1;
            }
        }
        let elapsed_us = start.elapsed().as_secs_f64() * 1_000_000.0;

        println!("{{\"time_us\": {:.3}, \"new\": {}}}", elapsed_us, new_count);
    } else if command == "benchmark-datalake" {
        let layout = &args[2];
        let books_dir = Path::new(&args[3]);
        let out_lake = Path::new(&args[4]);

        let start = Instant::now();
        let mut count = 0;

        if let Ok(entries) = fs::read_dir(books_dir) {
            for entry in entries.flatten() {
                let p = entry.path();
                if p.is_file() && p.extension().map_or(false, |ext| ext == "txt") {
                    let stem = p.file_stem().unwrap().to_string_lossy();
                    if let Ok(id) = stem.parse::<u32>() {
                        if let Ok(content) = fs::read_to_string(&p) {
                            if layout == "time_based" {
                                let dl = datalake::TimeBasedDatalake::new(out_lake);
                                dl.save_book(id, &format!("Header {}", id), &content, "20260923", "12")?;
                            } else if layout == "book_based" {
                                let dl = datalake::BookBasedDatalake::new(out_lake);
                                dl.save_book(id, &format!("Header {}", id), &content)?;
                            } else if layout == "batch_based" {
                                let dl = datalake::BatchBasedDatalake::new(out_lake, 1000);
                                dl.save_book(id, &format!("Header {}", id), &content)?;
                            }
                            count += 1;
                        }
                    }
                }
            }
        }

        let elapsed = start.elapsed();
        println!(
            "{{\"status\": \"success\", \"layout\": \"{}\", \"books\": {}, \"time_ms\": {}}}",
            layout,
            count,
            elapsed.as_millis()
        );
    } else if command == "index" {
        let mut indexer_type = "monolithic";
        let mut i = 2;
        while i < args.len() {
            if args[i] == "--indexer" && i + 1 < args.len() {
                indexer_type = &args[i + 1];
                i += 1;
            }
            i += 1;
        }

        let lake_dir = Path::new("datalake");
        let start = Instant::now();
        let mut docs = Vec::new();
        walk_body_files(lake_dir, &mut docs);

        if indexer_type.eq_ignore_ascii_case("hierarchical") {
            let out_dir = Path::new("datamarts/hierarchical");
            let index = inverted_index::HierarchicalIndex::new(out_dir);
            for (id, body) in docs {
                index.add_document(id, &body)?;
            }
            let elapsed = start.elapsed();
            println!(
                "\n=== Rust Indexing Summary (hierarchical) ===\nTotal time: {} ms\nOutput directory: {}",
                elapsed.as_millis(),
                out_dir.display()
            );
        } else {
            let out_json = Path::new("datamarts/inverted_index.json");
            let mut index = inverted_index::MonolithicIndex::new();
            for (id, body) in docs {
                index.add_document(id, &body);
            }
            index.save(out_json)?;
            let elapsed = start.elapsed();
            println!(
                "\n=== Rust Indexing Summary (monolithic) ===\nIndexed {} terms in {} ms\nOutput saved to: {}",
                index.terms_count(),
                elapsed.as_millis(),
                out_json.display()
            );
        }
    } else if command == "search" {
        let mut indexer_type = "monolithic";
        let mut query: Option<&String> = None;
        let mut i = 2;
        while i < args.len() {
            if args[i] == "--indexer" && i + 1 < args.len() {
                indexer_type = &args[i + 1];
                i += 1;
            } else if !args[i].starts_with("--") {
                query = Some(&args[i]);
            }
            i += 1;
        }

        let query_str = match query {
            Some(q) => q,
            None => {
                eprintln!("Usage: searchengine_rust search [--indexer <monolithic|hierarchical>] <query>");
                std::process::exit(1);
            }
        };

        let start = Instant::now();
        let terms = tokenizer::tokenize(query_str, true);
        if terms.is_empty() {
            println!(
                "\n=== Rust Search Results for: '{}' ({}) ===\nTotal matching books: 0\n(Query contained only stop words or invalid characters)",
                query_str, indexer_type
            );
            return Ok(());
        }

        let mut matching_ids: Option<std::collections::HashSet<u32>> = None;

        if indexer_type.eq_ignore_ascii_case("hierarchical") {
            let index = inverted_index::HierarchicalIndex::new("datamarts/hierarchical");
            for term in &terms {
                let postings: std::collections::HashSet<u32> = index.lookup(term)?.into_iter().collect();
                matching_ids = match matching_ids {
                    None => Some(postings),
                    Some(prev) => Some(prev.intersection(&postings).cloned().collect()),
                };
            }
        } else {
            let index = inverted_index::MonolithicIndex::load("datamarts/inverted_index.json")?;
            for term in &terms {
                let postings: std::collections::HashSet<u32> = index.lookup(term).into_iter().collect();
                matching_ids = match matching_ids {
                    None => Some(postings),
                    Some(prev) => Some(prev.intersection(&postings).cloned().collect()),
                };
            }
        }

        let elapsed = start.elapsed();
        let mut sorted: Vec<u32> = matching_ids.map(|s| s.into_iter().collect()).unwrap_or_default();
        sorted.sort();

        println!(
            "\n=== Rust Search Results for: '{}' ({}) ===",
            query_str, indexer_type
        );
        println!(
            "Total matching books: {} (in {:.2} ms)",
            sorted.len(),
            elapsed.as_secs_f64() * 1000.0
        );
        for id in sorted {
            println!("  - [Book ID {}]", id);
        }
    } else {
        eprintln!("Unknown command: {}", command);
        std::process::exit(1);
    }

    Ok(())
}
