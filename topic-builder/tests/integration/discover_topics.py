"""
Integration test for the `topicbuilder discover_topics` subcommand.

Run with:
    python -m tests.integration.discover_topics
"""

import csv
import json
import tempfile
from pathlib import Path

import yaml

from tests.integration.conftest import MOCK_DISCOVER_TOPICS_RESPONSE, MockVllmServer
from tests.integration.helpers import load_json, run_subcommand

DATASET_PATH = Path(__file__).parent.parent / "data" / "dataset.csv"
TAXONOMY_PATH = Path(__file__).parent.parent / "data" / "topics_config.json"
PROMPTS_DIR = Path(__file__).resolve().parents[2] / "conf" / "prompts"


def _expected_new_topics() -> list[dict]:
    """
    Extract expected new topics from the mock discover_topics response fixture.
    """
    args = json.loads(MOCK_DISCOVER_TOPICS_RESPONSE["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"])
    return args["topics"]


def _dataset_ids() -> set[str]:
    """
    Return the set of text ids present in the dataset CSV used by this test.
    """
    with DATASET_PATH.open(encoding="utf-8") as f:
        return {row["id"] for row in csv.DictReader(f)}


def run() -> None:
    """
    Start the mock vLLM server, invoke discover_topics, and assert the output taxonomy is correct.
    """
    server = MockVllmServer()
    server.start()

    with (
        tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as tmp_cfg,
        tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_out,
    ):
        yaml.dump(
            {
                "backend": "default",
                "model": "mock-model",
                "pool_size": 2,
                "api_key_env_var": None,
                "endpoint_args": {"base_url": server.base_url},
            },
            tmp_cfg,
        )
        llm_config_path = Path(tmp_cfg.name)
        output_path = Path(tmp_out.name)

    try:
        result = run_subcommand(
            "discover-topics",
            {
                "--dataset-path": str(DATASET_PATH),
                "--taxonomy-path": str(TAXONOMY_PATH),
                "--llm-config-path": str(llm_config_path),
                "--prompt-path": str(PROMPTS_DIR / "discover_topics.md"),
                "--output-path": str(output_path),
            },
        )

        assert result.returncode == 0, f"Command failed:\n{result.stderr}"

        existing = load_json(TAXONOMY_PATH)
        output = load_json(output_path)
        expected_new = _expected_new_topics()

        assert "topics" in output, "Output JSON missing 'topics' key"
        assert len(output["topics"]) == len(existing["topics"]) + len(expected_new), (
            f"Expected {len(existing['topics']) + len(expected_new)} topics, got {len(output['topics'])}"
        )
        new_names = {t["name"] for t in expected_new}
        output_names = {t["name"] for t in output["topics"]}
        assert new_names <= output_names, f"New topics missing from output: {new_names - output_names}"

        dataset_ids = _dataset_ids()
        new_topics_by_name = {t["name"]: t for t in output["topics"] if t["name"] in new_names}
        for name, topic in new_topics_by_name.items():
            assert topic["sources"], f"Topic {name!r} has no source text ids"
            assert set(topic["sources"]) <= dataset_ids, f"Topic {name!r} has unknown source ids: {topic['sources']}"

        print(f"OK — {len(output['topics'])} topic(s) in output ({len(expected_new)} new).")

    finally:
        server.stop()
        llm_config_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)

    return None


if __name__ == "__main__":
    run()
