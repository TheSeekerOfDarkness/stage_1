"""Downloader and parser for Project Gutenberg books."""

import requests
from src.config import (
    DEFAULT_USER_AGENT,
    END_MARKER,
    GUTENBERG_URL_TEMPLATE,
    START_MARKER,
)


class BookDownloader:
    """Handles downloading plain text books and splitting them into header, body, and footer."""

    def __init__(self, user_agent: str = DEFAULT_USER_AGENT, timeout: int = 30):
        self.user_agent = user_agent
        self.timeout = timeout

    def download_text(self, book_id: int) -> str:
        """Download the raw text of a book from Project Gutenberg.

        Raises:
            requests.HTTPError: If the download fails.
        """
        url = GUTENBERG_URL_TEMPLATE.format(book_id=book_id)
        headers = {"User-Agent": self.user_agent}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        # Gutenberg files are typically UTF-8 or ASCII
        response.encoding = "utf-8"
        return response.text

    def split_book_text(self, text: str) -> tuple[str, str, str]:
        """Split raw book text into header, body, and footer.

        Args:
            text: Raw content of the Project Gutenberg book.

        Returns:
            A tuple of (header, body, footer).

        Raises:
            ValueError: If START_MARKER or END_MARKER is missing.
        """
        if START_MARKER not in text or END_MARKER not in text:
            raise ValueError("Text does not contain required Project Gutenberg delimiters.")

        header, body_and_footer = text.split(START_MARKER, 1)

        # Remove the remainder of the START_MARKER line if present (e.g., ' PRIDE AND PREJUDICE ***')
        first_newline = body_and_footer.find("\n")
        if first_newline != -1:
            first_line = body_and_footer[:first_newline]
            if "***" in first_line:
                body_and_footer = body_and_footer[first_newline + 1 :]

        body, footer = body_and_footer.split(END_MARKER, 1)

        return header.strip(), body.strip(), footer.strip()
