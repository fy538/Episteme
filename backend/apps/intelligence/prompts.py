"""
Unified Prompt Builder for Intelligence Engine

Builds prompts that generate sectioned output:
- <response> - Main chat response
- <reflection> - Meta-cognitive reflection
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class UnifiedPromptConfig:
    """Configuration for unified prompt generation"""
    topic: str = ""
    patterns: Dict = None


def build_unified_system_prompt(
    config: UnifiedPromptConfig,
    available_tools: Optional[List] = None,
) -> str:
    """
    Build the system prompt for unified analysis.

    Args:
        config: Configuration for prompt generation
        available_tools: Optional list of ToolDefinition objects to inject

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

    # Add tool actions section if tools are available
    if available_tools:
        base += _build_tool_actions_prompt(available_tools)

    # Add context about current patterns if available
    if config.patterns:
        patterns_context = _format_patterns_context(config.patterns)
        if patterns_context:
            base += f"""

Context about the conversation:
{patterns_context}"""

    return base


def _build_tool_actions_prompt(available_tools: List) -> str:
    """
    Build the <tool_actions> section instruction for tools.

    This teaches the LLM to emit executable tool calls in a structured
    JSON section, separate from the suggestive action_hints.
    """
    from apps.intelligence.tools.registry import ToolRegistry

    tool_descriptions = ToolRegistry.get_prompt_text(available_tools)

    return f"""

<tool_actions>
If you determine an action should be taken NOW (not just suggested), emit it here as a JSON array.
Return [] if no action is warranted.

Available tools:
{tool_descriptions}

Each action must have:
- "tool": Tool name from the list above
- "params": Parameters matching the tool's schema
- "reason": Brief explanation of why this action is appropriate now

IMPORTANT:
- Only emit actions when you're confident they're correct and the conversation warrants them
- Actions marked [auto] will execute immediately — be conservative
- Actions marked [requires confirmation] will be shown to the user for approval before executing
- Prefer tool_actions over action_hints when the action is concrete enough to execute
- You may emit multiple actions if warranted

Example:
[{{"tool": "create_inquiry", "params": {{"title": "What are the cost implications of Option B?", "description": "The user raised budget concerns that need focused investigation."}}, "reason": "This specific question emerged as a key uncertainty."}}]

Return [] if:
- No concrete action is warranted right now
- The conversation is exploratory and actions would be premature
- You're unsure about the parameters
</tool_actions>"""


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


def build_case_aware_system_prompt(
    stage: str,
    plan_content: Optional[Dict] = None,
    decision_question: str = '',
    position_statement: str = '',
    constraints: Optional[List] = None,
    success_criteria: Optional[List] = None,
    available_tools: Optional[List] = None,
) -> str:
    """
    Build a system prompt for case-scoped chat that includes the full plan
    state and instructions for proposing plan edits.

    The AI sees the current investigation plan (assumptions, criteria, phases)
    and can propose changes through a <plan_edits> section. The LLM emits
    only the diff (what changed); the backend merges it with the current plan
    state to produce the full snapshot.

    Uses a composable sections pattern — each section is built independently
    and joined at the end.

    Args:
        stage: Current investigation stage (exploring/investigating/synthesizing/ready)
        plan_content: Current plan version content dict (assumptions, criteria, phases)
        decision_question: The case's decision question
        position_statement: Current position statement from the plan
        constraints: Case constraints list
        success_criteria: Case success criteria list
    """
    sections: List[str] = []

    # --- Section: Persona + output format ---
    sections.append(_build_persona_section())

    # --- Section: Case context ---
    case_section = _build_case_context_section(
        decision_question, position_statement, constraints, success_criteria,
    )
    if case_section:
        sections.append(case_section)

    # --- Section: Stage guidance ---
    sections.append(_build_stage_guidance_section(stage))

    # --- Section: Plan state ---
    sections.append(_build_plan_state_section(plan_content))

    # --- Section: Plan edits instructions ---
    sections.append(_build_plan_edits_section())

    # --- Section: Tool actions (if tools available) ---
    if available_tools:
        sections.append(_build_tool_actions_prompt(available_tools))

    return "\n\n".join(sections)


def _build_persona_section() -> str:
    """Base persona and output format for case-scoped chat."""
    return """You are Episteme, a decision-support analyst guiding the user through a structured investigation.

You have access to the user's investigation plan — their assumptions, decision criteria, and investigation phases. Your role is to help them investigate rigorously, challenge weak reasoning, and evolve the plan as new information emerges.

Your response MUST use exactly this format with XML tags:

<response>
Your main conversational response goes here. Be concise (2-4 paragraphs max).
- Help the user investigate their decision systematically
- Challenge assumptions when evidence warrants it
- Suggest concrete next steps aligned with the current investigation stage
- Reference specific assumptions or criteria by their IDs when relevant
- Point out when new information should update the plan
</response>

<reflection>
Brief meta-cognitive observation (2-3 sentences max).
Focus on ONE key insight about the investigation's progress or gaps.
</reflection>

<action_hints>
Return a JSON array with at most one action hint. Return empty [] if no action is warranted.

Available action types:
- "suggest_inquiry": When a specific question needs focused investigation
- "suggest_evidence": When mentioned evidence should be formally tracked
- "suggest_resolution": When there's enough evidence to resolve an open inquiry

Each hint should have:
- "type": One of the action types above
- "reason": A conversational sentence explaining why this action would help RIGHT NOW
- "data": Type-specific payload

Return [] if no action is warranted right now.
</action_hints>"""


def _build_case_context_section(
    decision_question: str,
    position_statement: str,
    constraints: Optional[List],
    success_criteria: Optional[List],
) -> Optional[str]:
    """Case context section — decision question, position, constraints."""
    parts = []
    if decision_question:
        parts.append(f"**Decision question:** {decision_question}")
    if position_statement:
        parts.append(f"**Current position:** {position_statement}")
    if constraints:
        constraint_texts = []
        for c in constraints:
            if isinstance(c, dict):
                constraint_texts.append(c.get('description', c.get('text', str(c))))
            else:
                constraint_texts.append(str(c))
        parts.append("**Constraints:** " + "; ".join(constraint_texts))
    if success_criteria:
        criteria_texts = []
        for sc in success_criteria:
            if isinstance(sc, dict):
                # Canonical key is 'criterion'; fall back to 'text'/'name' for legacy data
                criteria_texts.append(sc.get('criterion', sc.get('text', sc.get('name', str(sc)))))
            else:
                criteria_texts.append(str(sc))
        parts.append("**Success criteria:** " + "; ".join(criteria_texts))

    if not parts:
        return None
    return "## Case Context\n" + "\n".join(parts)


_STAGE_GUIDANCE = {
    'exploring': (
        "**Stage: Exploring** — The investigation is just getting started. "
        "Help surface assumptions, identify blind spots, and map the decision space. "
        "Ask probing questions. Suggest areas that need investigation."
    ),
    'investigating': (
        "**Stage: Investigating** — The user is actively gathering evidence. "
        "Help them evaluate evidence quality, challenge assumptions, and update "
        "assumption statuses as new information arrives. Flag when assumptions "
        "should move from untested → confirmed/challenged/refuted."
    ),
    'synthesizing': (
        "**Stage: Synthesizing** — The user is pulling findings together. "
        "Help them evaluate decision criteria, weigh trade-offs, assess which "
        "criteria are met vs unmet, and refine their position. Surface any "
        "remaining gaps before a decision."
    ),
    'ready': (
        "**Stage: Ready** — The investigation is nearing completion. "
        "Help finalize the decision, ensure all criteria are addressed, "
        "and identify any last concerns. The plan should be stable."
    ),
}


def _build_stage_guidance_section(stage: str) -> str:
    """Stage-specific guidance section."""
    return _STAGE_GUIDANCE.get(stage, _STAGE_GUIDANCE['exploring'])


def _build_plan_state_section(plan_content: Optional[Dict]) -> str:
    """Plan state section — assumptions, criteria, phases."""
    if plan_content and isinstance(plan_content, dict):
        return "## Investigation Plan" + _format_plan_state(plan_content)
    return (
        "## Investigation Plan\n"
        "No plan has been created yet. If the conversation warrants it, "
        "help the user think about what assumptions and criteria matter "
        "for their decision."
    )


def _build_plan_edits_section() -> str:
    """Plan edits instructions — diff-only format (no proposed_content)."""
    return """## Plan Edits

When the conversation warrants changes to the investigation plan, emit a <plan_edits> section with a JSON object describing ONLY the changes. Do NOT echo back unchanged content — the system will merge your diff with the current plan state automatically.

<plan_edits>
{
  "diff_summary": "Human-readable summary of what changed and why",
  "diff_data": {
    "added_assumptions": [{"text": "...", "risk_level": "low|medium|high"}],
    "updated_assumptions": [{"id": "existing-uuid", "status": "confirmed|challenged|refuted", "evidence_summary": "Why this status changed"}],
    "added_criteria": [{"text": "...", "priority": "must_have|nice_to_have"}],
    "updated_criteria": [{"id": "existing-uuid", "is_met": true}],
    "stage_change": "investigating|synthesizing|ready" or null
  }
}
</plan_edits>

Only include the keys in diff_data that have actual changes. Omit empty arrays.

**When to propose plan edits:**
- User mentions a new assumption or belief → add assumption
- Evidence changes an assumption's validity → update assumption status
- User articulates a new success criterion → add criterion
- Evidence satisfies a criterion → mark criterion as met
- Investigation has progressed enough to advance the stage → propose stage change
- User explicitly asks to modify the plan

**When NOT to propose plan edits:**
- Casual conversation or clarifying questions
- No new information that affects assumptions or criteria
- The user is asking about the plan (just answer their question)

If no plan changes are warranted, emit an empty object:
<plan_edits>{}</plan_edits>"""


def _format_plan_state(plan_content: Dict) -> str:
    """
    Format plan content into a compact representation for the system prompt.

    For plans with many assumptions, applies size management:
    - Always includes non-default-status items (confirmed/challenged/refuted)
    - Includes first 5 untested assumptions
    - Shows summary counts for the rest
    """
    parts = []

    # --- Assumptions ---
    assumptions = plan_content.get('assumptions', [])
    if assumptions:
        status_symbols = {
            'untested': '❓',
            'confirmed': '✅',
            'challenged': '⚠️',
            'refuted': '❌',
        }

        # Separate by status for size management
        non_default = [a for a in assumptions if a.get('status', 'untested') != 'untested']
        untested = [a for a in assumptions if a.get('status', 'untested') == 'untested']

        # Always show non-default status items
        shown = list(non_default)

        # Show up to 5 untested + summarize rest
        if len(untested) <= 5:
            shown.extend(untested)
            remaining_untested = 0
        else:
            shown.extend(untested[:5])
            remaining_untested = len(untested) - 5

        parts.append(f"\n### Assumptions ({len(assumptions)} total)")
        for a in shown:
            status = a.get('status', 'untested')
            symbol = status_symbols.get(status, '❓')
            risk = a.get('risk_level', '')
            risk_tag = f" (risk: {risk})" if risk else ""
            a_id = a.get('id', '')
            id_tag = f" [id: {a_id}]" if a_id else ""
            text = a.get('text', a.get('content', ''))
            parts.append(f"- {symbol} [{status.upper()}] \"{text}\"{risk_tag}{id_tag}")

        if remaining_untested > 0:
            parts.append(f"- ... and {remaining_untested} more untested assumptions")

    # --- Decision criteria ---
    criteria = plan_content.get('decision_criteria', [])
    if criteria:
        met_count = sum(1 for c in criteria if c.get('is_met'))
        parts.append(f"\n### Decision Criteria ({len(criteria)} total, {met_count} met)")
        for c in criteria:
            check = "x" if c.get('is_met') else " "
            c_id = c.get('id', '')
            id_tag = f" [id: {c_id}]" if c_id else ""
            priority = c.get('priority', '')
            priority_tag = f" ({priority})" if priority else ""
            text = c.get('text', c.get('content', ''))
            parts.append(f"- [{check}] \"{text}\"{priority_tag}{id_tag}")

    # --- Phases ---
    phases = plan_content.get('phases', [])
    if phases:
        parts.append(f"\n### Investigation Phases ({len(phases)} total)")
        for i, phase in enumerate(phases):
            title = phase.get('title', phase.get('name', f'Phase {i+1}'))
            status = phase.get('status', '')
            status_tag = f" [{status}]" if status else ""
            parts.append(f"- {title}{status_tag}")
            # Show phase tasks briefly
            tasks = phase.get('tasks', phase.get('steps', []))
            if tasks and len(tasks) <= 5:
                for task in tasks:
                    if isinstance(task, dict):
                        task_text = task.get('text', task.get('title', str(task)))
                        task_done = task.get('done', task.get('completed', False))
                        t_check = "x" if task_done else " "
                        parts.append(f"  - [{t_check}] {task_text}")
                    else:
                        parts.append(f"  - {task}")
            elif tasks:
                done_count = sum(1 for t in tasks if isinstance(t, dict) and (t.get('done') or t.get('completed')))
                parts.append(f"  ({len(tasks)} tasks, {done_count} done)")

    return "\n".join(parts) if parts else "\nNo assumptions, criteria, or phases defined yet."


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

    # Add retrieved document context for grounding with citation instructions
    if retrieval_context:
        parts.append(f"""The following passages are from the user's project documents. When you use information from these sources, cite them using the bracketed number (e.g. [1], [2]).

{retrieval_context}

Citation rules:
- Use [N] inline when referencing a source, e.g. "PostgreSQL handles 50k writes/sec [1]"
- Only cite when you're actually using information from that source
- You can cite multiple sources in one statement [1][3]
- If you're not using any source, don't cite anything
- Don't fabricate citations — only use numbers that appear above""")

    # Add the current message
    parts.append(f"User's latest message:\n{user_message}")

    return "\n\n".join(parts)
