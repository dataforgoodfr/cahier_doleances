import pytest
from dash import html

from topicbuilder.app.cards import render_label_section, render_node_card
from topicbuilder.core.schemas import Label

NODE_DATA = {"label": "Water Cycle", "level": 1, "validated": "Yes", "description": "desc", "id": "abc"}


def test_render_node_card_header_carries_label_and_level():
    header = render_node_card(NODE_DATA).children[0]
    assert header.children[0].children == "Water Cycle"
    assert header.children[1].children == "Level 1"


@pytest.mark.parametrize("validated, expected_color", [("Yes", "success"), ("No", "danger")])
def test_render_node_card_validated_badge_color_matches_status(validated, expected_color):
    data = {**NODE_DATA, "validated": validated}
    header = render_node_card(data).children[0]
    assert header.children[2].color == expected_color


def test_render_node_card_uses_empty_div_when_no_labels():
    label_section = render_node_card(NODE_DATA, labels=None).children[3]
    assert isinstance(label_section, html.Div)
    assert label_section.children is None


def test_render_node_card_uses_label_section_when_labels_present():
    labels = [Label(name="Water Cycle", rationale="r", extract="e")]
    label_section = render_node_card(NODE_DATA, labels=labels).children[3]
    assert label_section.children[0].children == "Label occurrences"


def test_render_label_section_creates_one_card_per_label():
    labels = [
        Label(name="Water Cycle", rationale="r1", extract="e1"),
        Label(name="Water Cycle", rationale="r2", extract="e2"),
    ]
    cards_container = render_label_section(labels).children[1]
    assert len(cards_container.children) == 2


def test_render_label_section_includes_rationale_and_extract_text():
    labels = [Label(name="Water Cycle", rationale="my rationale", extract="my extract")]
    [card] = render_label_section(labels).children[1].children
    body_children = card.children.children
    assert body_children[0].children == "my rationale"
    assert body_children[1].children.children == "my extract"
