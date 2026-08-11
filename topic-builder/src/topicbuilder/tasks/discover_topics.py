from pathlib import Path

import typer
from loguru import logger

from topicbuilder.core.client import LLMClient, extract_tool_arguments
from topicbuilder.core.clustering import chunk_text
from topicbuilder.core.io import read_dataset, read_taxonomy, read_text, write_json
from topicbuilder.core.schemas import Taxonomy, Topic
from topicbuilder.core.taxonomy import sanitize_taxonomy

DISCOVER_TOPICS_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "record_new_topics",
        "description": "Record the list of new topics found in the text that are not covered by the existing config.",
        "parameters": {
            "type": "object",
            "properties": {
                "topics": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["name", "description"],
                    },
                }
            },
            "required": ["topics"],
        },
    },
}


def discover_topics(
    dataset_path: Path = typer.Option(
        ...,
        "--dataset-path",
        exists=True,
        help="Path to a CSV file with 'id' and 'content' columns.",
    ),
    taxonomy_path: Path | None = typer.Option(
        None,
        "--taxonomy-path",
        exists=True,
        help="Path to the existing taxonomy JSON. If omitted, starts from an empty taxonomy.",
    ),
    llm_config_path: Path = typer.Option(
        ...,
        "--llm-config-path",
        exists=True,
        help="Path to the LLM client config YAML.",
    ),
    prompt_path: Path = typer.Option(
        Path("conf/prompts/discover_topics.md"),
        "--prompt-path",
        exists=True,
        help="Path to the markdown system prompt file.",
    ),
    output_path: Path = typer.Option(
        ...,
        "--output-path",
        exists=False,
        help="Path where the updated topics config JSON will be written.",
    ),
    chunk_max_words: int = typer.Option(
        500,
        "--chunk-max-words",
        help="Number of max words per chunk of text.",
    ),
) -> None:
    """
    Read texts from `dataset_path`, discover new topics across all texts,
    and write the merged taxonomy to `output_path`.
    """
    # load llm client
    client = LLMClient.from_config(llm_config_path)
    prompt = read_text(prompt_path)

    # load texts and chunk them
    documents = read_dataset(dataset_path)
    chunks = [(doc.id, chunk) for doc in documents for chunk in chunk_text(doc.content, chunk_max_words)]
    logger.info(f"{len(documents)} texts segmented into {len(chunks)} chunks to process")

    # discover new topics
    ref_taxonomy = read_taxonomy(taxonomy_path) if taxonomy_path else Taxonomy(topics=[])
    new_taxonomy = discover_leaf_topics(chunks, ref_taxonomy, client, prompt)

    # save and log
    write_json(new_taxonomy, output_path)
    added = len(new_taxonomy.topics) - len(ref_taxonomy.topics)
    typer.echo(f"Wrote {len(new_taxonomy.topics)} topic(s) to {output_path} ({added} new).")
    return


def discover_leaf_topics(
    chunks: list[tuple[str, str]], taxonomy: Taxonomy, client: LLMClient, prompt: str,
) -> Taxonomy:
    """
    Send all text chunks to the LLM concurrently, tag each discovered topic with the id of the
    text it was found in, and return the merged taxonomy with name duplicates collapsed.
    """
    responses = client(
        inputs=[build_messages(text, taxonomy, prompt) for _, text in chunks],
        tools=[DISCOVER_TOPICS_TOOL],
        tool_choice={"type": "function", "function": {"name": "record_new_topics"}},
    )
    new_topics = [
        Topic(**(t | {"sources": [text_id]}))
        for (text_id, _), response in zip(chunks, responses, strict=True)
        for t in extract_tool_arguments(response).get("topics", [])
    ]
    return sanitize_taxonomy(Taxonomy(topics=taxonomy.topics + new_topics))


def build_messages(text: str, taxonomy: Taxonomy, prompt: str) -> list[dict]:
    """
    Build the chat messages combining the system prompt, existing topics, and input text.
    """
    topics_block = "\n".join(f"{i + 1}. {t.name}: {t.description}" for i, t in enumerate(taxonomy.topics))
    user_content = f"## Existing topics\n\n{topics_block}\n\n## Text\n\n{text}"
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_content},
    ]
