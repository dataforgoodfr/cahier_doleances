from uuid import uuid4

import pytest

from topicbuilder.core.schemas import Taxonomy, Topic
from topicbuilder.core.taxonomy import (
    CycleViolation,
    MultiPath,
    SanityReport,
    build_graph,
    check_taxonomy,
    clear_dangling_parents,
    clear_self_parents,
    drop_blank_names,
    find_cycles,
    find_dangling_parents,
    find_duplicate_names,
    find_empty_fields,
    find_multi_path_pairs,
    find_self_parents,
    format_violations,
    merge_name_duplicates,
    sanitize_taxonomy,
)


def test_find_duplicate_names_reports_repeated_names():
    taxonomy = Taxonomy(topics=[Topic(name="A", description="d"), Topic(name="A", description="d2")])
    assert find_duplicate_names(taxonomy) == ["A"]


def test_find_duplicate_names_returns_empty_for_unique_names():
    taxonomy = Taxonomy(topics=[Topic(name="A", description="d"), Topic(name="B", description="d")])
    assert find_duplicate_names(taxonomy) == []


def test_find_dangling_parents_reports_missing_parent():
    from uuid import uuid4

    dangling_id = uuid4()
    taxonomy = Taxonomy(topics=[Topic(name="A", description="d", parent=dangling_id)])
    assert find_dangling_parents(taxonomy) == [("A", str(dangling_id))]


def test_find_dangling_parents_ignores_null_parent():
    taxonomy = Taxonomy(topics=[Topic(name="A", description="d")])
    assert find_dangling_parents(taxonomy) == []


def test_find_dangling_parents_ignores_valid_parent():
    b = Topic(name="B", description="d")
    a = Topic(name="A", description="d", parent=b.id)
    taxonomy = Taxonomy(topics=[a, b])
    assert find_dangling_parents(taxonomy) == []


def test_find_self_parents_reports_self_reference():
    t = Topic(name="A", description="d")
    t = t.model_copy(update={"parent": t.id})
    taxonomy = Taxonomy(topics=[t])
    assert find_self_parents(taxonomy) == ["A"]


def test_find_self_parents_returns_empty_for_no_self_reference():
    taxonomy = Taxonomy(topics=[Topic(name="A", description="d")])
    assert find_self_parents(taxonomy) == []


def test_find_empty_fields_reports_blank_name():
    taxonomy = Taxonomy(topics=[Topic(name="", description="d")])
    violations = find_empty_fields(taxonomy)
    assert any(f == "name" for _, f in violations)


def test_find_empty_fields_reports_whitespace_description():
    taxonomy = Taxonomy(topics=[Topic(name="A", description="   ")])
    assert ("A", "description") in find_empty_fields(taxonomy)


def test_find_empty_fields_returns_empty_for_valid_fields():
    taxonomy = Taxonomy(topics=[Topic(name="A", description="valid")])
    assert find_empty_fields(taxonomy) == []


def test_find_cycles_detects_two_node_cycle():
    a = Topic(name="A", description="d")
    b = Topic(name="B", description="d")
    a = a.model_copy(update={"parent": b.id})
    b = b.model_copy(update={"parent": a.id})
    taxonomy = Taxonomy(topics=[a, b])
    graph, id_to_name = build_graph(taxonomy)
    cycles = find_cycles(graph, id_to_name)
    assert len(cycles) == 1
    assert set(cycles[0].path[:-1]) == {"A", "B"}


def test_find_cycles_detects_self_cycle():
    t = Topic(name="A", description="d")
    t = t.model_copy(update={"parent": t.id})
    taxonomy = Taxonomy(topics=[t])
    graph, id_to_name = build_graph(taxonomy)
    assert len(find_cycles(graph, id_to_name)) == 1


def test_find_cycles_returns_empty_for_acyclic_graph():
    b = Topic(name="B", description="d")
    a = Topic(name="A", description="d", parent=b.id)
    taxonomy = Taxonomy(topics=[a, b])
    graph, id_to_name = build_graph(taxonomy)
    assert find_cycles(graph, id_to_name) == []


def test_find_cycles_detects_longer_cycle():
    a = Topic(name="A", description="d")
    b = Topic(name="B", description="d")
    c = Topic(name="C", description="d")
    a = a.model_copy(update={"parent": b.id})
    b = b.model_copy(update={"parent": c.id})
    c = c.model_copy(update={"parent": a.id})
    taxonomy = Taxonomy(topics=[a, b, c])
    graph, id_to_name = build_graph(taxonomy)
    cycles = find_cycles(graph, id_to_name)
    assert len(cycles) == 1
    assert set(cycles[0].path[:-1]) == {"A", "B", "C"}


def test_find_multi_path_pairs_returns_empty_for_tree():
    root = Topic(name="Root", description="d")
    leaf = Topic(name="Leaf", description="d", parent=root.id)
    taxonomy = Taxonomy(topics=[leaf, root])
    graph, id_to_name = build_graph(taxonomy)
    assert find_multi_path_pairs(graph, id_to_name) == []


def test_find_multi_path_pairs_returns_empty_for_isolated_nodes():
    taxonomy = Taxonomy(topics=[Topic(name="A", description="d"), Topic(name="B", description="d")])
    graph, id_to_name = build_graph(taxonomy)
    assert find_multi_path_pairs(graph, id_to_name) == []


# Pre-computed module-level fixtures for the parametrize below
_dup_names_taxonomy = Taxonomy(topics=[Topic(name="A", description="d"), Topic(name="A", description="d2")])

_dangling_parent_topic = Topic(name="A", description="d")

_dangling_parent_topic = _dangling_parent_topic.model_copy(update={"parent": uuid4()})
_dangling_taxonomy = Taxonomy(topics=[_dangling_parent_topic])

_self_parent_topic = Topic(name="A", description="d")
_self_parent_topic = _self_parent_topic.model_copy(update={"parent": _self_parent_topic.id})
_self_parent_taxonomy = Taxonomy(topics=[_self_parent_topic])

_cycle_a = Topic(name="A", description="d")
_cycle_b = Topic(name="B", description="d")
_cycle_a = _cycle_a.model_copy(update={"parent": _cycle_b.id})
_cycle_b = _cycle_b.model_copy(update={"parent": _cycle_a.id})
_cycle_taxonomy = Taxonomy(topics=[_cycle_a, _cycle_b])


def test_run_checks_is_tree_true_for_clean_taxonomy():
    root = Topic(name="Root", description="d")
    child = Topic(name="Child", description="d", parent=root.id)
    taxonomy = Taxonomy(topics=[child, root])
    report = check_taxonomy(taxonomy)
    assert report.is_tree is True
    assert not report.has_violations()


@pytest.mark.parametrize(
    "taxonomy",
    [
        _dup_names_taxonomy,
        _dangling_taxonomy,
        _self_parent_taxonomy,
        _cycle_taxonomy,
    ],
)
def test_run_checks_is_tree_false_when_violations_present(taxonomy):
    assert check_taxonomy(taxonomy).is_tree is False


def test_run_checks_skips_multipath_when_cycle_present():
    a = Topic(name="A", description="d")
    b = Topic(name="B", description="d")
    a = a.model_copy(update={"parent": b.id})
    b = b.model_copy(update={"parent": a.id})
    taxonomy = Taxonomy(topics=[a, b])
    report = check_taxonomy(taxonomy)
    assert report.cycles
    assert report.multi_path_pairs == []


def test_sanity_report_has_violations_false_when_clean():
    report = SanityReport(
        is_tree=True,
        duplicate_names=[],
        dangling_parents=[],
        self_parents=[],
        empty_fields=[],
        cycles=[],
        multi_path_pairs=[],
    )
    assert report.has_violations() is False


def test_sanity_report_has_violations_true_when_cycles():
    report = SanityReport(
        is_tree=False,
        duplicate_names=[],
        dangling_parents=[],
        self_parents=[],
        empty_fields=[],
        cycles=[CycleViolation(path=["A", "B", "A"])],
        multi_path_pairs=[],
    )
    assert report.has_violations() is True


def _clean_report(**overrides) -> SanityReport:
    base = {
        "is_tree": True,
        "duplicate_names": [],
        "dangling_parents": [],
        "self_parents": [],
        "empty_fields": [],
        "cycles": [],
        "multi_path_pairs": [],
    }
    return SanityReport(**{**base, **overrides})


@pytest.mark.parametrize(
    "field, value, expected_fragment",
    [
        ("duplicate_names", ["A"], "Duplicate"),
        ("dangling_parents", [("A", "Ghost")], "Dangling"),
        ("self_parents", ["A"], "Self-parents"),
        ("empty_fields", [("A", "description")], "Empty fields"),
        ("cycles", [CycleViolation(path=["A", "B", "A"])], "Cycles"),
        ("multi_path_pairs", [MultiPath(source="A", target="B", paths=[["A", "B"], ["A", "C", "B"]])], "Multi-path"),
    ],
)
def test_format_violations_includes_section_for_each_violation_type(field, value, expected_fragment):
    report = _clean_report(**{field: value})
    assert expected_fragment in format_violations(report)


def test_format_violations_header_always_present():
    report = _clean_report(duplicate_names=["A"])
    assert "sanity check failed" in format_violations(report).lower()


# --- sanitize_taxonomy ---


def test_sanitize_taxonomy_removes_same_name_same_level():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="first", level=0),
            Topic(name="B", description="d", level=0),
            Topic(name="A", description="second", level=0),
        ]
    )
    result = sanitize_taxonomy(taxonomy)
    assert [t.name for t in result.topics] == ["A", "B"]


def test_sanitize_taxonomy_keeps_first_occurrence():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="first", level=0),
            Topic(name="A", description="second", level=0),
        ]
    )
    assert sanitize_taxonomy(taxonomy).topics[0].description == "first"


def test_sanitize_taxonomy_no_duplicates_unchanged():
    taxonomy = Taxonomy(topics=[Topic(name="A", description="d"), Topic(name="B", description="d")])
    assert [t.name for t in sanitize_taxonomy(taxonomy).topics] == ["A", "B"]


def test_sanitize_taxonomy_empty_taxonomy():
    assert sanitize_taxonomy(Taxonomy(topics=[])).topics == []


def test_sanitize_taxonomy_same_name_different_level_keeps_highest():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="low", level=0),
            Topic(name="A", description="high", level=1),
        ]
    )
    result = sanitize_taxonomy(taxonomy)
    assert len(result.topics) == 1
    assert result.topics[0].level == 1


def test_sanitize_taxonomy_same_name_different_level_preserves_first_occurrence_position():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d", level=0),
            Topic(name="B", description="d", level=0),
            Topic(name="A", description="d", level=2),
        ]
    )
    result = sanitize_taxonomy(taxonomy)
    assert [t.name for t in result.topics] == ["A", "B"]
    assert result.topics[0].level == 2


def test_sanitize_taxonomy_cross_level_parent_references_consistent():
    parent_topic = Topic(name="Parent", description="d", level=2)
    taxonomy = Taxonomy(
        topics=[
            Topic(name="Child", description="d", level=0, parent=parent_topic.id),
            Topic(name="Child", description="d", level=1),
            parent_topic,
        ]
    )
    result = sanitize_taxonomy(taxonomy)
    child = next(t for t in result.topics if t.name == "Child")
    assert child.level == 1
    assert any(t.name == "Parent" for t in result.topics)


def test_sanitize_taxonomy_survivor_inherits_parent_from_discard():
    # The inherited parent id exists in the taxonomy, so it survives the dangling-parent pass.
    real_parent = Topic(name="P", description="d", level=1)
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d", level=0, parent=None),
            Topic(name="A", description="d", level=0, parent=real_parent.id),
            real_parent,
        ]
    )
    result = sanitize_taxonomy(taxonomy)
    a = next(t for t in result.topics if t.name == "A")
    assert a.parent == real_parent.id


def test_sanitize_taxonomy_survivor_parent_not_overridden():
    # Both parent ids are absent from the taxonomy; survivor keeps its own (both become None).
    # Use a real parent topic so the assertion is meaningful.
    real_parent_q = Topic(name="Q", description="d", level=1)
    real_parent_p = Topic(name="P", description="d", level=1)
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="d", level=0, parent=real_parent_q.id),
            Topic(name="A", description="d", level=0, parent=real_parent_p.id),
            real_parent_q,
            real_parent_p,
        ]
    )
    result = sanitize_taxonomy(taxonomy)
    a = next(t for t in result.topics if t.name == "A")
    assert a.parent == real_parent_q.id


def test_sanitize_taxonomy_remaps_dropped_id_to_survivor():
    # Child's parent points to the id of a duplicate that will be dropped;
    # after sanitize_taxonomy, child.parent must point to the survivor's id.
    parent_v1 = Topic(name="P", description="first", level=0)
    parent_v2 = Topic(name="P", description="second", level=0)  # will be dropped
    child = Topic(name="Child", description="d", level=0, parent=parent_v2.id)
    taxonomy = Taxonomy(topics=[parent_v1, parent_v2, child])
    result = sanitize_taxonomy(taxonomy)
    survivor = next(t for t in result.topics if t.name == "P")
    result_child = next(t for t in result.topics if t.name == "Child")
    assert result_child.parent == survivor.id


def test_sanitize_taxonomy_clears_dangling_parent():
    from uuid import uuid4

    child = Topic(name="Child", description="d", parent=uuid4())  # id not in taxonomy
    taxonomy = Taxonomy(topics=[child])
    result = sanitize_taxonomy(taxonomy)
    assert result.topics[0].parent is None


def test_sanitize_taxonomy_keeps_valid_parent_intact():
    parent = Topic(name="P", description="d")
    child = Topic(name="Child", description="d", parent=parent.id)
    taxonomy = Taxonomy(topics=[parent, child])
    result = sanitize_taxonomy(taxonomy)
    result_child = next(t for t in result.topics if t.name == "Child")
    assert result_child.parent == parent.id


# --- merge_name_duplicates ---


def test_merge_name_duplicates_removes_same_name_same_level():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="first", level=0),
            Topic(name="A", description="second", level=0),
        ]
    )
    assert len(merge_name_duplicates(taxonomy).topics) == 1


def test_merge_name_duplicates_keeps_highest_level():
    taxonomy = Taxonomy(
        topics=[
            Topic(name="A", description="low", level=0),
            Topic(name="A", description="high", level=1),
        ]
    )
    result = merge_name_duplicates(taxonomy)
    assert result.topics[0].level == 1


def test_merge_name_duplicates_no_duplicates_unchanged():
    taxonomy = Taxonomy(topics=[Topic(name="A", description="d"), Topic(name="B", description="d")])
    assert [t.name for t in merge_name_duplicates(taxonomy).topics] == ["A", "B"]


# --- drop_blank_names ---


def test_drop_blank_names_removes_empty_name():
    taxonomy = Taxonomy(topics=[Topic(name="", description="d"), Topic(name="A", description="d")])
    result = drop_blank_names(taxonomy)
    assert all(t.name for t in result.topics)


def test_drop_blank_names_removes_whitespace_name():
    taxonomy = Taxonomy(topics=[Topic(name="   ", description="d"), Topic(name="A", description="d")])
    result = drop_blank_names(taxonomy)
    assert [t.name for t in result.topics] == ["A"]


def test_drop_blank_names_keeps_topics_with_blank_description():
    taxonomy = Taxonomy(topics=[Topic(name="A", description="   "), Topic(name="B", description="d")])
    result = drop_blank_names(taxonomy)
    assert len(result.topics) == 2


def test_drop_blank_names_keeps_valid_topics():
    taxonomy = Taxonomy(topics=[Topic(name="A", description="ok"), Topic(name="B", description="ok")])
    assert len(drop_blank_names(taxonomy).topics) == 2


# --- clear_dangling_parents ---


def test_clear_dangling_parents_clears_missing_id():
    from uuid import uuid4

    child = Topic(name="Child", description="d", parent=uuid4())
    result = clear_dangling_parents(Taxonomy(topics=[child]))
    assert result.topics[0].parent is None


def test_clear_dangling_parents_keeps_valid_parent():
    parent = Topic(name="P", description="d")
    child = Topic(name="Child", description="d", parent=parent.id)
    result = clear_dangling_parents(Taxonomy(topics=[parent, child]))
    assert next(t for t in result.topics if t.name == "Child").parent == parent.id


def test_clear_dangling_parents_null_parent_unchanged():
    topic = Topic(name="A", description="d")
    result = clear_dangling_parents(Taxonomy(topics=[topic]))
    assert result.topics[0].parent is None


# --- clear_self_parents ---


def test_clear_self_parents_clears_self_reference():
    t = Topic(name="A", description="d")
    t = t.model_copy(update={"parent": t.id})
    result = clear_self_parents(Taxonomy(topics=[t]))
    assert result.topics[0].parent is None


def test_clear_self_parents_keeps_other_parent():
    parent = Topic(name="P", description="d")
    child = Topic(name="Child", description="d", parent=parent.id)
    result = clear_self_parents(Taxonomy(topics=[parent, child]))
    assert next(t for t in result.topics if t.name == "Child").parent == parent.id


def test_clear_self_parents_null_parent_unchanged():
    topic = Topic(name="A", description="d")
    result = clear_self_parents(Taxonomy(topics=[topic]))
    assert result.topics[0].parent is None
