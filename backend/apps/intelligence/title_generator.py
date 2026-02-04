"""
Title Generator Service

Generates concise titles for:
- Chat threads (after 2nd response)
- Cases (when suggested)

Supports both streaming and non-streaming generation.
"""

from typing import List, Dict, Optional, AsyncIterator
import logging

from apps.common.llm_providers import get_provider

logger = logging.getLogger(__name__)

# Use a fast, cheap model for title generation
TITLE_MODEL = "claude-3-5-haiku-latest"

THREAD_TITLE_SYSTEM_PROMPT = """Generate a very short title (3-6 words) for this conversation.
The title should capture the main topic or intent.
Return ONLY the title, no quotes, no explanation.

Examples:
- Debugging Python async errors
- Marketing strategy for Q2
- Career change considerations
- API authentication design"""

CASE_TITLE_SYSTEM_PROMPT = """Generate a concise case/decision title (4-8 words) based on these signals.
The title should describe the decision or investigation being tracked.
Return ONLY the title, no quotes, no explanation.

Examples:
- Migrate to microservices architecture
- Q3 product launch timing decision
- Engineering team expansion plan
- Customer churn root cause analysis"""


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
        provider = get_provider("anthropic")

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


async def stream_thread_title(
    messages: List[Dict[str, str]],
) -> AsyncIterator[str]:
    """
    Stream a title for a chat thread token by token.

    Args:
        messages: List of message dicts with 'role' and 'content'

    Yields:
        Title tokens as they're generated
    """
    if not messages:
        return

    conversation = _build_conversation_summary(messages)

    try:
        provider = get_provider("anthropic")

        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": conversation}],
            system_prompt=THREAD_TITLE_SYSTEM_PROMPT,
            max_tokens=30,
        ):
            if chunk.content:
                yield chunk.content

    except Exception as e:
        logger.error(f"Failed to stream thread title: {e}")


def _build_conversation_summary(messages: List[Dict[str, str]]) -> str:
    """Build a conversation summary for title generation."""
    return "\n".join([
        f"{msg['role'].upper()}: {msg['content'][:500]}"
        for msg in messages[:4]  # First 4 messages max
    ])


def _clean_title(title: str, max_length: int = 50) -> str:
    """Clean and truncate a generated title."""
    title = title.strip().strip('"\'')
    if len(title) > max_length:
        title = title[:max_length-3] + "..."
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
    if not signals:
        return None

    # Format signals by type
    signals_text = "\n".join([
        f"- [{s.get('type', 'Signal')}] {s.get('text', '')[:200]}"
        for s in signals[:10]
    ])

    context = f"""Signals extracted:
{signals_text}
"""

    if conversation_summary:
        context += f"\nConversation context: {conversation_summary}"

    system_prompt = """Generate a concise case/decision title (4-8 words) based on these signals.
The title should describe the decision or investigation being tracked.
Return ONLY the title, no quotes, no explanation.

Examples:
- "Migrate to microservices architecture"
- "Q3 product launch timing decision"
- "Engineering team expansion plan"
- "Customer churn root cause analysis"
"""

    try:
        provider = get_provider("anthropic")

        response = await provider.generate(
            messages=[{"role": "user", "content": context}],
            system_prompt=system_prompt,
            model=TITLE_MODEL,
            max_tokens=40,
            temperature=0.3,
        )

        title = response.strip().strip('"\'')

        if len(title) > max_length:
            title = title[:max_length-3] + "..."

        logger.info(f"Generated case title: {title}")
        return title

    except Exception as e:
        logger.error(f"Failed to generate case title: {e}")
        return None
