from unittest.mock import MagicMock

import pytest

from tests.unit.helpers import make_label_response
from topicbuilder.core.schemas import Document, Label, LabeledDataset, Taxonomy, Topic
from topicbuilder.tasks.label import (
    LABEL_TOOL,
    build_messages,
    generate_labels,
)

STUB_PROMPT = "stub label prompt"


def test_label_tool_function_name():
    assert LABEL_TOOL["function"]["name"] == "record_labeled_topics"


def test_label_tool_schema_requires_topics_array():
    params = LABEL_TOOL["function"]["parameters"]
    assert "topics" in params["required"]
    assert params["properties"]["topics"]["type"] == "array"


@pytest.mark.parametrize("field", ["name", "rationale", "extract"])
def test_label_tool_schema_includes_field(field: str):
    item_props = LABEL_TOOL["function"]["parameters"]["properties"]["topics"]["items"]["properties"]
    assert field in item_props


def test_build_messages_returns_two_messages(taxonomy):
    msgs = build_messages("some text", taxonomy, STUB_PROMPT)
    assert len(msgs) == 2


def test_build_messages_system_role_carries_prompt(taxonomy):
    msgs = build_messages("some text", taxonomy, STUB_PROMPT)
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == STUB_PROMPT


def test_build_messages_user_content_includes_text(taxonomy):
    msgs = build_messages("some text", taxonomy, STUB_PROMPT)
    assert "some text" in msgs[1]["content"]


def test_build_messages_user_content_includes_topics_header(taxonomy):
    msgs = build_messages("some text", taxonomy, STUB_PROMPT)
    assert "## Topics" in msgs[1]["content"]


def test_build_messages_user_content_includes_text_header(taxonomy):
    msgs = build_messages("some text", taxonomy, STUB_PROMPT)
    assert "## Text" in msgs[1]["content"]


def test_build_messages_user_content_includes_all_topic_names(taxonomy):
    msgs = build_messages("some text", taxonomy, STUB_PROMPT)
    for t in taxonomy.topics:
        assert t.name in msgs[1]["content"]


def test_build_messages_user_content_includes_all_topic_descriptions(taxonomy):
    msgs = build_messages("some text", taxonomy, STUB_PROMPT)
    for t in taxonomy.topics:
        assert t.description in msgs[1]["content"]


def test_build_messages_topics_are_numbered(taxonomy):
    msgs = build_messages("some text", taxonomy, STUB_PROMPT)
    for i in range(len(taxonomy.topics)):
        assert f"{i + 1}." in msgs[1]["content"]


def test_generate_labels_forces_record_labeled_topics_tool(taxonomy, labeled_topics, clustering_config):
    mock_client = MagicMock(return_value=[make_label_response(labeled_topics)])
    generate_labels(
        documents=[Document(id="doc1", content="text")],
        taxonomy=taxonomy,
        client=mock_client,
        prompt=STUB_PROMPT,
        chunk_max_words=500,
        clustering_config=clustering_config,
    )
    assert mock_client.call_args.kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "record_labeled_topics"},
    }


def test_generate_labels_one_input_per_text_and_taxonomy_chunk(taxonomy, clustering_config):
    mock_client = MagicMock(return_value=[make_label_response([]), make_label_response([])])
    docs = [Document(id="d1", content="text1"), Document(id="d2", content="text2")]
    generate_labels(
        documents=docs,
        taxonomy=taxonomy,
        client=mock_client,
        prompt=STUB_PROMPT,
        chunk_max_words=500,
        clustering_config=clustering_config,
    )
    assert mock_client.call_count == 1
    assert len(mock_client.call_args.kwargs["inputs"]) == 2


def test_generate_labels_snaps_near_miss_name_to_real_topic(taxonomy, clustering_config):
    typo_label = Label(name="Water Cycl", rationale="r", extract="e")
    mock_client = MagicMock(return_value=[make_label_response([typo_label])])
    docs = [Document(id="d", content="text")]
    result = generate_labels(
        documents=docs,
        taxonomy=taxonomy,
        client=mock_client,
        prompt=STUB_PROMPT,
        chunk_max_words=500,
        clustering_config=clustering_config,
    )
    assert result.documents[0].labels[0].name == "Water Cycle"


def test_generate_labels_drops_label_with_empty_rationale(taxonomy, clustering_config):
    bad = Label(name="Water Cycle", rationale="", extract="e")
    mock_client = MagicMock(return_value=[make_label_response([bad])])
    docs = [Document(id="d", content="text")]
    result = generate_labels(
        documents=docs,
        taxonomy=taxonomy,
        client=mock_client,
        prompt=STUB_PROMPT,
        chunk_max_words=500,
        clustering_config=clustering_config,
    )
    assert result.documents[0].labels == []


def test_generate_labels_drops_label_with_empty_extract(taxonomy, clustering_config):
    bad = Label(name="Water Cycle", rationale="r", extract="")
    mock_client = MagicMock(return_value=[make_label_response([bad])])
    docs = [Document(id="d", content="text")]
    result = generate_labels(
        documents=docs,
        taxonomy=taxonomy,
        client=mock_client,
        prompt=STUB_PROMPT,
        chunk_max_words=500,
        clustering_config=clustering_config,
    )
    assert result.documents[0].labels == []


def test_generate_labels_returns_empty_labels_on_empty_taxonomy(clustering_config):
    mock_client = MagicMock()
    docs = [Document(id="d", content="text")]
    result = generate_labels(
        documents=docs,
        taxonomy=Taxonomy(topics=[]),
        client=mock_client,
        prompt=STUB_PROMPT,
        chunk_max_words=500,
        clustering_config=clustering_config,
    )
    assert isinstance(result, LabeledDataset)
    assert result.documents[0].labels == []
    mock_client.assert_not_called()


def test_generate_labels_returns_labeled_dataset(taxonomy, labeled_topics, clustering_config):
    mock_client = MagicMock(return_value=[make_label_response(labeled_topics)])
    docs = [Document(id="doc1", content="text")]
    result = generate_labels(
        documents=docs,
        taxonomy=taxonomy,
        client=mock_client,
        prompt=STUB_PROMPT,
        chunk_max_words=500,
        clustering_config=clustering_config,
    )
    assert isinstance(result, LabeledDataset)
    assert result.documents[0].id == "doc1"
    assert result.documents[0].labels == labeled_topics


def test_generate_labels_returns_empty_labels_when_none_found(taxonomy, clustering_config):
    mock_client = MagicMock(return_value=[make_label_response([])])
    docs = [Document(id="doc1", content="text")]
    result = generate_labels(
        documents=docs,
        taxonomy=taxonomy,
        client=mock_client,
        prompt=STUB_PROMPT,
        chunk_max_words=500,
        clustering_config=clustering_config,
    )
    assert result.documents[0].labels == []


def test_generate_labels_returns_per_document_labels(taxonomy, clustering_config):
    label_a = Label(name="Water Cycle", rationale="s", extract="e")
    label_b = Label(name="Photosynthesis", rationale="s", extract="e")
    mock_client = MagicMock(return_value=[make_label_response([label_a]), make_label_response([label_b])])
    docs = [Document(id="doc1", content="text1"), Document(id="doc2", content="text2")]
    result = generate_labels(
        documents=docs,
        taxonomy=taxonomy,
        client=mock_client,
        prompt=STUB_PROMPT,
        chunk_max_words=500,
        clustering_config=clustering_config,
    )
    assert result.documents[0].labels == [label_a]
    assert result.documents[1].labels == [label_b]


def test_generate_labels_deduplicates_by_name_keeping_last(clustering_config):
    taxonomy = Taxonomy(topics=[Topic(name="Water Cycle", description="d")])
    first = Label(name="Water Cycle", rationale="first", extract="e1")
    second = Label(name="Water Cycle", rationale="second", extract="e2")
    mock_client = MagicMock(return_value=[make_label_response([first, second])])
    docs = [Document(id="d", content="text")]
    result = generate_labels(
        documents=docs,
        taxonomy=taxonomy,
        client=mock_client,
        prompt=STUB_PROMPT,
        chunk_max_words=500,
        clustering_config=clustering_config,
    )
    assert len(result.documents[0].labels) == 1
    assert result.documents[0].labels[0].rationale == "second"
