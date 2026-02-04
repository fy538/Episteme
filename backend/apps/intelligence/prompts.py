"""
Unified Prompt Builder for Intelligence Engine

Builds prompts that generate sectioned output:
- <response> - Main chat response
- <reflection> - Meta-cognitive reflection
- <signals> - Signal extraction (conditional)
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class UnifiedPromptConfig:
    """Configuration for unified prompt generation"""
    include_signals: bool = True
    signal_types: List[str] = None
    topic: str = ""
    patterns: Dict = None


def build_unified_system_prompt(config: UnifiedPromptConfig) -> str:
    """
    Build the system prompt for unified analysis.

    Args:
        config: Configuration for prompt generation

    Returns:
        System prompt string
    """
    # Base persona
    base = """You are Episteme, a thoughtful assistant that helps users think through complex decisions and investigations.

Your response MUST use exactly this format with XML tags:

<response>
Your main conversational response goes here. Be concise (2-4 paragraphs max).
- Ask clarifying questions to surface assumptions
- Help articulate constraints and goals
- Challenge weak reasoning gently
- Suggest alternative perspectives
- Point out potential risks or blind spots
</response>

<reflection>
Brief meta-cognitive observation (2-3 sentences max).
Focus on ONE key insight:
- A blind spot in their thinking
- An assumption worth questioning
- A missing perspective
- A pattern you notice
Be direct and specific. No fluff.
</reflection>"""

    # Add signals section if extraction is enabled
    if config.include_signals:
        signal_types = config.signal_types or ["Assumption", "Question", "Constraint", "Goal", "Claim"]
        types_list = ", ".join(signal_types)

        signals_section = f"""

<signals>
Extract epistemic signals from the USER's message as a JSON array.
Signal types to extract: {types_list}

Each signal should have:
- "type": One of [{types_list}]
- "text": The extracted statement (normalized to standalone)
- "confidence": 0.0-1.0 (how certain is the extraction)

Example:
[
  {{"type": "Assumption", "text": "Users prefer speed over accuracy", "confidence": 0.85}},
  {{"type": "Question", "text": "What's the current system latency?", "confidence": 0.95}}
]

Return empty array [] if no clear signals found.
</signals>"""
        base += signals_section
    else:
        # Even without extraction, include empty signals tag for consistent parsing
        base += """

<signals>
[]
</signals>"""

    # Add context about current patterns if available
    if config.patterns:
        patterns_context = _format_patterns_context(config.patterns)
        if patterns_context:
            base += f"""

Context about the conversation:
{patterns_context}"""

    return base


def _format_patterns_context(patterns: Dict) -> str:
    """Format graph patterns into context string"""
    parts = []

    ungrounded = patterns.get('ungrounded_assumptions', [])
    if ungrounded:
        count = len(ungrounded)
        parts.append(f"- {count} ungrounded assumption(s) identified")

    contradictions = patterns.get('contradictions', [])
    if contradictions:
        count = len(contradictions)
        parts.append(f"- {count} potential contradiction(s) detected")

    strong_claims = patterns.get('strong_claims', [])
    if strong_claims:
        count = len(strong_claims)
        parts.append(f"- {count} well-supported claim(s)")

    return "\n".join(parts) if parts else ""


def build_unified_user_prompt(
    user_message: str,
    conversation_context: str = "",
    signals_context: Optional[List[Dict]] = None
) -> str:
    """
    Build the user portion of the unified prompt.

    Args:
        user_message: The user's current message
        conversation_context: Formatted previous conversation
        signals_context: Existing signals for context (optional)

    Returns:
        User prompt string
    """
    parts = []

    # Add conversation context if available
    if conversation_context:
        parts.append(f"Previous conversation:\n{conversation_context}")

    # Add signals context if available
    if signals_context:
        signals_text = _format_signals_context(signals_context)
        if signals_text:
            parts.append(f"Existing signals from this conversation:\n{signals_text}")

    # Add the current message
    parts.append(f"User's latest message:\n{user_message}")

    return "\n\n".join(parts)


def _format_signals_context(signals: List[Dict]) -> str:
    """Format existing signals into context string"""
    if not signals:
        return ""

    # Group by type
    by_type = {}
    for signal in signals[:10]:  # Limit to 10 most relevant
        sig_type = signal.get('type', 'Unknown')
        if sig_type not in by_type:
            by_type[sig_type] = []
        by_type[sig_type].append(signal)

    parts = []
    for sig_type, sigs in by_type.items():
        type_signals = [f"  - {s['text']}" for s in sigs[:3]]  # Max 3 per type
        parts.append(f"{sig_type}s:\n" + "\n".join(type_signals))

    return "\n".join(parts)


def build_action_hints(thread_context: Dict) -> str:
    """
    Build action hints to weave into response naturally.

    When the assistant detects certain patterns, it can naturally
    incorporate suggestions into the response.

    Args:
        thread_context: Context about the thread state

    Returns:
        Action hints string (or empty)
    """
    hints = []

    # Check for case suggestion
    if thread_context.get('should_suggest_case'):
        hints.append(
            "If appropriate, naturally suggest that this decision "
            "might benefit from more structured tracking."
        )

    # Check for research suggestion
    if thread_context.get('has_ungrounded_assumptions'):
        hints.append(
            "If appropriate, gently note that some assumptions "
            "could benefit from validation."
        )

    # Check for inquiry suggestion
    if thread_context.get('has_open_questions', 0) > 3:
        hints.append(
            "If appropriate, suggest organizing the open questions "
            "into a focused investigation."
        )

    return "\n".join(hints) if hints else ""
