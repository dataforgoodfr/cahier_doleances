from pathlib import Path

import pytest

from topicbuilder.tasks.discover_parents import PARENT_GENERATION_TOOL, PARENT_VALIDATION_TOOL
from topicbuilder.tasks.discover_topics import DISCOVER_TOPICS_TOOL
from topicbuilder.tasks.factorize import MERGE_GENERATION_TOOL, MERGE_VALIDATION_TOOL
from topicbuilder.tasks.label import LABEL_TOOL

PROMPTS_DIR = Path(__file__).resolve().parents[3] / "conf" / "prompts"

PROMPT_PATHS = [
    PROMPTS_DIR / "discover_topics.md",
    PROMPTS_DIR / "factorize" / "merge_generation.md",
    PROMPTS_DIR / "factorize" / "merge_validation.md",
    PROMPTS_DIR / "discover_parents" / "parent_generation.md",
    PROMPTS_DIR / "discover_parents" / "parent_validation.md",
    PROMPTS_DIR / "label.md",
]

# (tool schema, expected function name, expected fields, array property holding those fields as items, or None)
TOOL_SCHEMAS = [
    (DISCOVER_TOPICS_TOOL, "record_new_topics", ["name", "description"], "topics"),
    (MERGE_GENERATION_TOOL, "propose_merge_candidates", ["names"], "groups"),
    (MERGE_VALIDATION_TOOL, "record_merges", ["target", "sources"], None),
    (PARENT_GENERATION_TOOL, "propose_parent_candidates", ["parent", "children"], "candidates"),
    (PARENT_VALIDATION_TOOL, "record_parent", ["parent", "description", "children"], None),
    (LABEL_TOOL, "record_labeled_topics", ["name", "rationale", "extract"], "topics"),
]


@pytest.mark.parametrize("prompt_path", PROMPT_PATHS, ids=[p.name for p in PROMPT_PATHS])
def test_prompt_file_is_non_empty(prompt_path: Path):
    """
    Checks that a prompt markdown file holds non-empty text content.
    """
    content = prompt_path.read_text(encoding="utf-8")
    assert isinstance(content, str) and len(content) > 0
    return


@pytest.mark.parametrize(
    "tool, expected_name, expected_fields, array_field",
    TOOL_SCHEMAS,
    ids=[schema[1] for schema in TOOL_SCHEMAS],
)
def test_tool_schema_is_well_formed(
    tool: dict, expected_name: str, expected_fields: list[str], array_field: str | None
):
    """
    Checks that a tool schema exposes the expected function name and declares its expected fields
    as required parameters, either directly or within the items of its required array property.
    """
    params = tool["function"]["parameters"]
    if array_field:
        assert array_field in params["required"]
        assert params["properties"][array_field]["type"] == "array"
        field_container = params["properties"][array_field]["items"]
    else:
        field_container = params
    assert tool["function"]["name"] == expected_name
    assert set(expected_fields) <= set(field_container["properties"])
    assert set(expected_fields) <= set(field_container["required"])
    return
