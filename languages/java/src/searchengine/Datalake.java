package searchengine;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public class Datalake {

    public static class TimeBased {
        private final Path baseDir;

        public TimeBased(Path baseDir) {
            this.baseDir = baseDir;
        }

        public void saveBook(int bookId, String header, String body, LocalDateTime dt) throws IOException {
            String dateFolder = dt.format(DateTimeFormatter.ofPattern("yyyyMMdd"));
            String hourFolder = dt.format(DateTimeFormatter.ofPattern("HH"));
            Path dir = baseDir.resolve(dateFolder).resolve(hourFolder);
            Files.createDirectories(dir);

            Files.writeString(dir.resolve(bookId + ".header.txt"), header, StandardCharsets.UTF_8);
            Files.writeString(dir.resolve(bookId + ".body.txt"), body, StandardCharsets.UTF_8);
        }

        public Path findBook(int bookId) throws IOException {
            try (var stream = Files.walk(baseDir)) {
                return stream
                    .filter(p -> p.getFileName().toString().equals(bookId + ".body.txt"))
                    .findFirst()
                    .orElse(null);
            }
        }
    }

    public static class BookBased {
        private final Path baseDir;

        public BookBased(Path baseDir) {
            this.baseDir = baseDir;
        }

        public void saveBook(int bookId, String header, String body) throws IOException {
            Path dir = baseDir.resolve(String.valueOf(bookId));
            Files.createDirectories(dir);

            Files.writeString(dir.resolve("header.txt"), header, StandardCharsets.UTF_8);
            Files.writeString(dir.resolve("body.txt"), body, StandardCharsets.UTF_8);
        }

        public Path findBook(int bookId) {
            Path p = baseDir.resolve(String.valueOf(bookId)).resolve("body.txt");
            return Files.exists(p) ? p : null;
        }
    }

    public static class BatchBased {
        private final Path baseDir;
        private final int batchSize;

        public BatchBased(Path baseDir, int batchSize) {
            this.baseDir = baseDir;
            this.batchSize = batchSize;
        }

        public void saveBook(int bookId, String header, String body) throws IOException {
            int start = (bookId / batchSize) * batchSize;
            int end = start + batchSize - 1;
            String batchFolder = String.format("batch_%05d_%05d", start, end);
            Path dir = baseDir.resolve(batchFolder);
            Files.createDirectories(dir);

            Files.writeString(dir.resolve(bookId + ".header.txt"), header, StandardCharsets.UTF_8);
            Files.writeString(dir.resolve(bookId + ".body.txt"), body, StandardCharsets.UTF_8);
        }

        public Path findBook(int bookId) {
            int start = (bookId / batchSize) * batchSize;
            int end = start + batchSize - 1;
            String batchFolder = String.format("batch_%05d_%05d", start, end);
            Path p = baseDir.resolve(batchFolder).resolve(bookId + ".body.txt");
            return Files.exists(p) ? p : null;
        }
    }
}
