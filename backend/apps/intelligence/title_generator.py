"""
Title Generator Service

Generates concise titles for:
- Chat threads (inline during SSE stream)
- Cases (when scaffolded or suggested)
- Inquiries (when promoted from signals)

Uses a small, fast model and instruction-after-content prompting
for reliable short-form generation.
"""

import re
from typing import List, Dict, Optional
import logging

from apps.common.llm_providers import get_llm_provider

logger = logging.getLogger(__name__)

# Use a fast, cheap model for title generation
TITLE_MODEL = "claude-haiku-4-5-20251001"

# Lightweight system prompt — formatting rules go in the user message suffix
THREAD_TITLE_SYSTEM_PROMPT = (
    "You are a concise title generator. "
    "Respond with only the title text, nothing else."
)

CASE_TITLE_SYSTEM_PROMPT = (
    "You are a concise title generator for decision cases. "
    "Respond with only the title text, nothing else."
)

INQUIRY_TITLE_SYSTEM_PROMPT = (
    "You are a concise title generator for investigations. "
    "Respond with only the title text, nothing else."
)


async def generate_thread_title(
    messages: List[Dict[str, str]],
    max_length: int = 50
) -> Optional[str]:
    """
    Generate a concise title for a chat thread (non-streaming).

    Args:
        messages: List of message dicts with 'role' and 'content'
        max_length: Maximum title length

    Returns:
        Generated title or None if generation fails
    """
    if not messages:
        return None

    conversation = _build_conversation_summary(messages)

    try:
        provider = get_llm_provider("fast")

        response = await provider.generate(
            messages=[{"role": "user", "content": conversation}],
            system_prompt=THREAD_TITLE_SYSTEM_PROMPT,
            model=TITLE_MODEL,
            max_tokens=30,
            temperature=0.3,
        )

        title = _clean_title(response, max_length)
        logger.info(f"Generated thread title: {title}")
        return title

    except Exception as e:
        logger.error(f"Failed to generate thread title: {e}")
        return None


def _build_conversation_summary(messages: List[Dict[str, str]]) -> str:
    """
    Build a conversation summary for title generation.

    Uses instruction-after-content pattern for better compliance
    with small models.
    """
    conversation = "\n".join([
        f"{msg['role'].upper()}: {msg['content'][:500]}"
        for msg in messages[:6]
    ])
    return (
        f"{conversation}\n"
        "-----\n"
        "Generate a concise 3-6 word title for the above conversation. "
        "Do not add quotation marks or formatting. "
        "Respond with only the title."
    )


def _clean_title(title: str, max_length: int = 50) -> str:
    """Clean and truncate a generated title."""
    # Strip quotes, markdown, asterisks, hashes
    title = re.sub(r'^[#*"\'`\s]+', '', title)
    title = re.sub(r'["\'`]+$', '', title)
    title = title.strip()
    # Remove common model preambles
    title = re.sub(r'^(?:Title|Subject|Topic|Here\'s a title):\s*', '', title, flags=re.IGNORECASE)
    if len(title) > max_length:
        title = title[:max_length - 3] + "..."
    return title


async def generate_case_title(
    signals: List[Dict],
    conversation_summary: str = "",
    max_length: int = 60
) -> Optional[str]:
    """
    Generate a title for a case based on signals and context.

    Args:
        signals: List of signal dicts with 'type' and 'text'
        conversation_summary: Brief summary of the conversation
        max_length: Maximum title length

    Returns:
        Generated case title or None if generation fails
    """
    if not signals and not conversation_summary:
        return None

    # Build context from signals if present
    parts = []
    if signals:
        signals_text = "\n".join([
            f"- [{s.get('type', 'Signal')}] {s.get('text', '')[:200]}"
            for s in signals[:10]
        ])
        parts.append(f"Signals extracted:\n{signals_text}")

    if conversation_summary:
        parts.append(f"Context: {conversation_summary}")

    context = "\n\n".join(parts)
    context += (
        "\n-----\n"
        "Generate a concise 4-8 word title describing the decision or investigation. "
        "Do not add quotation marks or formatting. "
        "Respond with only the title."
    )

    try:
        provider = get_llm_provider("fast")

        response = await provider.generate(
            messages=[{"role": "user", "content": context}],
            system_prompt=CASE_TITLE_SYSTEM_PROMPT,
            model=TITLE_MODEL,
            max_tokens=40,
            temperature=0.3,
        )

        title = _clean_title(response, max_length)
        logger.info(f"Generated case title: {title}")
        return title

    except Exception as e:
        logger.error(f"Failed to generate case title: {e}")
        return None


async def generate_inquiry_title(
    source_text: str,
    signal_type: str = "assumption",
    max_length: int = 80
) -> Optional[str]:
    """
    Generate a concise investigation title from a signal or assumption.

    Args:
        source_text: The signal/assumption text to convert
        signal_type: Type of signal (assumption, question, claim, etc.)
        max_length: Maximum title length

    Returns:
        Generated inquiry title or None if generation fails
    """
    if not source_text:
        return None

    content = (
        f"[{signal_type.upper()}] {source_text[:300]}\n"
        "-----\n"
        "Convert the above into a concise 4-8 word investigation title. "
        "Frame it as an active investigation or question to resolve. "
        "Do not add quotation marks or formatting. "
        "Respond with only the title."
    )

    try:
        provider = get_llm_provider("fast")

        response = await provider.generate(
            messages=[{"role": "user", "content": content}],
            system_prompt=INQUIRY_TITLE_SYSTEM_PROMPT,
            model=TITLE_MODEL,
            max_tokens=30,
            temperature=0.3,
        )

        title = _clean_title(response, max_length)
        logger.info(f"Generated inquiry title: {title}")
        return title

    except Exception as e:
        logger.error(f"Failed to generate inquiry title: {e}")
        return None
