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

        public static Monolithic load(Path filePath) throws IOException {
            Monolithic mono = new Monolithic();
            if (!Files.exists(filePath)) return mono;
            try (BufferedReader reader = Files.newBufferedReader(filePath, StandardCharsets.UTF_8)) {
                String line;
                String currentTerm = null;
                List<Integer> currentList = null;

                while ((line = reader.readLine()) != null) {
                    line = line.trim();
                    if (line.isEmpty() || line.equals("{") || line.equals("}")) continue;

                    if (currentTerm != null) {
                        if (line.startsWith("]") || line.startsWith("],")) {
                            mono.index.put(currentTerm, currentList);
                            currentTerm = null;
                            currentList = null;
                        } else {
                            String numStr = line.endsWith(",") ? line.substring(0, line.length() - 1).trim() : line;
                            if (!numStr.isEmpty()) {
                                try {
                                    currentList.add(Integer.parseInt(numStr));
                                } catch (NumberFormatException ignored) {}
                            }
                        }
                    } else if (line.startsWith("\"")) {
                        int colonIdx = line.indexOf("\":");
                        if (colonIdx != -1) {
                            String term = line.substring(1, colonIdx);
                            int startBracket = line.indexOf('[', colonIdx);
                            if (startBracket != -1) {
                                int endBracket = line.indexOf(']', startBracket);
                                if (endBracket != -1) {
                                    String idsStr = line.substring(startBracket + 1, endBracket).trim();
                                    List<Integer> ids = new ArrayList<>();
                                    if (!idsStr.isEmpty()) {
                                        for (String id : idsStr.split(",")) {
                                            ids.add(Integer.parseInt(id.trim()));
                                        }
                                    }
                                    mono.index.put(term, ids);
                                } else {
                                    currentTerm = term;
                                    currentList = new ArrayList<>();
                                }
                            }
                        }
                    }
                }
            }
            return mono;
        }

        public int getTermsCount() {
            return index.size();
        }
    }

    public static class Hierarchical {
        private static final Set<String> WINDOWS_RESERVED_NAMES = new HashSet<>(Arrays.asList(
            "con", "prn", "aux", "nul",
            "com0", "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
            "lpt0", "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9"
        ));

        private final Path baseDir;

        public Hierarchical(Path baseDir) {
            this.baseDir = baseDir;
        }

        private String getFileName(String term) {
            return WINDOWS_RESERVED_NAMES.contains(term) ? term + "_.txt" : term + ".txt";
        }

        public void addDocument(int docId, String text) throws IOException {
            Set<String> terms = Tokenizer.getUniqueTerms(text);
            for (String term : terms) {
                char first = Character.toUpperCase(term.charAt(0));
                String folder = Character.isLetterOrDigit(first) ? String.valueOf(first) : "_";
                Path dir = baseDir.resolve(folder);
                Files.createDirectories(dir);

                Path termFile = dir.resolve(getFileName(term));
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
            Path termFile = baseDir.resolve(folder).resolve(getFileName(clean));
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
