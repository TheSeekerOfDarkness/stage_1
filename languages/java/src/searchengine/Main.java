package searchengine;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.LocalDateTime;
import java.util.*;

public class Main {
    public static void main(String[] args) throws Exception {
        if (args.length < 1) {
            System.err.println("Usage: java searchengine.Main <command> [args...]");
            System.exit(1);
        }

        String command = args[0];

        if ("index-monolithic".equals(command)) {
            Path lakeDir = Paths.get(args[1]);
            Path outJson = Paths.get(args[2]);

            long start = System.currentTimeMillis();
            InvertedIndex.Monolithic index = new InvertedIndex.Monolithic();

            try (var stream = Files.walk(lakeDir)) {
                stream.filter(p -> p.getFileName().toString().endsWith(".body.txt")).forEach(p -> {
                    try {
                        String name = p.getFileName().toString().replace(".body.txt", "");
                        int bookId = Integer.parseInt(name);
                        String body = Files.readString(p, StandardCharsets.UTF_8);
                        index.addDocument(bookId, body);
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                });
            }

            index.save(outJson);
            long elapsed = System.currentTimeMillis() - start;
            System.out.printf("{\"status\": \"success\", \"time_ms\": %d, \"terms\": %d, \"output\": \"%s\"}%n",
                    elapsed, index.getTermsCount(), outJson.toString());

        } else if ("index-hierarchical".equals(command)) {
            Path lakeDir = Paths.get(args[1]);
            Path outDir = Paths.get(args[2]);

            long start = System.currentTimeMillis();
            InvertedIndex.Hierarchical index = new InvertedIndex.Hierarchical(outDir);

            try (var stream = Files.walk(lakeDir)) {
                stream.filter(p -> p.getFileName().toString().endsWith(".body.txt")).forEach(p -> {
                    try {
                        String name = p.getFileName().toString().replace(".body.txt", "");
                        int bookId = Integer.parseInt(name);
                        String body = Files.readString(p, StandardCharsets.UTF_8);
                        index.addDocument(bookId, body);
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                });
            }

            long elapsed = System.currentTimeMillis() - start;
            System.out.printf("{\"status\": \"success\", \"time_ms\": %d, \"output\": \"%s\"}%n",
                    elapsed, outDir.toString());

        } else if ("query-hierarchical".equals(command)) {
            Path indexDir = Paths.get(args[1]);
            String term = args[2];
            long start = System.nanoTime();
            InvertedIndex.Hierarchical index = new InvertedIndex.Hierarchical(indexDir);
            List<Integer> res = index.lookup(term);
            long elapsedNs = System.nanoTime() - start;
            System.out.printf("{\"term\": \"%s\", \"time_us\": %.2f, \"postings\": %s}%n",
                    term, elapsedNs / 1000.0, res.toString());

        } else if ("benchmark-datalake".equals(command)) {
            String layout = args[1];
            Path booksDir = Paths.get(args[2]);
            Path outLake = Paths.get(args[3]);

            long start = System.currentTimeMillis();
            if ("time_based".equals(layout)) {
                var dl = new Datalake.TimeBased(outLake);
                try (var stream = Files.list(booksDir)) {
                    stream.filter(p -> p.toString().endsWith(".txt")).forEach(p -> {
                        try {
                            String content = Files.readString(p);
                            int id = Integer.parseInt(p.getFileName().toString().replace(".txt", ""));
                            dl.saveBook(id, "Header " + id, content, LocalDateTime.now());
                        } catch (Exception e) { e.printStackTrace(); }
                    });
                }
            } else if ("book_based".equals(layout)) {
                var dl = new Datalake.BookBased(outLake);
                try (var stream = Files.list(booksDir)) {
                    stream.filter(p -> p.toString().endsWith(".txt")).forEach(p -> {
                        try {
                            String content = Files.readString(p);
                            int id = Integer.parseInt(p.getFileName().toString().replace(".txt", ""));
                            dl.saveBook(id, "Header " + id, content);
                        } catch (Exception e) { e.printStackTrace(); }
                    });
                }
            } else if ("batch_based".equals(layout)) {
                var dl = new Datalake.BatchBased(outLake, 1000);
                try (var stream = Files.list(booksDir)) {
                    stream.filter(p -> p.toString().endsWith(".txt")).forEach(p -> {
                        try {
                            String content = Files.readString(p);
                            int id = Integer.parseInt(p.getFileName().toString().replace(".txt", ""));
                            dl.saveBook(id, "Header " + id, content);
                        } catch (Exception e) { e.printStackTrace(); }
                    });
                }
            }
            long elapsed = System.currentTimeMillis() - start;
            System.out.printf("{\"status\": \"success\", \"layout\": \"%s\", \"time_ms\": %d}%n", layout, elapsed);
        } else if ("index".equals(command)) {
            String indexerType = "monolithic";
            for (int i = 1; i < args.length; i++) {
                if ("--indexer".equals(args[i]) && i + 1 < args.length) {
                    indexerType = args[i + 1];
                    i++;
                }
            }
            Path lakeDir = Paths.get("datalake");
            long start = System.currentTimeMillis();

            if ("hierarchical".equalsIgnoreCase(indexerType)) {
                Path outDir = Paths.get("datamarts", "hierarchical");
                InvertedIndex.Hierarchical index = new InvertedIndex.Hierarchical(outDir);
                try (var stream = Files.walk(lakeDir)) {
                    stream.filter(p -> p.getFileName().toString().endsWith(".body.txt")).forEach(p -> {
                        try {
                            String name = p.getFileName().toString().replace(".body.txt", "");
                            int bookId = Integer.parseInt(name);
                            String body = Files.readString(p, StandardCharsets.UTF_8);
                            index.addDocument(bookId, body);
                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    });
                }
                long elapsed = System.currentTimeMillis() - start;
                System.out.printf("\n=== Java Indexing Summary (hierarchical) ===\nTotal time: %d ms\nOutput directory: %s\n", elapsed, outDir);
            } else {
                Path outJson = Paths.get("datamarts", "inverted_index.json");
                InvertedIndex.Monolithic index = new InvertedIndex.Monolithic();
                try (var stream = Files.walk(lakeDir)) {
                    stream.filter(p -> p.getFileName().toString().endsWith(".body.txt")).forEach(p -> {
                        try {
                            String name = p.getFileName().toString().replace(".body.txt", "");
                            int bookId = Integer.parseInt(name);
                            String body = Files.readString(p, StandardCharsets.UTF_8);
                            index.addDocument(bookId, body);
                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    });
                }
                index.save(outJson);
                long elapsed = System.currentTimeMillis() - start;
                System.out.printf("\n=== Java Indexing Summary (monolithic) ===\nIndexed %d terms in %d ms\nOutput saved to: %s\n",
                        index.getTermsCount(), elapsed, outJson);
            }

        } else if ("search".equals(command)) {
            String indexerType = "monolithic";
            String query = null;
            for (int i = 1; i < args.length; i++) {
                if ("--indexer".equals(args[i]) && i + 1 < args.length) {
                    indexerType = args[i + 1];
                    i++;
                } else if (!args[i].startsWith("--")) {
                    query = args[i];
                }
            }
            if (query == null) {
                System.err.println("Usage: java searchengine.Main search [--indexer <monolithic|hierarchical>] <query>");
                System.exit(1);
            }

            long start = System.nanoTime();
            List<String> terms = Tokenizer.tokenize(query, true);
            if (terms.isEmpty()) {
                System.out.printf("\n=== Java Search Results for: '%s' (%s) ===\nTotal matching books: 0\n(Query contained only stop words or invalid characters)\n", query, indexerType);
                return;
            }

            Set<Integer> matchingIds = null;
            if ("hierarchical".equalsIgnoreCase(indexerType)) {
                InvertedIndex.Hierarchical index = new InvertedIndex.Hierarchical(Paths.get("datamarts", "hierarchical"));
                for (String term : terms) {
                    Set<Integer> postings = new HashSet<>(index.lookup(term));
                    if (matchingIds == null) {
                        matchingIds = postings;
                    } else {
                        matchingIds.retainAll(postings);
                    }
                }
            } else {
                InvertedIndex.Monolithic index = InvertedIndex.Monolithic.load(Paths.get("datamarts", "inverted_index.json"));
                for (String term : terms) {
                    Set<Integer> postings = new HashSet<>(index.lookup(term));
                    if (matchingIds == null) {
                        matchingIds = postings;
                    } else {
                        matchingIds.retainAll(postings);
                    }
                }
            }

            long elapsedNs = System.nanoTime() - start;
            List<Integer> sorted = new ArrayList<>(matchingIds == null ? Collections.emptyList() : matchingIds);
            Collections.sort(sorted);

            System.out.printf("\n=== Java Search Results for: '%s' (%s) ===\n", query, indexerType);
            System.out.printf("Total matching books: %d (in %.2f ms)\n", sorted.size(), elapsedNs / 1_000_000.0);
            for (int id : sorted) {
                System.out.printf("  - [Book ID %d]\n", id);
            }

        } else {
            System.err.println("Unknown command: " + command);
            System.exit(1);
        }
    }
}
