package searchengine;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

public class InvertedIndex {

    public static class Monolithic {
        private final Map<String, List<Integer>> index = new HashMap<>();

        public void addDocument(int docId, String text) {
            Set<String> terms = Tokenizer.getUniqueTerms(text);
            for (String term : terms) {
                index.computeIfAbsent(term, k -> new ArrayList<>()).add(docId);
            }
        }

        public List<Integer> lookup(String term) {
            return index.getOrDefault(term.toLowerCase().trim(), Collections.emptyList());
        }

        public void save(Path filePath) throws IOException {
            if (filePath.getParent() != null && !Files.exists(filePath.getParent())) {
                Files.createDirectories(filePath.getParent());
            }
            try (BufferedWriter writer = Files.newBufferedWriter(filePath, StandardCharsets.UTF_8)) {
                writer.write("{\n");
                var it = index.entrySet().iterator();
                while (it.hasNext()) {
                    var entry = it.next();
                    writer.write("  \"" + entry.getKey() + "\": " + entry.getValue().toString());
                    if (it.hasNext()) {
                        writer.write(",\n");
                    } else {
                        writer.write("\n");
                    }
                }
                writer.write("}\n");
            }
        }

        public int getTermsCount() {
            return index.size();
        }
    }

    public static class Hierarchical {
        private final Path baseDir;

        public Hierarchical(Path baseDir) {
            this.baseDir = baseDir;
        }

        public void addDocument(int docId, String text) throws IOException {
            Set<String> terms = Tokenizer.getUniqueTerms(text);
            for (String term : terms) {
                char first = Character.toUpperCase(term.charAt(0));
                String folder = Character.isLetterOrDigit(first) ? String.valueOf(first) : "_";
                Path dir = baseDir.resolve(folder);
                Files.createDirectories(dir);

                Path termFile = dir.resolve(term + ".txt");
                try (BufferedWriter writer = Files.newBufferedWriter(termFile, StandardCharsets.UTF_8,
                        StandardOpenOption.CREATE, StandardOpenOption.APPEND)) {
                    writer.write(docId + "\n");
                }
            }
        }

        public List<Integer> lookup(String term) throws IOException {
            String clean = term.toLowerCase().trim();
            if (clean.isEmpty()) return Collections.emptyList();
            char first = Character.toUpperCase(clean.charAt(0));
            String folder = Character.isLetterOrDigit(first) ? String.valueOf(first) : "_";
            Path termFile = baseDir.resolve(folder).resolve(clean + ".txt");
            if (!Files.exists(termFile)) return Collections.emptyList();

            List<Integer> ids = new ArrayList<>();
            for (String line : Files.readAllLines(termFile, StandardCharsets.UTF_8)) {
                String trimmed = line.trim();
                if (!trimmed.isEmpty()) {
                    ids.add(Integer.parseInt(trimmed));
                }
            }
            return ids;
        }
    }
}
