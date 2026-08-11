from pathlib import Path

import typer
from loguru import logger
from pydantic import BaseModel

from topicbuilder.core.client import LLMClient, parse_tool_arguments
from topicbuilder.core.clustering import chunk_text, most_similar_topic
from topicbuilder.core.io import read_dataset, read_taxonomy, read_text, write_json
from topicbuilder.core.schemas import Document, DocumentLabels, Label, LabeledDataset, Taxonomy
from topicbuilder.core.taxonomy import display_duplicates, filter_taxonomy_by_source, sanitize_taxonomy

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

    # ensure taxonomy is healthy
    taxonomy = sanitize_taxonomy(taxonomy)

    # run labeling
    labeled = generate_labels(
        documents=documents,
        taxonomy=taxonomy,
        client=client,
        prompt=prompt,
        chunk_max_words=chunk_max_words,
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
) -> LabeledDataset:
    """
    Chunk each document's text and send every chunk to the LLM concurrently, together with the
    topics recording that document among their sources, then return labels grouped by document id.
    """
    if not taxonomy.topics:
        return empty_labels(documents)

    # check for duplicate topic names
    display_duplicates(taxonomy)

    # restrict the candidate topics of each document to those discovered in it
    taxonomy_by_document = {doc.id: filter_taxonomy_by_source(taxonomy, doc.id) for doc in documents}
    if unmatched := [doc.id for doc in documents if not taxonomy_by_document[doc.id].topics]:
        logger.warning(f"{len(unmatched)} document(s) are not recorded as source of any topic: {unmatched}")

    pairs = [
        (doc.id, chunk)
        for doc in documents
        if taxonomy_by_document[doc.id].topics
        for chunk in chunk_text(doc.content, chunk_max_words)
    ]
    if not pairs:
        return empty_labels(documents)

    logger.info(f"{len(documents)} document(s) → {len(pairs)} text chunk(s) to label")

    responses = client(
        inputs=[build_messages(chunk, taxonomy_by_document[doc_id], prompt) for doc_id, chunk in pairs],
        tools=[LABEL_TOOL],
        tool_choice={"type": "function", "function": {"name": "record_labeled_topics"}},
    )

    labels: dict[str, list[Label]] = {doc.id: [] for doc in documents}
    for (doc_id, _), response in zip(pairs, responses, strict=True):
        args = parse_tool_arguments(response, LabelArgs)
        if args is None:
            continue
        for t in args.topics:
            # clean the topic
            if t.name and t.rationale and t.extract:
                clean_name = most_similar_topic(t.name, taxonomy_by_document[doc_id]).name
                clean_label = Label(name=clean_name, rationale=t.rationale, extract=t.extract)
                labels[doc_id].append(clean_label)

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


def empty_labels(documents: list[Document]) -> LabeledDataset:
    """
    Build a labeled dataset where every document carries an empty list of labels.
    """
    return LabeledDataset(documents=[DocumentLabels(id=doc.id, labels=[]) for doc in documents])
