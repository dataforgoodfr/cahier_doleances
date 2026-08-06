import pytest

from topicbuilder.app.elements import build_elements
from topicbuilder.core.schemas import Topic


@pytest.mark.parametrize(
    "description, validated, expected_description, expected_validated",
    [
        ("desc", True, "desc", "Yes"),
        ("", True, "(no description)", "Yes"),
        ("desc", False, "desc", "No"),
    ],
)
def test_build_elements_node_data_maps_topic_fields(
    description: str, validated: bool, expected_description: str, expected_validated: str
):
    """
    Verifies node data reflects topic fields, including the description placeholder fallback
    and the validated flag mapping to "Yes"/"No".
    """
    topic = Topic(name="A", description=description, level=2, validated=validated)
    [node] = build_elements([topic])
    assert node["data"] == {
        "id": str(topic.id),
        "label": "A",
        "description": expected_description,
        "validated": expected_validated,
        "level": 2,
    }


@pytest.mark.parametrize("case", ["known_parent", "dangling_parent", "no_parent"])
def test_build_elements_creates_edge_only_for_known_parent(case: str):
    """
    Verifies an edge is created only when a topic's parent id matches another topic in the
    list, and that exactly one node is produced per input topic regardless of parent linkage.
    """
    parent = Topic(name="P", description="d")
    parent_id = {
        "known_parent": parent.id,
        "dangling_parent": Topic(name="P2", description="d").id,
        "no_parent": None,
    }[case]
    child = Topic(name="C", description="d", parent=parent_id)
    topics = [parent, child] if case == "known_parent" else [child]
    elements = build_elements(topics)
    nodes = [el for el in elements if "source" not in el["data"]]
    edges = [el for el in elements if "source" in el["data"]]
    expected_edges = [{"data": {"source": str(parent.id), "target": str(child.id)}}] if case == "known_parent" else []
    assert len(nodes) == len(topics)
    assert edges == expected_edges
