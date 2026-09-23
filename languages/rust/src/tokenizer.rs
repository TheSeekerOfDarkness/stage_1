use regex::Regex;
use std::collections::HashSet;
use std::sync::LazyLock;

static STOP_WORDS: LazyLock<HashSet<&'static str>> = LazyLock::new(|| {
    let words = [
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
    ];
    words.into_iter().collect()
});

static TOKEN_REGEX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"\b[a-zA-Z0-9]+(?:'[a-zA-Z0-9]+)?\b").unwrap());

pub fn tokenize(text: &str, remove_stopwords: bool) -> Vec<String> {
    let lower = text.to_lowercase();
    let mut tokens = Vec::new();
    for mat in TOKEN_REGEX.find_iter(&lower) {
        let word = mat.as_str();
        if !remove_stopwords || !STOP_WORDS.contains(word) {
            tokens.push(word.to_string());
        }
    }
    tokens
}

pub fn get_unique_terms(text: &str) -> HashSet<String> {
    tokenize(text, true).into_iter().collect()
}
