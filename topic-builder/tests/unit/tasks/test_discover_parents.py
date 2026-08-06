from unittest.mock import MagicMock

from tests.unit.helpers import make_parent_candidates_response, make_parent_response
from topicbuilder.core.schemas import ParentAddition, ParentCandidate, Taxonomy, Topic
from topicbuilder.tasks.discover_parents import (
    PARENT_GENERATION_TOOL,
    PARENT_VALIDATION_TOOL,
    build_parent_generation_messages,
    build_parent_validation_messages,
    generate_parent_candidates,
    insert_parents,
    validate_parent_candidates,
)

STUB_PROMPT = "stub parent prompt"


def test_parent_candidates_tool_function_name():
    assert PARENT_GENERATION_TOOL["function"]["name"] == "propose_parent_candidates"


def test_parent_tool_function_name():
    assert PARENT_VALIDATION_TOOL["function"]["name"] == "record_parent"


def test_build_parent_candidates_messages_returns_two_messages(topic_config):
    msgs = build_parent_generation_messages(topic_config, STUB_PROMPT)
    assert len(msgs) == 2


def test_build_parent_candidates_messages_system_carries_prompt(topic_config):
    msgs = build_parent_generation_messages(topic_config, STUB_PROMPT)
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == STUB_PROMPT


def test_build_parent_candidates_messages_user_contains_topics_header(topic_config):
    msgs = build_parent_generation_messages(topic_config, STUB_PROMPT)
    assert "## Topics" in msgs[1]["content"]


def test_build_parent_candidates_messages_user_contains_all_names(topic_config):
    msgs = build_parent_generation_messages(topic_config, STUB_PROMPT)
    for t in topic_config.topics:
        assert t.name in msgs[1]["content"]


def test_build_parent_candidates_messages_user_excludes_descriptions(topic_config):
    msgs = build_parent_generation_messages(topic_config, STUB_PROMPT)
    for t in topic_config.topics:
        assert t.description not in msgs[1]["content"]


def test_build_parent_messages_returns_two_messages(topic_config):
    candidate = ParentCandidate(parent="Earth Sciences", children=Taxonomy(topics=[topic_config.topics[0]]))
    msgs = build_parent_validation_messages(candidate, STUB_PROMPT)
    assert len(msgs) == 2


def test_build_parent_messages_user_contains_parent_candidate_header(topic_config):
    candidate = ParentCandidate(parent="Earth Sciences", children=Taxonomy(topics=[topic_config.topics[0]]))
    msgs = build_parent_validation_messages(candidate, STUB_PROMPT)
    assert "## Parent candidate" in msgs[1]["content"]
    assert "Earth Sciences" in msgs[1]["content"]


def test_build_parent_messages_user_contains_children_candidates_header(topic_config):
    candidate = ParentCandidate(parent="Earth Sciences", children=Taxonomy(topics=[topic_config.topics[0]]))
    msgs = build_parent_validation_messages(candidate, STUB_PROMPT)
    assert "## Children candidates" in msgs[1]["content"]


def test_build_parent_messages_user_contains_child_name_and_description(topic_config):
    t = next(t for t in topic_config.topics if t.name == "Water Cycle")
    candidate = ParentCandidate(parent="Earth Sciences", children=Taxonomy(topics=[t]))
    msgs = build_parent_validation_messages(candidate, STUB_PROMPT)
    assert t.name in msgs[1]["content"]
    assert t.description in msgs[1]["content"]


def test_build_parent_messages_marks_validated_child():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="desc A", validated=True),
            Topic(name="B", description="desc B"),
        ]
    )
    candidate = ParentCandidate(parent="P", children=taxonomy)
    msgs = build_parent_validation_messages(candidate, STUB_PROMPT)
    assert "A [validated]" in msgs[1]["content"]
    assert "B [validated]" not in msgs[1]["content"]


def test_propose_parent_candidates_uses_correct_tool_choice(topic_config):
    response = make_parent_candidates_response(
        [ParentCandidate(parent="Earth Sciences", children=Taxonomy(topics=[topic_config.topics[0]]))]
    )
    mock_client = MagicMock(return_value=[response])
    generate_parent_candidates(topic_config, mock_client, STUB_PROMPT, chunk_size=50)
    assert mock_client.call_args.kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "propose_parent_candidates"},
    }


def test_propose_parent_candidates_returns_valid_candidates(topic_config):
    candidates = [ParentCandidate(parent="Earth Sciences", children=topic_config)]
    response = make_parent_candidates_response(candidates)
    mock_client = MagicMock(return_value=[response])
    result = generate_parent_candidates(topic_config, mock_client, STUB_PROMPT, chunk_size=50)
    assert len(result) == 1
    assert result[0].parent == "Earth Sciences"
    assert "Water Cycle" in [t.name for t in result[0].children.topics]


def test_propose_parent_candidates_snaps_children_to_nearest_chunk_name(topic_config):
    photo = next(t for t in topic_config.topics if t.name == "Photosynthesis")
    response = make_parent_candidates_response(
        [ParentCandidate(parent="P", children=Taxonomy(topics=[Topic(name="Photosynthesi", description="d")]))]
    )
    mock_client = MagicMock(return_value=[response])
    result = generate_parent_candidates(topic_config, mock_client, STUB_PROMPT, chunk_size=50)
    assert len(result) == 1
    assert result[0].children.topics[0].id == photo.id


def test_propose_parent_candidates_dedupes_children_across_candidates():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d"),
            Topic(name="B", description="d"),
        ]
    )
    response = make_parent_candidates_response(
        [
            ParentCandidate(parent="P1", children=taxonomy),
            ParentCandidate(parent="P2", children=Taxonomy(topics=[taxonomy.topics[0]])),
        ]
    )
    mock_client = MagicMock(return_value=[response])
    result = generate_parent_candidates(taxonomy, mock_client, STUB_PROMPT, chunk_size=50)
    all_children = [t.name for c in result for t in c.children.topics]
    assert all_children.count("A") <= 1


def test_propose_parent_candidates_calls_client_once_with_one_input_per_chunk():
    taxonomy = Taxonomy(topics=[Topic(name=str(i), description="d") for i in range(6)])
    mock_client = MagicMock(
        return_value=[
            make_parent_candidates_response([]),
            make_parent_candidates_response([]),
        ]
    )
    generate_parent_candidates(taxonomy, mock_client, STUB_PROMPT, chunk_size=3)
    assert mock_client.call_count == 1
    assert len(mock_client.call_args.kwargs["inputs"]) == 2


def test_propose_parent_candidates_merges_results_across_chunks():
    topics = [Topic(name=n, description="d") for n in ["A", "B", "C", "D"]]
    taxonomy = Taxonomy(topics=topics)

    def adaptive_client(inputs, tools, tool_choice):
        responses = []
        for i, msg_list in enumerate(inputs):
            names = [line.split(". ", 1)[1] for line in msg_list[1]["content"].strip().split("\n") if ". " in line]
            chunk_topics = [t for t in topics if t.name in names]
            responses.append(
                make_parent_candidates_response(
                    [ParentCandidate(parent=f"P{i + 1}", children=Taxonomy(topics=chunk_topics))]
                )
            )
        return responses

    mock_client = MagicMock(side_effect=adaptive_client)
    result = generate_parent_candidates(taxonomy, mock_client, STUB_PROMPT, chunk_size=2)
    all_children = {t.name for c in result for t in c.children.topics}
    assert all_children == {"A", "B", "C", "D"}


def test_resolve_parent_candidates_returns_empty_list_when_no_candidates(topic_config):
    mock_client = MagicMock()
    result = validate_parent_candidates([], mock_client, STUB_PROMPT)
    assert result == []
    mock_client.assert_not_called()


def test_resolve_parent_candidates_calls_client_once_per_candidate(topic_config):
    candidates = [ParentCandidate(parent="Earth Sciences", children=Taxonomy(topics=[topic_config.topics[0]]))]
    addition = ParentAddition(
        parent=Topic(name="Earth Sciences", description="desc"), children=Taxonomy(topics=[topic_config.topics[0]])
    )
    mock_client = MagicMock(return_value=[make_parent_response(addition)])
    validate_parent_candidates(candidates, mock_client, STUB_PROMPT)
    inputs = mock_client.call_args.kwargs["inputs"]
    assert len(inputs) == len(candidates)


def test_resolve_parent_candidates_uses_correct_tool_choice(topic_config):
    candidates = [ParentCandidate(parent="P", children=Taxonomy(topics=[topic_config.topics[0]]))]
    addition = ParentAddition(
        parent=Topic(name="P", description="d"), children=Taxonomy(topics=[topic_config.topics[0]])
    )
    mock_client = MagicMock(return_value=[make_parent_response(addition)])
    validate_parent_candidates(candidates, mock_client, STUB_PROMPT)
    assert mock_client.call_args.kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "record_parent"},
    }


def test_resolve_parent_candidates_keeps_validated_children():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d", validated=True),
            Topic(name="B", description="d"),
        ]
    )
    candidates = [ParentCandidate(parent="P", children=taxonomy)]
    addition = ParentAddition(parent=Topic(name="P", description="d"), children=taxonomy)
    mock_client = MagicMock(return_value=[make_parent_response(addition)])
    result = validate_parent_candidates(candidates, mock_client, STUB_PROMPT)
    assert len(result) == 1
    assert "A" in [t.name for t in result[0].children.topics]
    assert "B" in [t.name for t in result[0].children.topics]


def test_resolve_parent_candidates_drops_parent_when_no_children_remain():
    taxonomy = Taxonomy(topics=[Topic(name="A", description="d")])
    candidates = [ParentCandidate(parent="P", children=taxonomy)]
    addition = ParentAddition(parent=Topic(name="P", description="d"), children=Taxonomy(topics=[]))
    mock_client = MagicMock(return_value=[make_parent_response(addition)])
    result = validate_parent_candidates(candidates, mock_client, STUB_PROMPT)
    assert result == []


def test_resolve_parent_candidates_dedupes_children_across_candidates():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d"),
            Topic(name="B", description="d"),
        ]
    )
    candidates = [
        ParentCandidate(parent="P1", children=Taxonomy(topics=[taxonomy.topics[0]])),
        ParentCandidate(parent="P2", children=taxonomy),
    ]
    mock_client = MagicMock(
        return_value=[
            make_parent_response(
                ParentAddition(
                    parent=Topic(name="P1", description="d"), children=Taxonomy(topics=[taxonomy.topics[0]])
                )
            ),
            make_parent_response(ParentAddition(parent=Topic(name="P2", description="d"), children=taxonomy)),
        ]
    )
    result = validate_parent_candidates(candidates, mock_client, STUB_PROMPT)
    all_children = [t.name for r in result for t in r.children.topics]
    assert all_children.count("A") <= 1


def test_resolve_parent_candidates_carries_description_from_llm_response(topic_config):
    candidates = [ParentCandidate(parent="Earth Sciences", children=topic_config)]
    addition = ParentAddition(
        parent=Topic(name="Earth Sciences", description="Natural earth processes."), children=topic_config
    )
    mock_client = MagicMock(return_value=[make_parent_response(addition)])
    result = validate_parent_candidates(candidates, mock_client, STUB_PROMPT)
    assert result[0].parent.description == "Natural earth processes."


def test_apply_parents_sets_parent_field_on_children():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d"),
            Topic(name="B", description="d"),
        ]
    )
    parent_topic = Topic(name="P", description="desc P")
    additions = [ParentAddition(parent=parent_topic, children=taxonomy)]
    result = insert_parents(taxonomy, additions)
    for t in result.topics:
        if t.name in ("A", "B"):
            assert t.parent == parent_topic.id


def test_apply_parents_changes_validated_topic_parent():
    old_parent = Topic(name="OldParent", description="d")
    new_parent = Topic(name="NewParent", description="d")
    taxonomy = Taxonomy(topics=[Topic(name="A", description="d", parent=old_parent.id, validated=True)])
    additions = [ParentAddition(parent=new_parent, children=taxonomy)]
    result = insert_parents(taxonomy, additions)
    a = next(t for t in result.topics if t.name == "A")
    assert a.parent == new_parent.id


def test_apply_parents_appends_new_parent_topic_with_description():
    taxonomy = Taxonomy(topics=[Topic(name="A", description="d")])
    additions = [ParentAddition(parent=Topic(name="P", description="Parent description."), children=taxonomy)]
    result = insert_parents(taxonomy, additions)
    p = next((t for t in result.topics if t.name == "P"), None)
    assert p is not None
    assert p.description == "Parent description."


def test_apply_parents_new_parent_level_is_max_children_level_plus_one():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d", level=0),
            Topic(name="B", description="d", level=2),
        ]
    )
    additions = [ParentAddition(parent=Topic(name="P", description="d", level=3), children=taxonomy)]
    result = insert_parents(taxonomy, additions)
    p = next(t for t in result.topics if t.name == "P")
    assert p.level == 3


def test_apply_parents_does_not_duplicate_existing_parent():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d"),
            Topic(name="P", description="existing"),
        ]
    )
    additions = [
        ParentAddition(parent=Topic(name="P", description="new desc"), children=Taxonomy(topics=[taxonomy.topics[0]]))
    ]
    result = insert_parents(taxonomy, additions)
    assert sum(1 for t in result.topics if t.name == "P") == 1


def test_apply_parents_empty_additions_returns_unchanged_taxonomy(topic_config):
    result = insert_parents(topic_config, [])
    assert [t.name for t in result.topics] == [t.name for t in topic_config.topics]
