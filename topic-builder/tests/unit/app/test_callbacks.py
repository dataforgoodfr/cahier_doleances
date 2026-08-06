import dash

from topicbuilder.app.callbacks import _apply_filters_and_search, _build_stats_text
from topicbuilder.app.styles import BASE_STYLESHEET, build_highlight_stylesheet
from topicbuilder.core.schemas import Topic


def make_node(id_: str, level: int = 0, validated: str = "No") -> dict:
    return {"data": {"id": id_, "label": id_, "description": "d", "validated": validated, "level": level}}


def make_edge(source: str, target: str) -> dict:
    return {"data": {"source": source, "target": target}}


def test_apply_filters_and_search_keeps_all_nodes_without_filters():
    elements = [make_node("a"), make_node("b"), make_edge("a", "b")]
    result, stylesheet, zoom = _apply_filters_and_search(elements, min_level=0, validated_filter="all", search_id=None)
    ids = {el["data"]["id"] for el in result if "source" not in el["data"]}
    assert ids == {"a", "b"}
    assert stylesheet == BASE_STYLESHEET
    assert zoom is dash.no_update


def test_apply_filters_and_search_filters_by_min_level():
    elements = [make_node("a", level=0), make_node("b", level=2)]
    result, _, _ = _apply_filters_and_search(elements, min_level=1, validated_filter="all", search_id=None)
    assert {el["data"]["id"] for el in result} == {"b"}


def test_apply_filters_and_search_filters_by_validated_status():
    elements = [make_node("a", validated="Yes"), make_node("b", validated="No")]
    result, _, _ = _apply_filters_and_search(elements, min_level=0, validated_filter="Yes", search_id=None)
    assert {el["data"]["id"] for el in result} == {"a"}


def test_apply_filters_and_search_drops_edges_touching_filtered_out_node():
    elements = [make_node("a", level=0), make_node("b", level=2), make_edge("a", "b")]
    result, _, _ = _apply_filters_and_search(elements, min_level=1, validated_filter="all", search_id=None)
    assert [el for el in result if "source" in el["data"]] == []


def test_apply_filters_and_search_highlights_searched_node():
    elements = [make_node("a"), make_node("b")]
    result, stylesheet, zoom = _apply_filters_and_search(elements, min_level=0, validated_filter="all", search_id="a")
    tagged = next(el for el in result if el["data"]["id"] == "a")
    assert tagged["selected"] is True
    assert stylesheet == build_highlight_stylesheet("a")
    assert zoom == 1.5


def test_apply_filters_and_search_ignores_search_id_excluded_by_filters():
    elements = [make_node("a", level=0)]
    result, stylesheet, zoom = _apply_filters_and_search(elements, min_level=1, validated_filter="all", search_id="a")
    assert stylesheet == BASE_STYLESHEET
    assert zoom is dash.no_update


def test_build_stats_text_counts_topics_levels_and_validated():
    topics = [
        Topic(name="A", description="d", level=0, validated=True),
        Topic(name="B", description="d", level=1, validated=False),
    ]
    assert _build_stats_text(topics) == "2 topics · 2 levels · 1 validated"


def test_build_stats_text_handles_empty_topics():
    assert _build_stats_text([]) == "0 topics · 0 levels · 0 validated"
