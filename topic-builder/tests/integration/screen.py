"""
Integration test for the `topicbuilder screen` subcommand.

Run with:
    python -m tests.integration.screen
"""

import csv
import tempfile
from pathlib import Path

from tests.integration.helpers import run_subcommand


def run() -> None:
    """
    Scan a temp directory tree with the screen subcommand and assert the output CSV is correct.
    """
    with tempfile.TemporaryDirectory() as input_dir:
        root = Path(input_dir)
        (root / "a.txt").write_text("content a", encoding="utf-8")
        (root / "b.csv").write_text("should be ignored", encoding="utf-8")
        nested = root / "nested"
        nested.mkdir()
        (nested / "c.md").write_text("content c", encoding="utf-8")

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_out:
            output_path = Path(tmp_out.name)

        try:
            result = run_subcommand(
                "screen",
                {"--input-dir": str(root), "--output-path": str(output_path)},
            )

            assert result.returncode == 0, f"Command failed:\n{result.stderr}"

            with output_path.open(encoding="utf-8", newline="") as f:
                rows = {row["id"]: row["content"] for row in csv.DictReader(f)}

            assert rows == {
                str(root / "a.txt"): "content a",
                str(nested / "c.md"): "content c",
            }, f"Unexpected rows: {rows}"

            print(f"OK — {len(rows)} file(s) written to {output_path}.")

        finally:
            output_path.unlink(missing_ok=True)

    return None


if __name__ == "__main__":
    run()
