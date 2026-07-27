import pytest

from topicbuilder.core.clustering import clusterize, clusterize_taxonomy_by_level, filter_taxonomy, most_similar_topic
from topicbuilder.core.schemas import Taxonomy, Topic

# ---------------------------------------------------------------------------
# clusterize — partition invariants (order-agnostic)
# ---------------------------------------------------------------------------


def test_clusterize_returns_empty_for_empty_input():
    assert clusterize([], 5) == []


def test_clusterize_single_chunk_when_texts_fit_in_n():
    result = clusterize(["a", "b", "c"], 5)
    assert len(result) == 1
    assert sorted(result[0]) == ["a", "b", "c"]


def test_clusterize_exact_fit():
    result = clusterize(["a", "b", "c", "d"], 2)
    assert len(result) == 2
    assert all(len(chunk) == 2 for chunk in result)
    assert {x for chunk in result for x in chunk} == {"a", "b", "c", "d"}


def test_clusterize_no_chunk_exceeds_n():
    texts = list(range(17))
    for n in [3, 5, 7, 10]:
        result = clusterize(texts, n)
        assert all(len(chunk) <= n for chunk in result)


def test_clusterize_partition_covers_all_texts():
    texts = ["x"] * 13
    result = clusterize(texts, 4)
    assert sum(len(chunk) for chunk in result) == len(texts)


def test_clusterize_partition_is_disjoint():
    texts = list(range(10))
    result = clusterize(texts, 3)
    flattened = [item for chunk in result for item in chunk]
    assert sorted(flattened) == sorted(texts)


@pytest.mark.parametrize(
    "total, n, expected_chunks",
    [
        (1, 10, 1),
        (10, 10, 1),
        (11, 10, 2),
        (20, 7, 3),
    ],
)
def test_clusterize_chunk_count(total: int, n: int, expected_chunks: int):
    result = clusterize(list(range(total)), n)
    assert len(result) == expected_chunks


# ---------------------------------------------------------------------------
# clusterize — shuffle semantics
# ---------------------------------------------------------------------------


def test_clusterize_is_deterministic_with_same_seed():
    texts = list(range(20))
    assert clusterize(texts, 5, seed=42) == clusterize(texts, 5, seed=42)


def test_clusterize_default_seed_equals_seed_zero():
    texts = list(range(20))
    assert clusterize(texts, 5) == clusterize(texts, 5, seed=0)


def test_clusterize_different_seeds_yield_different_order():
    texts = list(range(20))
    # With 20 items the probability of a collision is astronomically low
    assert clusterize(texts, 20, seed=0) != clusterize(texts, 20, seed=1)


def test_clusterize_does_not_mutate_input():
    texts = list(range(10))
    original = texts[:]
    clusterize(texts, 3)
    assert texts == original


# ---------------------------------------------------------------------------
# filter_taxonomy
# ---------------------------------------------------------------------------


def test_filter_taxonomy_keeps_matching_name_and_level():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d", level=0),
            Topic(name="B", description="d", level=0),
            Topic(name="C", description="d", level=1),
        ]
    )
    result = filter_taxonomy(taxonomy, ["A", "B"], level=0)
    assert {t.name for t in result.topics} == {"A", "B"}


def test_filter_taxonomy_excludes_wrong_level():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d", level=0),
            Topic(name="A", description="d", level=1),  # same name, different level
        ]
    )
    result = filter_taxonomy(taxonomy, ["A"], level=0)
    assert all(t.level == 0 for t in result.topics)
    assert len(result.topics) == 1


def test_filter_taxonomy_returns_empty_when_no_match():
    taxonomy = Taxonomy(topics=[Topic(name="A", description="d", level=0)])
    assert filter_taxonomy(taxonomy, ["Z"], level=0).topics == []


# ---------------------------------------------------------------------------
# clusterize_taxonomy_by_level
# ---------------------------------------------------------------------------


def _make_taxonomy(*names_by_level: tuple[int, list[str]]) -> Taxonomy:
    """
    Build a Taxonomy from (level, [name, ...]) pairs.
    """
    return Taxonomy(
        topics=[Topic(name=name, description="d", level=lvl) for lvl, names in names_by_level for name in names]
    )


def test_clusterize_taxonomy_by_level_empty_returns_empty():
    assert clusterize_taxonomy_by_level(Taxonomy(topics=[]), n=5) == []


def test_clusterize_taxonomy_by_level_single_level_all_fit():
    taxonomy = _make_taxonomy((0, ["A", "B", "C"]))
    taxonomies = clusterize_taxonomy_by_level(taxonomy, n=10)
    assert len(taxonomies) == 1
    assert {t.name for t in taxonomies[0].topics} == {"A", "B", "C"}


def test_clusterize_taxonomy_by_level_each_chunk_contains_single_level():
    taxonomy = _make_taxonomy((0, ["A", "B"]), (1, ["P", "Q"]))
    taxonomies = clusterize_taxonomy_by_level(taxonomy, n=10)
    for sub_tax in taxonomies:
        levels = {t.level for t in sub_tax.topics}
        assert len(levels) == 1


def test_clusterize_taxonomy_by_level_multiple_chunks_per_level():
    taxonomy = _make_taxonomy((0, ["A", "B", "C", "D"]))
    taxonomies = clusterize_taxonomy_by_level(taxonomy, n=2)
    assert len(taxonomies) == 2
    all_names = {t.name for sub in taxonomies for t in sub.topics}
    assert all_names == {"A", "B", "C", "D"}


def test_clusterize_taxonomy_by_level_topics_from_other_levels_excluded():
    taxonomy = _make_taxonomy((0, ["A", "B"]), (1, ["P"]))
    taxonomies = clusterize_taxonomy_by_level(taxonomy, n=10)
    level_0_sub = next(sub for sub in taxonomies if all(t.level == 0 for t in sub.topics))
    assert all(t.name != "P" for t in level_0_sub.topics)


def test_clusterize_taxonomy_by_level_no_empty_sub_taxonomy():
    taxonomy = _make_taxonomy((0, ["A", "B", "C"]))
    taxonomies = clusterize_taxonomy_by_level(taxonomy, n=2)
    assert all(len(sub.topics) > 0 for sub in taxonomies)


# ---------------------------------------------------------------------------
# most_similar_topic
# ---------------------------------------------------------------------------


def test_most_similar_topic_returns_exact_match():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="Water Cycle", description="d"),
            Topic(name="Photosynthesis", description="d"),
        ]
    )
    assert most_similar_topic("Water Cycle", taxonomy).name == "Water Cycle"


def test_most_similar_topic_returns_closest_name():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="Water Cycle", description="d"),
            Topic(name="Photosynthesis", description="d"),
        ]
    )
    assert most_similar_topic("Hydrological Cycle", taxonomy).name == "Water Cycle"


def test_most_similar_topic_returns_topic_object():
    taxonomy = Taxonomy(topics=[Topic(name="A", description="desc", level=2)])
    result = most_similar_topic("A", taxonomy)
    assert result.description == "desc"
    assert result.level == 2


def test_most_similar_topic_filters_by_level():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="Water Cycle", description="d", level=0),
            Topic(name="Water Cycle", description="d", level=1),
            Topic(name="Photosynthesis", description="d", level=1),
        ]
    )
    result = most_similar_topic("Water Cycle", taxonomy, level=1)
    assert result.level == 1
