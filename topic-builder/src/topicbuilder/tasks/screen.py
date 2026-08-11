import csv
from pathlib import Path

import typer


def screen(
    input_dir: Path = typer.Option(
        ...,
        "--input-dir",
        exists=True,
        file_okay=False,
        help="Directory to scan recursively for .txt and .md files.",
    ),
    output_path: Path = typer.Option(
        ...,
        "--output-path",
        help="Path where the output CSV will be written.",
    ),
) -> None:
    """
    Recursively find all .txt and .md files under `input_dir` and write a CSV
    with their paths as 'id' and their text content as 'content'.
    """
    paths = collect_paths(input_dir)
    write_dataset(paths, output_path)
    typer.echo(f"Wrote {len(paths)} file(s) to {output_path}.")
    return


def collect_paths(root: Path) -> list[Path]:
    """
    Recursively collect all .txt and .md files under `root`, sorted for determinism.
    """
    return sorted(p for ext in ("*.txt", "*.md") for p in root.rglob(ext))


def write_dataset(paths: list[Path], output_path: Path) -> None:
    """
    Write a CSV with 'id' (file path as string) and 'content' (file text) columns.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "content"])
        writer.writeheader()
        writer.writerows({"id": str(p), "content": p.read_text(encoding="utf-8")} for p in paths)
    return
