"""
Integration test for the `topicbuilder label` subcommand.

Run with:
    python -m tests.integration.label
"""

import json
import tempfile
from pathlib import Path

import yaml

from tests.integration.conftest import MOCK_FIND_RESPONSE, MockVllmServer
from tests.integration.helpers import load_json, run_subcommand

DATASET_PATH = Path(__file__).parent.parent / "data" / "dataset.csv"
TAXONOMY_PATH = Path(__file__).parent.parent / "data" / "topics_config.json"
PROMPTS_DIR = Path(__file__).resolve().parents[2] / "conf" / "prompts"


def _expected_labeled_topics() -> list[dict]:
    """
    Extract expected labeled topics from the mock find response fixture.
    """
    args = json.loads(MOCK_FIND_RESPONSE["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"])
    return args["topics"]


def run() -> None:
    """
    Start the mock vLLM server, invoke label, and assert the labeled output is correct.
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
            "label",
            {
                "--dataset-path": str(DATASET_PATH),
                "--taxonomy-path": str(TAXONOMY_PATH),
                "--llm-config-path": str(llm_config_path),
                "--prompt-path": str(PROMPTS_DIR / "label.md"),
                "--output-path": str(output_path),
            },
        )

        assert result.returncode == 0, f"Command failed:\n{result.stderr}"

        expected = _expected_labeled_topics()
        output = load_json(output_path)

        assert "documents" in output, "Output JSON missing 'documents' key"
        labeled_names = {label["name"] for doc in output["documents"] for label in doc["labels"]}
        expected_names = {t["name"] for t in expected}
        assert expected_names <= labeled_names, (
            f"Expected topics missing from output: {expected_names - labeled_names}"
        )

        print(f"OK — {len(output['documents'])} document(s) labeled.")

    finally:
        server.stop()
        llm_config_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)

    return None


if __name__ == "__main__":
    run()
