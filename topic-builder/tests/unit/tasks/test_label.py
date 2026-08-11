from unittest.mock import MagicMock

import pytest

from tests.unit.helpers import make_label_response, with_sources
from topicbuilder.core.schemas import Document, Label, Taxonomy, Topic
from topicbuilder.tasks.label import LABEL_TOOL, build_messages, generate_labels

STUB_PROMPT = "stub label prompt"


def test_label_tool_schema():
    assert LABEL_TOOL["function"]["name"] == "record_labeled_topics"
    params = LABEL_TOOL["function"]["parameters"]
    assert "topics" in params["required"]
    assert params["properties"]["topics"]["type"] == "array"
    item_props = params["properties"]["topics"]["items"]["properties"]
    assert {"name", "rationale", "extract"} <= item_props.keys()


def test_build_messages_builds_expected_messages(taxonomy):
    msgs = build_messages("some text", taxonomy, STUB_PROMPT)
    topics_block = "\n".join(f"{i + 1}. {t.name}: {t.description}" for i, t in enumerate(taxonomy.topics))
    assert msgs == [
        {"role": "system", "content": STUB_PROMPT},
        {"role": "user", "content": f"## Topics\n\n{topics_block}\n\n## Text\n\nsome text"},
    ]


def test_generate_labels_returns_per_document_labels(taxonomy):
    label_a = Label(name="Water Cycle", rationale="s", extract="e")
    label_b = Label(name="Photosynthesis", rationale="s", extract="e")
    mock_client = MagicMock(return_value=[make_label_response([label_a]), make_label_response([label_b])])
    docs = [Document(id="doc1", content="text1"), Document(id="doc2", content="text2")]
    result = generate_labels(
        documents=docs,
        taxonomy=with_sources(taxonomy, "doc1", "doc2"),
        client=mock_client,
        prompt=STUB_PROMPT,
        chunk_max_words=500,
    )
    assert mock_client.call_count == 1
    assert len(mock_client.call_args.kwargs["inputs"]) == 2
    assert mock_client.call_args.kwargs["tool_choice"] == {
        "type": "function",
        "function": {"name": "record_labeled_topics"},
    }
    assert result.documents[0].labels == [label_a]
    assert result.documents[1].labels == [label_b]


def test_generate_labels_snaps_near_miss_name_to_real_topic(taxonomy):
    typo_label = Label(name="Water Cycl", rationale="r", extract="e")
    mock_client = MagicMock(return_value=[make_label_response([typo_label])])
    docs = [Document(id="d", content="text")]
    result = generate_labels(
        documents=docs,
        taxonomy=with_sources(taxonomy, "d"),
        client=mock_client,
        prompt=STUB_PROMPT,
        chunk_max_words=500,
    )
    assert result.documents[0].labels[0].name == "Water Cycle"


@pytest.mark.parametrize("field", ["name", "rationale", "extract"])
def test_generate_labels_drops_label_missing_required_field(taxonomy, field: str):
    kwargs = {"name": "Water Cycle", "rationale": "r", "extract": "e", field: ""}
    bad = Label(**kwargs)
    mock_client = MagicMock(return_value=[make_label_response([bad])])
    docs = [Document(id="d", content="text")]
    result = generate_labels(
        documents=docs,
        taxonomy=with_sources(taxonomy, "d"),
        client=mock_client,
        prompt=STUB_PROMPT,
        chunk_max_words=500,
    )
    assert result.documents[0].labels == []


def test_generate_labels_deduplicates_by_name_keeping_last():
    taxonomy = Taxonomy(topics=[Topic(name="Water Cycle", description="d", sources=["d"])])
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
    )
    assert len(result.documents[0].labels) == 1
    assert result.documents[0].labels[0].rationale == "second"


def test_generate_labels_restricts_topics_to_document_sources():
    topic_a = Topic(name="Topic A", description="da", sources=["doc1"])
    topic_b = Topic(name="Topic B", description="db", sources=["doc2"])
    taxonomy = Taxonomy(topics=[topic_a, topic_b])
    mock_client = MagicMock(return_value=[make_label_response([]), make_label_response([])])
    docs = [Document(id="doc1", content="text1"), Document(id="doc2", content="text2")]
    generate_labels(
        documents=docs,
        taxonomy=taxonomy,
        client=mock_client,
        prompt=STUB_PROMPT,
        chunk_max_words=500,
    )
    inputs = mock_client.call_args.kwargs["inputs"]
    doc1_content = inputs[0][1]["content"]
    doc2_content = inputs[1][1]["content"]
    assert "Topic A" in doc1_content and "Topic B" not in doc1_content
    assert "Topic B" in doc2_content and "Topic A" not in doc2_content


def test_generate_labels_skips_document_absent_from_all_sources():
    topic_a = Topic(name="Topic A", description="da", sources=["doc1"])
    taxonomy = Taxonomy(topics=[topic_a])
    mock_client = MagicMock(return_value=[make_label_response([])])
    docs = [Document(id="doc1", content="text1"), Document(id="doc2", content="text2")]
    result = generate_labels(
        documents=docs,
        taxonomy=taxonomy,
        client=mock_client,
        prompt=STUB_PROMPT,
        chunk_max_words=500,
    )
    assert len(mock_client.call_args.kwargs["inputs"]) == 1
    assert {d.id for d in result.documents} == {"doc1", "doc2"}
    assert next(d for d in result.documents if d.id == "doc2").labels == []


def test_generate_labels_does_not_snap_label_onto_excluded_topic():
    topic_a = Topic(name="Water Cycle", description="da", sources=["doc1"])
    excluded_typo = Label(name="Photosynthesis", rationale="r", extract="e")
    mock_client = MagicMock(return_value=[make_label_response([excluded_typo])])
    docs = [Document(id="doc1", content="text1")]
    result = generate_labels(
        documents=docs,
        taxonomy=Taxonomy(topics=[topic_a]),
        client=mock_client,
        prompt=STUB_PROMPT,
        chunk_max_words=500,
    )
    assert result.documents[0].labels[0].name == "Water Cycle"


@pytest.mark.parametrize("empty_taxonomy", [True, False])
def test_generate_labels_makes_no_llm_call_without_matching_topics(taxonomy, empty_taxonomy: bool):
    tx = Taxonomy(topics=[]) if empty_taxonomy else taxonomy
    mock_client = MagicMock()
    docs = [Document(id="doc1", content="text1"), Document(id="doc2", content="text2")]
    result = generate_labels(
        documents=docs,
        taxonomy=tx,
        client=mock_client,
        prompt=STUB_PROMPT,
        chunk_max_words=500,
    )
    mock_client.assert_not_called()
    assert all(d.labels == [] for d in result.documents)
