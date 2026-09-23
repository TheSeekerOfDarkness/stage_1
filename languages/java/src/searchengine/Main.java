package searchengine;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.LocalDateTime;
import java.util.List;

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
        } else {
            System.err.println("Unknown command: " + command);
            System.exit(1);
        }
    }
}
