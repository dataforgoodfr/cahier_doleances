import math
import random
from difflib import SequenceMatcher

import faiss
import numpy as np
import umap
from openai import OpenAI
from sklearn.cluster import HDBSCAN

from topicbuilder.core.schemas import Taxonomy, Topic
from topicbuilder.core.utils import TEST_TEXTS, clean_before_embedding

# Ollama must be installed aside with bge-m3 installed
# https://ollama.com/library/bge-m3
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

# Semantic Configuration
EMBEDDING_BATCH_SIZE = 20
EMBEDDING_MODEL_NAME = "bge-m3"
UMAP_N_COMPONENTS = 15
UMAP_N_NEIGHBOURS = 15
MIN_CLUSTER_SIZE = 15
MIN_SAMPLES = 1
CLUSTER_SELECTION_EPSILON = 0.05


def cluster_texts_umap_hdbscan(
    texts,
    embeddings,
    n_components=UMAP_N_COMPONENTS,  # Taille de l'espace réduit (ex: 5 dimensions)
    n_neighbours=UMAP_N_COMPONENTS,  # Taille de l'espace de recherche autour des vecteurs
    min_cluster_size=MIN_CLUSTER_SIZE,  # Taille min pour former un groupe
    min_samples=MIN_SAMPLES,  # Contrôle du bruit (1 = très permissif)
    cluster_selection_epsilon=CLUSTER_SELECTION_EPSILON,  # Tolérance pour étendre les clusters
):
    """
    Reduce vectors dimension with UMAP and clusterise with HDBSCAN
    """

    # Reduce vectors dimension 1024 (for bge model) to 15
    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=n_neighbours,
        min_dist=0.1,
        metric="cosine",
        random_state=42,
    )
    reduced_embeddings = reducer.fit_transform(embeddings)

    # HDBSCAN Configuration
    hdbscan_model = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        cluster_selection_epsilon=cluster_selection_epsilon,
        metric="euclidean",
    )

    # HDBSCAN running on reduced embeddings
    labels = hdbscan_model.fit_predict(reduced_embeddings)

    clusters = {}
    remaining_vectors = []

    # Gather results per cluster in a dict
    for texte, label in zip(texts, labels, strict=False):
        if label == -1:
            remaining_vectors.append(texte)
        else:
            cluster_name = f"Cluster_{label + 1}"
            if cluster_name not in clusters:
                clusters[cluster_name] = []
            clusters[cluster_name].append(texte)

    return clusters, remaining_vectors


def get_embeddings(texts, model_name=EMBEDDING_MODEL_NAME, batch_size=EMBEDDING_BATCH_SIZE):
    """
    Generate embeddings per batch and normalize them with FAISS
    """
    all_embeddings = []
    total_texts = len(texts)

    for i in range(0, total_texts, batch_size):
        batch_texts = texts[i : i + batch_size]
        batch_texts = [clean_before_embedding(text) for text in batch_texts]

        # Embedding
        response = client.embeddings.create(model=model_name, input=batch_texts)
        batch_embeddings = np.array([item.embedding for item in response.data], dtype="float32")

        # Normalize embeddings
        faiss.normalize_L2(batch_embeddings)
        all_embeddings.append(batch_embeddings)

    # Gathering embeddings
    full_embeddings = np.vstack(all_embeddings)

    return full_embeddings


def clusterize_semantic(texts: list[str]) -> list[list[str]]:
    """
    Get semantic clustering from texts.
    """
    if not texts:
        return []
    embeddings = get_embeddings(texts=texts)
    clusters_final, topics_restants = cluster_texts_umap_hdbscan(
        texts=texts, embeddings=embeddings, n_components=15, min_cluster_size=15, min_samples=1
    )
    return list(clusters_final.values()) + topics_restants


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


if __name__ == "__main__":
    print("Embedding...")
    embeddings = get_embeddings(texts=TEST_TEXTS)

    print("Clusterize...")
    clusters_final, topics_restants = cluster_texts_umap_hdbscan(
        texts=TEST_TEXTS,
        embeddings=embeddings,
    )

    print("\n================ RÉSULTATS UMAP + HDBSCAN ================")
    print(f"Nombre de clusters formés : {len(clusters_final)}")
    print(f"Nombre de restants (bruit) : {len(topics_restants)}")
    print(type(clusters_final))
    print(type(topics_restants))

    for nom_cluster, contenu in list(clusters_final.items()):
        print(f"\n{nom_cluster} ({len(contenu)} éléments) :")
        for t in contenu:
            print(f"  - {t}")
    if topics_restants:
        print(f"\nTopics restants / Bruit (-1) ({len(topics_restants)} éléments) :")
        for texte in topics_restants:
            print(f"  - {texte}")
