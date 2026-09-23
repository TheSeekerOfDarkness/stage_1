use crate::tokenizer;
use std::collections::{BTreeMap, HashMap};
use std::fs::{self, OpenOptions};
use std::io::{Result, Write};
use std::path::{Path, PathBuf};

pub struct MonolithicIndex {
    pub index: HashMap<String, Vec<u32>>,
}

impl MonolithicIndex {
    pub fn new() -> Self {
        Self {
            index: HashMap::new(),
        }
    }

    pub fn add_document(&mut self, doc_id: u32, text: &str) {
        let terms = tokenizer::get_unique_terms(text);
        for term in terms {
            self.index.entry(term).or_default().push(doc_id);
        }
    }

    pub fn save<P: AsRef<Path>>(&self, file_path: P) -> Result<()> {
        let path = file_path.as_ref();
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }

        // Sort keys for deterministic JSON output
        let sorted: BTreeMap<&String, &Vec<u32>> = self.index.iter().collect();
        let json_str = serde_json::to_string_pretty(&sorted).map_err(|e| {
            std::io::Error::new(std::io::ErrorKind::Other, e.to_string())
        })?;

        fs::write(path, json_str)?;
        Ok(())
    }

    pub fn lookup(&self, term: &str) -> Vec<u32> {
        let clean = term.to_lowercase();
        self.index.get(&clean).cloned().unwrap_or_default()
    }

    pub fn terms_count(&self) -> usize {
        self.index.len()
    }
}

pub struct HierarchicalIndex {
    pub base_dir: PathBuf,
}

impl HierarchicalIndex {
    pub fn new<P: AsRef<Path>>(base_dir: P) -> Self {
        Self {
            base_dir: base_dir.as_ref().to_path_buf(),
        }
    }

    pub fn add_document(&self, doc_id: u32, text: &str) -> Result<()> {
        let terms = tokenizer::get_unique_terms(text);
        for term in terms {
            let first_char = term.chars().next().unwrap_or('_').to_ascii_uppercase();
            let folder = if first_char.is_ascii_alphanumeric() {
                first_char.to_string()
            } else {
                "_".to_string()
            };

            let dir = self.base_dir.join(folder);
            fs::create_dir_all(&dir)?;

            let term_file = dir.join(format!("{}.txt", term));
            let mut file = OpenOptions::new()
                .create(true)
                .append(true)
                .open(term_file)?;
            writeln!(file, "{}", doc_id)?;
        }
        Ok(())
    }

    pub fn lookup(&self, term: &str) -> Result<Vec<u32>> {
        let clean = term.to_lowercase();
        let first_char = clean.chars().next().unwrap_or('_').to_ascii_uppercase();
        let folder = if first_char.is_ascii_alphanumeric() {
            first_char.to_string()
        } else {
            "_".to_string()
        };

        let term_file = self.base_dir.join(folder).join(format!("{}.txt", clean));
        if !term_file.exists() {
            return Ok(Vec::new());
        }

        let content = fs::read_to_string(term_file)?;
        let mut ids = Vec::new();
        for line in content.lines() {
            if let Ok(id) = line.trim().parse::<u32>() {
                ids.push(id);
            }
        }
        Ok(ids)
    }
}
