from pathlib import Path

import typer
from loguru import logger
from pydantic import BaseModel

from topicbuilder.core.client import LLMClient, parse_tool_arguments
from topicbuilder.core.clustering import (
    ClusteringConfig,
    chunk_text,
    clusterize_taxonomy_by_level,
    most_similar_topic,
)
from topicbuilder.core.io import read_dataset, read_taxonomy, read_text, write_json
from topicbuilder.core.schemas import Document, DocumentLabels, Label, LabeledDataset, Taxonomy
from topicbuilder.core.taxonomy import display_duplicates, sanitize_taxonomy

LABEL_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "record_labeled_topics",
        "description": "Record the topics from the config that were identified in the text.",
        "parameters": {
            "type": "object",
            "properties": {
                "topics": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "rationale": {"type": "string"},
                            "extract": {"type": "string"},
                        },
                        "required": ["name", "rationale", "extract"],
                    },
                }
            },
            "required": ["topics"],
        },
    },
}


class LabelItemArgs(BaseModel):
    name: str
    rationale: str
    extract: str


class LabelArgs(BaseModel):
    topics: list[LabelItemArgs]


def label(
    dataset_path: Path = typer.Option(
        ...,
        "--dataset-path",
        exists=True,
        help="Path to a CSV file with 'id' and 'content' columns.",
    ),
    taxonomy_path: Path = typer.Option(
        ...,
        "--taxonomy-path",
        exists=True,
        help="Path to the topics config JSON.",
    ),
    llm_config_path: Path = typer.Option(
        ...,
        "--llm-config-path",
        exists=True,
        help="Path to the LLM client config YAML.",
    ),
    prompt_path: Path = typer.Option(
        Path("conf/prompts/label.md"),
        "--prompt-path",
        exists=True,
        help="Path to the markdown system prompt file.",
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
        help="Path where the labeled topics JSON will be written.",
    ),
    chunk_max_words: int = typer.Option(
        500,
        "--chunk-max-words",
        help="Maximum number of words per text chunk.",
    ),
) -> None:
    """
    Read texts from `dataset_path`, identify which topics appear in each document,
    and write per-document labeled topics to `output_path`.
    """
    # load artifacts
    documents = read_dataset(dataset_path)
    taxonomy = read_taxonomy(taxonomy_path)
    client = LLMClient.from_config(llm_config_path)
    prompt = read_text(prompt_path)
    clustering_config = ClusteringConfig.from_config(clustering_config_path)

    # ensure taxonomy is healthy
    taxonomy = sanitize_taxonomy(taxonomy)

    # run labeling
    labeled = generate_labels(
        documents=documents,
        taxonomy=taxonomy,
        client=client,
        prompt=prompt,
        chunk_max_words=chunk_max_words,
        clustering_config=clustering_config,
    )

    # save output artifacts
    write_json(labeled, output_path)
    typer.echo(f"Wrote labels for {len(labeled.documents)} document(s) to {output_path}.")
    return


def generate_labels(
    documents: list[Document],
    taxonomy: Taxonomy,
    client: LLMClient,
    prompt: str,
    chunk_max_words: int,
    clustering_config: ClusteringConfig,
) -> LabeledDataset:
    """
    Chunk each document's text and the level-0 taxonomy, send all (text chunk x topic chunk) pairs
    to the LLM concurrently, and return labels grouped by document id.
    """
    if not taxonomy.topics:
        return LabeledDataset(documents=[DocumentLabels(id=doc.id, labels=[]) for doc in documents])

    # check for duplicate topic names
    display_duplicates(taxonomy)

    topic_chunks = clusterize_taxonomy_by_level(taxonomy, clustering_config)
    text_chunks = [(doc, chunk) for doc in documents for chunk in chunk_text(doc.content, chunk_max_words)]
    triples = [(doc, text_chunk, topic_chunk) for (doc, text_chunk) in text_chunks for topic_chunk in topic_chunks]
    logger.info(
        f"{len(documents)} document(s) → {len(text_chunks)} text chunk(s), "
        f"{len(topic_chunks)} taxonomy chunk(s), {len(triples)} LLM calls total"
    )

    responses = client(
        inputs=[build_messages(text_chunk, topic_chunk, prompt) for (_, text_chunk, topic_chunk) in triples],
        tools=[LABEL_TOOL],
        tool_choice={"type": "function", "function": {"name": "record_labeled_topics"}},
    )

    labels: dict[str, list[Label]] = {doc.id: [] for doc in documents}
    for (doc, _, topic_chunk), response in zip(triples, responses, strict=True):
        args = parse_tool_arguments(response, LabelArgs)
        if args is None:
            continue
        for t in args.topics:
            # clean the topic
            if t.name and t.rationale and t.extract:
                clean_name = most_similar_topic(t.name, topic_chunk).name
                clean_label = Label(name=clean_name, rationale=t.rationale, extract=t.extract)
                labels[doc.id].append(clean_label)

    # deduplicate labels by topic name
    labels = {doc_id: list({t.name: t for t in ls}.values()) for doc_id, ls in labels.items()}

    # return labeled dataset
    return LabeledDataset(documents=[DocumentLabels(id=k, labels=v) for k, v in labels.items()])


def build_messages(text: str, taxonomy: Taxonomy, prompt: str) -> list[dict]:
    """
    Build the chat messages combining the system prompt, a topic chunk, and a text chunk.
    """
    topics_block = "\n".join(f"{i + 1}. {t.name}: {t.description}" for i, t in enumerate(taxonomy.topics))
    user_content = f"## Topics\n\n{topics_block}\n\n## Text\n\n{text}"
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_content},
    ]
