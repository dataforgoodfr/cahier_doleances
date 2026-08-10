from unittest.mock import MagicMock

import pytest

from tests.unit.helpers import make_merge_candidates_response, make_merges_response
from topicbuilder.core.schemas import Taxonomy, Topic, TopicMerge
from topicbuilder.tasks import factorize
from topicbuilder.tasks.factorize import (
    MERGE_GENERATION_TOOL,
    MERGE_VALIDATION_TOOL,
    build_merge_generation_messages,
    build_merge_validation_messages,
    generate_merge_candidates,
    insert_merges,
    validate_merge_candidates,
)

STUB_PROMPT = "stub merge prompt"


@pytest.mark.parametrize(
    "tool, expected_name",
    [
        (MERGE_GENERATION_TOOL, "propose_merge_candidates"),
        (MERGE_VALIDATION_TOOL, "record_merges"),
    ],
)
def test_merge_tools_declare_expected_function_name(tool, expected_name):
    assert tool["function"]["name"] == expected_name


def test_build_merge_generation_messages_builds_expected_messages(taxonomy):
    msgs = build_merge_generation_messages(taxonomy, STUB_PROMPT)
    names_block = "\n".join(f"{i + 1}. {t.name}" for i, t in enumerate(taxonomy.topics))
    assert msgs == [
        {"role": "system", "content": STUB_PROMPT},
        {"role": "user", "content": f"## Topics\n\n{names_block}"},
    ]


def test_build_merge_validation_messages_builds_expected_messages():
    candidate = Taxonomy(
        topics=[
            Topic(name="Water Cycle", description="desc A", validated=True),
            Topic(name="Photosynthesis", description="desc B"),
        ]
    )
    msgs = build_merge_validation_messages(candidate, STUB_PROMPT)
    topics_block = "1. Water Cycle [validated]: desc A\n2. Photosynthesis: desc B"
    assert msgs == [
        {"role": "system", "content": STUB_PROMPT},
        {"role": "user", "content": f"## Topics\n\n{topics_block}"},
    ]


@pytest.mark.parametrize(
    "instructions, expect_section",
    [
        ("focus on exact synonyms", True),
        (None, False),
    ],
)
def test_build_merge_validation_messages_appends_instructions_section(instructions, expect_section, taxonomy):
    msgs = build_merge_validation_messages(taxonomy, STUB_PROMPT, instructions)
    assert ("## Instructions" in msgs[1]["content"]) == expect_section
    if instructions:
        assert instructions in msgs[1]["content"]


def test_generate_merge_candidates_returns_valid_groups_with_correct_tool_choice(taxonomy, clustering_config):
    response = make_merge_candidates_response([taxonomy])
    mock_client = MagicMock(return_value=[response])
    result = generate_merge_candidates(taxonomy, mock_client, STUB_PROMPT, clustering_config)
    assert mock_client.call_args.kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "propose_merge_candidates"},
    }
    assert len(result) == 1
    assert {t.name for t in result[0].topics} == {"Water Cycle", "Photosynthesis"}


@pytest.mark.parametrize(
    "chunk_names, group_names",
    [
        # 'Unknown Topic' snaps onto the same topic as 'Water Cycle', dedup collapses the group to 1.
        (["Water Cycle", "Photosynthesis"], ["Water Cycle", "Unknown Topic"]),
        # Single-topic chunk: both names snap onto the lone topic, dedup collapses the group to 1.
        (["A"], ["A", "Unknown"]),
    ],
)
def test_generate_merge_candidates_drops_group_when_dedup_leaves_fewer_than_two(
    chunk_names, group_names, clustering_config
):
    taxonomy = Taxonomy(topics=[Topic(name=n, description="d") for n in chunk_names])
    group = Taxonomy(topics=[Topic(name=n, description="d") for n in group_names])
    response = make_merge_candidates_response([group])
    mock_client = MagicMock(return_value=[response])
    result = generate_merge_candidates(taxonomy, mock_client, STUB_PROMPT, clustering_config)
    assert result == []


def test_generate_merge_candidates_calls_client_once_per_chunk_and_aggregates_results(clustering_config, monkeypatch):
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d"),
            Topic(name="B", description="d"),
            Topic(name="C", description="d"),
            Topic(name="D", description="d"),
        ]
    )
    chunks = [Taxonomy(topics=taxonomy.topics[:2]), Taxonomy(topics=taxonomy.topics[2:])]
    monkeypatch.setattr(factorize, "clusterize_taxonomy_by_level", lambda t, c: chunks)

    def adaptive_client(inputs, tools, tool_choice):
        responses = []
        for msg_list in inputs:
            names = [line.split(". ", 1)[1] for line in msg_list[1]["content"].strip().split("\n") if ". " in line]
            group = Taxonomy(topics=[Topic(name=n, description="d") for n in names])
            responses.append(make_merge_candidates_response([group]))
        return responses

    mock_client = MagicMock(side_effect=adaptive_client)
    result = generate_merge_candidates(taxonomy, mock_client, STUB_PROMPT, clustering_config)
    assert mock_client.call_count == 1
    assert len(mock_client.call_args.kwargs["inputs"]) == 2
    all_names = {t.name for g in result for t in g.topics}
    assert all_names == {"A", "B", "C", "D"}


def test_generate_merge_candidates_dedupes_names_across_groups(clustering_config):
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d"),
            Topic(name="B", description="d"),
            Topic(name="C", description="d"),
        ]
    )
    group1 = Taxonomy(topics=[Topic(name="A", description="d"), Topic(name="B", description="d")])
    group2 = Taxonomy(topics=[Topic(name="A", description="d"), Topic(name="C", description="d")])
    response = make_merge_candidates_response([group1, group2])
    mock_client = MagicMock(return_value=[response])
    result = generate_merge_candidates(taxonomy, mock_client, STUB_PROMPT, clustering_config)
    all_names = [t.name for g in result for t in g.topics]
    assert all_names.count("A") <= 1


def test_validate_merge_candidates_returns_empty_and_skips_client_when_no_candidates():
    mock_client = MagicMock()
    result = validate_merge_candidates([], mock_client, STUB_PROMPT)
    assert result == []
    mock_client.assert_not_called()


def test_validate_merge_candidates_calls_client_once_with_correct_tool_choice(taxonomy):
    response = make_merges_response(None)
    mock_client = MagicMock(return_value=[response])
    validate_merge_candidates([taxonomy], mock_client, STUB_PROMPT)
    assert len(mock_client.call_args.kwargs["inputs"]) == 1
    assert mock_client.call_args.kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "record_merges"},
    }


@pytest.mark.parametrize(
    "target_name, source_names",
    [
        # Target itself snaps onto the same in-group topic as its sole source.
        ("Outside Topic", ["Water Cycle"]),
        # Source is literally the same topic as the target.
        ("Water Cycle", ["Water Cycle"]),
    ],
)
def test_validate_merge_candidates_drops_merge_when_no_sources_remain_after_filtering(
    target_name, source_names, taxonomy
):
    merge = TopicMerge(
        sources=Taxonomy(topics=[Topic(name=n, description="d") for n in source_names]),
        target=Topic(name=target_name, description="d"),
    )
    response = make_merges_response(merge)
    mock_client = MagicMock(return_value=[response])
    result = validate_merge_candidates([taxonomy], mock_client, STUB_PROMPT)
    assert result == []


def test_validate_merge_candidates_filters_sources_outside_group(taxonomy):
    merge = TopicMerge(
        sources=Taxonomy(
            topics=[Topic(name="Photosynthesis", description="d"), Topic(name="Not In Group", description="d")]
        ),
        target=Topic(name="Water Cycle", description="d"),
    )
    response = make_merges_response(merge)
    mock_client = MagicMock(return_value=[response])
    result = validate_merge_candidates([taxonomy], mock_client, STUB_PROMPT)
    assert len(result) == 1
    source_names = [s.name for s in result[0].sources.topics]
    assert "Not In Group" not in source_names


def merge(target_name: str, source_names: list[str], level: int = 0) -> TopicMerge:
    return TopicMerge(
        sources=Taxonomy(topics=[Topic(name=n, description="d", level=level) for n in source_names]),
        target=Topic(name=target_name, description="d", level=level),
    )


def test_insert_merges_merges_source_into_target():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d", sources=["sA"]),
            Topic(name="B", description="d", sources=["sB"]),
            Topic(name="C", description="d", sources=["sC"]),
        ]
    )
    result = insert_merges(taxonomy, [merge("A", ["B"])])
    names = [t.name for t in result.topics]
    assert "B" not in names
    assert {"A", "C"} <= set(names)
    target = next(t for t in result.topics if t.name == "A")
    assert target.sources == ["sA", "sB"]


def test_insert_merges_keeps_validated_source_topic():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d", validated=True),
            Topic(name="B", description="d"),
        ]
    )
    result = insert_merges(taxonomy, [merge("B", ["A"])])
    assert "A" in [t.name for t in result.topics]


def test_insert_merges_empty_merges_returns_unchanged_taxonomy(taxonomy):
    result = insert_merges(taxonomy, [])
    assert [t.name for t in result.topics] == [t.name for t in taxonomy.topics]


@pytest.mark.parametrize("child_parent_is_source", [True, False])
def test_insert_merges_redirects_child_parent_to_target(child_parent_is_source):
    other = Topic(name="X", description="d")
    topic_a = Topic(name="A", description="d")
    topic_b = Topic(name="B", description="d")
    topic_c = Topic(name="C", description="d", parent=topic_b.id if child_parent_is_source else other.id)
    taxonomy = Taxonomy(topics=[topic_a, topic_b, topic_c, other])
    result = insert_merges(taxonomy, [TopicMerge(sources=Taxonomy(topics=[topic_b]), target=topic_a)])
    c = next(t for t in result.topics if t.name == "C")
    assert c.parent == (topic_a.id if child_parent_is_source else other.id)


@pytest.mark.parametrize(
    "target_has_parent, source_parent_flags",
    [
        (False, [True]),  # target has no parent -> inherits its sole source's parent
        (True, [True]),  # target already has a parent -> not overridden
        (False, [False, True]),  # inherits the parent from the first source that has one
    ],
)
def test_insert_merges_target_parent_inherited_from_source_unless_already_set(target_has_parent, source_parent_flags):
    real_parent = Topic(name="P", description="d")
    other_parent = Topic(name="Q", description="d")
    topic_a = Topic(name="A", description="d", parent=other_parent.id if target_has_parent else None)
    sources = [
        Topic(name=f"S{i}", description="d", parent=real_parent.id if has_parent else None)
        for i, has_parent in enumerate(source_parent_flags)
    ]
    taxonomy = Taxonomy(topics=[topic_a, *sources, real_parent, other_parent])
    result = insert_merges(taxonomy, [TopicMerge(sources=Taxonomy(topics=sources), target=topic_a)])
    a = next(t for t in result.topics if t.name == "A")
    assert a.parent == (other_parent.id if target_has_parent else real_parent.id)


def test_insert_merges_does_not_remove_same_name_at_different_level():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d", level=0),
            Topic(name="B", description="d", level=0),
            Topic(name="B", description="d", level=1),
        ]
    )
    result = insert_merges(taxonomy, [merge("A", ["B"], level=0)])
    names_by_level = [(t.name, t.level) for t in result.topics]
    assert ("B", 0) not in names_by_level
    assert ("B", 1) in names_by_level
