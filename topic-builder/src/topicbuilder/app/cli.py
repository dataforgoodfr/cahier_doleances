from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import typer

from topicbuilder.app.callbacks import register_callbacks
from topicbuilder.app.elements import build_elements
from topicbuilder.app.layout import build_layout
from topicbuilder.core.io import read_labeled_dataset, read_taxonomy
from topicbuilder.core.schemas import Label, LabeledDataset


def display(
    taxonomy_path: Path = typer.Option(
        ...,
        "--taxonomy-path",
        help="Path to the taxonomy JSON file to visualise.",
    ),
    labels_path: Path | None = typer.Option(
        None,
        "--labels-path",
        help="Optional path to a labeled-dataset JSON to show per-topic summaries and extracts.",
    ),
    debug: bool = typer.Option(
        False,
        help="Run the Dash server in debug mode.",
    ),
    port: int = typer.Option(
        8050,
        help="Port to listen on.",
    ),
) -> None:
    """
    Launch the knowledge-graph viewer in a local browser tab.
    """
    build_app(taxonomy_path, labels_path).run(debug=debug, port=port)
    return


def build_app(taxonomy_path: Path, labels_path: Path | None = None) -> dash.Dash:
    """
    Loads taxonomy (and optionally label results) and returns a configured Dash app.
    """
    topics = read_taxonomy(taxonomy_path).topics
    elements = build_elements(topics)
    search_options = sorted(
        [{"label": t.name, "value": str(t.id)} for t in topics],
        key=lambda o: o["label"].lower(),
    )
    node_data_by_id = {el["data"]["id"]: el["data"] for el in elements if "id" in el.get("data", {})}
    max_level = max((t.level for t in topics), default=0)
    stats = {
        "topics": len(topics),
        "levels": len({t.level for t in topics}),
        "validated": sum(1 for t in topics if t.validated),
    }

    labeled_dataset: LabeledDataset | None = read_labeled_dataset(labels_path) if labels_path else None
    labels_by_topic_name: dict[str, list[Label]] = _build_labels_index(labeled_dataset)

    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.FLATLY],
    )
    app.title = "Knowledge Graph Viewer"
    app.layout = build_layout(elements, search_options, stats, max_level)
    register_callbacks(app, node_data_by_id, taxonomy_path, labels_by_topic_name)
    return app


def _build_labels_index(labeled_dataset: LabeledDataset | None) -> dict[str, list[Label]]:
    """
    Builds a topic-name → list[Label] index from a LabeledDataset, or returns an empty dict.
    """
    if not labeled_dataset:
        return {}
    index: dict[str, list[Label]] = {}
    for doc_labels in labeled_dataset.documents:
        for label in doc_labels.labels:
            index.setdefault(label.name, []).append(label)
    return index
