import pytest

from topicbuilder.core.clustering import chunk_text, most_similar


@pytest.mark.parametrize(
    "sample, choices, expected",
    [
        ("Water Cycle", ["Water Cycle", "Photosynthesis"], "Water Cycle"),
        ("Hydrological Cycle", ["Water Cycle", "Photosynthesis"], "Water Cycle"),
        ("photosynthesis", ["Water Cycle", "Photosynthesis"], "Photosynthesis"),
        ("A", ["B", "A", "C"], "A"),
    ],
)
def test_most_similar_returns_closest_match(sample, choices, expected):
    assert most_similar(sample, choices) == expected


def test_most_similar_single_choice():
    assert most_similar("anything", ["only"]) == "only"


def test_chunk_text_short_text_returns_single_chunk():
    text = "This is a short sentence."
    result = chunk_text(text, chunk_max_words=100)
    assert len(result) == 1
    assert "short sentence" in result[0]


def test_chunk_text_no_chunk_exceeds_max_words():
    text = " ".join(f"word{i}" for i in range(50))
    chunks = chunk_text(text, chunk_max_words=10)
    assert all(len(c.split()) <= 10 for c in chunks)


def test_chunk_text_covers_all_words():
    words = [f"w{i}" for i in range(25)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_max_words=10)
    recovered = " ".join(chunks).split()
    assert recovered == words


def test_chunk_text_empty_string_returns_one_empty_chunk():
    result = chunk_text("", chunk_max_words=10)
    assert result == [""]


def test_chunk_text_respects_newline_boundaries():
    line_a = " ".join(["a"] * 5)
    line_b = " ".join(["b"] * 5)
    chunks = chunk_text(f"{line_a}\n{line_b}", chunk_max_words=5)
    assert len(chunks) == 2
