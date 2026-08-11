from unittest.mock import MagicMock

import numpy as np
import pytest

from tests.unit.helpers import make_capturing_hdbscan, make_clustering_config, make_stub_hdbscan, make_stub_umap
from topicbuilder.core import clustering as clustering_module
from topicbuilder.core.clustering import (
    ClusteringConfig,
    chunk_text,
    clusterize,
    clusterize_taxonomy_by_level,
    filter_taxonomy,
    get_embeddings,
    most_similar,
    most_similar_topic,
    preprocess_for_embedding,
    reduce_dimensions,
)
from topicbuilder.core.schemas import Taxonomy, Topic


def test_clustering_config_from_config_loads_real_yaml():
    config = ClusteringConfig.from_config("tests/conf/test_clustering.yaml")
    assert config.embedding["model"] == "BAAI/bge-small-en-v1.5"
    assert config.umap["n_neighbors"] == 2
    assert config.hdbscan["min_cluster_size"] == 2


def test_clusterize_returns_single_group_for_a_single_text_without_embedding(monkeypatch):
    mock_get_embeddings = MagicMock()
    monkeypatch.setattr(clustering_module, "get_embeddings", mock_get_embeddings)
    config = make_clustering_config(n_neighbors=15, n_components=5)
    result = clusterize(["A"], config)
    assert result == [["A"]]
    mock_get_embeddings.assert_not_called()


def test_clusterize_skips_umap_for_exactly_two_texts(monkeypatch):
    config = make_clustering_config(n_neighbors=15, n_components=5)
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0]], dtype="float32")
    captured: dict = {}
    monkeypatch.setattr(clustering_module, "get_embeddings", lambda texts, **kw: embeddings)
    monkeypatch.setattr(clustering_module.umap, "UMAP", MagicMock(side_effect=AssertionError("UMAP should not run")))
    monkeypatch.setattr(clustering_module, "HDBSCAN", make_capturing_hdbscan(captured, np.array([-1, -1])))
    result = clusterize(["A", "B"], config)
    np.testing.assert_array_equal(captured["reduced"], embeddings)
    assert {frozenset(g) for g in result} == {frozenset(["A"]), frozenset(["B"])}


@pytest.mark.parametrize(
    "n_texts, configured_n_components, expected_n_components",
    [
        (9, 50, 2),
        (50, 50, 5),
        (500, 50, 50),
    ],
)
def test_reduce_dimensions_scales_n_components_down_for_small_sample_sizes(
    monkeypatch, n_texts, configured_n_components, expected_n_components
):
    config = make_clustering_config(n_neighbors=15, n_components=configured_n_components)
    captured: dict = {}
    monkeypatch.setattr(clustering_module.umap, "UMAP", make_stub_umap(captured))
    reduce_dimensions(np.zeros((n_texts, 4), "float32"), config)
    assert captured["n_components"] == expected_n_components


@pytest.mark.parametrize(
    "n_texts, configured_n_neighbors, expected_n_neighbors",
    [
        (5, 100, 4),
        (5, 1, 2),
    ],
)
def test_reduce_dimensions_clamps_n_neighbors_to_sample_size(
    monkeypatch, n_texts, configured_n_neighbors, expected_n_neighbors
):
    config = make_clustering_config(n_neighbors=configured_n_neighbors, n_components=2)
    captured: dict = {}
    monkeypatch.setattr(clustering_module.umap, "UMAP", make_stub_umap(captured))
    reduce_dimensions(np.zeros((n_texts, 4), "float32"), config)
    assert captured["n_neighbors"] == expected_n_neighbors


def test_clusterize_runs_umap_at_or_above_three_texts(monkeypatch):
    n_texts = 10
    config = make_clustering_config(n_neighbors=15, n_components=1)
    captured: dict = {}
    monkeypatch.setattr(clustering_module, "get_embeddings", lambda texts, **kw: np.zeros((len(texts), 4), "float32"))
    monkeypatch.setattr(clustering_module.umap, "UMAP", make_stub_umap(captured))
    monkeypatch.setattr(clustering_module, "HDBSCAN", make_stub_hdbscan(np.full(n_texts, -1)))
    clusterize([str(i) for i in range(n_texts)], config)
    assert captured["n_neighbors"] == 9


def test_clusterize_groups_by_label_and_returns_singleton_groups_for_noise(monkeypatch):
    config = make_clustering_config(n_neighbors=2, n_components=1)
    texts = ["a", "b", "c", "d"]
    monkeypatch.setattr(clustering_module, "get_embeddings", lambda texts, **kw: np.zeros((len(texts), 4), "float32"))
    monkeypatch.setattr(clustering_module.umap, "UMAP", make_stub_umap({}))
    monkeypatch.setattr(clustering_module, "HDBSCAN", make_stub_hdbscan(np.array([0, 0, -1, 1])))
    result = clusterize(texts, config)
    assert {frozenset(g) for g in result} == {frozenset(g) for g in [["a", "b"], ["c"], ["d"]]}


@pytest.mark.parametrize(
    "topics, expected_names",
    [
        ([], []),
        ([("A", 0), ("B", 0), ("C", 1), ("D", 1)], ["A", "B", "C", "D"]),
    ],
)
def test_clusterize_taxonomy_by_level_partitions_by_level_without_losing_topics(monkeypatch, topics, expected_names):
    config = make_clustering_config(n_neighbors=2, n_components=1)
    monkeypatch.setattr(clustering_module, "get_embeddings", lambda texts, **kw: np.zeros((len(texts), 4), "float32"))
    monkeypatch.setattr(clustering_module, "HDBSCAN", make_stub_hdbscan(np.array([0, 0])))
    taxonomy = Taxonomy(topics=[Topic(name=name, description="d", level=level) for name, level in topics])
    result = clusterize_taxonomy_by_level(taxonomy, config)
    assert all(len({t.level for t in sub.topics}) == 1 for sub in result)
    assert sorted(t.name for sub in result for t in sub.topics) == sorted(expected_names)


@pytest.mark.parametrize(
    "topics, names, level, expected_names",
    [
        ([("A", 0), ("B", 0), ("C", 1)], ["A", "B"], 0, {"A", "B"}),
        ([("A", 0), ("A", 1)], ["A"], 0, {"A"}),
        ([("A", 0)], ["Z"], 0, set()),
    ],
)
def test_filter_taxonomy_keeps_only_names_and_level_matches(topics, names, level, expected_names):
    taxonomy = Taxonomy(topics=[Topic(name=name, description="d", level=lvl) for name, lvl in topics])
    result = filter_taxonomy(taxonomy, names, level)
    assert {t.name for t in result.topics} == expected_names
    assert all(t.level == level for t in result.topics)


@pytest.mark.parametrize(
    "sample, expected_name",
    [
        ("Water Cycle", "Water Cycle"),
        ("Water Cycl", "Water Cycle"),
    ],
)
def test_most_similar_topic_returns_closest_by_name_similarity(sample, expected_name):
    taxonomy = Taxonomy(
        topics=[
            Topic(name="Water Cycle", description="d"),
            Topic(name="Photosynthesis", description="d"),
        ]
    )
    assert most_similar_topic(sample, taxonomy).name == expected_name


def test_most_similar_topic_always_returns_a_topic_without_a_similarity_floor():
    taxonomy = Taxonomy(topics=[Topic(name="Water Cycle", description="d")])
    result = most_similar_topic("Completely unrelated gibberish", taxonomy)
    assert result.name == "Water Cycle"


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


@pytest.mark.parametrize(
    "sample, choices, expected",
    [
        ("Water Cycle", ["Water Cycle", "Photosynthesis"], "Water Cycle"),
        ("Hydrological Cycle", ["Water Cycle", "Photosynthesis"], "Water Cycle"),
        ("photosynthesis", ["Water Cycle", "Photosynthesis"], "Photosynthesis"),
        ("A", ["B", "A", "C"], "A"),
        ("anything", ["only"], "only"),
    ],
)
def test_most_similar_returns_closest_match(sample, choices, expected):
    assert most_similar(sample, choices) == expected


@pytest.mark.parametrize(
    "text, chunk_max_words, expected",
    [
        ("", 10, [""]),
        ("This is a short sentence.", 100, ["This is a short sentence."]),
    ],
)
def test_chunk_text_returns_single_chunk_for_short_or_empty_text(text, chunk_max_words, expected):
    assert chunk_text(text, chunk_max_words) == expected


def test_chunk_text_packs_words_without_exceeding_max_and_preserves_content():
    words = [f"w{i}" for i in range(25)]
    chunks = chunk_text(" ".join(words), chunk_max_words=10)
    assert all(len(c.split()) <= 10 for c in chunks)
    assert " ".join(chunks).split() == words


def test_chunk_text_splits_into_new_chunk_when_line_exactly_fills_budget():
    line_a = " ".join(["a"] * 5)
    line_b = " ".join(["b"] * 5)
    chunks = chunk_text(f"{line_a}\n{line_b}", chunk_max_words=5)
    assert len(chunks) == 2


def test_get_embeddings_prepends_prefix_and_returns_unit_normalized_vectors(monkeypatch):
    captured: dict = {}

    class StubEmbedder:
        def __init__(self, model_name: str) -> None:
            return

        def embed(self, texts: list[str], batch_size: int) -> list[np.ndarray]:
            captured["texts"] = texts
            return [np.array([3.0, 4.0], dtype="float32") for _ in texts]

    monkeypatch.setattr(clustering_module, "TextEmbedding", StubEmbedder)
    result = get_embeddings(["chat"], model="stub", batch_size=8, prefix="query: ")
    assert captured["texts"] == ["query: chat"]
    assert result.shape == (1, 2)
    np.testing.assert_allclose(np.linalg.norm(result, axis=1), 1.0)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("", ""),
        ("Le chat", "chat"),
        ("Café au lait", "cafe lait"),
        ("cœur", "coeur"),
        ("test123 word", "test123 word"),
        ("A", ""),
    ],
)
def test_preprocess_for_embedding_normalizes_text(text, expected):
    assert preprocess_for_embedding(text) == expected
