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


def test_clusterize_taxonomy_by_level_returns_empty_list_for_empty_taxonomy():
    config = make_clustering_config(n_neighbors=2, n_components=1)
    assert clusterize_taxonomy_by_level(Taxonomy(topics=[]), config) == []


def test_clusterize_taxonomy_by_level_never_mixes_levels(monkeypatch):
    config = make_clustering_config(n_neighbors=2, n_components=1)
    monkeypatch.setattr(clustering_module, "get_embeddings", lambda texts, **kw: np.zeros((len(texts), 4), "float32"))
    monkeypatch.setattr(clustering_module, "HDBSCAN", make_stub_hdbscan(np.array([0, 0])))
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d", level=0),
            Topic(name="B", description="d", level=0),
            Topic(name="C", description="d", level=1),
            Topic(name="D", description="d", level=1),
        ]
    )
    result = clusterize_taxonomy_by_level(taxonomy, config)
    assert all(len({t.level for t in sub.topics}) == 1 for sub in result)


def test_clusterize_taxonomy_by_level_covers_all_topics_exactly_once(monkeypatch):
    config = make_clustering_config(n_neighbors=2, n_components=1)
    monkeypatch.setattr(clustering_module, "get_embeddings", lambda texts, **kw: np.zeros((len(texts), 4), "float32"))
    monkeypatch.setattr(clustering_module, "HDBSCAN", make_stub_hdbscan(np.array([0, 0])))
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d", level=0),
            Topic(name="B", description="d", level=0),
            Topic(name="C", description="d", level=1),
        ]
    )
    result = clusterize_taxonomy_by_level(taxonomy, config)
    all_names = [t.name for sub in result for t in sub.topics]
    assert sorted(all_names) == ["A", "B", "C"]


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


def test_get_embeddings_normalizes_to_unit_vectors(monkeypatch):
    class StubEmbedder:
        def __init__(self, model_name: str) -> None:
            return

        def embed(self, texts: list[str], batch_size: int) -> list[np.ndarray]:
            return [np.array([3.0, 4.0], dtype="float32") for _ in texts]

    monkeypatch.setattr(clustering_module, "TextEmbedding", StubEmbedder)
    result = get_embeddings(["a", "b"], model="stub", batch_size=8)
    assert result.shape == (2, 2)
    np.testing.assert_allclose(np.linalg.norm(result, axis=1), 1.0)


def test_get_embeddings_prepends_prefix_before_cleaning(monkeypatch):
    captured: dict = {}

    class StubEmbedder:
        def __init__(self, model_name: str) -> None:
            return

        def embed(self, texts: list[str], batch_size: int) -> list[np.ndarray]:
            captured["texts"] = texts
            return [np.array([1.0, 0.0], dtype="float32") for _ in texts]

    monkeypatch.setattr(clustering_module, "TextEmbedding", StubEmbedder)
    get_embeddings(["chat"], model="stub", batch_size=8, prefix="query: ")
    assert captured["texts"] == ["query: chat"]


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
