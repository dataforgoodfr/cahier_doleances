from topicbuilder.app.cli import _build_labels_index
from topicbuilder.core.schemas import DocumentLabels, Label, LabeledDataset


def test_build_labels_index_returns_empty_dict_for_none():
    assert _build_labels_index(None) == {}


def test_build_labels_index_returns_empty_dict_when_no_documents():
    assert _build_labels_index(LabeledDataset(documents=[])) == {}


def test_build_labels_index_groups_labels_by_topic_name_across_documents():
    dataset = LabeledDataset(
        documents=[
            DocumentLabels(id="d1", labels=[Label(name="A", rationale="r1", extract="e1")]),
            DocumentLabels(
                id="d2",
                labels=[
                    Label(name="A", rationale="r2", extract="e2"),
                    Label(name="B", rationale="r3", extract="e3"),
                ],
            ),
        ]
    )
    index = _build_labels_index(dataset)
    assert [label.rationale for label in index["A"]] == ["r1", "r2"]
    assert [label.rationale for label in index["B"]] == ["r3"]
