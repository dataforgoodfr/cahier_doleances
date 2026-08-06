"""
Integration test for the `topicbuilder factorize` subcommand.

Run with:
    python -m tests.integration.factorize
"""

import json
import tempfile
from pathlib import Path

import yaml

from tests.integration.conftest import MOCK_MERGES_RESPONSE, MockVllmServer
from tests.integration.helpers import load_json, run_subcommand

TAXONOMY_PATH = Path(__file__).parent.parent / "data" / "topics_config.json"
PROMPTS_DIR = Path(__file__).resolve().parents[2] / "conf" / "prompts" / "factorize"


def _expected_merge() -> dict:
    """
    Extract the expected merge from the mock merges response fixture.
    """
    return json.loads(MOCK_MERGES_RESPONSE["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"])


def run() -> None:
    """
    Start the mock vLLM server, invoke factorize, and assert the output taxonomy and report are correct.
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
            "factorize",
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
        assert "merges" in report, "Report JSON missing 'merges' key"

        output = load_json(output_path)
        assert "topics" in output, "Output JSON missing 'topics' key"

        # merged-away sources must not appear in the output
        merged_away = {t["name"] for m in report["merges"] for t in m["sources"]["topics"]}
        output_names = {t["name"] for t in output["topics"]}
        assert not merged_away & output_names, f"Merged-away topics still present: {merged_away & output_names}"

        # the merge from the mock must appear in the report
        expected = _expected_merge()
        merge_entry = next((m for m in report["merges"] if m["target"]["name"] == expected["target"]), None)
        assert merge_entry is not None, f"Merge target '{expected['target']}' missing from report"
        assert expected["sources"][0] in {t["name"] for t in merge_entry["sources"]["topics"]}

        print(f"OK — {len(output['topics'])} topic(s) in output, {len(report['merges'])} merge(s).")

    finally:
        server.stop()
        llm_config_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        report_path.unlink(missing_ok=True)

    return None


if __name__ == "__main__":
    run()
