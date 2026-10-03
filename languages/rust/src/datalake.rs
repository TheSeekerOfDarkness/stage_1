use std::fs;
use std::io::Result;
use std::path::{Path, PathBuf};

pub struct TimeBasedDatalake {
    pub base_dir: PathBuf,
}

impl TimeBasedDatalake {
    pub fn new<P: AsRef<Path>>(base_dir: P) -> Self {
        Self {
            base_dir: base_dir.as_ref().to_path_buf(),
        }
    }

    pub fn save_book(
        &self,
        book_id: u32,
        header: &str,
        body: &str,
        date_str: &str,
        hour_str: &str,
    ) -> Result<(PathBuf, PathBuf)> {
        let dir = self.base_dir.join(date_str).join(hour_str);
        fs::create_dir_all(&dir)?;

        let header_path = dir.join(format!("{}.header.txt", book_id));
        let body_path = dir.join(format!("{}.body.txt", book_id));

        fs::write(&header_path, header.trim())?;
        fs::write(&body_path, body.trim())?;

        Ok((header_path, body_path))
    }

    pub fn find_book(&self, book_id: u32) -> Option<PathBuf> {
        find_file(&self.base_dir, &format!("{}.body.txt", book_id))
    }
}

fn find_file(dir: &Path, name: &str) -> Option<PathBuf> {
    if let Ok(entries) = fs::read_dir(dir) {
        for entry in entries {
            if let Ok(entry) = entry {
                let path = entry.path();
                if path.is_dir() {
                    if let Some(found) = find_file(&path, name) {
                        return Some(found);
                    }
                } else if entry.file_name().to_string_lossy() == name {
                    return Some(path);
                }
            }
        }
    }
    None
}

pub struct BookBasedDatalake {
    pub base_dir: PathBuf,
}

impl BookBasedDatalake {
    pub fn new<P: AsRef<Path>>(base_dir: P) -> Self {
        Self {
            base_dir: base_dir.as_ref().to_path_buf(),
        }
    }

    pub fn save_book(&self, book_id: u32, header: &str, body: &str) -> Result<(PathBuf, PathBuf)> {
        let dir = self.base_dir.join(book_id.to_string());
        fs::create_dir_all(&dir)?;

        let header_path = dir.join("header.txt");
        let body_path = dir.join("body.txt");

        fs::write(&header_path, header.trim())?;
        fs::write(&body_path, body.trim())?;

        Ok((header_path, body_path))
    }

    pub fn find_book(&self, book_id: u32) -> Option<PathBuf> {
        let path = self.base_dir.join(book_id.to_string()).join("body.txt");
        if path.exists() {
            Some(path)
        } else {
            None
        }
    }
}

pub struct BatchBasedDatalake {
    pub base_dir: PathBuf,
    pub batch_size: u32,
}

impl BatchBasedDatalake {
    pub fn new<P: AsRef<Path>>(base_dir: P, batch_size: u32) -> Self {
        Self {
            base_dir: base_dir.as_ref().to_path_buf(),
            batch_size,
        }
    }

    pub fn save_book(&self, book_id: u32, header: &str, body: &str) -> Result<(PathBuf, PathBuf)> {
        let start = (book_id / self.batch_size) * self.batch_size;
        let end = start + self.batch_size - 1;
        let dir = self
            .base_dir
            .join(format!("batch_{:05}_{:05}", start, end));
        fs::create_dir_all(&dir)?;

        let header_path = dir.join(format!("{}.header.txt", book_id));
        let body_path = dir.join(format!("{}.body.txt", book_id));

        fs::write(&header_path, header.trim())?;
        fs::write(&body_path, body.trim())?;

        Ok((header_path, body_path))
    }

    pub fn find_book(&self, book_id: u32) -> Option<PathBuf> {
        let start = (book_id / self.batch_size) * self.batch_size;
        let end = start + self.batch_size - 1;
        let path = self
            .base_dir
            .join(format!("batch_{:05}_{:05}", start, end))
            .join(format!("{}.body.txt", book_id));
        if path.exists() {
            Some(path)
        } else {
            None
        }
    }
}
