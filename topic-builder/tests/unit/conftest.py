import pytest

from topicbuilder.core.schemas import (
    FactorizeReport,
    Label,
    ParentAddition,
    ParentDiscoveryReport,
    Taxonomy,
    Topic,
    TopicMerge,
)


@pytest.fixture
def topic() -> Topic:
    return Topic(
        name="Water Cycle",
        description="The continuous movement of water through the environment.",
    )


@pytest.fixture
def topic_config(topic: Topic) -> Taxonomy:
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
