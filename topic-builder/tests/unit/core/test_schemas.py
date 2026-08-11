from uuid import uuid4

import pytest

from topicbuilder.core.schemas import (
    DocumentLabels,
    FactorizeReport,
    Label,
    LabeledDataset,
    ParentAddition,
    ParentDiscoveryReport,
    Taxonomy,
    Topic,
    TopicMerge,
)


def test_topic_construction_stores_required_fields_and_optional_defaults():
    t = Topic(name="n", description="d")
    assert t.name == "n"
    assert t.description == "d"
    assert t.parent is None
    assert t.validated is False
    assert t.level == 0
    assert t.sources == []


@pytest.mark.parametrize(
    "field, value",
    [("parent", uuid4()), ("validated", True), ("level", 2), ("sources", ["doc1", "doc2"])],
)
def test_topic_optional_fields_can_be_overridden(field: str, value):
    t = Topic(name="n", description="d", **{field: value})
    assert getattr(t, field) == value


@pytest.mark.parametrize(
    "field, value",
    [("parent", uuid4()), ("validated", True), ("level", 3), ("sources", ["doc1"])],
)
def test_topic_model_validate_roundtrips_optional_fields(field: str, value):
    t = Topic(name="n", description="d", **{field: value})
    result = Topic.model_validate(t.model_dump())
    assert getattr(result, field) == value


def test_taxonomy_wraps_topic_list(taxonomy: Taxonomy):
    assert len(taxonomy.topics) == 2


def test_taxonomy_model_validate_roundtrip(taxonomy: Taxonomy):
    result = Taxonomy.model_validate(taxonomy.model_dump())
    assert result == taxonomy


def test_label_construction_stores_fields():
    label = Label(name="n", rationale="s", extract="e")
    assert label.name == "n"
    assert label.rationale == "s"
    assert label.extract == "e"


def test_document_labels_stores_id_and_labels(labeled_topics: list[Label]):
    dl = DocumentLabels(id="doc1", labels=labeled_topics)
    assert dl.id == "doc1"
    assert dl.labels == labeled_topics


def test_labeled_dataset_wraps_documents_and_roundtrips(labeled_topics: list[Label]):
    dl = DocumentLabels(id="doc1", labels=labeled_topics)
    ds = LabeledDataset(documents=[dl])
    assert len(ds.documents) == 1
    assert ds.documents[0].id == "doc1"
    result = LabeledDataset.model_validate(ds.model_dump())
    assert result.documents[0].labels == labeled_topics


def test_factorize_report_stores_merges_and_roundtrips(merge_report: FactorizeReport):
    assert len(merge_report.merges) == 1
    result = FactorizeReport.model_validate(merge_report.model_dump())
    assert result == merge_report


def test_structure_report_stores_parents_added_and_roundtrips(structure_report: ParentDiscoveryReport):
    assert len(structure_report.parents_added) == 1
    result = ParentDiscoveryReport.model_validate(structure_report.model_dump())
    assert result == structure_report


def test_topic_merge_stores_sources_and_target():
    m = TopicMerge(
        sources=Taxonomy(topics=[Topic(name="B", description="d"), Topic(name="C", description="d")]),
        target=Topic(name="A", description="d"),
    )
    assert m.target.name == "A"
    assert [s.name for s in m.sources.topics] == ["B", "C"]


def test_parent_addition_stores_parent_and_children():
    children = Taxonomy(topics=[Topic(name="A", description="d"), Topic(name="B", description="d")])
    pa = ParentAddition(parent=Topic(name="P", description="d"), children=children)
    assert pa.parent.name == "P"
    assert [t.name for t in pa.children.topics] == ["A", "B"]
