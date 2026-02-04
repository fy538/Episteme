"""
Common utilities
"""
import hashlib
import json
import uuid


def generate_dedupe_key(signal_type: str, normalized_text: str, scope_hint: str = "") -> str:
    """
    Generate a dedupe key for signals to prevent duplicates
    
    Args:
        signal_type: Type of signal (e.g., 'Assumption', 'Question')
        normalized_text: Normalized text content
        scope_hint: Optional scope hint (e.g., case_id, thread_id)
    
    Returns:
        SHA256 hash as dedupe key
    """
    content = f"{signal_type}:{normalized_text}:{scope_hint}"
    return hashlib.sha256(content.encode()).hexdigest()


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison and deduplication

    Args:
        text: Raw text

    Returns:
        Normalized text (lowercased, stripped, whitespace normalized)
    """
    return " ".join(text.lower().strip().split())


def is_valid_uuid(value: str) -> bool:
    """
    Check if a string is a valid UUID

    Args:
        value: String to validate

    Returns:
        True if valid UUID, False otherwise
    """
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False
