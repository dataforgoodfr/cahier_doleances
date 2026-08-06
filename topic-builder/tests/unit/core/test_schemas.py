import pytest
from pydantic import ValidationError

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

# --- Topic ---


def test_topic_instantiation_stores_fields():
    t = Topic(name="n", description="d")
    assert t.name == "n"
    assert t.description == "d"
    assert t.parent is None


def test_topic_parent_can_be_set():
    from uuid import uuid4

    parent_id = uuid4()
    t = Topic(name="n", description="d", parent=parent_id)
    assert t.parent == parent_id


def test_topic_validated_defaults_to_false():
    t = Topic(name="n", description="d")
    assert t.validated is False


def test_topic_validated_roundtrip():
    t = Topic(name="n", description="d", validated=True)
    raw = t.model_dump()
    result = Topic.model_validate(raw)
    assert result.validated is True


def test_topic_validated_missing_field_defaults_to_false():
    raw = {"name": "n", "description": "d"}
    t = Topic.model_validate(raw)
    assert t.validated is False


def test_topic_level_defaults_to_zero():
    t = Topic(name="n", description="d")
    assert t.level == 0


def test_topic_level_can_be_set():
    t = Topic(name="n", description="d", level=2)
    assert t.level == 2


def test_topic_level_roundtrip():
    t = Topic(name="n", description="d", level=3)
    raw = t.model_dump()
    result = Topic.model_validate(raw)
    assert result.level == 3


def test_topic_level_missing_field_defaults_to_zero():
    raw = {"name": "n", "description": "d"}
    t = Topic.model_validate(raw)
    assert t.level == 0


@pytest.mark.parametrize("missing_field", ["name", "description"])
def test_topic_raises_on_missing_field(missing_field: str):
    fields = {"name": "n", "description": "d"}
    del fields[missing_field]
    with pytest.raises(ValidationError):
        Topic(**fields)


# --- TopicConfig ---


def test_topicconfig_wraps_topic_list(taxonomy):
    assert len(taxonomy.topics) == 2


def test_topicconfig_accepts_empty_list():
    tc = Taxonomy(topics=[])
    assert tc.topics == []


def test_topicconfig_model_validate_roundtrip(taxonomy):
    raw = taxonomy.model_dump()
    result = Taxonomy.model_validate(raw)
    assert result == taxonomy


@pytest.mark.parametrize(
    "bad_payload",
    [
        {"topics": [{"name": "n"}]},
        {"topics": "not-a-list"},
        {},
    ],
)
def test_topicconfig_raises_on_invalid_payload(bad_payload: dict):
    with pytest.raises(ValidationError):
        Taxonomy.model_validate(bad_payload)


# --- LabeledTopic ---


def test_labeled_topic_instantiation_stores_fields():
    t = Label(name="n", rationale="s", extract="e")
    assert t.name == "n"
    assert t.rationale == "s"
    assert t.extract == "e"


@pytest.mark.parametrize("missing_field", ["name", "rationale", "extract"])
def test_labeled_topic_raises_on_missing_field(missing_field: str):
    fields = {"name": "n", "rationale": "s", "extract": "e"}
    del fields[missing_field]
    with pytest.raises(ValidationError):
        Label(**fields)


# --- DocumentLabels / LabeledDataset ---


def test_document_labels_stores_id_and_labels(labeled_topics):
    dl = DocumentLabels(id="doc1", labels=labeled_topics)
    assert dl.id == "doc1"
    assert dl.labels == labeled_topics


def test_labeled_dataset_wraps_documents(labeled_topics):
    dl = DocumentLabels(id="doc1", labels=labeled_topics)
    ds = LabeledDataset(documents=[dl])
    assert len(ds.documents) == 1
    assert ds.documents[0].id == "doc1"


def test_labeled_dataset_roundtrip(labeled_topics):
    dl = DocumentLabels(id="doc1", labels=labeled_topics)
    raw = LabeledDataset(documents=[dl]).model_dump()
    result = LabeledDataset.model_validate(raw)
    assert result.documents[0].labels == labeled_topics


def test_factorize_report_stores_merges(merge_report):
    assert len(merge_report.merges) == 1


def test_factorize_report_roundtrip(merge_report):
    raw = merge_report.model_dump()
    result = FactorizeReport.model_validate(raw)
    assert result == merge_report


def test_structure_report_stores_parents_added(structure_report):
    assert len(structure_report.parents_added) == 1


def test_structure_report_roundtrip(structure_report):
    raw = structure_report.model_dump()
    result = ParentDiscoveryReport.model_validate(raw)
    assert result == structure_report


def test_topic_merge_stores_fields():
    m = TopicMerge(
        sources=Taxonomy(topics=[Topic(name="B", description="d"), Topic(name="C", description="d")]),
        target=Topic(name="A", description="d"),
    )
    assert m.target.name == "A"
    assert [s.name for s in m.sources.topics] == ["B", "C"]


def test_parent_addition_stores_fields():
    children = Taxonomy(topics=[Topic(name="A", description="d"), Topic(name="B", description="d")])
    pa = ParentAddition(parent=Topic(name="P", description="d"), children=children)
    assert pa.parent.name == "P"
    assert [t.name for t in pa.children.topics] == ["A", "B"]
