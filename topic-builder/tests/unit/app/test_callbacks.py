import dash
import pytest

from topicbuilder.app.callbacks import _apply_filters_and_search, _build_stats_text
from topicbuilder.app.styles import BASE_STYLESHEET, build_highlight_stylesheet
from topicbuilder.core.schemas import Topic


def make_node(id_: str, level: int = 0, validated: str = "No") -> dict:
    return {"data": {"id": id_, "label": id_, "description": "d", "validated": validated, "level": level}}


def make_edge(source: str, target: str) -> dict:
    return {"data": {"source": source, "target": target}}


@pytest.mark.parametrize(
    "min_level, validated_filter, expected_node_ids, expect_edge",
    [
        (0, "all", {"a", "b"}, True),
        (1, "all", {"b"}, False),
        (0, "Yes", {"a"}, False),
    ],
)
def test_apply_filters_and_search_filters_nodes_and_edges(min_level, validated_filter, expected_node_ids, expect_edge):
    elements = [make_node("a", level=0, validated="Yes"), make_node("b", level=2, validated="No"), make_edge("a", "b")]
    result, stylesheet, zoom = _apply_filters_and_search(
        elements, min_level=min_level, validated_filter=validated_filter, search_id=None
    )
    assert {el["data"]["id"] for el in result if "source" not in el["data"]} == expected_node_ids
    assert bool([el for el in result if "source" in el["data"]]) == expect_edge
    assert stylesheet == BASE_STYLESHEET
    assert zoom is dash.no_update


@pytest.mark.parametrize(
    "min_level, search_id, expect_highlighted, expected_stylesheet, expected_zoom",
    [
        (0, "a", True, build_highlight_stylesheet("a"), 1.5),
        (1, "a", False, BASE_STYLESHEET, dash.no_update),
    ],
)
def test_apply_filters_and_search_search_highlighting(
    min_level, search_id, expect_highlighted, expected_stylesheet, expected_zoom
):
    elements = [make_node("a", level=0), make_node("b", level=0)]
    result, stylesheet, zoom = _apply_filters_and_search(
        elements, min_level=min_level, validated_filter="all", search_id=search_id
    )
    assert stylesheet == expected_stylesheet
    assert zoom == expected_zoom
    if expect_highlighted:
        tagged = next(el for el in result if el["data"]["id"] == search_id)
        assert tagged["selected"] is True


@pytest.mark.parametrize(
    "topics, expected",
    [
        (
            [
                Topic(name="A", description="d", level=0, validated=True),
                Topic(name="B", description="d", level=1, validated=False),
            ],
            "2 topics · 2 levels · 1 validated",
        ),
        ([], "0 topics · 0 levels · 0 validated"),
    ],
)
def test_build_stats_text_returns_summary_string(topics, expected):
    assert _build_stats_text(topics) == expected
