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


def test_merge_candidates_tool_function_name():
    assert MERGE_GENERATION_TOOL["function"]["name"] == "propose_merge_candidates"


def test_merge_tool_function_name():
    assert MERGE_VALIDATION_TOOL["function"]["name"] == "record_merges"


def test_build_merge_candidates_messages_returns_two_messages(taxonomy):
    msgs = build_merge_generation_messages(taxonomy, STUB_PROMPT)
    assert len(msgs) == 2


def test_build_merge_candidates_messages_system_carries_prompt(taxonomy):
    msgs = build_merge_generation_messages(taxonomy, STUB_PROMPT)
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == STUB_PROMPT


def test_build_merge_candidates_messages_user_contains_topics_header(taxonomy):
    msgs = build_merge_generation_messages(taxonomy, STUB_PROMPT)
    assert "## Topics" in msgs[1]["content"]


def test_build_merge_candidates_messages_user_contains_all_names(taxonomy):
    msgs = build_merge_generation_messages(taxonomy, STUB_PROMPT)
    for t in taxonomy.topics:
        assert t.name in msgs[1]["content"]


def test_build_merge_candidates_messages_user_excludes_descriptions(taxonomy):
    msgs = build_merge_generation_messages(taxonomy, STUB_PROMPT)
    for t in taxonomy.topics:
        assert t.description not in msgs[1]["content"]


def test_build_merge_candidates_messages_topics_are_numbered(taxonomy):
    msgs = build_merge_generation_messages(taxonomy, STUB_PROMPT)
    for i in range(len(taxonomy.topics)):
        assert f"{i + 1}." in msgs[1]["content"]


def test_build_merge_messages_returns_two_messages(taxonomy):
    candidate = taxonomy
    msgs = build_merge_validation_messages(candidate, STUB_PROMPT)
    assert len(msgs) == 2


def test_build_merge_messages_system_carries_prompt(taxonomy):
    msgs = build_merge_validation_messages(taxonomy, STUB_PROMPT)
    assert msgs[0]["content"] == STUB_PROMPT


def test_build_merge_messages_user_contains_name_and_description(taxonomy):
    t = next(t for t in taxonomy.topics if t.name == "Water Cycle")
    msgs = build_merge_validation_messages(taxonomy, STUB_PROMPT)
    assert t.name in msgs[1]["content"]
    assert t.description in msgs[1]["content"]


def test_build_merge_messages_marks_validated_topic():
    candidate = Taxonomy(
        topics=[
            Topic(name="A", description="desc A", validated=True),
            Topic(name="B", description="desc B"),
        ]
    )
    msgs = build_merge_validation_messages(candidate, STUB_PROMPT)
    assert "A [validated]" in msgs[1]["content"]
    assert "B [validated]" not in msgs[1]["content"]


@pytest.mark.parametrize(
    "instructions, expect_section",
    [
        ("focus on exact synonyms", True),
        (None, False),
    ],
)
def test_build_merge_messages_appends_instructions_section(instructions, expect_section, taxonomy):
    msgs = build_merge_validation_messages(taxonomy, STUB_PROMPT, instructions)
    assert ("## Instructions" in msgs[1]["content"]) == expect_section
    if instructions:
        assert instructions in msgs[1]["content"]


def test_propose_merge_candidates_uses_correct_tool_choice(taxonomy, clustering_config):
    response = make_merge_candidates_response([taxonomy])
    mock_client = MagicMock(return_value=[response])
    generate_merge_candidates(taxonomy, mock_client, STUB_PROMPT, clustering_config)
    assert mock_client.call_args.kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "propose_merge_candidates"},
    }


def test_propose_merge_candidates_returns_valid_groups(taxonomy, clustering_config):
    response = make_merge_candidates_response([taxonomy])
    mock_client = MagicMock(return_value=[response])
    result = generate_merge_candidates(taxonomy, mock_client, STUB_PROMPT, clustering_config)
    assert len(result) == 1
    assert {t.name for t in result[0].topics} == {"Water Cycle", "Photosynthesis"}


def test_propose_merge_candidates_drops_names_not_in_taxonomy(taxonomy, clustering_config):
    group = Taxonomy(topics=[Topic(name="Water Cycle", description="d"), Topic(name="Unknown Topic", description="d")])
    response = make_merge_candidates_response([group])
    mock_client = MagicMock(return_value=[response])
    result = generate_merge_candidates(taxonomy, mock_client, STUB_PROMPT, clustering_config)
    assert result == []


def test_propose_merge_candidates_drops_groups_with_fewer_than_two_valid_names(clustering_config):
    # Single-topic taxonomy: both 'A' and 'Unknown' snap to the only available name 'A',
    # deduplication leaves one entry, and the group (len < 2) is discarded.
    taxonomy = Taxonomy(topics=[Topic(name="A", description="d")])
    group = Taxonomy(topics=[Topic(name="A", description="d"), Topic(name="Unknown", description="d")])
    response = make_merge_candidates_response([group])
    mock_client = MagicMock(return_value=[response])
    result = generate_merge_candidates(taxonomy, mock_client, STUB_PROMPT, clustering_config)
    assert result == []


def test_propose_merge_candidates_calls_client_once_with_one_input_per_chunk(clustering_config, monkeypatch):
    taxonomy = Taxonomy(topics=[Topic(name=str(i), description="d") for i in range(6)])
    chunks = [Taxonomy(topics=taxonomy.topics[:3]), Taxonomy(topics=taxonomy.topics[3:])]
    monkeypatch.setattr(factorize, "clusterize_taxonomy_by_level", lambda t, c: chunks)
    mock_client = MagicMock(return_value=[make_merge_candidates_response([]), make_merge_candidates_response([])])
    generate_merge_candidates(taxonomy, mock_client, STUB_PROMPT, clustering_config)
    assert mock_client.call_count == 1
    assert len(mock_client.call_args.kwargs["inputs"]) == 2


def test_propose_merge_candidates_merges_results_across_chunks(clustering_config, monkeypatch):
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
    all_names = {t.name for g in result for t in g.topics}
    assert all_names == {"A", "B", "C", "D"}


def test_propose_merge_candidates_dedupes_names_across_groups(clustering_config):
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


def test_resolve_merges_returns_empty_list_when_no_candidates():
    mock_client = MagicMock()
    result = validate_merge_candidates([], mock_client, STUB_PROMPT)
    assert result == []
    mock_client.assert_not_called()


def test_resolve_merges_calls_client_once_per_candidate(taxonomy):
    merge = TopicMerge(
        sources=Taxonomy(topics=[Topic(name="Photosynthesis", description="d")]),
        target=Topic(name="Water Cycle", description="d"),
    )
    response = make_merges_response(merge)
    mock_client = MagicMock(return_value=[response])
    validate_merge_candidates([taxonomy], mock_client, STUB_PROMPT)
    inputs = mock_client.call_args.kwargs["inputs"]
    assert len(inputs) == 1


def test_resolve_merges_filters_target_not_in_group(taxonomy):
    merge = TopicMerge(
        sources=Taxonomy(topics=[Topic(name="Water Cycle", description="d")]),
        target=Topic(name="Outside Topic", description="d"),
    )
    response = make_merges_response(merge)
    mock_client = MagicMock(return_value=[response])
    result = validate_merge_candidates([taxonomy], mock_client, STUB_PROMPT)
    assert result == []


def test_resolve_merges_filters_sources_outside_group(taxonomy):
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


def test_resolve_merges_drops_merge_when_sources_all_remap_to_target(taxonomy):
    merge = TopicMerge(
        sources=Taxonomy(topics=[Topic(name="Water Cycle", description="d")]),
        target=Topic(name="Water Cycle", description="d"),
    )
    response = make_merges_response(merge)
    mock_client = MagicMock(return_value=[response])
    result = validate_merge_candidates([taxonomy], mock_client, STUB_PROMPT)
    assert result == []


def test_resolve_merges_uses_correct_tool_choice(taxonomy):
    response = make_merges_response(None)
    mock_client = MagicMock(return_value=[response])
    validate_merge_candidates([taxonomy], mock_client, STUB_PROMPT)
    assert mock_client.call_args.kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "record_merges"},
    }


def _merge(target_name: str, source_names: list[str], level: int = 0) -> TopicMerge:
    return TopicMerge(
        sources=Taxonomy(topics=[Topic(name=n, description="d", level=level) for n in source_names]),
        target=Topic(name=target_name, description="d", level=level),
    )


def test_apply_merges_removes_source_topics():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d"),
            Topic(name="B", description="d"),
            Topic(name="C", description="d"),
        ]
    )
    result = insert_merges(taxonomy, [_merge("A", ["B"])])
    names = [t.name for t in result.topics]
    assert "B" not in names
    assert "A" in names
    assert "C" in names


def test_apply_merges_preserves_validated_source():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d", validated=True),
            Topic(name="B", description="d"),
        ]
    )
    result = insert_merges(taxonomy, [_merge("B", ["A"])])
    names = [t.name for t in result.topics]
    assert "A" in names


def test_apply_merges_retains_target_topic():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d"),
            Topic(name="B", description="d"),
        ]
    )
    result = insert_merges(taxonomy, [_merge("A", ["B"])])
    assert any(t.name == "A" for t in result.topics)


def test_apply_merges_empty_merges_returns_unchanged_taxonomy(taxonomy):
    result = insert_merges(taxonomy, [])
    assert [t.name for t in result.topics] == [t.name for t in taxonomy.topics]


def test_apply_merges_redirects_parent_reference_to_target():
    topic_a = Topic(name="A", description="d")
    topic_b = Topic(name="B", description="d")
    topic_c = Topic(name="C", description="d", parent=topic_b.id)
    taxonomy = Taxonomy(topics=[topic_a, topic_b, topic_c])
    merge = TopicMerge(sources=Taxonomy(topics=[topic_b]), target=topic_a)
    result = insert_merges(taxonomy, [merge])
    c = next(t for t in result.topics if t.name == "C")
    assert c.parent == topic_a.id


def test_apply_merges_keeps_parent_unchanged_when_not_a_source():
    other = Topic(name="X", description="d")
    topic_a = Topic(name="A", description="d")
    topic_b = Topic(name="B", description="d")
    topic_c = Topic(name="C", description="d", parent=other.id)
    taxonomy = Taxonomy(topics=[topic_a, topic_b, topic_c, other])
    merge = TopicMerge(sources=Taxonomy(topics=[topic_b]), target=topic_a)
    result = insert_merges(taxonomy, [merge])
    c = next(t for t in result.topics if t.name == "C")
    assert c.parent == other.id


def test_apply_merges_target_inherits_source_parent_when_target_has_none():
    real_parent = Topic(name="P", description="d")
    topic_a = Topic(name="A", description="d", parent=None)
    topic_b = Topic(name="B", description="d", parent=real_parent.id)
    taxonomy = Taxonomy(topics=[topic_a, topic_b, real_parent])
    merge = TopicMerge(sources=Taxonomy(topics=[topic_b]), target=topic_a)
    result = insert_merges(taxonomy, [merge])
    a = next(t for t in result.topics if t.name == "A")
    assert a.parent == real_parent.id


def test_apply_merges_target_parent_not_overridden_when_already_set():
    real_q = Topic(name="Q", description="d")
    real_p = Topic(name="P", description="d")
    topic_a = Topic(name="A", description="d", parent=real_q.id)
    topic_b = Topic(name="B", description="d", parent=real_p.id)
    taxonomy = Taxonomy(topics=[topic_a, topic_b, real_q, real_p])
    merge = TopicMerge(sources=Taxonomy(topics=[topic_b]), target=topic_a)
    result = insert_merges(taxonomy, [merge])
    a = next(t for t in result.topics if t.name == "A")
    assert a.parent == real_q.id


def test_apply_merges_target_inherits_first_source_with_parent():
    real_parent = Topic(name="P", description="d")
    topic_a = Topic(name="A", description="d", parent=None)
    topic_b = Topic(name="B", description="d", parent=None)
    topic_c = Topic(name="C", description="d", parent=real_parent.id)
    taxonomy = Taxonomy(topics=[topic_a, topic_b, topic_c, real_parent])
    merge = TopicMerge(sources=Taxonomy(topics=[topic_b, topic_c]), target=topic_a)
    result = insert_merges(taxonomy, [merge])
    a = next(t for t in result.topics if t.name == "A")
    assert a.parent == real_parent.id


def test_apply_merges_does_not_remove_same_name_at_different_level():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d", level=0),
            Topic(name="B", description="d", level=0),
            Topic(name="B", description="d", level=1),
        ]
    )
    result = insert_merges(taxonomy, [_merge("A", ["B"], level=0)])
    names_by_level = [(t.name, t.level) for t in result.topics]
    assert ("B", 0) not in names_by_level
    assert ("B", 1) in names_by_level
