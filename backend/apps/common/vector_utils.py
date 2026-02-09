"""
Vector embedding utilities — wraps sentence-transformers and pgvector.

Model is configurable via EMBEDDING_MODEL setting (default: all-MiniLM-L12-v2,
384 dimensions). Shared across graph node and document chunk pipelines.

Embedding generation is delegated to apps.common.embeddings to avoid
duplicate model instances and to benefit from its query cache (LRU + TTL).
"""
import logging
from typing import List, Optional

import numpy as np
from pgvector.django import CosineDistance

logger = logging.getLogger(__name__)

# Embedding dimensions — must match the sentence-transformers model
EMBEDDING_DIM = 384


def generate_embedding(text: str) -> List[float]:
    """
    Generate a 384-dim embedding vector for text. Synchronous.

    Delegates to embeddings.py which maintains a singleton model instance
    and an LRU query cache (saves ~50ms per repeated query).

    Args:
        text: The text to embed

    Returns:
        List of 384 floats
    """
    from apps.common.embeddings import generate_embedding as _cached_generate
    result = _cached_generate(text, use_cache=True)
    if result is None:
        # Fallback for very short text — embeddings.py returns None for <10 chars
        from apps.common.embeddings import _get_service
        return _get_service().encode(text).tolist()
    return result


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Batch embedding generation. More efficient for multiple texts.

    Delegates to embeddings.py to share the singleton model instance.

    Args:
        texts: List of texts to embed

    Returns:
        List of 384-dim float lists
    """
    from apps.common.embeddings import generate_embeddings_batch as _batch_generate
    return _batch_generate(texts)


def similarity_search(queryset, embedding_field: str, query_vector: List[float],
                       threshold: float = 0.6, top_k: int = 10):
    """
    Find similar objects using pgvector cosine distance.

    Args:
        queryset: Django queryset with VectorField
        embedding_field: Name of the VectorField on the model
        query_vector: The query embedding (384-dim list)
        threshold: Minimum similarity (0.0-1.0). Default 0.6
        top_k: Maximum results to return

    Returns:
        Queryset annotated with 'distance' and filtered/ordered by similarity
    """
    return (
        queryset
        .exclude(**{f'{embedding_field}__isnull': True})
        .annotate(distance=CosineDistance(embedding_field, query_vector))
        .filter(distance__lt=(1 - threshold))  # cosine distance = 1 - similarity
        .order_by('distance')[:top_k]
    )


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Similarity score (0.0 to 1.0)
    """
    a = np.array(vec1)
    b = np.array(vec2)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(a, b) / (norm_a * norm_b))


def batch_cosine_similarity(
    query: List[float],
    embeddings: List[List[float]]
) -> np.ndarray:
    """
    Compute cosine similarity between one query and multiple embeddings.

    Vectorized implementation — much faster than calling cosine_similarity
    in a loop when comparing against many embeddings.

    Args:
        query: Single query embedding vector
        embeddings: List of embedding vectors to compare against

    Returns:
        Numpy array of similarity scores (same order as input)
    """
    if not embeddings:
        return np.array([])

    query_vec = np.array(query)
    embed_matrix = np.array(embeddings)

    query_norm = np.linalg.norm(query_vec)
    if query_norm == 0:
        return np.zeros(len(embeddings))

    embed_norms = np.linalg.norm(embed_matrix, axis=1)
    embed_norms = np.where(embed_norms == 0, 1, embed_norms)

    similarities = np.dot(embed_matrix, query_vec) / (embed_norms * query_norm)

    return similarities
