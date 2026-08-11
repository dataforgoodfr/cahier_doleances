import pytest

from topicbuilder.core.clustering import ClusteringConfig
from topicbuilder.core.schemas import (
    FactorizeReport,
    Label,
    ParentAddition,
    ParentDiscoveryReport,
    Taxonomy,
    Topic,
    TopicMerge,
)
from topicbuilder.tasks import discover_parents, factorize


def stub_clusterize_taxonomy_by_level(taxonomy: Taxonomy, config: ClusteringConfig) -> list[Taxonomy]:
    """
    Stand in for clusterize_taxonomy_by_level: group topics by level only, with no embedding
    or clustering involved. Tests that need multiple chunks within a level should override
    this stub via `monkeypatch.setattr` on the relevant task module.
    """
    levels = sorted({t.level for t in taxonomy.topics})
    return [Taxonomy(topics=[t for t in taxonomy.topics if t.level == lvl]) for lvl in levels]


@pytest.fixture
def clustering_config(monkeypatch: pytest.MonkeyPatch) -> ClusteringConfig:
    """
    Return a valid ClusteringConfig and stub clusterize_taxonomy_by_level across task modules,
    so tests requesting this fixture never invoke the real embedding/UMAP/HDBSCAN pipeline.
    """
    monkeypatch.setattr(discover_parents, "clusterize_taxonomy_by_level", stub_clusterize_taxonomy_by_level)
    monkeypatch.setattr(factorize, "clusterize_taxonomy_by_level", stub_clusterize_taxonomy_by_level)
    return ClusteringConfig.from_config("tests/conf/test_clustering.yaml")


@pytest.fixture
def topic() -> Topic:
    return Topic(
        name="Water Cycle",
        description="The continuous movement of water through the environment.",
    )


@pytest.fixture
def taxonomy(topic: Topic) -> Taxonomy:
    return Taxonomy(
        topics=[
            topic,
            Topic(
                name="Photosynthesis",
                description="The process by which plants convert sunlight and CO2 into glucose.",
            ),
        ]
    )


@pytest.fixture
def labeled_topic() -> Label:
    return Label(
        name="Water Cycle",
        rationale="The text explains the stages of the water cycle.",
        extract="Evaporation drives water from oceans and lakes into the atmosphere.",
    )


@pytest.fixture
def labeled_topics(labeled_topic: Label) -> list[Label]:
    return [
        labeled_topic,
        Label(
            name="Photosynthesis",
            rationale="The text describes how plants convert sunlight into energy.",
            extract="Plants convert sunlight, carbon dioxide, and water into glucose.",
        ),
    ]


@pytest.fixture
def merge_report() -> FactorizeReport:
    return FactorizeReport(
        merges=[
            TopicMerge(
                sources=Taxonomy(topics=[Topic(name="Hydrological Cycle", description="d")]),
                target=Topic(name="Water Cycle", description="d"),
            )
        ],
    )


@pytest.fixture
def structure_report() -> ParentDiscoveryReport:
    return ParentDiscoveryReport(
        parents_added=[
            ParentAddition(
                parent=Topic(name="Earth Sciences", description=""),
                children=Taxonomy(
                    topics=[Topic(name="Water Cycle", description=""), Topic(name="Soil Composition", description="")]
                ),
            )
        ],
    )
