"""
Embedding generation utilities

Uses sentence-transformers for local embedding generation.
Model: configurable via EMBEDDING_MODEL setting (default: all-MiniLM-L12-v2, 384 dimensions).
"""

import logging
import time
from typing import List, Optional, Tuple
from collections import OrderedDict

logger = logging.getLogger(__name__)

# Lazy-loaded SentenceTransformer model (singleton)
_embedding_model = None

# Query embedding cache: {text: (embedding, timestamp)}
# LRU with TTL for query embeddings (saves ~50ms per repeated query)
_query_cache: OrderedDict[str, Tuple[List[float], float]] = OrderedDict()
_CACHE_MAX_SIZE = 100  # Max cached queries
_CACHE_TTL_SECONDS = 300  # 5 minutes TTL


class _EmbeddingService:
    """
    Singleton wrapper for SentenceTransformer model.

    Uses EMBEDDING_MODEL setting (default: all-MiniLM-L12-v2, 384 dimensions).
    """

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            from django.conf import settings
            model_name = getattr(settings, 'EMBEDDING_MODEL', 'all-MiniLM-L12-v2')
            self.__class__._model = SentenceTransformer(model_name)

    def encode(self, text, **kwargs):
        """Encode text to embedding vector(s)."""
        return self._model.encode(text, **kwargs)


# Module-level singleton
_embedding_service = None


def _get_service():
    """Lazy load embedding service to avoid import overhead."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = _EmbeddingService()
    return _embedding_service


def generate_embedding(text: str, use_cache: bool = True) -> Optional[List[float]]:
    """
    Generate embedding for text using sentence-transformers.

    Args:
        text: Text to embed (should be non-empty)
        use_cache: Whether to use query cache (default True for search queries)

    Returns:
        List of floats (384-dim vector) or None if text is too short
    """
    if not text or len(text.strip()) < 10:
        logger.debug("Text too short for embedding, skipping")
        return None

    # Check cache for repeated queries (saves ~50ms per hit)
    if use_cache:
        cached = _get_cached_embedding(text)
        if cached is not None:
            return cached

    try:
        service = _get_service()
        embedding = service.encode(text)
        result = embedding.tolist()

        # Cache the result for future queries
        if use_cache:
            _cache_embedding(text, result)

        return result
    except Exception as e:
        logger.warning(f"Embedding generation failed: {e}")
        return None


def _get_cached_embedding(text: str) -> Optional[List[float]]:
    """Get embedding from cache if valid (not expired)."""
    if text not in _query_cache:
        return None

    embedding, timestamp = _query_cache[text]
    if time.time() - timestamp > _CACHE_TTL_SECONDS:
        # Expired, remove and return None
        del _query_cache[text]
        return None

    # Move to end (LRU)
    _query_cache.move_to_end(text)
    return embedding


def _cache_embedding(text: str, embedding: List[float]) -> None:
    """Cache an embedding with current timestamp."""
    # Evict oldest if at capacity
    while len(_query_cache) >= _CACHE_MAX_SIZE:
        _query_cache.popitem(last=False)

    _query_cache[text] = (embedding, time.time())


def generate_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """
    Generate embeddings for multiple texts efficiently.

    Args:
        texts: List of texts to embed

    Returns:
        List of embeddings (same order as input), None for invalid texts
    """
    if not texts:
        return []

    try:
        service = _get_service()

        # Filter valid texts and track indices
        valid_indices = []
        valid_texts = []
        for i, text in enumerate(texts):
            if text and len(text.strip()) >= 10:
                valid_indices.append(i)
                valid_texts.append(text)

        if not valid_texts:
            return [None] * len(texts)

        # Batch encode
        embeddings = service.encode(valid_texts)

        # Map back to original indices
        result = [None] * len(texts)
        for i, emb in zip(valid_indices, embeddings):
            result[i] = emb.tolist()

        return result
    except Exception as e:
        logger.warning(f"Batch embedding generation failed: {e}")
        return [None] * len(texts)
