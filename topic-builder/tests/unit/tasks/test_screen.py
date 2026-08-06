import csv

import pytest

from topicbuilder.tasks.screen import collect_paths, write_dataset


@pytest.mark.parametrize(
    "filenames,expected_names",
    [
        (["a.txt", "b.md", "c.py"], ["a.txt", "b.md"]),
        ([], []),
        (["b.txt", "a.txt"], ["a.txt", "b.txt"]),
    ],
)
def test_collect_paths_filters_and_sorts_matching_files(tmp_path, filenames, expected_names):
    for name in filenames:
        (tmp_path / name).write_text("text")
    paths = collect_paths(tmp_path)
    assert [p.name for p in paths] == expected_names


def test_collect_paths_recurses_into_subdirectories(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.txt").write_text("nested")
    paths = collect_paths(tmp_path)
    assert any(p.name == "nested.txt" for p in paths)


@pytest.mark.parametrize("contents", [["hello"], ["content 0", "content 1", "content 2"]])
def test_write_dataset_writes_id_and_content_per_file(tmp_path, contents):
    files = []
    for i, content in enumerate(contents):
        p = tmp_path / f"f{i}.txt"
        p.write_text(content)
        files.append(p)
    out = tmp_path / "out.csv"
    write_dataset(files, out)
    rows = list(csv.DictReader(out.read_text(encoding="utf-8").splitlines()))
    assert [r["id"] for r in rows] == [str(f) for f in files]
    assert [r["content"] for r in rows] == contents


def test_write_dataset_creates_parent_directories(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("x")
    out = tmp_path / "nested" / "dir" / "out.csv"
    write_dataset([f], out)
    assert out.exists()
