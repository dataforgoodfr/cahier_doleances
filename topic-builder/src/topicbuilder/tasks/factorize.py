from pathlib import Path

import typer
from pydantic import BaseModel

from topicbuilder.core.client import LLMClient, parse_tool_arguments
from topicbuilder.core.clustering import (
    ClusteringConfig,
    clusterize_taxonomy_by_level,
    most_similar_topic,
)
from topicbuilder.core.io import read_taxonomy, read_text, write_json
from topicbuilder.core.schemas import FactorizeReport, Taxonomy, TopicMerge
from topicbuilder.core.taxonomy import check_taxonomy, display_duplicates, format_violations, sanitize_taxonomy

MERGE_GENERATION_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "propose_merge_candidates",
        "description": "Propose groups of topic names that may refer to the same concept.",
        "parameters": {
            "type": "object",
            "properties": {
                "groups": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "names": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["names"],
                    },
                },
            },
            "required": ["groups"],
        },
    },
}

MERGE_VALIDATION_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "record_merges",
        "description": "Record the merge operation decided for a candidate group.",
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string"},
                "sources": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["target", "sources"],
        },
    },
}


class MergeGroup(BaseModel):
    names: list[str]


class MergeGenerationArgs(BaseModel):
    groups: list[MergeGroup]


class MergeValidationArgs(BaseModel):
    target: str
    sources: list[str]


def factorize(
    taxonomy_path: Path = typer.Option(
        ...,
        "--taxonomy-path",
        exists=True,
        help="Path to the taxonomy JSON to clean.",
    ),
    llm_config_path: Path = typer.Option(
        ...,
        "--llm-config-path",
        exists=True,
        help="Path to the LLM client config YAML.",
    ),
    prompts_dir: Path = typer.Option(
        Path("conf/prompts/factorize"),
        "--prompts-dir",
        exists=True,
        help="Directory containing the factorize prompt files.",
    ),
    clustering_config_path: Path = typer.Option(
        Path("conf/clustering/default.yaml"),
        "--clustering-config-path",
        exists=True,
        help="Path to the clustering config YAML.",
    ),
    output_path: Path = typer.Option(
        ...,
        "--output-path",
        help="Path where the cleaned taxonomy JSON will be written.",
    ),
    report_path: Path = typer.Option(
        ...,
        "--report-path",
        help="Path where the change report JSON will be written.",
    ),
) -> None:
    """
    Read `taxonomy_path`, merge near-duplicate level-0 topics, and write the cleaned taxonomy
    and change report. Only level-0 topics are considered; higher-level topics pass through unchanged.
    """
    # load artifacts
    taxonomy = read_taxonomy(taxonomy_path)
    client = LLMClient.from_config(llm_config_path)
    merge_generation_prompt = read_text(prompts_dir / "merge_generation.md")
    merge_validation_prompt = read_text(prompts_dir / "merge_validation.md")
    clustering_config = ClusteringConfig.from_config(clustering_config_path)

    # ensure taxonomy is healthy
    taxonomy = sanitize_taxonomy(taxonomy)

    # run merging process
    merge_candidates = generate_merge_candidates(
        taxonomy=taxonomy,
        client=client,
        prompt=merge_generation_prompt,
        clustering_config=clustering_config,
    )
    merges = validate_merge_candidates(merge_candidates, client, merge_validation_prompt)
    taxonomy = insert_merges(taxonomy, merges)

    # checks and report
    report = FactorizeReport(merges=merges)
    checks = check_taxonomy(taxonomy)
    if checks.has_violations():
        typer.echo(format_violations(checks), err=True)

    # save output artifacts
    write_json(taxonomy, output_path)
    write_json(report, report_path)
    typer.echo(f"Wrote {len(taxonomy.topics)} topic(s) to {output_path} ({len(report.merges)} merge(s)).")
    return


def generate_merge_candidates(
    taxonomy: Taxonomy,
    client: LLMClient,
    prompt: str,
    clustering_config: ClusteringConfig,
) -> list[Taxonomy]:
    """
    Partition the taxonomy into clusters, ask the model to identify
    near-duplicate groups per chunk, then dedupe so each topic appears in at most one group.
    2-step production of candidates for merging:
        - segmentation of the full taxonomy into clusters of similar topics, done without LLM call.
        - segmentation of each cluster into actual candidates using LLM calls.
    """
    if not taxonomy.topics:
        return []

    # check for duplicate topic names
    display_duplicates(taxonomy)

    chunks = clusterize_taxonomy_by_level(taxonomy, clustering_config)
    responses = client(
        inputs=[build_merge_generation_messages(ct, prompt) for ct in chunks],
        tools=[MERGE_GENERATION_TOOL],
        tool_choice={"type": "function", "function": {"name": "propose_merge_candidates"}},
    )

    attributed: set[str] = set()
    candidates = []
    for chunk, response in zip(chunks, responses, strict=True):
        # parse the groups
        args = parse_tool_arguments(response, MergeGenerationArgs)
        if args is None:
            continue

        # clean the groups
        for group in args.groups:
            proposed = [most_similar_topic(name, chunk) for name in group.names]
            proposed = list({t.name: t for t in proposed if t.name not in attributed}.values())
            if len(proposed) >= 2:
                attributed.update(t.name for t in proposed)
                candidates.append(Taxonomy(topics=proposed))
    return candidates


def validate_merge_candidates(candidates: list[Taxonomy], client: LLMClient, prompt: str) -> list[TopicMerge]:
    """
    For each candidate group, ask the model to decide the actual merges using full topic objects,
    then filter results to only topics belonging to the group.
    """
    if not candidates:
        return []

    responses = client(
        inputs=[build_merge_validation_messages(c, prompt) for c in candidates],
        tools=[MERGE_VALIDATION_TOOL],
        tool_choice={"type": "function", "function": {"name": "record_merges"}},
    )
    merges = []
    for candidate, response in zip(candidates, responses, strict=True):
        # check for duplicate topic names
        display_duplicates(candidate)

        # parse the merge
        args = parse_tool_arguments(response, MergeValidationArgs)
        if args is None:
            continue

        # clean the merge
        if args.target and args.sources:
            clean_target = most_similar_topic(args.target, candidate)
            clean_sources = [most_similar_topic(r, candidate) for r in args.sources]
            clean_sources = list({t.id: t for t in clean_sources if t.id != clean_target.id}.values())
            if clean_sources:
                merges.append(TopicMerge(sources=Taxonomy(topics=clean_sources), target=clean_target))
    return merges


def insert_merges(taxonomy: Taxonomy, merges: list[TopicMerge]) -> Taxonomy:
    """
    Rename each source topic to its merge target name, redirect parent references pointing to
    a renamed source, then let sanitize_taxonomy collapse the resulting name duplicates, preserving
    the target's properties. Validated topics are never renamed.
    """
    # check for duplicate topic names
    display_duplicates(taxonomy)

    validated = {(t.name, t.level) for t in taxonomy.topics if t.validated}
    merge_map: dict[tuple[str, int], str] = {
        (s.name, s.level): m.target.name
        for m in merges
        for s in m.sources.topics
        if (s.name, s.level) not in validated
    }
    # redirect parent ids: source topic id → target topic id
    source_id_to_target_id = {
        s.id: m.target.id for m in merges for s in m.sources.topics if (s.name, s.level) not in validated
    }

    # reorder topics so the target of each merge appears first,
    # and subsequently rename all source topics with the name of the target topic,
    # so applying sanitize_taxonomy will remove all source and keep the target topic
    topics = sorted(taxonomy.topics, key=lambda t: (t.name, t.level) in merge_map)
    topics = [
        t.model_copy(
            update={
                "name": merge_map.get((t.name, t.level), t.name),
                "parent": source_id_to_target_id.get(t.parent, t.parent),
            }
        )
        for t in topics
    ]
    return sanitize_taxonomy(Taxonomy(topics=topics))


def build_merge_generation_messages(taxonomy: Taxonomy, prompt: str) -> list[dict]:
    """
    Build messages for the name-only merge candidate pass: list all topic names, no descriptions.
    """
    names_block = "\n".join(f"{i + 1}. {t.name}" for i, t in enumerate(taxonomy.topics))
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"## Topics\n\n{names_block}"},
    ]


def build_merge_validation_messages(candidate: Taxonomy, prompt: str, instructions: str | None = None) -> list[dict]:
    """
    Build messages for a single merge resolution call: full name and description for the group's topics.
    """
    topics_block = "\n".join(
        f"{i + 1}. {t.name}{' [validated]' if t.validated else ''}: {t.description}"
        for i, t in enumerate(candidate.topics)
    )
    user_content = f"## Topics\n\n{topics_block}"
    if instructions:
        user_content += f"\n\n## Instructions\n\n{instructions}"
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_content},
    ]
