"""Unit tests for PDF discovery helpers."""

from pathlib import Path

import pytest

from cahier_doleances.extraction.discovery import (
    _natural_sort_key,
    first_pdf,
    list_pdfs,
    require_path_to_data,
)


def test_natural_sort_key_handles_numbers():
    p1 = Path("page_2.pdf")
    p2 = Path("page_10.pdf")
    assert _natural_sort_key(p1) < _natural_sort_key(p2)


def test_list_pdfs_returns_only_pdf_files(tmp_path: Path):
    (tmp_path / "a.pdf").touch()
    (tmp_path / "b.txt").touch()
    (tmp_path / "c.pdf").touch()

    result = list_pdfs(tmp_path)
    assert [p.name for p in result] == ["a.pdf", "c.pdf"]


def test_list_pdfs_sorts_naturally(tmp_path: Path):
    (tmp_path / "page_10.pdf").touch()
    (tmp_path / "page_2.pdf").touch()
    (tmp_path / "page_1.pdf").touch()

    result = list_pdfs(tmp_path)
    assert [p.name for p in result] == ["page_1.pdf", "page_2.pdf", "page_10.pdf"]


def test_list_pdfs_raises_when_directory_does_not_exist():
    with pytest.raises(FileNotFoundError):
        list_pdfs("/does/not/exist")


def test_list_pdfs_raises_when_not_a_directory(tmp_path: Path):
    file = tmp_path / "not_a_dir.pdf"
    file.touch()
    with pytest.raises(NotADirectoryError):
        list_pdfs(file)


def test_list_pdfs_raises_when_no_pdf_found(tmp_path: Path):
    with pytest.raises(ValueError):
        list_pdfs(tmp_path)


def test_first_pdf_returns_first_sorted_pdf(tmp_path: Path):
    (tmp_path / "z.pdf").touch()
    (tmp_path / "a.pdf").touch()

    assert first_pdf(tmp_path).name == "a.pdf"


def test_first_pdf_raises_when_no_pdf_found(tmp_path: Path):
    with pytest.raises(ValueError):
        first_pdf(tmp_path)


def test_require_path_to_data_uses_setting(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "cahier_doleances.extraction.discovery.settings.path_to_data",
        str(tmp_path),
    )
    assert require_path_to_data() == tmp_path


def test_require_path_to_data_raises_when_empty(monkeypatch):
    monkeypatch.setattr(
        "cahier_doleances.extraction.discovery.settings.path_to_data",
        "",
    )
    with pytest.raises(ValueError):
        require_path_to_data()
