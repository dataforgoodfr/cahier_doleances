from pathlib import Path

import dash
from dash import Input, Output, State, html

from topicbuilder.app.cards import render_node_card
from topicbuilder.app.elements import build_elements
from topicbuilder.app.styles import BASE_STYLESHEET, build_highlight_stylesheet
from topicbuilder.core.io import read_taxonomy
from topicbuilder.core.schemas import Label, Topic


def register_callbacks(
    app: dash.Dash,
    node_data_by_id: dict[str, dict],
    taxonomy_path: Path,
    labels_by_topic_name: dict[str, list[Label]],
) -> None:
    """
    Registers all Dash callbacks on the app instance.
    """

    @app.callback(
        Output("all-elements", "data"),
        Output("stats-bar", "children"),
        Input("reload-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def reload_taxonomy(_n_clicks: int | None) -> tuple:
        """
        Re-reads the taxonomy from disk and refreshes the element store and stats bar.
        """
        topics = read_taxonomy(taxonomy_path).topics
        all_elements = build_elements(topics)
        return all_elements, _build_stats_text(topics)

    @app.callback(
        Output("kg-graph", "elements"),
        Output("kg-graph", "stylesheet"),
        Output("kg-graph", "zoom"),
        Output("kg-graph", "layout"),
        Input("all-elements", "data"),
        Input("search-dropdown", "value"),
        Input("level-filter", "value"),
        Input("validated-filter", "value"),
    )
    def filter_and_search(
        all_elements: list[dict],
        search_id: str | None,
        min_level: int,
        validated_filter: str,
    ) -> tuple:
        """
        Filters nodes by min level/validated and highlights the searched node; sole owner of kg-graph elements.
        """
        elements, stylesheet, zoom = _apply_filters_and_search(all_elements, min_level, validated_filter, search_id)
        layout = {"name": "cose-bilkent", "animate": True}
        return elements, stylesheet, zoom, layout

    @app.callback(
        Output("node-info", "children"),
        Input("kg-graph", "mouseoverNodeData"),
        Input("kg-graph", "tapNodeData"),
        Input("search-dropdown", "value"),
    )
    def display_node_data(
        hover_data: dict | None,
        tap_data: dict | None,
        search_id: str | None,
    ) -> dash.development.base_component.Component:
        """
        Renders the detail card for the currently active node.
        """
        trigger = dash.callback_context.triggered[0]["prop_id"] if dash.callback_context.triggered else ""

        if "search-dropdown" in trigger and search_id:
            node_data = node_data_by_id.get(search_id)
            if node_data:
                return render_node_card(node_data, labels_by_topic_name.get(node_data["label"]))
            return dash.no_update

        data = tap_data if "tapNodeData" in trigger else hover_data
        data = data or tap_data or hover_data
        if not data:
            return html.P("Hover over, click, or search a node to see details.", className="text-muted small")
        return render_node_card(data, labels_by_topic_name.get(data["label"]))

    @app.callback(
        Output("legend", "className"),
        Output("legend-open", "data"),
        Input("legend-toggle", "n_clicks"),
        State("legend-open", "data"),
    )
    def toggle_legend(n_clicks: int | None, is_open: bool) -> tuple:
        """
        Toggles the legend overlay visibility and tracks its open state.
        """
        new_open = (not is_open) if n_clicks else is_open
        class_name = "legend" if new_open else "legend legend--hidden"
        return class_name, new_open

    @app.callback(
        Output("detail-panel", "className"),
        Output("detail-open", "data"),
        Input("detail-toggle", "n_clicks"),
        State("detail-open", "data"),
    )
    def toggle_detail(n_clicks: int | None, is_open: bool) -> tuple:
        """
        Toggles the detail panel visibility and tracks its open state.
        """
        new_open = (not is_open) if n_clicks else is_open
        class_name = "detail-panel" if new_open else "detail-panel detail-panel--collapsed"
        return class_name, new_open

    return


def _apply_filters_and_search(
    all_elements: list[dict],
    min_level: int,
    validated_filter: str,
    search_id: str | None,
) -> tuple[list[dict], list[dict], object]:
    """
    Applies node filters and search highlight, returning (elements, stylesheet, zoom).
    """
    nodes = [el for el in all_elements if "source" not in el.get("data", {})]
    edges = [el for el in all_elements if "source" in el.get("data", {})]

    if min_level:
        nodes = [n for n in nodes if n["data"].get("level", 0) >= min_level]
    if validated_filter != "all":
        nodes = [n for n in nodes if n["data"].get("validated") == validated_filter]

    surviving_ids = {n["data"]["id"] for n in nodes}
    visible_edges = [e for e in edges if e["data"]["source"] in surviving_ids and e["data"]["target"] in surviving_ids]

    if not search_id or search_id not in surviving_ids:
        clean_nodes = [{k: v for k, v in n.items() if k != "selected"} for n in nodes]
        return clean_nodes + visible_edges, BASE_STYLESHEET, dash.no_update

    tagged_nodes = [
        {**n, "selected": True} if n["data"]["id"] == search_id else {k: v for k, v in n.items() if k != "selected"}
        for n in nodes
    ]
    return tagged_nodes + visible_edges, build_highlight_stylesheet(search_id), 1.5


def _build_stats_text(topics: list[Topic]) -> str:
    """
    Returns a human-readable stats summary string from a list of Topic objects.
    """
    n_levels = len({t.level for t in topics})
    n_validated = sum(1 for t in topics if t.validated)
    return f"{len(topics)} topics · {n_levels} levels · {n_validated} validated"
