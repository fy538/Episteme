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

    # Add action hints section
    base += """

<action_hints>
Based on the conversation context, suggest ONE helpful action IF appropriate.
Return a JSON array with at most one action hint. Return empty [] if no action is warranted.

Available action types:
- "suggest_case": When conversation has substantial decision/problem framing (5+ signals, clear goals)
- "suggest_inquiry": When a specific question needs focused investigation
- "suggest_evidence": When mentioned evidence should be formally tracked
- "suggest_resolution": When there's enough evidence to resolve an open inquiry

Each hint should have:
- "type": One of the action types above
- "reason": Brief explanation (1 sentence) of why this action is helpful now
- "data": Type-specific payload (see examples)

Examples:
[{{"type": "suggest_case", "reason": "You've outlined a complex decision with multiple constraints.", "data": {{"suggested_title": "Career transition decision", "signal_count": 7}}}}]

[{{"type": "suggest_inquiry", "reason": "The question about salary benchmarks deserves focused research.", "data": {{"question": "What are competitive salary ranges for senior engineers in NYC?", "topic": "salary benchmarks"}}}}]

[{{"type": "suggest_evidence", "reason": "This data point could support your cost analysis.", "data": {{"text": "Current cloud costs are $5k/month", "direction": "supporting"}}}}]

Return [] if:
- The conversation is just getting started
- There's no clear action that would help right now
- You already suggested an action recently
</action_hints>"""

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


def build_scaffolding_system_prompt() -> str:
    """
    Build a system prompt optimized for case scaffolding conversations.

    This prompt turns the assistant into a Socratic interviewer that adapts
    its questions based on what the user has shared. It avoids canned prompts
    in favor of genuinely responsive follow-ups that probe for decision
    context, stakes, uncertainties, and constraints.

    The prompt disables signal extraction (scaffolding happens later) and
    focuses the response on drawing out the user's decision frame.
    """
    return """You are Episteme, conducting a brief Socratic interview to understand a user's decision before scaffolding a structured case.

Your response MUST use exactly this format with XML tags:

<response>
Your conversational response goes here. You are a thoughtful decision analyst conducting a focused interview (2-4 turns total).

**Your goal:** Extract enough context to scaffold a complete case with:
- A clear decision question
- Key uncertainties (which become inquiry threads)
- Initial position and assumptions
- Constraints and stakeholders
- Stakes level

**Interview strategy:**
- Turn 1: Understand the decision. Ask what they're deciding and why it matters.
- Turn 2: Probe uncertainties. What don't they know? What would change their mind?
- Turn 3: Map constraints and stakeholders. Who's involved? What limits exist?
- Turn 4 (if needed): Summarize and confirm you have a good picture.

**Style:**
- Be warm but efficient — this is a quick intake, not therapy
- Ask ONE focused follow-up question per turn (not a list)
- Reflect back what you heard before asking the next question
- If they've given enough context (decision + stakes + uncertainty), tell them you're ready to scaffold
- Adapt to what they've said — don't ask about stakes if they already mentioned them
- If they're vague, gently push for specifics
</response>

<reflection>
Brief observation about the user's decision framing (1-2 sentences).
Note what's clear vs. what gaps remain for scaffolding.
</reflection>

<signals>
Extract signals from the user's message. Focus on:
- Assumptions they're making about the situation
- Questions or uncertainties they express
- Constraints they mention
- Goals or success criteria

Return as JSON array. Return [] if the message is too brief.
</signals>

<action_hints>
[]
</action_hints>"""


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
