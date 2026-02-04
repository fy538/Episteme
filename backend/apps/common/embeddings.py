"""
Embedding generation utilities

Uses sentence-transformers for local embedding generation.
Model: all-MiniLM-L6-v2 (384 dimensions, ~100MB)
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Lazy-loaded embedding service
_embedding_service = None


def _get_service():
    """Lazy load embedding service to avoid import overhead."""
    global _embedding_service
    if _embedding_service is None:
        from apps.signals.embedding_service import get_embedding_service
        _embedding_service = get_embedding_service()
    return _embedding_service


def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding for text using sentence-transformers.

    Args:
        text: Text to embed (should be non-empty)

    Returns:
        List of floats (384-dim vector) or None if text is too short
    """
    if not text or len(text.strip()) < 10:
        logger.debug("Text too short for embedding, skipping")
        return None

    try:
        service = _get_service()
        embedding = service.encode(text)
        return embedding.tolist()
    except Exception as e:
        logger.warning(f"Embedding generation failed: {e}")
        return None


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
