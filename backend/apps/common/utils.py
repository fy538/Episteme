"""
Common utilities
"""
import json
import logging
import re
import uuid
from typing import Any

logger = logging.getLogger(__name__)


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


def parse_json_from_response(text: str) -> Any:
    """
    Multi-strategy JSON extraction from LLM response text.

    Tries in order:
    1. Direct JSON parse
    2. Extract from Markdown code fence (```json ... ```)
    3. Find outermost array ([...]) or object ({...})

    Returns the parsed JSON (dict, list, etc.) or None on failure.
    """
    if not text:
        return None

    text = text.strip()

    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from code fence
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find first [ to last ] (array) or { to } (object)
    for open_char, close_char in [('[', ']'), ('{', '}')]:
        first = text.find(open_char)
        last = text.rfind(close_char)
        if first != -1 and last > first:
            try:
                return json.loads(text[first:last + 1])
            except json.JSONDecodeError:
                pass

    logger.warning("json_parse_failed", extra={"text_preview": text[:200]})
    return None
