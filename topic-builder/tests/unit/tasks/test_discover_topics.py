from unittest.mock import MagicMock

from tests.unit.helpers import make_discover_topics_response
from topicbuilder.core.schemas import Topic
from topicbuilder.tasks.discover_topics import build_messages, discover_leaf_topics

STUB_PROMPT = "stub discover_topics prompt"


def test_discover_topics_messages_returns_two_messages(topic_config):
    msgs = build_messages("some text", topic_config, STUB_PROMPT)
    assert len(msgs) == 2


def test_discover_topics_messages_system_role_carries_prompt(topic_config):
    msgs = build_messages("some text", topic_config, STUB_PROMPT)
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == STUB_PROMPT


def test_discover_topics_messages_user_content_includes_text(topic_config):
    msgs = build_messages("some text", topic_config, STUB_PROMPT)
    assert "some text" in msgs[1]["content"]


def test_discover_topics_messages_user_content_includes_all_topic_names(topic_config):
    msgs = build_messages("some text", topic_config, STUB_PROMPT)
    for t in topic_config.topics:
        assert t.name in msgs[1]["content"]


def test_discover_topics_messages_topics_are_numbered(topic_config):
    msgs = build_messages("some text", topic_config, STUB_PROMPT)
    for i in range(len(topic_config.topics)):
        assert f"{i + 1}." in msgs[1]["content"]


def test_discover_topics_topics_returns_merged_config(topic_config):
    new_topic = Topic(name="Soil Composition", description="Mineral and organic components of soil.")
    mock_response = make_discover_topics_response([new_topic])
    mock_client = MagicMock(return_value=[mock_response])
    result = discover_leaf_topics(["text"], topic_config, mock_client, STUB_PROMPT)
    assert len(result.topics) == len(topic_config.topics) + 1
    assert result.topics[-1].name == "Soil Composition"


def test_discover_topics_topics_no_new_topics_returns_original(topic_config):
    mock_response = make_discover_topics_response([])
    mock_client = MagicMock(return_value=[mock_response])
    result = discover_leaf_topics(["text"], topic_config, mock_client, STUB_PROMPT)
    assert result.topics == topic_config.topics


def test_discover_topics_topics_deduplicates_across_files(topic_config):
    new_topic = Topic(name="Soil Composition", description="Mineral and organic components of soil.")
    mock_response = make_discover_topics_response([new_topic])
    mock_client = MagicMock(return_value=[mock_response, mock_response])
    result = discover_leaf_topics(["text1", "text2"], topic_config, mock_client, STUB_PROMPT)
    assert sum(1 for t in result.topics if t.name == "Soil Composition") == 1


def test_discover_topics_topics_merges_topics_from_multiple_files(topic_config):
    topic_a = Topic(name="Soil Composition", description="Mineral and organic components of soil.")
    topic_b = Topic(name="Erosion", description="Wearing away of soil by wind and water.")
    mock_client = MagicMock(
        return_value=[make_discover_topics_response([topic_a]), make_discover_topics_response([topic_b])]
    )
    result = discover_leaf_topics(["text1", "text2"], topic_config, mock_client, STUB_PROMPT)
    names = [t.name for t in result.topics]
    assert "Soil Composition" in names
    assert "Erosion" in names


def test_discover_topics_topics_forces_record_new_topics_tool(topic_config):
    mock_response = make_discover_topics_response([])
    mock_client = MagicMock(return_value=[mock_response])
    discover_leaf_topics(["text"], topic_config, mock_client, STUB_PROMPT)
    call_kwargs = mock_client.call_args.kwargs
    assert call_kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "record_new_topics"},
    }


def test_discover_topics_topics_new_topics_have_level_zero(topic_config):
    new_topic = Topic(name="Soil Composition", description="Mineral and organic components of soil.")
    mock_client = MagicMock(return_value=[make_discover_topics_response([new_topic])])
    result = discover_leaf_topics(["text"], topic_config, mock_client, STUB_PROMPT)
    new_topics = [t for t in result.topics if t.name == "Soil Composition"]
    assert new_topics[0].level == 0
