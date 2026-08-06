from pathlib import Path

import typer
from pydantic import BaseModel

from topicbuilder.core.client import LLMClient, parse_tool_arguments
from topicbuilder.core.clustering import clusterize_taxonomy_by_level, most_similar_topic
from topicbuilder.core.io import read_taxonomy, read_text, write_json
from topicbuilder.core.schemas import ParentAddition, ParentCandidate, ParentDiscoveryReport, Taxonomy, Topic
from topicbuilder.core.taxonomy import check_taxonomy, display_duplicates, format_violations, sanitize_taxonomy

PARENT_GENERATION_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "propose_parent_candidates",
        "description": "Propose candidate parent topics with their candidate child topics.",
        "parameters": {
            "type": "object",
            "properties": {
                "candidates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "parent": {"type": "string"},
                            "children": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["parent", "children"],
                    },
                },
            },
            "required": ["candidates"],
        },
    },
}

PARENT_VALIDATION_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "record_parent",
        "description": "Record a new parent topic and the confirmed subset of its children.",
        "parameters": {
            "type": "object",
            "properties": {
                "parent": {"type": "string"},
                "description": {"type": "string"},
                "children": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["parent", "description", "children"],
        },
    },
}


class ParentCandidateArgs(BaseModel):
    parent: str
    children: list[str]


class ParentGenerationArgs(BaseModel):
    candidates: list[ParentCandidateArgs]


class ParentValidationArgs(BaseModel):
    parent: str
    description: str
    children: list[str]


def discover_parents(
    taxonomy_path: Path = typer.Option(
        ...,
        "--taxonomy-path",
        exists=True,
        help="Path to the taxonomy JSON to structure.",
    ),
    llm_config_path: Path = typer.Option(
        ...,
        "--llm-config-path",
        exists=True,
        help="Path to the LLM client config YAML.",
    ),
    prompts_dir: Path = typer.Option(
        Path("conf/prompts/discover_parents"),
        "--prompts-dir",
        exists=True,
        help="Directory containing the structure prompt files.",
    ),
    output_path: Path = typer.Option(
        ...,
        "--output-path",
        help="Path where the structured taxonomy JSON will be written.",
    ),
    report_path: Path = typer.Option(
        ...,
        "--report-path",
        help="Path where the change report JSON will be written.",
    ),
    chunk_size: int = typer.Option(
        500,
        "--chunk-size",
        help="Maximum number of parentless topics per parent-generation chunk.",
    ),
) -> None:
    """
    Read `taxonomy_path`, group parentless topics under new parent meta-topics per level, and write
    the updated taxonomy and change report. Processes each level independently.
    """
    # load artifacts
    taxonomy = read_taxonomy(taxonomy_path)
    client = LLMClient.from_config(llm_config_path)
    parent_generation_prompt = read_text(prompts_dir / "parent_generation.md")
    parent_validation_prompt = read_text(prompts_dir / "parent_validation.md")

    # ensure taxonomy is healthy
    taxonomy = sanitize_taxonomy(taxonomy)

    # run parent grouping process
    parentless = Taxonomy(topics=[t for t in taxonomy.topics if t.parent is None])
    candidates = generate_parent_candidates(parentless, client, parent_generation_prompt, chunk_size)
    additions = validate_parent_candidates(candidates, client, parent_validation_prompt)
    taxonomy = insert_parents(taxonomy, additions)

    # checks and report
    report = ParentDiscoveryReport(parents_added=additions)
    checks = check_taxonomy(taxonomy)
    if checks.has_violations():
        typer.echo(format_violations(checks), err=True)

    # save output artifacts
    write_json(taxonomy, output_path)
    write_json(report, report_path)
    typer.echo(
        f"Wrote {len(taxonomy.topics)} topic(s) to {output_path} ({len(report.parents_added)} parent(s) added)."
    )
    return


def generate_parent_candidates(
    taxonomy: Taxonomy,
    client: LLMClient,
    prompt: str,
    chunk_size: int,
) -> list[ParentCandidate]:
    """
    Partition the taxonomy into chunks of at most `chunk_size` topics, ask the model to propose
    parent candidates per chunk, then dedupe so each child name appears in at most one candidate.
    """
    if not taxonomy.topics:
        return []

    # check for duplicate topic names
    display_duplicates(taxonomy)

    chunks = clusterize_taxonomy_by_level(taxonomy, chunk_size)
    responses = client(
        inputs=[build_parent_generation_messages(ct, prompt) for ct in chunks],
        tools=[PARENT_GENERATION_TOOL],
        tool_choice={"type": "function", "function": {"name": "propose_parent_candidates"}},
    )

    attributed: set[str] = set()
    candidates = []
    for chunk, response in zip(chunks, responses, strict=True):
        # parse the candidates
        args = parse_tool_arguments(response, ParentGenerationArgs)
        if args is None:
            continue

        # clean the candidates
        for c in args.candidates:
            children = [most_similar_topic(ch, chunk) for ch in c.children]
            children = list({t.name: t for t in children if t.name not in attributed}.values())
            if c.parent and children:
                attributed.update(t.name for t in children)
                candidates.append(ParentCandidate(parent=c.parent, children=Taxonomy(topics=children)))
    return candidates


def validate_parent_candidates(
    candidates: list[ParentCandidate],
    client: LLMClient,
    prompt: str,
) -> list[ParentAddition]:
    """
    For each parent candidate, ask the model to confirm the parent, provide a description, and
    select the confirmed subset of children.
    """
    if not candidates:
        return []

    responses = client(
        inputs=[build_parent_validation_messages(c, prompt) for c in candidates],
        tools=[PARENT_VALIDATION_TOOL],
        tool_choice={"type": "function", "function": {"name": "record_parent"}},
    )
    attributed: set[str] = set()
    additions = []
    for candidate, response in zip(candidates, responses, strict=True):
        # parse the parent
        args = parse_tool_arguments(response, ParentValidationArgs)
        if args is None:
            continue

        # clean the parent
        clean_children = [most_similar_topic(ch, candidate.children) for ch in args.children]
        clean_children = list({t.name: t for t in clean_children if t.name not in attributed}.values())
        if args.parent and clean_children:
            level = max(t.level for t in clean_children) + 1
            clean_parent = Topic(name=args.parent, description=args.description, level=level)
            attributed.update(t.name for t in clean_children)
            additions.append(ParentAddition(parent=clean_parent, children=Taxonomy(topics=clean_children)))
    return additions


def insert_parents(taxonomy: Taxonomy, additions: list[ParentAddition]) -> Taxonomy:
    """
    Set each child's parent field to the new parent Topic's id and append new parent Topic entries.
    Merge the possible duplicate topics.
    """
    parent_map = {t.name: pa.parent.id for pa in additions for t in pa.children.topics}
    updated_topics = [t.model_copy(update={"parent": parent_map.get(t.name, t.parent)}) for t in taxonomy.topics]
    new_topics = [pa.parent for pa in additions]
    return sanitize_taxonomy(Taxonomy(topics=updated_topics + new_topics))


def build_parent_generation_messages(taxonomy: Taxonomy, prompt: str) -> list[dict]:
    """
    Build messages for the name-only parent candidate pass: list all topic names, no descriptions.
    """
    names_block = "\n".join(f"{i + 1}. {t.name}" for i, t in enumerate(taxonomy.topics))
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"## Topics\n\n{names_block}"},
    ]


def build_parent_validation_messages(candidate: ParentCandidate, prompt: str) -> list[dict]:
    """
    Build messages for a single parent resolution call: full name and description for each candidate child.
    """
    topics_block = "\n".join(
        f"{i + 1}. {t.name}{' [validated]' if t.validated else ''}: {t.description}"
        for i, t in enumerate(candidate.children.topics)
    )
    user_content = f"## Parent candidate\n\n{candidate.parent}\n\n## Children candidates\n\n{topics_block}"
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_content},
    ]
