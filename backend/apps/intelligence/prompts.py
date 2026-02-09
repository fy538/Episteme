"""
Unified Prompt Builder for Intelligence Engine

Builds prompts that generate sectioned output:
- <response> - Main chat response
- <reflection> - Meta-cognitive reflection
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class UnifiedPromptConfig:
    """Configuration for unified prompt generation"""
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

    # Add action hints section
    base += """

<action_hints>
Based on the conversation context, suggest ONE helpful action IF appropriate.
Return a JSON array with at most one action hint. Return empty [] if no action is warranted.

Available action types:
- "suggest_case": When the user is wrestling with a real decision that involves multiple factors, trade-offs, or uncertainties. Look for: competing options, unclear consequences, assumptions that need testing, or a question the user keeps circling around. Don't wait for a specific signal count — use your judgment about whether structured thinking would help.
- "suggest_inquiry": When a specific question needs focused investigation
- "suggest_evidence": When mentioned evidence should be formally tracked
- "suggest_resolution": When there's enough evidence to resolve an open inquiry

Each hint should have:
- "type": One of the action types above
- "reason": A conversational sentence explaining why this action would help RIGHT NOW, written as if speaking to the user. This will be shown directly to them.
- "data": Type-specific payload (see examples)

Examples:
[{{"type": "suggest_case", "reason": "You're weighing some real trade-offs here between cost and speed — structuring this as a case could help you test those assumptions.", "data": {{"suggested_title": "Build vs. buy integration decision"}}}}]

[{{"type": "suggest_inquiry", "reason": "The question about salary benchmarks deserves focused research.", "data": {{"question": "What are competitive salary ranges for senior engineers in NYC?", "topic": "salary benchmarks"}}}}]

[{{"type": "suggest_evidence", "reason": "This data point could support your cost analysis.", "data": {{"text": "Current cloud costs are $5k/month", "direction": "supporting"}}}}]

IMPORTANT rules for suggest_case:
- If the user EXPLICITLY asks to create/start/structure a case (e.g. "let's make a case", "structure this as a case", "I want to track this decision"), ALWAYS emit suggest_case immediately.
- If you already suggested a case and the user declined or dismissed it, do NOT suggest again unless the conversation has meaningfully evolved (new decision framing, new constraints, or shifted focus).
- The "reason" field is shown directly to the user as a gentle nudge — make it feel natural, not robotic.

Return [] if:
- The conversation is just getting started (fewer than 3 exchanges)
- There's no clear action that would help right now
- The conversation is purely informational with no decision at stake
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


def build_scaffolding_system_prompt(skill_context: Optional[Dict] = None) -> str:
    """
    Build a system prompt optimized for case scaffolding conversations.

    This prompt turns the assistant into a Socratic interviewer that adapts
    its questions based on what the user has shared. It avoids canned prompts
    in favor of genuinely responsive follow-ups that probe for decision
    context, stakes, uncertainties, and constraints.

    When skill_context is provided (from active skills), the interviewer
    is enhanced with domain knowledge — asking more targeted questions,
    using domain vocabulary, and probing for domain-specific concerns.

    Args:
        skill_context: Optional dict from build_skill_context(), containing
            system_prompt_extension, evidence_standards, artifact_template, etc.
    """
    base = """You are Episteme, conducting a brief Socratic interview to understand a user's decision before scaffolding a structured case.

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

<action_hints>
[]
</action_hints>"""

    # Inject skill-aware domain knowledge
    if skill_context:
        domain_sections = []

        # Add domain knowledge from SKILL.md body
        if skill_context.get('system_prompt_extension'):
            domain_sections.append(
                "# Domain Knowledge\n"
                "Use this domain expertise to ask better, more targeted questions "
                "during the interview. Probe for domain-specific concerns, "
                "use appropriate terminology, and surface risks the user might not "
                "think to mention.\n"
                + skill_context['system_prompt_extension']
            )

        # Add evidence standards awareness
        if skill_context.get('evidence_standards'):
            standards = skill_context['evidence_standards']
            standards_text = "# Evidence Standards for This Domain\n"
            standards_text += (
                "When probing uncertainties, keep these standards in mind — "
                "they shape what kind of evidence will be needed later:\n"
            )
            if 'preferred_sources' in standards:
                standards_text += "Preferred sources: " + ", ".join(standards['preferred_sources']) + "\n"
            if 'minimum_credibility' in standards:
                standards_text += f"Minimum credibility: {standards['minimum_credibility']}\n"
            domain_sections.append(standards_text)

        # Add brief template awareness so interviewer knows what sections to fill
        if skill_context.get('artifact_template'):
            template = skill_context['artifact_template']
            brief_config = template.get('brief', {}) if isinstance(template, dict) else {}
            sections_list = brief_config.get('sections', []) if isinstance(brief_config, dict) else []
            if sections_list:
                headings = []
                for item in sections_list:
                    if isinstance(item, str):
                        headings.append(item)
                    elif isinstance(item, dict):
                        headings.append(item.get('heading', item.get('name', '')))
                if headings:
                    template_text = "# Brief Template Sections\n"
                    template_text += (
                        "This case will use a specialized brief structure. "
                        "During the interview, try to surface information "
                        "relevant to these sections:\n"
                    )
                    for h in headings:
                        template_text += f"- {h}\n"
                    domain_sections.append(template_text)

        if domain_sections:
            base += "\n\n" + "\n\n".join(domain_sections)

    return base


def build_unified_user_prompt(
    user_message: str,
    conversation_context: str = "",
    retrieval_context: str = "",
) -> str:
    """
    Build the user portion of the unified prompt.

    Args:
        user_message: The user's current message
        conversation_context: Formatted previous conversation
        retrieval_context: RAG-retrieved document chunks

    Returns:
        User prompt string
    """
    parts = []

    # Add conversation context if available
    if conversation_context:
        parts.append(f"Previous conversation:\n{conversation_context}")

    # Add retrieved document context for grounding
    if retrieval_context:
        parts.append(f"Relevant documents (cite when using):\n{retrieval_context}")

    # Add the current message
    parts.append(f"User's latest message:\n{user_message}")

    return "\n\n".join(parts)
