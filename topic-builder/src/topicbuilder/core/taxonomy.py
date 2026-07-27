from collections import Counter
from dataclasses import dataclass, field

import networkx as nx
from loguru import logger

from topicbuilder.core.schemas import Taxonomy, Topic


@dataclass
class CycleViolation:
    """
    A cycle in the taxonomy's parent hierarchy, as the name-sequence that forms the loop.
    """

    path: list[str]


@dataclass
class MultiPath:
    """
    A (source, target) concept pair reachable by more than one distinct ancestor path.
    """

    source: str
    target: str
    paths: list[list[str]] = field(default_factory=list)


@dataclass
class SanityReport:
    """
    Structural sanity check results for a taxonomy.
    """

    is_tree: bool
    duplicate_names: list[str]
    dangling_parents: list[tuple[str, str]]
    self_parents: list[str]
    empty_fields: list[tuple[str, str]]
    cycles: list[CycleViolation]
    multi_path_pairs: list[MultiPath]

    def has_violations(self) -> bool:
        """
        Return True if any check found at least one violation.
        """
        return bool(
            self.duplicate_names
            or self.dangling_parents
            or self.self_parents
            or self.empty_fields
            or self.cycles
            or self.multi_path_pairs
        )


def sanitize_taxonomy(taxonomy: Taxonomy) -> Taxonomy:
    """
    Warn on duplicate ids, then apply all four structural fixes in sequence: merge name
    duplicates, drop topics with a blank name, clear dangling parent references,
    and clear self-parent references.
    """
    if duplicate_ids := find_duplicate_ids(taxonomy):
        logger.warning(f"Found {len(duplicate_ids)} duplicate topic id(s): {duplicate_ids}")

    taxonomy = merge_name_duplicates(taxonomy)
    taxonomy = drop_blank_names(taxonomy)
    taxonomy = clear_dangling_parents(taxonomy)
    taxonomy = clear_self_parents(taxonomy)
    return taxonomy


def merge_name_duplicates(taxonomy: Taxonomy) -> Taxonomy:
    """
    Merge topics sharing the same name into a single survivor. Among topics with the same name
    and level, the first occurrence wins, inheriting a parent from discarded duplicates when the
    survivor has none. Among topics with the same name but different levels, the highest-level
    entry wins. Children whose parent id referred to a discarded duplicate are remapped to the
    surviving topic's id.
    """
    by_key: dict[tuple[str, int], Topic] = {}
    for t in taxonomy.topics:
        key = (t.name, t.level)
        if key not in by_key:
            by_key[key] = t
        elif by_key[key].parent is None and t.parent is not None:
            by_key[key] = by_key[key].model_copy(update={"parent": t.parent})

    highest_level: dict[str, int] = {}
    for name, level in by_key:
        if name not in highest_level or level > highest_level[name]:
            highest_level[name] = level

    id_remap = {t.id: by_key[(t.name, highest_level[t.name])].id for t in taxonomy.topics}

    seen: set[str] = set()
    topics = [
        (survivor := by_key[(t.name, highest_level[t.name])]).model_copy(
            update={"parent": id_remap.get(survivor.parent, survivor.parent)}
        )
        for t in taxonomy.topics
        if t.name not in seen and not seen.add(t.name)
    ]
    return Taxonomy(topics=topics)


def drop_blank_names(taxonomy: Taxonomy) -> Taxonomy:
    """
    Remove topics whose name is missing or whitespace-only.
    """
    if len(blank_ids := [t.id for t in taxonomy.topics if not t.name.strip()]) > 0:
        logger.warning(f"Removing {len(blank_ids)} topics pointing with blank names: {blank_ids}")

    return Taxonomy(topics=[t for t in taxonomy.topics if t.name.strip()])


def clear_dangling_parents(taxonomy: Taxonomy) -> Taxonomy:
    """
    Set to None any parent reference whose id is not present in the taxonomy.
    """
    global_ids = {t.id for t in taxonomy.topics}
    parent_ids = {t.parent for t in taxonomy.topics} - {None}
    if len(dangling_ids := parent_ids - global_ids) > 0:
        logger.warning(f"Removing {len(dangling_ids)} parent links pointing to non-existing ids: {dangling_ids}")

    return Taxonomy(
        topics=[
            t if (t.parent is None or t.parent in global_ids) else t.model_copy(update={"parent": None})
            for t in taxonomy.topics
        ]
    )


def clear_self_parents(taxonomy: Taxonomy) -> Taxonomy:
    """
    Set to None any parent reference where a topic points to itself.
    """
    if len(self_ids := [t.id for t in taxonomy.topics if t.parent == t.id]) > 0:
        logger.warning(f"Removing {len(self_ids)} parent links pointing to self: {self_ids}")

    return Taxonomy(topics=[t if t.parent != t.id else t.model_copy(update={"parent": None}) for t in taxonomy.topics])


def check_taxonomy(taxonomy: Taxonomy) -> SanityReport:
    """
    Run all structural sanity checks on a taxonomy and return a SanityReport.
    Multi-path detection is skipped when cycles are present to avoid unbounded path enumeration.
    """
    duplicate_names = find_duplicate_names(taxonomy)
    dangling_parents = find_dangling_parents(taxonomy)
    self_parents = find_self_parents(taxonomy)
    empty_fields = find_empty_fields(taxonomy)

    graph, id_to_name = build_graph(taxonomy)
    cycles = find_cycles(graph, id_to_name)
    multi_path_pairs = [] if cycles else find_multi_path_pairs(graph, id_to_name)
    is_tree = not (duplicate_names or dangling_parents or cycles or multi_path_pairs)

    return SanityReport(
        is_tree=is_tree,
        duplicate_names=duplicate_names,
        dangling_parents=dangling_parents,
        self_parents=self_parents,
        empty_fields=empty_fields,
        cycles=cycles,
        multi_path_pairs=multi_path_pairs,
    )


def format_violations(report: SanityReport) -> str:
    """
    Render a human-readable summary of all violations found in a SanityReport.
    """
    lines = ["Taxonomy sanity check failed:"]
    if report.duplicate_names:
        lines.append(f"  Duplicate names ({len(report.duplicate_names)}): {', '.join(report.duplicate_names[:5])}")
    if report.dangling_parents:
        examples = ", ".join(f"{c!r}→{p!r}" for c, p in report.dangling_parents[:3])
        lines.append(f"  Dangling parent references ({len(report.dangling_parents)}): {examples}")
    if report.self_parents:
        lines.append(f"  Self-parents ({len(report.self_parents)}): {', '.join(report.self_parents[:5])}")
    if report.empty_fields:
        examples = ", ".join(f"{n!r}.{f}" for n, f in report.empty_fields[:3])
        lines.append(f"  Empty fields ({len(report.empty_fields)}): {examples}")
    if report.cycles:
        examples = " | ".join(" → ".join(c.path) for c in report.cycles[:3])
        lines.append(f"  Cycles ({len(report.cycles)}): {examples}")
    if report.multi_path_pairs:
        examples = " | ".join(f"{mp.source}→{mp.target} ({len(mp.paths)} paths)" for mp in report.multi_path_pairs[:3])
        lines.append(f"  Multi-path pairs ({len(report.multi_path_pairs)}): {examples}")
    return "\n".join(lines)


def find_duplicate_ids(taxonomy: Taxonomy) -> list[str]:
    """
    Return all topic ids that appear more than once in the taxonomy.
    """
    counts = Counter(t.id for t in taxonomy.topics)
    return sorted(str(item) for item, n in counts.items() if n > 1)


def find_duplicate_names(taxonomy: Taxonomy) -> list[str]:
    """
    Return all topic names that appear more than once in the taxonomy.
    """
    counts = Counter(t.name for t in taxonomy.topics)
    return sorted(item for item, n in counts.items() if n > 1)


def find_dangling_parents(taxonomy: Taxonomy) -> list[tuple[str, str]]:
    """
    Return (child_name, parent_id_str) pairs where the parent id is not found in the taxonomy.
    """
    known_ids = {t.id for t in taxonomy.topics}
    return [(t.name, str(t.parent)) for t in taxonomy.topics if t.parent is not None and t.parent not in known_ids]


def find_self_parents(taxonomy: Taxonomy) -> list[str]:
    """
    Return names of topics whose parent field equals their own id.
    """
    return [t.name for t in taxonomy.topics if t.parent == t.id]


def find_empty_fields(taxonomy: Taxonomy) -> list[tuple[str, str]]:
    """
    Return (identifier, field_name) pairs for topics with an empty or whitespace-only name or description.
    """
    violations = []
    for t in taxonomy.topics:
        label = t.name if t.name and t.name.strip() else str(t.id)
        if not t.name or not t.name.strip():
            violations.append((label, "name"))
        if not t.description or not t.description.strip():
            violations.append((label, "description"))
    return violations


def find_cycles(graph: nx.DiGraph, id_to_name: dict[str, str]) -> list[CycleViolation]:
    """
    Return all distinct simple cycles in the parent hierarchy as CycleViolation objects.
    Each cycle path ends by repeating the first node so the loop is explicit.
    """
    return [
        CycleViolation(path=[id_to_name[n] for n in cycle] + [id_to_name[cycle[0]]])
        for cycle in nx.simple_cycles(graph)
    ]


def find_multi_path_pairs(graph: nx.DiGraph, id_to_name: dict[str, str]) -> list[MultiPath]:
    """
    Return MultiPath entries for every (source, target) pair reachable by more than one distinct
    simple path, indicating the taxonomy is not a tree.
    Assumes no cycles — call find_cycles first and skip if any are found.
    """
    multi_paths: list[MultiPath] = []
    for source in graph.nodes:
        by_target_name: dict[str, list[list[str]]] = {}
        for target in nx.descendants(graph, source):
            named_paths = [[id_to_name[n] for n in path] for path in nx.all_simple_paths(graph, source, target)]
            by_target_name.setdefault(id_to_name[target], []).extend(named_paths)
        for target_name, named_paths in by_target_name.items():
            if len(named_paths) > 1:
                multi_paths.append(MultiPath(source=id_to_name[source], target=target_name, paths=named_paths))
    return multi_paths


def build_graph(taxonomy: Taxonomy) -> tuple[nx.DiGraph, dict[str, str]]:
    """
    Build a directed graph (child → parent edges) and an id-to-name lookup.
    Each node is a topic UUID string. Parent is stored as a UUID, so each child
    has at most one edge pointing directly to its parent node.
    """
    id_to_name = {str(t.id): t.name for t in taxonomy.topics}
    known_ids = set(id_to_name)
    graph = nx.DiGraph()
    graph.add_nodes_from(id_to_name)
    for t in taxonomy.topics:
        if t.parent is not None and str(t.parent) in known_ids:
            graph.add_edge(str(t.id), str(t.parent))
    return graph, id_to_name


def display_duplicates(taxonomy: Taxonomy) -> None:
    """
    Display duplicate ids and (name, level) pairs
    """
    if dupl_ids := find_duplicate_ids(taxonomy):
        logger.warning(f"Found {len(dupl_ids)} duplicate ids: {dupl_ids}")
    if dupl_names := find_duplicate_names(taxonomy):
        logger.warning(f"Found {len(dupl_names)} duplicate names: {dupl_names}")
    return
