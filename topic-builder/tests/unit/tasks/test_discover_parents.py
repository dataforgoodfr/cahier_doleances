from unittest.mock import MagicMock

import pytest

from tests.unit.helpers import make_parent_candidates_response, make_parent_response
from topicbuilder.core.schemas import ParentAddition, ParentCandidate, Taxonomy, Topic
from topicbuilder.tasks import discover_parents
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


@pytest.mark.parametrize(
    "tool, expected_name",
    [(PARENT_GENERATION_TOOL, "propose_parent_candidates"), (PARENT_VALIDATION_TOOL, "record_parent")],
)
def test_tool_function_name(tool: dict, expected_name: str):
    assert tool["function"]["name"] == expected_name


def test_build_parent_generation_messages_builds_name_only_message(taxonomy):
    msgs = build_parent_generation_messages(taxonomy, STUB_PROMPT)
    names_block = "\n".join(f"{i + 1}. {t.name}" for i, t in enumerate(taxonomy.topics))
    assert msgs == [
        {"role": "system", "content": STUB_PROMPT},
        {"role": "user", "content": f"## Topics\n\n{names_block}"},
    ]
    assert all(t.description not in msgs[1]["content"] for t in taxonomy.topics)


def test_build_parent_validation_messages_builds_candidate_message():
    children = Taxonomy(
        topics=[
            Topic(name="Water Cycle", description="Moves water through the environment.", validated=True),
            Topic(name="Photosynthesis", description="Converts sunlight into glucose."),
        ]
    )
    candidate = ParentCandidate(parent="Earth Sciences", children=children)
    msgs = build_parent_validation_messages(candidate, STUB_PROMPT)
    assert len(msgs) == 2
    assert msgs[0] == {"role": "system", "content": STUB_PROMPT}
    content = msgs[1]["content"]
    assert "## Parent candidate" in content and "Earth Sciences" in content
    assert "## Children candidates" in content
    assert "Water Cycle [validated]: Moves water through the environment." in content
    assert "Photosynthesis: Converts sunlight into glucose." in content
    assert "Photosynthesis [validated]" not in content


def test_generate_parent_candidates_calls_client_with_expected_tool_choice_and_parses_response(
    taxonomy, clustering_config
):
    candidates = [ParentCandidate(parent="Earth Sciences", children=taxonomy)]
    response = make_parent_candidates_response(candidates)
    mock_client = MagicMock(return_value=[response])
    result = generate_parent_candidates(taxonomy, mock_client, STUB_PROMPT, clustering_config)
    assert mock_client.call_args.kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "propose_parent_candidates"},
    }
    assert len(result) == 1
    assert result[0].parent == "Earth Sciences"
    assert "Water Cycle" in [t.name for t in result[0].children.topics]


def test_generate_parent_candidates_snaps_children_to_nearest_chunk_name(taxonomy, clustering_config):
    photo = next(t for t in taxonomy.topics if t.name == "Photosynthesis")
    response = make_parent_candidates_response(
        [ParentCandidate(parent="P", children=Taxonomy(topics=[Topic(name="Photosynthesi", description="d")]))]
    )
    mock_client = MagicMock(return_value=[response])
    result = generate_parent_candidates(taxonomy, mock_client, STUB_PROMPT, clustering_config)
    assert len(result) == 1
    assert result[0].children.topics[0].id == photo.id


def test_generate_parent_candidates_dedupes_children_across_candidates(clustering_config):
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
    result = generate_parent_candidates(taxonomy, mock_client, STUB_PROMPT, clustering_config)
    all_children = [t.name for c in result for t in c.children.topics]
    assert all_children.count("A") <= 1


def test_generate_parent_candidates_calls_client_once_with_one_input_per_chunk(clustering_config, monkeypatch):
    taxonomy = Taxonomy(topics=[Topic(name=str(i), description="d") for i in range(6)])
    chunks = [Taxonomy(topics=taxonomy.topics[:3]), Taxonomy(topics=taxonomy.topics[3:])]
    monkeypatch.setattr(discover_parents, "clusterize_taxonomy_by_level", lambda t, c: chunks)
    mock_client = MagicMock(
        return_value=[
            make_parent_candidates_response([]),
            make_parent_candidates_response([]),
        ]
    )
    generate_parent_candidates(taxonomy, mock_client, STUB_PROMPT, clustering_config)
    assert mock_client.call_count == 1
    assert len(mock_client.call_args.kwargs["inputs"]) == 2


def test_generate_parent_candidates_merges_results_across_chunks(clustering_config):
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
    result = generate_parent_candidates(taxonomy, mock_client, STUB_PROMPT, clustering_config)
    all_children = {t.name for c in result for t in c.children.topics}
    assert all_children == {"A", "B", "C", "D"}


def test_validate_parent_candidates_returns_empty_list_when_no_candidates():
    mock_client = MagicMock()
    result = validate_parent_candidates([], mock_client, STUB_PROMPT)
    assert result == []
    mock_client.assert_not_called()


def test_validate_parent_candidates_calls_client_and_parses_response(taxonomy):
    candidates = [ParentCandidate(parent="Earth Sciences", children=taxonomy)]
    addition = ParentAddition(
        parent=Topic(name="Earth Sciences", description="Natural earth processes."), children=taxonomy
    )
    mock_client = MagicMock(return_value=[make_parent_response(addition)])
    result = validate_parent_candidates(candidates, mock_client, STUB_PROMPT)
    assert len(mock_client.call_args.kwargs["inputs"]) == len(candidates)
    assert mock_client.call_args.kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "record_parent"},
    }
    assert result[0].parent.description == "Natural earth processes."


def test_validate_parent_candidates_keeps_validated_children():
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
    assert {t.name for t in result[0].children.topics} == {"A", "B"}


def test_validate_parent_candidates_drops_parent_when_no_children_remain():
    taxonomy = Taxonomy(topics=[Topic(name="A", description="d")])
    candidates = [ParentCandidate(parent="P", children=taxonomy)]
    addition = ParentAddition(parent=Topic(name="P", description="d"), children=Taxonomy(topics=[]))
    mock_client = MagicMock(return_value=[make_parent_response(addition)])
    result = validate_parent_candidates(candidates, mock_client, STUB_PROMPT)
    assert result == []


def test_validate_parent_candidates_dedupes_children_across_candidates():
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


def test_validate_parent_candidates_computes_level_as_max_child_level_plus_one():
    children = Taxonomy(
        topics=[
            Topic(name="A", description="d", level=0),
            Topic(name="B", description="d", level=2),
        ]
    )
    candidates = [ParentCandidate(parent="P", children=children)]
    addition = ParentAddition(parent=Topic(name="P", description="d"), children=children)
    mock_client = MagicMock(return_value=[make_parent_response(addition)])
    result = validate_parent_candidates(candidates, mock_client, STUB_PROMPT)
    assert result[0].parent.level == 3


def test_insert_parents_reparents_children_and_appends_new_parent():
    old_parent = Topic(name="OldParent", description="d")
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d"),
            Topic(name="B", description="d", parent=old_parent.id, validated=True),
        ]
    )
    new_parent = Topic(name="P", description="Parent description.")
    additions = [ParentAddition(parent=new_parent, children=taxonomy)]
    result = insert_parents(taxonomy, additions)
    assert all(t.parent == new_parent.id for t in result.topics if t.name in ("A", "B"))
    p = next(t for t in result.topics if t.name == "P")
    assert p.description == "Parent description."


def test_insert_parents_does_not_duplicate_existing_parent():
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


def test_insert_parents_empty_additions_returns_unchanged_taxonomy(taxonomy):
    result = insert_parents(taxonomy, [])
    assert [t.name for t in result.topics] == [t.name for t in taxonomy.topics]
