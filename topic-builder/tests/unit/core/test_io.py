import json

import pytest

from topicbuilder.core.io import read_dataset, read_labeled_dataset, read_taxonomy, read_text, write_json
from topicbuilder.core.schemas import DocumentLabels, LabeledDataset, Taxonomy


def test_read_text_returns_file_contents(tmp_path):
    p = tmp_path / "doc.txt"
    p.write_text("hello world", encoding="utf-8")
    assert read_text(p) == "hello world"


def test_read_text_preserves_unicode(tmp_path):
    p = tmp_path / "doc.txt"
    p.write_text("café naïve", encoding="utf-8")
    assert read_text(p) == "café naïve"


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


def test_write_json_produces_valid_json(tmp_path, taxonomy):
    out = tmp_path / "out.json"
    write_json(taxonomy, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "topics" in data


def test_write_json_creates_parent_directories(tmp_path, taxonomy):
    out = tmp_path / "nested" / "dir" / "out.json"
    write_json(taxonomy, out)
    assert out.exists()


def test_write_json_serialises_all_fields(tmp_path, merge_report):
    out = tmp_path / "report.json"
    write_json(merge_report, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "merges" in data


def test_write_json_empty_topics(tmp_path):
    out = tmp_path / "out.json"
    write_json(Taxonomy(topics=[]), out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["topics"] == []


def test_read_dataset_returns_documents(tmp_path):
    p = tmp_path / "data.csv"
    p.write_text("id,content\ndoc1,hello world\n", encoding="utf-8")
    docs = read_dataset(p)
    assert len(docs) == 1
    assert docs[0].id == "doc1"
    assert docs[0].content == "hello world"


def test_read_dataset_returns_multiple_rows(tmp_path):
    p = tmp_path / "data.csv"
    rows = "id,content\n" + "\n".join(f"doc{i},text{i}" for i in range(5))
    p.write_text(rows, encoding="utf-8")
    assert len(read_dataset(p)) == 5


def test_read_dataset_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_dataset(tmp_path / "missing.csv")


def test_read_labeled_dataset_roundtrip(tmp_path, labeled_topics):
    dataset = LabeledDataset(documents=[DocumentLabels(id="doc1", labels=labeled_topics)])
    out = tmp_path / "labels.json"
    write_json(dataset, out)
    result = read_labeled_dataset(out)
    assert result == dataset


def test_read_labeled_dataset_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_labeled_dataset(tmp_path / "missing.json")
