"""
General-purpose AI services using PydanticAI

These are "one-off" LLM services for features like title generation,
summarization, and other non-agentic tasks.
"""
import logging
from typing import List, Optional
from pydantic_ai import Agent
from django.conf import settings

from .ai_schemas import TitleGeneration, SummaryGeneration
from .ai_models import get_model

logger = logging.getLogger(__name__)

# Title Generation Agent
title_agent = Agent(
    get_model(settings.AI_MODELS['fast']),
    result_type=TitleGeneration,
    system_prompt=(
        "You generate concise, descriptive titles for conversations and cases. "
        "Keep titles between 3-7 words. Focus on the core topic or decision. "
        "No quotes, no punctuation at the end."
    )
)


# Summary Agent
summary_agent = Agent(
    get_model(settings.AI_MODELS['reasoning']),
    result_type=SummaryGeneration,
    system_prompt=(
        "You create clear, actionable summaries of technical conversations. "
        "Extract the key points and decision factors. "
        "Be concise but comprehensive."
    )
)


async def generate_chat_title(messages: List[str], max_length: int = 50) -> str:
    """
    Generate a title for a chat thread based on its messages
    
    Args:
        messages: List of message contents (chronological order)
        max_length: Maximum character length for title
        
    Returns:
        Generated title string
    """
    if not messages:
        return "New Conversation"
    
    # Take first 5 messages for context
    context_messages = messages[:5]
    chat_preview = "\n".join([f"- {msg[:200]}" for msg in context_messages])
    
    prompt = f"""Based on this conversation, generate a descriptive title:

{chat_preview}

Title should capture the main topic or decision being discussed."""
    
    try:
        result = await title_agent.run(prompt)
        title = result.data.title
        
        # Enforce max length
        if len(title) > max_length:
            title = title[:max_length-3] + "..."
        
        return title
    except Exception:
        logger.exception("title_generation_failed", extra={"message_count": len(messages)})
        return "Untitled Conversation"


async def generate_case_title(
    position: str,
    context: Optional[str] = None
) -> str:
    """
    Generate a title for a case based on its position statement
    
    Args:
        position: The case's position/thesis statement
        context: Optional additional context
        
    Returns:
        Generated title string
    """
    prompt = f"""Generate a clear, decision-focused title for this case:

Position: {position}
"""
    
    if context:
        prompt += f"\nContext: {context}\n"
    
    prompt += "\nTitle should describe the decision or investigation."
    
    try:
        result = await title_agent.run(prompt)
        return result.data.title
    except Exception:
        logger.exception("case_title_generation_failed", extra={"position_length": len(position)})
        # Fallback: use first few words of position
        words = position.split()[:6]
        return " ".join(words) + ("..." if len(position.split()) > 6 else "")


async def summarize_conversation(
    messages: List[str],
    focus: Optional[str] = None
) -> dict:
    """
    Generate a summary of a conversation
    
    Args:
        messages: List of message contents
        focus: Optional focus area (e.g., "decisions", "questions", "risks")
        
    Returns:
        Dict with 'summary' and 'key_points' keys
    """
    if not messages:
        return {"summary": "No messages to summarize", "key_points": []}
    
    conversation_text = "\n\n".join([
        f"Message {i+1}: {msg}"
        for i, msg in enumerate(messages)
    ])
    
    prompt = f"""Summarize this conversation:

{conversation_text[:3000]}  # Limit to prevent token overflow
"""
    
    if focus:
        prompt += f"\nFocus on: {focus}"
    
    try:
        result = await summary_agent.run(prompt)
        return {
            "summary": result.data.summary,
            "key_points": result.data.key_points
        }
    except Exception:
        logger.exception("summarization_failed", extra={"message_count": len(messages)})
        return {
            "summary": "Summary generation failed",
            "key_points": []
        }
