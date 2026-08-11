from unittest.mock import MagicMock

from tests.unit.helpers import make_discover_topics_response
from topicbuilder.core.schemas import Topic
from topicbuilder.tasks.discover_topics import build_messages, discover_leaf_topics

STUB_PROMPT = "stub discover_topics prompt"


def test_build_messages_returns_expected_messages(taxonomy):
    msgs = build_messages("some text", taxonomy, STUB_PROMPT)
    topics_block = "\n".join(f"{i + 1}. {t.name}: {t.description}" for i, t in enumerate(taxonomy.topics))
    assert msgs == [
        {"role": "system", "content": STUB_PROMPT},
        {"role": "user", "content": f"## Existing topics\n\n{topics_block}\n\n## Text\n\nsome text"},
    ]


def test_discover_leaf_topics_adds_new_topic_with_source_and_level(taxonomy):
    new_topic = Topic(name="Soil Composition", description="Mineral and organic components of soil.")
    mock_client = MagicMock(return_value=[make_discover_topics_response([new_topic])])
    result = discover_leaf_topics([("doc1", "text")], taxonomy, mock_client, STUB_PROMPT)
    assert len(result.topics) == len(taxonomy.topics) + 1
    added = result.topics[-1]
    assert added.name == "Soil Composition"
    assert added.level == 0
    assert added.sources == ["doc1"]


def test_discover_leaf_topics_no_new_topics_returns_original_and_forces_tool_choice(taxonomy):
    mock_response = make_discover_topics_response([])
    mock_client = MagicMock(return_value=[mock_response])
    result = discover_leaf_topics([("doc1", "text")], taxonomy, mock_client, STUB_PROMPT)
    assert result.topics == taxonomy.topics
    assert mock_client.call_args.kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "record_new_topics"},
    }


def test_discover_leaf_topics_dedupes_same_topic_across_files_and_unions_sources(taxonomy):
    new_topic = Topic(name="Soil Composition", description="Mineral and organic components of soil.")
    mock_response = make_discover_topics_response([new_topic])
    mock_client = MagicMock(return_value=[mock_response, mock_response])
    result = discover_leaf_topics([("doc1", "text1"), ("doc2", "text2")], taxonomy, mock_client, STUB_PROMPT)
    merged = [t for t in result.topics if t.name == "Soil Composition"]
    assert len(merged) == 1
    assert merged[0].sources == ["doc1", "doc2"]


def test_discover_leaf_topics_rediscovered_topic_keeps_id_and_gains_source(taxonomy):
    existing = taxonomy.topics[0]
    same_topic = Topic(name=existing.name, description=existing.description)
    mock_client = MagicMock(return_value=[make_discover_topics_response([same_topic])])
    result = discover_leaf_topics([("doc1", "text")], taxonomy, mock_client, STUB_PROMPT)
    rediscovered = next(t for t in result.topics if t.name == existing.name)
    assert rediscovered.id == existing.id
    assert rediscovered.sources == ["doc1"]
