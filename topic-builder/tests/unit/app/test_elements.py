from topicbuilder.app.elements import build_elements
from topicbuilder.core.schemas import Topic


def test_build_elements_returns_one_node_per_topic():
    topics = [Topic(name="A", description="d"), Topic(name="B", description="d")]
    elements = build_elements(topics)
    nodes = [el for el in elements if "source" not in el["data"]]
    assert len(nodes) == 2


def test_build_elements_node_data_carries_expected_fields():
    topic = Topic(name="A", description="desc", level=2, validated=True)
    [node] = build_elements([topic])
    assert node["data"] == {
        "id": str(topic.id),
        "label": "A",
        "description": "desc",
        "validated": "Yes",
        "level": 2,
    }


def test_build_elements_falls_back_to_placeholder_description():
    topic = Topic(name="A", description="")
    [node] = build_elements([topic])
    assert node["data"]["description"] == "(no description)"


def test_build_elements_marks_unvalidated_topic_as_no():
    topic = Topic(name="A", description="d", validated=False)
    [node] = build_elements([topic])
    assert node["data"]["validated"] == "No"


def test_build_elements_creates_edge_for_known_parent():
    parent = Topic(name="P", description="d")
    child = Topic(name="C", description="d", parent=parent.id)
    elements = build_elements([parent, child])
    edges = [el for el in elements if "source" in el["data"]]
    assert edges == [{"data": {"source": str(parent.id), "target": str(child.id)}}]


def test_build_elements_omits_edge_for_dangling_parent_reference():
    child = Topic(name="C", description="d", parent=Topic(name="P", description="d").id)
    elements = build_elements([child])
    edges = [el for el in elements if "source" in el["data"]]
    assert edges == []


def test_build_elements_omits_edge_when_parent_is_none():
    topic = Topic(name="A", description="d")
    elements = build_elements([topic])
    edges = [el for el in elements if "source" in el["data"]]
    assert edges == []
