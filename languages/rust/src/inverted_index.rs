use crate::tokenizer;
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::fs;
use std::io::Result;
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
        let mut sorted: BTreeMap<&String, BTreeSet<u32>> = BTreeMap::new();
        for (term, ids) in &self.index {
            let mut set = BTreeSet::new();
            for id in ids {
                set.insert(*id);
            }
            sorted.insert(term, set);
        }
        let json_str = serde_json::to_string_pretty(&sorted).map_err(|e| {
            std::io::Error::new(std::io::ErrorKind::Other, e.to_string())
        })?;

        fs::write(path, json_str)?;
        Ok(())
    }

    pub fn load<P: AsRef<Path>>(file_path: P) -> Result<Self> {
        let path = file_path.as_ref();
        if !path.exists() {
            return Ok(Self::new());
        }
        let data = fs::read_to_string(path)?;
        let index: HashMap<String, Vec<u32>> = serde_json::from_str(&data).map_err(|e| {
            std::io::Error::new(std::io::ErrorKind::Other, e.to_string())
        })?;
        Ok(Self { index })
    }

    pub fn lookup(&self, term: &str) -> Vec<u32> {
        let clean = term.to_lowercase();
        self.index.get(&clean).cloned().unwrap_or_default()
    }

    pub fn terms_count(&self) -> usize {
        self.index.len()
    }
}

pub fn is_windows_reserved(name: &str) -> bool {
    matches!(
        name,
        "con" | "prn" | "aux" | "nul"
            | "com0" | "com1" | "com2" | "com3" | "com4" | "com5" | "com6" | "com7" | "com8" | "com9"
            | "lpt0" | "lpt1" | "lpt2" | "lpt3" | "lpt4" | "lpt5" | "lpt6" | "lpt7" | "lpt8" | "lpt9"
    )
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

    fn get_file_name(term: &str) -> String {
        if is_windows_reserved(term) {
            format!("{}_.txt", term)
        } else {
            format!("{}.txt", term)
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

            let term_file = dir.join(Self::get_file_name(&term));
            let mut ids = BTreeSet::new();
            if term_file.exists() {
                for line in fs::read_to_string(&term_file)?.lines() {
                    if let Ok(id) = line.trim().parse::<u32>() {
                        ids.insert(id);
                    }
                }
            }
            ids.insert(doc_id);
            let mut content = String::new();
            for id in &ids {
                content.push_str(&format!("{}\n", id));
            }
            fs::write(&term_file, content)?;
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

        let term_file = self.base_dir.join(folder).join(Self::get_file_name(&clean));
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
