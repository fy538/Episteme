"""
Shared utilities for LLM interactions.

Eliminates duplicated JSON-parsing boilerplate across views and services.
"""
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def strip_markdown_fences(text: str) -> str:
    """
    Strip markdown code fences from LLM response text.

    Handles patterns like:
        ```json\n{...}\n```
        ```\n{...}\n```
    """
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


async def stream_and_collect(provider, messages: list, system_prompt: str) -> str:
    """
    Stream an LLM response and collect the full text.

    Args:
        provider: LLM provider instance (from get_llm_provider)
        messages: List of message dicts [{"role": "user", "content": "..."}]
        system_prompt: System prompt string

    Returns:
        Full response text
    """
    full_response = ""
    async for chunk in provider.stream_chat(
        messages=messages,
        system_prompt=system_prompt,
    ):
        full_response += chunk.content
    return full_response


async def stream_json(
    provider,
    messages: list,
    system_prompt: str,
    fallback: Any = None,
    description: str = "LLM JSON response",
) -> Any:
    """
    Stream an LLM response and parse it as JSON.

    Handles markdown code fences and provides safe fallback on parse failure.

    Args:
        provider: LLM provider instance
        messages: List of message dicts
        system_prompt: System prompt string
        fallback: Value to return if parsing fails (default: None)
        description: Human-readable description for log messages

    Returns:
        Parsed JSON value, or fallback on failure
    """
    full_response = await stream_and_collect(provider, messages, system_prompt)

    try:
        cleaned = strip_markdown_fences(full_response)
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError, IndexError) as e:
        logger.warning("Failed to parse %s: %s", description, e)
        return fallback
