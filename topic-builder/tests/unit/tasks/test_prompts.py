from pathlib import Path

import pytest

from topicbuilder.tasks.discover_parents import PARENT_GENERATION_TOOL, PARENT_VALIDATION_TOOL
from topicbuilder.tasks.discover_topics import DISCOVER_TOPICS_TOOL
from topicbuilder.tasks.factorize import MERGE_GENERATION_TOOL, MERGE_VALIDATION_TOOL
from topicbuilder.tasks.label import LABEL_TOOL

PROMPTS_DIR = Path(__file__).resolve().parents[3] / "conf" / "prompts"
FACTORIZE_PROMPTS_DIR = PROMPTS_DIR / "factorize"
DISCOVER_PARENTS_PROMPTS_DIR = PROMPTS_DIR / "discover_parents"


def test_discover_topics_prompt_is_non_empty_string():
    content = (PROMPTS_DIR / "discover_topics.md").read_text(encoding="utf-8")
    assert isinstance(content, str) and len(content) > 0


@pytest.mark.parametrize("keyword", ["name", "description"])
def test_discover_topics_prompt_mentions_required_fields(keyword: str):
    content = (PROMPTS_DIR / "discover_topics.md").read_text(encoding="utf-8")
    assert keyword in content


def test_discover_topics_tool_function_name():
    assert DISCOVER_TOPICS_TOOL["function"]["name"] == "record_new_topics"


@pytest.mark.parametrize("field", ["name", "description"])
def test_discover_topics_tool_schema_includes_field(field: str):
    item_props = DISCOVER_TOPICS_TOOL["function"]["parameters"]["properties"]["topics"]["items"]["properties"]
    assert field in item_props


def test_discover_topics_tool_schema_requires_topics_array():
    params = DISCOVER_TOPICS_TOOL["function"]["parameters"]
    assert "topics" in params["required"]
    assert params["properties"]["topics"]["type"] == "array"


@pytest.mark.parametrize("filename", ["merge_generation.md", "merge_validation.md"])
def test_factorize_prompt_is_non_empty_string(filename: str):
    content = (FACTORIZE_PROMPTS_DIR / filename).read_text(encoding="utf-8")
    assert isinstance(content, str) and len(content) > 0


@pytest.mark.parametrize("keyword", ["synonymes", "concept", "groupe"])
def test_factorize_merge_generation_prompt_mentions_merge_concept(keyword: str):
    content = (FACTORIZE_PROMPTS_DIR / "merge_generation.md").read_text(encoding="utf-8")
    assert keyword.lower() in content.lower()


@pytest.mark.parametrize("keyword", ["target", "sources"])
def test_factorize_merge_validation_prompt_mentions_output_fields(keyword: str):
    content = (FACTORIZE_PROMPTS_DIR / "merge_validation.md").read_text(encoding="utf-8")
    assert keyword in content


def test_merge_candidates_tool_function_name():
    assert MERGE_GENERATION_TOOL["function"]["name"] == "propose_merge_candidates"


def test_merge_tool_function_name():
    assert MERGE_VALIDATION_TOOL["function"]["name"] == "record_merges"


def test_merge_candidates_tool_schema_requires_groups_array():
    params = MERGE_GENERATION_TOOL["function"]["parameters"]
    assert "groups" in params["required"]
    assert params["properties"]["groups"]["type"] == "array"


@pytest.mark.parametrize("field", ["target", "sources"])
def test_merge_tool_schema_includes_field(field: str):
    assert field in MERGE_VALIDATION_TOOL["function"]["parameters"]["properties"]


@pytest.mark.parametrize("filename", ["parent_generation.md", "parent_validation.md"])
def test_structure_prompt_is_non_empty_string(filename: str):
    content = (DISCOVER_PARENTS_PROMPTS_DIR / filename).read_text(encoding="utf-8")
    assert isinstance(content, str) and len(content) > 0


@pytest.mark.parametrize("keyword", ["parent", "children"])
def test_structure_parent_generation_prompt_mentions_hierarchy_concept(keyword: str):
    content = (DISCOVER_PARENTS_PROMPTS_DIR / "parent_generation.md").read_text(encoding="utf-8")
    assert keyword.lower() in content.lower()


@pytest.mark.parametrize("keyword", ["description", "children"])
def test_structure_parent_validation_prompt_mentions_output_fields(keyword: str):
    content = (DISCOVER_PARENTS_PROMPTS_DIR / "parent_validation.md").read_text(encoding="utf-8")
    assert keyword in content


def test_parent_candidates_tool_function_name():
    assert PARENT_GENERATION_TOOL["function"]["name"] == "propose_parent_candidates"


def test_parent_tool_function_name():
    assert PARENT_VALIDATION_TOOL["function"]["name"] == "record_parent"


def test_parent_candidates_tool_schema_requires_candidates_array():
    params = PARENT_GENERATION_TOOL["function"]["parameters"]
    assert "candidates" in params["required"]
    assert params["properties"]["candidates"]["type"] == "array"


@pytest.mark.parametrize("field", ["parent", "description", "children"])
def test_parent_tool_schema_includes_field(field: str):
    props = PARENT_VALIDATION_TOOL["function"]["parameters"]["properties"]
    assert field in props


def test_label_prompt_is_non_empty_string():
    content = (PROMPTS_DIR / "label.md").read_text(encoding="utf-8")
    assert isinstance(content, str) and len(content) > 0


@pytest.mark.parametrize("keyword", ["name", "rationale", "extract", "citation"])
def test_label_prompt_mentions_required_fields(keyword: str):
    content = (PROMPTS_DIR / "label.md").read_text(encoding="utf-8")
    assert keyword in content


def test_label_tool_function_name():
    assert LABEL_TOOL["function"]["name"] == "record_labeled_topics"


@pytest.mark.parametrize("field", ["name", "rationale", "extract"])
def test_label_tool_schema_includes_field(field: str):
    item_props = LABEL_TOOL["function"]["parameters"]["properties"]["topics"]["items"]["properties"]
    assert field in item_props


def test_label_tool_schema_requires_topics_array():
    params = LABEL_TOOL["function"]["parameters"]
    assert "topics" in params["required"]
    assert params["properties"]["topics"]["type"] == "array"
