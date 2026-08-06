"""
Shared helper functions for integration tests.
"""

import json
import subprocess
import sys
from pathlib import Path


def run_subcommand(
    subcommand: str,
    options: dict[str, str],
) -> subprocess.CompletedProcess:
    """
    Spawn `topicbuilder <subcommand>` as a subprocess and return the result.
    """
    cmd = [sys.executable, "-m", "topicbuilder", subcommand]
    for key, value in options.items():
        cmd += [key, str(value)]
    return subprocess.run(cmd, capture_output=True, text=True)


def load_json(path: Path) -> dict:
    """
    Read and parse a JSON file, returning the decoded object.
    """
    return json.loads(path.read_text(encoding="utf-8"))
