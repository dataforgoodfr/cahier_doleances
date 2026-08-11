import pytest

from topicbuilder.app.styles import BASE_STYLESHEET, LEVEL_COLORS, _level_selectors, build_highlight_stylesheet


@pytest.mark.parametrize(
    "level, expected_color",
    [(0, LEVEL_COLORS[0]), (len(LEVEL_COLORS) - 1, LEVEL_COLORS[-1]), (len(LEVEL_COLORS) + 1, LEVEL_COLORS[-1])],
)
def test_level_selectors_maps_level_to_palette_color(level: int, expected_color: str):
    selectors = _level_selectors()
    selector = next(s for s in selectors if s["selector"] == f"node[level = {level}]")
    assert selector["style"]["background-color"] == expected_color


def test_build_highlight_stylesheet_extends_base_and_highlights_selected_node():
    result = build_highlight_stylesheet("node-1")
    assert result[: len(BASE_STYLESHEET)] == BASE_STYLESHEET
    highlighted = next(s for s in result if s["selector"] == 'node[id = "node-1"]')
    assert highlighted["style"]["opacity"] == 1
    edge_selector = next(s for s in result if "edge[source" in s["selector"])
    assert 'edge[source = "node-1"]' in edge_selector["selector"]
    assert 'edge[target = "node-1"]' in edge_selector["selector"]
