"""Unit tests for TextTokenizer."""

from src.datamart.tokenizer import TextTokenizer


def test_tokenizer_stop_word_removal():
    tokenizer = TextTokenizer()
    text = "The car is nice and the best car in town."
    tokens = tokenizer.tokenize(text)

    # Stop words like 'the', 'is', 'and', 'in' should be removed
    assert "the" not in tokens
    assert "is" not in tokens
    assert "and" not in tokens
    assert "in" not in tokens

    # Content terms must remain
    assert "car" in tokens
    assert "nice" in tokens
    assert "best" in tokens
    assert "town" in tokens


def test_tokenizer_term_frequencies():
    tokenizer = TextTokenizer()
    text = "apple banana apple orange apple banana"
    freqs = tokenizer.extract_term_frequencies(text)

    assert freqs["apple"] == 3
    assert freqs["banana"] == 2
    assert freqs["orange"] == 1


def test_tokenizer_positions():
    tokenizer = TextTokenizer()
    # "the" is at 0, "car" is at 1, "is" is at 2, "nice" is at 3
    text = "The car is nice"
    positions = tokenizer.extract_terms_with_positions(text)

    assert "the" not in positions
    assert positions["car"] == [1]
    assert positions["nice"] == [3]
