import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import umap
import yaml
from fastembed import TextEmbedding
from loguru import logger
from pydantic import BaseModel
from sklearn.cluster import HDBSCAN

from topicbuilder.core.schemas import Taxonomy, Topic

STOP_WORDS_FR = {
    "a",
    "au",
    "aux",
    "avec",
    "ce",
    "ces",
    "dans",
    "de",
    "des",
    "du",
    "elle",
    "en",
    "et",
    "eux",
    "il",
    "ils",
    "je",
    "la",
    "le",
    "les",
    "leur",
    "lui",
    "ma",
    "mais",
    "me",
    "même",
    "meme",
    "mes",
    "moi",
    "mon",
    "ne",
    "nos",
    "notre",
    "nous",
    "on",
    "ou",
    "par",
    "pas",
    "pour",
    "qu",
    "que",
    "qui",
    "sa",
    "se",
    "ses",
    "son",
    "sur",
    "ta",
    "te",
    "tes",
    "toi",
    "ton",
    "tu",
    "un",
    "une",
    "vos",
    "votre",
    "vous",
    "c",
    "d",
    "j",
    "l",
    "m",
    "n",
    "s",
    "t",
    "y",
    "ete",
    "été",
    "etee",
    "étée",
    "etant",
    "étant",
    "etante",
    "étante",
    "etants",
    "étants",
    "etantes",
    "étantes",
    "suis",
    "es",
    "est",
    "sommes",
    "êtes",
    "etes",
    "sont",
    "serai",
    "seras",
    "sera",
    "serons",
    "serez",
    "seront",
    "serais",
    "serait",
    "serions",
    "seriez",
    "seraient",
    "etais",
    "étais",
    "etait",
    "était",
    "etions",
    "étions",
    "etiez",
    "étiez",
    "etaient",
    "étaient",
    "fus",
    "fut",
    "fûmes",
    "fumes",
    "fûtes",
    "futes",
    "furent",
    "sois",
    "soit",
    "soyons",
    "soyez",
    "soient",
    "fusse",
    "fusses",
    "fût",
    "fussions",
    "fussiez",
    "fussent",
    "ai",
    "as",
    "avons",
    "avez",
    "ont",
    "aurai",
    "auras",
    "aura",
    "aurons",
    "aurez",
    "auront",
    "aurais",
    "aurait",
    "aurions",
    "auriez",
    "auraient",
    "avais",
    "avait",
    "avions",
    "aviez",
    "avaient",
    "eut",
    "eûmes",
    "eumes",
    "eûtes",
    "eutes",
    "eurent",
    "aie",
    "aies",
    "ait",
    "ayons",
    "ayez",
    "aient",
    "eusse",
    "eusses",
    "eût",
    "eussions",
    "eussiez",
    "eussent",
}


class ClusteringConfig(BaseModel):
    """
    Full configuration for the semantic clustering pipeline (embedding + UMAP + HDBSCAN).
    """

    embedding: dict
    umap: dict
    hdbscan: dict

    @classmethod
    def from_config(cls, config_path: str | Path) -> "ClusteringConfig":
        """
        Load a ClusteringConfig from a YAML file.
        """
        with Path(config_path).resolve().open(encoding="utf-8") as f:
            return cls.model_validate(yaml.safe_load(f))


def clusterize(texts: list[str], config: ClusteringConfig) -> list[list[str]]:
    """
    Partition `texts` into semantically coherent groups using embedding + UMAP + HDBSCAN.
    Noise points are each returned as a singleton group. Below 2 texts, there is nothing to
    compare, so all texts are returned as a single group. UMAP cannot build a neighbor graph
    from exactly 2 texts, so HDBSCAN runs directly on the raw embeddings in that case.
    """
    if len(texts) < 2:
        return [texts]

    # compute embeddings
    embeddings = get_embeddings(texts, **config.embedding)

    # perform umap dimension reduction, unless too few texts for umap to build a neighbor graph
    reduced = embeddings if len(embeddings) < 3 else reduce_dimensions(embeddings, config)

    # clusterize reduced embeddings
    labels = HDBSCAN(**config.hdbscan).fit_predict(reduced)

    # polish clusters
    clusters = defaultdict(list)
    noise: list[str] = []
    for text, label in zip(texts, labels, strict=True):
        if label == -1:
            noise.append(text)
        else:
            clusters[label].append(text)
    logger.info(
        f"Created {len(clusters)} clusters and left {len(noise)} singletons. "
        + f"Cluster size distribution: {sorted((len(c) for c in clusters.values()), reverse=True)}"
    )
    return list(clusters.values()) + [[t] for t in noise]


def reduce_dimensions(embeddings: np.ndarray, config: ClusteringConfig) -> np.ndarray:
    """
    Reduce embeddings to a lower-dimensional space via UMAP, clamping n_neighbors to the sample
    size and scaling n_components down when there are too few texts for the configured value.
    """
    n = len(embeddings)
    umap_params = {
        **config.umap,
        "n_components": min(config.umap.get("n_components", 2), max(2, n // 10), n - 2),
        "n_neighbors": max(2, min(config.umap.get("n_neighbors", 15), n - 1)),
    }
    return umap.UMAP(**umap_params).fit_transform(embeddings)


def clusterize_taxonomy_by_level(taxonomy: Taxonomy, config: ClusteringConfig) -> list[Taxonomy]:
    """
    Partition a taxonomy into per-level groups of semantically coherent topics, returning one
    sub-taxonomy per group. Topics from different levels never share a group. Returns an empty
    list if the taxonomy has no topics.
    """
    levels = sorted({t.level for t in taxonomy.topics})
    topics_by_level = {lvl: [t.name for t in taxonomy.topics if t.level == lvl] for lvl in levels}
    chunks_by_level = {lvl: clusterize(names, config) for lvl, names in topics_by_level.items()}
    return [
        sub
        for lvl, lvl_chunks in chunks_by_level.items()
        for chunk in lvl_chunks
        for sub in [filter_taxonomy(taxonomy, chunk, lvl)]
        if sub.topics
    ]


def filter_taxonomy(taxonomy: Taxonomy, names: list[str], level: int) -> Taxonomy:
    """
    Filter a taxonomy.
    """
    return Taxonomy(topics=[t for t in taxonomy.topics if t.name in set(names) and t.level == level])


def most_similar_topic(sample: str, taxonomy: Taxonomy, level: int | None = None) -> Topic:
    """
    Return the topic in taxonomy whose name is the most similar to the supplied sample.
    When `level` is provided, only topics at that level are considered.
    """
    topics = [t for t in taxonomy.topics if t.level == level] if level is not None else taxonomy.topics
    return max(topics, key=lambda t: SequenceMatcher(None, sample, t.name).ratio())


def most_similar(sample: str, choices: list[str]) -> str:
    """
    Return the item of choices that is the most similar to the supplied sample.
    """
    return max(choices, key=lambda choice: SequenceMatcher(None, sample, choice).ratio())


def chunk_text(text: str, chunk_max_words: int) -> list[str]:
    """
    Chunk a text into segments of full sentences (if possible).
    """
    # split into sentences, each sentence spllited into words,
    # with pre-chunking ensuring that each sentence has max length <= chunk_max_words
    splitted_sentences = [s.split() for s in text.split("\n")]
    splitted_sentences = [
        sent[i : i + chunk_max_words] for sent in splitted_sentences for i in range(0, len(sent), chunk_max_words)
    ]
    all_chunks = []
    tmp_chunks = []
    n_word = 0
    for sent in splitted_sentences:
        # is possible, append the sentence to current chunk
        if n_word + len(sent) <= chunk_max_words:
            tmp_chunks.append(sent)
            n_word += len(sent)
        # else store the chunk and start a new one
        else:
            all_chunks.append(tmp_chunks)
            tmp_chunks = [sent]
            n_word = len(sent)
    all_chunks.append(tmp_chunks)
    return ["\n".join(" ".join(sent) for sent in chunk) for chunk in all_chunks]


def get_embeddings(texts: list[str], model: str, batch_size: int, prefix: str = "") -> np.ndarray:
    """
    Clean texts, optionally prepend a prefix, embed via fastembed in batches, L2-normalize,
    and return a float32 matrix of shape (len(texts), embedding_dim).
    """
    cleaned = [prefix + preprocess_for_embedding(t) for t in texts]
    embedder = TextEmbedding(model_name=model)
    vectors = list(embedder.embed(cleaned, batch_size=batch_size))
    embeddings = np.array(vectors, dtype="float32")
    embeddings /= np.linalg.norm(embeddings, ord=2, axis=1, keepdims=True)
    return embeddings


def preprocess_for_embedding(text: str) -> str:
    """
    Normalize and clean text for embedding: remove accents, special chars, and stop words.
    """
    if not text:
        return ""

    for old, new in {"œ": "oe", "Œ": "OE", "æ": "ae", "Æ": "AE"}.items():
        text = text.replace(old, new)

    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    words = re.sub(r"[^a-zA-Z0-9]+", " ", text).lower().split()
    return " ".join(w for w in words if w not in STOP_WORDS_FR and len(w) > 1)
