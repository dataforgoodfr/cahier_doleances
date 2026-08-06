import math
import random
from difflib import SequenceMatcher

from topicbuilder.core.schemas import Taxonomy, Topic


# TODO: do semantic clustering that scales as the list of texts grows
def clusterize(texts: list[str], n: int, seed: int = 0) -> list[list[str]]:
    """
    Partition `texts` into consecutive chunks of at most `n` items each,
    with chunk sizes as equal as possible.
    """
    if not texts:
        return []
    shuffled = random.Random(seed).sample(texts, len(texts))
    k = math.ceil(len(shuffled) / n)
    size = math.ceil(len(shuffled) / k)
    return [shuffled[i : i + size] for i in range(0, len(shuffled), size)]


def clusterize_taxonomy_by_level(taxonomy: Taxonomy, n: int) -> list[Taxonomy]:
    """
    Partition a taxonomy into per-level chunks of at most `n` topics each, returning one sub-taxonomy
    per chunk. Topics from different levels never share a chunk. Returns an empty list if the taxonomy
    has no topics.
    """
    levels = sorted({t.level for t in taxonomy.topics})
    topics_by_level = {lvl: [t.name for t in taxonomy.topics if t.level == lvl] for lvl in levels}
    chunks_by_level = {lvl: clusterize(names, n) for lvl, names in topics_by_level.items()}
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
