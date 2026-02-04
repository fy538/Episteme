"""
Embedding generation utilities

Stub implementation - embeddings are optional for signal storage.
"""

import logging

logger = logging.getLogger(__name__)


def generate_embedding(text: str) -> list:
    """
    Generate embedding for text.

    Current implementation is a stub that returns None.
    Future implementation will use sentence-transformers or OpenAI embeddings.

    Args:
        text: Text to embed

    Returns:
        List of floats (embedding vector) or None if not available
    """
    # Stub implementation - return None to indicate no embedding
    # Future: Use sentence-transformers or OpenAI embeddings
    logger.debug(f"Embedding generation not implemented, skipping for: {text[:50]}...")
    return None
