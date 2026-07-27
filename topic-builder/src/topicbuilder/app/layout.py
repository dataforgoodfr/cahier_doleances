import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from dash import dcc, html

from topicbuilder.app.styles import BASE_STYLESHEET, LEVEL_COLORS


def build_layout(elements: list[dict], search_options: list[dict], stats: dict, max_level: int) -> html.Div:
    """
    Returns the full Dash layout for the graph viewer using dash-bootstrap-components.
    """
    return html.Div(
        className="app-shell",
        children=[
            build_topbar(stats),
            build_toolbar(search_options, max_level),
            build_workspace(elements),
            dcc.Store(id="all-elements", data=elements),
            dcc.Store(id="detail-open", data=True),
            dcc.Store(id="legend-open", data=False),
        ],
    )


def build_topbar(stats: dict) -> dbc.Navbar:
    """
    Returns a Bootstrap navbar with the app title and a stats summary.
    """
    stats_text = f"{stats['topics']} topics · {stats['levels']} levels · {stats['validated']} validated"
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand("Knowledge Graph Viewer", className="fw-bold me-4"),
                html.Span(id="stats-bar", children=stats_text, className="text-light opacity-75 small"),
            ],
            fluid=True,
        ),
        color="primary",
        dark=True,
        className="topbar py-2",
    )


def build_toolbar(search_options: list[dict], max_level: int) -> html.Div:
    """
    Returns the toolbar row with layout switcher, search, filters, and toggle buttons.
    """
    slider_max = max(max_level, 1)
    return html.Div(
        className="toolbar",
        children=[
            html.Div(
                className="toolbar__group toolbar__search",
                children=[
                    dcc.Dropdown(
                        id="search-dropdown",
                        options=search_options,
                        placeholder="🔍 Search node…",
                        clearable=True,
                        searchable=True,
                        className="toolbar__select",
                    ),
                ],
            ),
            html.Div(
                className="toolbar__group",
                children=[
                    html.Label("Min level", className="toolbar__label"),
                    dcc.Slider(
                        id="level-filter",
                        min=0,
                        max=slider_max,
                        step=1,
                        value=0,
                        marks={i: str(i) for i in range(slider_max + 1)},
                        className="toolbar__slider",
                    ),
                ],
            ),
            html.Div(
                className="toolbar__group",
                children=[
                    html.Label("Validated", className="toolbar__label"),
                    dcc.Dropdown(
                        id="validated-filter",
                        options=[
                            {"label": "All", "value": "all"},
                            {"label": "Validated", "value": "Yes"},
                            {"label": "Unvalidated", "value": "No"},
                        ],
                        value="all",
                        clearable=False,
                        className="toolbar__select toolbar__select--narrow",
                    ),
                ],
            ),
            html.Div(
                className="toolbar__group toolbar__buttons",
                children=[
                    dbc.Button(
                        "Legend", id="legend-toggle", size="sm", outline=True, color="secondary", className="me-1"
                    ),
                    dbc.Button(
                        "Details", id="detail-toggle", size="sm", outline=True, color="secondary", className="me-1"
                    ),
                    dbc.Button("⟳ Reload", id="reload-btn", size="sm", outline=True, color="primary"),
                ],
            ),
        ],
    )


def build_workspace(elements: list[dict]) -> html.Div:
    """
    Returns the workspace row containing the graph pane and the detail panel.
    """
    return html.Div(
        className="workspace",
        children=[
            build_graph_pane(elements),
            build_detail_panel(),
        ],
    )


def build_graph_pane(elements: list[dict]) -> html.Div:
    """
    Returns the graph pane containing the Cytoscape canvas and the legend overlay.
    """
    return html.Div(
        className="graph-pane",
        children=[
            cyto.Cytoscape(
                id="kg-graph",
                elements=elements,
                stylesheet=BASE_STYLESHEET,
                layout={"name": "cose-bilkent", "animate": True},
                autoRefreshLayout=True,
                style={"width": "100%", "height": "100%"},
                minZoom=0.2,
                maxZoom=3,
                wheelSensitivity=0.2,
            ),
            build_legend(),
        ],
    )


def build_legend() -> html.Div:
    """
    Returns the legend overlay card explaining node colors and shapes.
    """
    level_labels = ["Level 0", "Level 1", "Level 2", "Level 3", "Level 4+"]
    level_rows = [
        html.Div(
            className="legend__row",
            children=[
                html.Span(style={"background": color}, className="legend__swatch"),
                html.Span(label, className="small"),
            ],
        )
        for label, color in zip(level_labels, LEVEL_COLORS, strict=True)
    ]
    return html.Div(
        id="legend",
        className="legend legend--hidden",
        children=[
            html.H6("Legend", className="mb-2 fw-bold"),
            *level_rows,
            html.Div(
                className="legend__row",
                children=[
                    html.Span(className="legend__swatch legend__swatch--selected"),
                    html.Span("Selected", className="small"),
                ],
            ),
        ],
    )


def build_detail_panel() -> html.Div:
    """
    Returns the collapsible detail panel that shows node metadata and label occurrences.
    """
    return html.Div(
        id="detail-panel",
        className="detail-panel",
        children=[
            html.H5("Node Details", className="detail-panel__title"),
            html.Div(
                id="node-info",
                children=html.P(
                    "Hover over, click, or search a node to see details.",
                    className="text-muted small",
                ),
            ),
        ],
    )
