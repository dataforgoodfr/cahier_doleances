import pytest

from topicbuilder.app.cards import render_label_section, render_node_card
from topicbuilder.core.schemas import Label

NODE_DATA = {"label": "Water Cycle", "level": 1, "validated": "Yes", "description": "desc", "id": "abc"}


@pytest.mark.parametrize("validated, expected_color", [("Yes", "success"), ("No", "danger")])
def test_render_node_card_header_reflects_data_and_validated_status(validated, expected_color):
    header = render_node_card({**NODE_DATA, "validated": validated}).children[0]
    assert header.children[0].children == "Water Cycle"
    assert header.children[1].children == "Level 1"
    assert header.children[2].color == expected_color


@pytest.mark.parametrize(
    "labels, expected_first_child",
    [(None, None), ([Label(name="Water Cycle", rationale="r", extract="e")], "Label occurrences")],
)
def test_render_node_card_label_section_reflects_labels_presence(labels, expected_first_child):
    label_section = render_node_card(NODE_DATA, labels=labels).children[3]
    first_child = label_section.children[0].children if label_section.children else None
    assert first_child == expected_first_child


def test_render_label_section_creates_one_card_per_label_with_rationale_and_extract():
    labels = [
        Label(name="Water Cycle", rationale="r1", extract="e1"),
        Label(name="Water Cycle", rationale="r2", extract="e2"),
    ]
    cards = render_label_section(labels).children[1].children
    assert len(cards) == 2
    assert [card.children.children[0].children for card in cards] == ["r1", "r2"]
    assert [card.children.children[1].children.children for card in cards] == ["e1", "e2"]
