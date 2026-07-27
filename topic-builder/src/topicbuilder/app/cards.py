import dash_bootstrap_components as dbc
from dash import html

from topicbuilder.core.schemas import Label


def render_node_card(data: dict, labels: list[Label] | None = None) -> html.Div:
    """
    Returns a styled card Div from a Cytoscape node data dict, optionally with label occurrences.
    """
    is_validated = data["validated"] == "Yes"
    validated_color = "success" if is_validated else "danger"

    header = html.Div(
        [
            html.H5(data["label"], className="mb-2"),
            dbc.Badge(f"Level {data['level']}", color="primary", className="me-1"),
            dbc.Badge(f"validated: {data['validated']}", color=validated_color),
        ],
        className="mb-2",
    )
    description = html.P(data["description"], className="text-body-secondary", style={"lineHeight": "1.6"})
    footer = html.Small(f"id: {data['id']}", className="text-muted")

    label_section = render_label_section(labels) if labels else html.Div()

    return html.Div([header, html.Hr(className="my-2"), description, label_section, html.Hr(className="my-2"), footer])


def render_label_section(labels: list[Label]) -> html.Div:
    """
    Returns a section listing label occurrences (rationale + extract) for a topic node.
    """
    cards = [
        dbc.Card(
            dbc.CardBody(
                [
                    html.P(label.rationale, className="mb-1 fw-semibold small"),
                    html.Blockquote(
                        html.P(label.extract, className="mb-0 fst-italic small"),
                        className="blockquote border-start border-2 ps-2 text-muted",
                    ),
                ]
            ),
            className="mb-2",
        )
        for label in labels
    ]
    return html.Div(
        [
            html.H6("Label occurrences", className="mt-3 mb-2 text-secondary"),
            html.Div(cards),
        ]
    )
