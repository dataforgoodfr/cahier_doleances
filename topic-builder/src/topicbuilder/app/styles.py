import dash_cytoscape as cyto

cyto.load_extra_layouts()

LEVEL_COLORS = [
    "#4C78A8",  # level 0: blue
    "#E45756",  # level 1: red
    "#F58518",  # level 2: orange
    "#F2BE45",  # level 3: yellow-orange
    "#EECA3B",  # level 4+: yellow
]


def _level_selectors() -> list[dict]:
    """
    Returns Cytoscape node selectors that color nodes by their level field.
    Levels beyond the palette reuse the last palette entry.
    """
    return [
        {
            "selector": f"node[level = {lvl}]",
            "style": {"background-color": LEVEL_COLORS[min(lvl, len(LEVEL_COLORS) - 1)]},
        }
        for lvl in range(len(LEVEL_COLORS) + 3)
    ]


BASE_STYLESHEET = [
    {
        "selector": "node",
        "style": {
            "content": "data(label)",
            "font-size": "11px",
            "text-wrap": "wrap",
            "text-max-width": "120px",
            "text-valign": "center",
            "text-halign": "center",
            "background-color": LEVEL_COLORS[0],
            "color": "#ffffff",
            "width": "label",
            "height": "label",
            "padding": "10px",
            "shape": "round-rectangle",
        },
    },
    *_level_selectors(),
    {
        "selector": "edge",
        "style": {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "target-arrow-color": "#999",
            "line-color": "#bbb",
            "width": 1.5,
        },
    },
    {
        "selector": ":selected",
        "style": {
            "border-width": 3,
            "border-color": "#F58518",
        },
    },
]


def build_highlight_stylesheet(selected_id: str) -> list[dict]:
    """
    Returns a Cytoscape stylesheet that highlights the selected node and dims all others.
    """
    return BASE_STYLESHEET + [
        {"selector": "node", "style": {"opacity": 0.25}},
        {"selector": "edge", "style": {"opacity": 0.1}},
        {
            "selector": f'node[id = "{selected_id}"]',
            "style": {
                "opacity": 1,
                "border-width": 4,
                "border-color": "#F58518",
                "background-color": "#F58518",
                "z-index": 9999,
            },
        },
        {
            "selector": f'edge[source = "{selected_id}"], edge[target = "{selected_id}"]',
            "style": {"opacity": 0.7, "line-color": "#F58518", "target-arrow-color": "#F58518", "width": 2.5},
        },
    ]
