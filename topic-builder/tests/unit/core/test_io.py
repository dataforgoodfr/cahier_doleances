import json

import pytest

from topicbuilder.core.io import read_dataset, read_labeled_dataset, read_taxonomy, read_text, write_json
from topicbuilder.core.schemas import DocumentLabels, LabeledDataset


@pytest.mark.parametrize("content", ["hello world", "café naïve"])
def test_read_text_returns_file_contents(tmp_path, content):
    p = tmp_path / "doc.txt"
    p.write_text(content, encoding="utf-8")
    assert read_text(p) == content


def test_read_text_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_text(tmp_path / "missing.txt")


def test_read_taxonomy_roundtrip(tmp_path, taxonomy):
    out = tmp_path / "out.json"
    write_json(taxonomy, out)
    assert read_taxonomy(out) == taxonomy


def test_read_taxonomy_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_taxonomy(tmp_path / "missing.json")


@pytest.mark.parametrize("model_fixture", ["taxonomy", "merge_report"])
def test_write_json_serialises_model(tmp_path, request, model_fixture):
    model = request.getfixturevalue(model_fixture)
    out = tmp_path / "out.json"
    write_json(model, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data == model.model_dump(mode="json")


def test_write_json_creates_parent_directories(tmp_path, taxonomy):
    out = tmp_path / "nested" / "dir" / "out.json"
    write_json(taxonomy, out)
    assert out.exists()


@pytest.mark.parametrize(
    "rows, expected",
    [
        ("id,content\ndoc1,hello world\n", [("doc1", "hello world")]),
        (
            "id,content\n" + "\n".join(f"doc{i},text{i}" for i in range(5)),
            [(f"doc{i}", f"text{i}") for i in range(5)],
        ),
    ],
)
def test_read_dataset_returns_documents(tmp_path, rows, expected):
    p = tmp_path / "data.csv"
    p.write_text(rows, encoding="utf-8")
    docs = read_dataset(p)
    assert [(d.id, d.content) for d in docs] == expected


def test_read_dataset_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_dataset(tmp_path / "missing.csv")


def test_read_labeled_dataset_roundtrip(tmp_path, labeled_topics):
    dataset = LabeledDataset(documents=[DocumentLabels(id="doc1", labels=labeled_topics)])
    out = tmp_path / "labels.json"
    write_json(dataset, out)
    assert read_labeled_dataset(out) == dataset


def test_read_labeled_dataset_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_labeled_dataset(tmp_path / "missing.json")
