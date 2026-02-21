"""Helpers for surfacing embedding generation state on node properties."""
from typing import Optional

EMBEDDING_STATUS_KEY = "_embedding_status"
EMBEDDING_ERROR_KEY = "_embedding_error"
EMBEDDING_STATUS_FAILED = "failed"


def mark_embedding_failed(properties: Optional[dict], reason: str) -> dict:
    """Mark properties to indicate embedding generation failed."""
    updated = dict(properties or {})
    updated[EMBEDDING_STATUS_KEY] = EMBEDDING_STATUS_FAILED
    updated[EMBEDDING_ERROR_KEY] = (reason or "unknown")[:200]
    return updated


def clear_embedding_failure(properties: Optional[dict]) -> dict:
    """Remove embedding-failure markers when embedding generation succeeds."""
    updated = dict(properties or {})
    updated.pop(EMBEDDING_STATUS_KEY, None)
    updated.pop(EMBEDDING_ERROR_KEY, None)
    return updated
