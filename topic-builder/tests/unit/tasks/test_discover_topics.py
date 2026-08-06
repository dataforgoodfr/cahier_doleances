from unittest.mock import MagicMock

from tests.unit.helpers import make_discover_topics_response
from topicbuilder.core.schemas import Topic
from topicbuilder.tasks.discover_topics import build_messages, discover_leaf_topics

STUB_PROMPT = "stub discover_topics prompt"


def test_discover_topics_messages_returns_two_messages(taxonomy):
    msgs = build_messages("some text", taxonomy, STUB_PROMPT)
    assert len(msgs) == 2


def test_discover_topics_messages_system_role_carries_prompt(taxonomy):
    msgs = build_messages("some text", taxonomy, STUB_PROMPT)
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == STUB_PROMPT


def test_discover_topics_messages_user_content_includes_text(taxonomy):
    msgs = build_messages("some text", taxonomy, STUB_PROMPT)
    assert "some text" in msgs[1]["content"]


def test_discover_topics_messages_user_content_includes_all_topic_names(taxonomy):
    msgs = build_messages("some text", taxonomy, STUB_PROMPT)
    for t in taxonomy.topics:
        assert t.name in msgs[1]["content"]


def test_discover_topics_messages_topics_are_numbered(taxonomy):
    msgs = build_messages("some text", taxonomy, STUB_PROMPT)
    for i in range(len(taxonomy.topics)):
        assert f"{i + 1}." in msgs[1]["content"]


def test_discover_topics_topics_returns_merged_config(taxonomy):
    new_topic = Topic(name="Soil Composition", description="Mineral and organic components of soil.")
    mock_response = make_discover_topics_response([new_topic])
    mock_client = MagicMock(return_value=[mock_response])
    result = discover_leaf_topics(["text"], taxonomy, mock_client, STUB_PROMPT)
    assert len(result.topics) == len(taxonomy.topics) + 1
    assert result.topics[-1].name == "Soil Composition"


def test_discover_topics_topics_no_new_topics_returns_original(taxonomy):
    mock_response = make_discover_topics_response([])
    mock_client = MagicMock(return_value=[mock_response])
    result = discover_leaf_topics(["text"], taxonomy, mock_client, STUB_PROMPT)
    assert result.topics == taxonomy.topics


def test_discover_topics_topics_deduplicates_across_files(taxonomy):
    new_topic = Topic(name="Soil Composition", description="Mineral and organic components of soil.")
    mock_response = make_discover_topics_response([new_topic])
    mock_client = MagicMock(return_value=[mock_response, mock_response])
    result = discover_leaf_topics(["text1", "text2"], taxonomy, mock_client, STUB_PROMPT)
    assert sum(1 for t in result.topics if t.name == "Soil Composition") == 1


def test_discover_topics_topics_merges_topics_from_multiple_files(taxonomy):
    topic_a = Topic(name="Soil Composition", description="Mineral and organic components of soil.")
    topic_b = Topic(name="Erosion", description="Wearing away of soil by wind and water.")
    mock_client = MagicMock(
        return_value=[make_discover_topics_response([topic_a]), make_discover_topics_response([topic_b])]
    )
    result = discover_leaf_topics(["text1", "text2"], taxonomy, mock_client, STUB_PROMPT)
    names = [t.name for t in result.topics]
    assert "Soil Composition" in names
    assert "Erosion" in names


def test_discover_topics_topics_forces_record_new_topics_tool(taxonomy):
    mock_response = make_discover_topics_response([])
    mock_client = MagicMock(return_value=[mock_response])
    discover_leaf_topics(["text"], taxonomy, mock_client, STUB_PROMPT)
    call_kwargs = mock_client.call_args.kwargs
    assert call_kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "record_new_topics"},
    }


def test_discover_topics_topics_new_topics_have_level_zero(taxonomy):
    new_topic = Topic(name="Soil Composition", description="Mineral and organic components of soil.")
    mock_client = MagicMock(return_value=[make_discover_topics_response([new_topic])])
    result = discover_leaf_topics(["text"], taxonomy, mock_client, STUB_PROMPT)
    new_topics = [t for t in result.topics if t.name == "Soil Composition"]
    assert new_topics[0].level == 0
