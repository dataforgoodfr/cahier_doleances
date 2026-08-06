from topicbuilder.app.styles import BASE_STYLESHEET, LEVEL_COLORS, _level_selectors, build_highlight_stylesheet


def test_level_selectors_maps_each_level_to_its_own_color():
    selectors = _level_selectors()
    for lvl in range(len(LEVEL_COLORS)):
        selector = next(s for s in selectors if s["selector"] == f"node[level = {lvl}]")
        assert selector["style"]["background-color"] == LEVEL_COLORS[lvl]


def test_level_selectors_reuses_last_color_beyond_palette():
    selectors = _level_selectors()
    overflow_level = len(LEVEL_COLORS) + 1
    selector = next(s for s in selectors if s["selector"] == f"node[level = {overflow_level}]")
    assert selector["style"]["background-color"] == LEVEL_COLORS[-1]


def test_build_highlight_stylesheet_extends_base_stylesheet():
    result = build_highlight_stylesheet("node-1")
    assert result[: len(BASE_STYLESHEET)] == BASE_STYLESHEET


def test_build_highlight_stylesheet_highlights_selected_node():
    result = build_highlight_stylesheet("node-1")
    highlighted = next(s for s in result if s["selector"] == 'node[id = "node-1"]')
    assert highlighted["style"]["opacity"] == 1


def test_build_highlight_stylesheet_connects_edges_touching_selected_node():
    result = build_highlight_stylesheet("node-1")
    edge_selector = next(s for s in result if "edge[source" in s["selector"])
    assert 'edge[source = "node-1"]' in edge_selector["selector"]
    assert 'edge[target = "node-1"]' in edge_selector["selector"]
