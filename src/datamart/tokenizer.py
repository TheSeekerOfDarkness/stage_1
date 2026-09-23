"""Text tokenizer, stop-word filter, and positional extractor for the Inverted Index."""

import re

# Standard English stop words (expanded from NLTK / Lucene / SMART lists)
STOP_WORDS = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any",
    "are", "aren't", "as", "at", "be", "because", "been", "before", "being", "below",
    "between", "both", "but", "by", "can", "can't", "cannot", "could", "couldn't", "did",
    "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each", "few",
    "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having",
    "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him",
    "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in",
    "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most",
    "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only",
    "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some",
    "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what",
    "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's",
    "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd",
    "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",
})

TOKEN_PATTERN = re.compile(r"\b[a-zA-Z0-9]+(?:'[a-zA-Z0-9]+)?\b")


class TextTokenizer:
    """Tokenizes and filters document text according to Big Data course specifications."""

    def __init__(self, stop_words: frozenset[str] = STOP_WORDS):
        self.stop_words = stop_words

    def tokenize(self, text: str, remove_stopwords: bool = True) -> list[str]:
        """Convert text into normalized list of tokens.

        - Lowercases all characters.
        - Splits using regex word boundaries.
        - Excludes stop words if remove_stopwords is True.
        """
        raw_tokens = TOKEN_PATTERN.findall(text.lower())
        if not remove_stopwords:
            return raw_tokens
        return [tok for tok in raw_tokens if tok not in self.stop_words]

    def extract_terms_with_positions(
        self, text: str, remove_stopwords: bool = True
    ) -> dict[str, list[int]]:
        """Extract terms mapped to their occurrence positions in the document.

        Positions are 0-indexed word offsets within the raw token sequence,
        enabling exact phrase and proximity search.
        """
        raw_tokens = TOKEN_PATTERN.findall(text.lower())
        postings: dict[str, list[int]] = {}

        for position, token in enumerate(raw_tokens):
            if remove_stopwords and token in self.stop_words:
                continue
            if token not in postings:
                postings[token] = []
            postings[token].append(position)

        return postings

    def extract_term_frequencies(
        self, text: str, remove_stopwords: bool = True
    ) -> dict[str, int]:
        """Extract terms mapped to their frequency count in the document."""
        tokens = self.tokenize(text, remove_stopwords=remove_stopwords)
        freqs: dict[str, int] = {}
        for token in tokens:
            freqs[token] = freqs.get(token, 0) + 1
        return freqs
