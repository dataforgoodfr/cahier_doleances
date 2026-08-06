import json
from types import SimpleNamespace

from topicbuilder.core.schemas import Label, ParentAddition, ParentCandidate, Taxonomy, Topic, TopicMerge


def _make_tool_response(tool_name: str, arguments: dict) -> SimpleNamespace:
    """
    Build a minimal fake OpenAI ChatCompletion response carrying a single forced tool call.
    """
    tool_call = SimpleNamespace(function=SimpleNamespace(name=tool_name, arguments=json.dumps(arguments)))
    message = SimpleNamespace(tool_calls=[tool_call])
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def make_discover_topics_response(topics: list[Topic]) -> SimpleNamespace:
    """
    Build a minimal fake OpenAI response carrying a record_new_topics tool call.
    """
    return _make_tool_response(
        "record_new_topics",
        {"topics": [{"name": t.name, "description": t.description} for t in topics]},
    )


def make_merge_candidates_response(groups: list[Taxonomy]) -> SimpleNamespace:
    """
    Build a minimal fake OpenAI response carrying a propose_merge_candidates tool call.
    """
    return _make_tool_response(
        "propose_merge_candidates",
        {"groups": [{"names": [t.name for t in g.topics]} for g in groups]},
    )


def make_merges_response(merge: TopicMerge | None) -> SimpleNamespace:
    """
    Build a minimal fake OpenAI response carrying a record_merges tool call.
    """
    if merge:
        args = {"target": merge.target.name, "sources": [s.name for s in merge.sources.topics]}
    else:
        args = {"target": "", "sources": []}
    return _make_tool_response("record_merges", args)


def make_parent_candidates_response(candidates: list[ParentCandidate]) -> SimpleNamespace:
    """
    Build a minimal fake OpenAI response carrying a propose_parent_candidates tool call.
    """
    return _make_tool_response(
        "propose_parent_candidates",
        {"candidates": [{"parent": c.parent, "children": [t.name for t in c.children.topics]} for c in candidates]},
    )


def make_parent_response(addition: ParentAddition) -> SimpleNamespace:
    """
    Build a minimal fake OpenAI response carrying a record_parent tool call.
    """
    return _make_tool_response(
        "record_parent",
        {
            "parent": addition.parent.name,
            "description": addition.parent.description,
            "children": [t.name for t in addition.children.topics],
        },
    )


def make_label_response(topics: list[Label]) -> SimpleNamespace:
    """
    Build a minimal fake OpenAI response carrying a record_labeled_topics tool call.
    """
    return _make_tool_response(
        "record_labeled_topics",
        {"topics": [t.model_dump() for t in topics]},
    )
