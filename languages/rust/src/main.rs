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
        let postings = index.lookup(term)?;
        let elapsed_us = start.elapsed().as_micros();

        println!(
            "{{\"term\": \"{}\", \"time_us\": {}, \"postings\": {:?}}}",
            term, elapsed_us, postings
        );
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
    } else {
        eprintln!("Unknown command: {}", command);
        std::process::exit(1);
    }

    Ok(())
}
