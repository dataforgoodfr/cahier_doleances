"""
Integration test for the `topicbuilder discover-parents` subcommand.

Run with:
    python -m tests.integration.discover_parents
"""

import json
import tempfile
from pathlib import Path

import yaml

from tests.integration.conftest import MOCK_PARENT_RESPONSE, MockVllmServer
from tests.integration.helpers import load_json, run_subcommand

TAXONOMY_PATH = Path(__file__).parent.parent / "data" / "topics_config.json"
PROMPTS_DIR = Path(__file__).resolve().parents[2] / "conf" / "prompts" / "discover_parents"


def _expected_parent() -> dict:
    """
    Extract the expected parent addition from the mock parent response fixture.
    """
    return json.loads(MOCK_PARENT_RESPONSE["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"])


def run() -> None:
    """
    Start the mock vLLM server, invoke discover-parents, and assert the output taxonomy and report are correct.
    """
    server = MockVllmServer()
    server.start()

    with (
        tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as tmp_cfg,
        tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_out,
        tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_report,
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
        report_path = Path(tmp_report.name)

    try:
        result = run_subcommand(
            "discover-parents",
            {
                "--taxonomy-path": str(TAXONOMY_PATH),
                "--llm-config-path": str(llm_config_path),
                "--prompts-dir": str(PROMPTS_DIR),
                "--output-path": str(output_path),
                "--report-path": str(report_path),
            },
        )

        assert result.returncode == 0, f"Command failed:\n{result.stderr}"

        report = load_json(report_path)
        assert "parents_added" in report, "Report JSON missing 'parents_added' key"

        output = load_json(output_path)
        assert "topics" in output, "Output JSON missing 'topics' key"

        expected = _expected_parent()
        addition = next((p for p in report["parents_added"] if p["parent"]["name"] == expected["parent"]), None)
        assert addition is not None, f"Parent '{expected['parent']}' missing from report"

        children_names = {t["name"] for t in addition["children"]["topics"]}
        assert children_names, "Parent addition has no children recorded"

        parent_id = next(t["id"] for t in output["topics"] if t["name"] == expected["parent"])
        assert all(t["parent"] == parent_id for t in output["topics"] if t["name"] in children_names)

        print(f"OK — {len(output['topics'])} topic(s) in output, {len(report['parents_added'])} parent(s) added.")

    finally:
        server.stop()
        llm_config_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        report_path.unlink(missing_ok=True)

    return None


if __name__ == "__main__":
    run()
