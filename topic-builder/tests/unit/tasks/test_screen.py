import csv

from topicbuilder.tasks.screen import collect_paths, write_dataset


def test_collect_paths_finds_txt_and_md_files(tmp_path):
    (tmp_path / "a.txt").write_text("text a")
    (tmp_path / "b.md").write_text("text b")
    (tmp_path / "c.py").write_text("not included")
    paths = collect_paths(tmp_path)
    names = [p.name for p in paths]
    assert "a.txt" in names
    assert "b.md" in names
    assert "c.py" not in names


def test_collect_paths_recurses_into_subdirectories(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.txt").write_text("nested")
    paths = collect_paths(tmp_path)
    assert any(p.name == "nested.txt" for p in paths)


def test_collect_paths_returns_sorted_paths(tmp_path):
    (tmp_path / "b.txt").write_text("")
    (tmp_path / "a.txt").write_text("")
    paths = collect_paths(tmp_path)
    assert paths == sorted(paths)


def test_collect_paths_returns_empty_for_empty_directory(tmp_path):
    assert collect_paths(tmp_path) == []


def test_write_dataset_writes_id_and_content_columns(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("hello")
    out = tmp_path / "out.csv"
    write_dataset([f], out)
    rows = list(csv.DictReader(out.read_text(encoding="utf-8").splitlines()))
    assert rows[0]["id"] == str(f)
    assert rows[0]["content"] == "hello"


def test_write_dataset_creates_parent_directories(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("x")
    out = tmp_path / "nested" / "dir" / "out.csv"
    write_dataset([f], out)
    assert out.exists()


def test_write_dataset_writes_one_row_per_file(tmp_path):
    files = []
    for i in range(3):
        p = tmp_path / f"f{i}.txt"
        p.write_text(f"content {i}")
        files.append(p)
    out = tmp_path / "out.csv"
    write_dataset(files, out)
    rows = list(csv.DictReader(out.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 3
