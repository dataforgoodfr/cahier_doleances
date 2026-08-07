import json
from types import SimpleNamespace

import numpy as np

from topicbuilder.core.clustering import ClusteringConfig
from topicbuilder.core.schemas import Label, ParentAddition, ParentCandidate, Taxonomy, Topic, TopicMerge


def with_sources(taxonomy: Taxonomy, *source_ids: str) -> Taxonomy:
    """
    Return a copy of the taxonomy where every topic records the supplied source text ids.
    """
    return Taxonomy(topics=[t.model_copy(update={"sources": list(source_ids)}) for t in taxonomy.topics])


def make_clustering_config(n_neighbors: int, n_components: int, min_cluster_size: int = 2) -> ClusteringConfig:
    """
    Build a minimal ClusteringConfig for testing clusterize() without loading a config file.
    """
    return ClusteringConfig(
        embedding={"model": "stub", "batch_size": 1},
        umap={"n_neighbors": n_neighbors, "n_components": n_components, "random_state": 42},
        hdbscan={"min_cluster_size": min_cluster_size},
    )


def make_stub_umap(captured_kwargs: dict) -> type:
    """
    Return a stand-in for umap.UMAP that records its constructor kwargs into `captured_kwargs`
    and reduces embeddings to a zero-valued matrix of the requested dimensionality.
    """

    class StubUMAP:
        def __init__(self, **kwargs) -> None:
            captured_kwargs.update(kwargs)

        def fit_transform(self, embeddings: np.ndarray) -> np.ndarray:
            return np.zeros((len(embeddings), captured_kwargs.get("n_components", 1)))

    return StubUMAP


def make_stub_hdbscan(labels: np.ndarray) -> type:
    """
    Return a stand-in for sklearn's HDBSCAN whose fit_predict always returns `labels`,
    regardless of constructor kwargs or input.
    """

    class StubHDBSCAN:
        def __init__(self, **kwargs) -> None:
            return

        def fit_predict(self, reduced: np.ndarray) -> np.ndarray:
            return labels

    return StubHDBSCAN


def make_capturing_hdbscan(captured: dict, labels: np.ndarray) -> type:
    """
    Return a stand-in for sklearn's HDBSCAN that records its fit_predict input into
    `captured["reduced"]` and always returns `labels`.
    """

    class CapturingHDBSCAN:
        def __init__(self, **kwargs) -> None:
            return

        def fit_predict(self, reduced: np.ndarray) -> np.ndarray:
            captured["reduced"] = reduced
            return labels

    return CapturingHDBSCAN


def make_tool_response(tool_name: str, arguments: dict) -> SimpleNamespace:
    """
    Build a minimal fake OpenAI ChatCompletion response carrying a single forced tool call.
    """
    tool_call = SimpleNamespace(function=SimpleNamespace(name=tool_name, arguments=json.dumps(arguments)))
    message = SimpleNamespace(tool_calls=[tool_call])
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def make_discover_topics_response(topics: list[Topic]) -> SimpleNamespace:
    """
    Build a minimal fake OpenAI response carrying a record_new_topics tool call.
    """
    return make_tool_response(
        "record_new_topics",
        {"topics": [{"name": t.name, "description": t.description} for t in topics]},
    )


def make_merge_candidates_response(groups: list[Taxonomy]) -> SimpleNamespace:
    """
    Build a minimal fake OpenAI response carrying a propose_merge_candidates tool call.
    """
    return make_tool_response(
        "propose_merge_candidates",
        {"groups": [{"names": [t.name for t in g.topics]} for g in groups]},
    )


def make_merges_response(merge: TopicMerge | None) -> SimpleNamespace:
    """
    Build a minimal fake OpenAI response carrying a record_merges tool call.
    """
    if merge:
        args = {"target": merge.target.name, "sources": [s.name for s in merge.sources.topics]}
    else:
        args = {"target": "", "sources": []}
    return make_tool_response("record_merges", args)


def make_parent_candidates_response(candidates: list[ParentCandidate]) -> SimpleNamespace:
    """
    Build a minimal fake OpenAI response carrying a propose_parent_candidates tool call.
    """
    return make_tool_response(
        "propose_parent_candidates",
        {"candidates": [{"parent": c.parent, "children": [t.name for t in c.children.topics]} for c in candidates]},
    )


def make_parent_response(addition: ParentAddition) -> SimpleNamespace:
    """
    Build a minimal fake OpenAI response carrying a record_parent tool call.
    """
    return make_tool_response(
        "record_parent",
        {
            "parent": addition.parent.name,
            "description": addition.parent.description,
            "children": [t.name for t in addition.children.topics],
        },
    )


def make_label_response(topics: list[Label]) -> SimpleNamespace:
    """
    Build a minimal fake OpenAI response carrying a record_labeled_topics tool call.
    """
    return make_tool_response(
        "record_labeled_topics",
        {"topics": [t.model_dump() for t in topics]},
    )
