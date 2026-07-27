from topicbuilder.core.schemas import Topic


def build_elements(topics: list[Topic]) -> list[dict]:
    """
    Converts a list of Topic objects into Cytoscape node + edge elements.
    """
    known_ids = {str(t.id) for t in topics}
    nodes = [
        {
            "data": {
                "id": str(t.id),
                "label": t.name,
                "description": t.description or "(no description)",
                "validated": "Yes" if t.validated else "No",
                "level": t.level,
            }
        }
        for t in topics
    ]
    edges = [
        {"data": {"source": str(t.parent), "target": str(t.id)}}
        for t in topics
        if t.parent is not None and str(t.parent) in known_ids
    ]
    return nodes + edges
