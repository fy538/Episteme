"""
Case-aware prompt builders for AI co-pilot integration.

These prompts help the AI understand case context and generate
relevant suggestions for inquiries, gaps, and evidence sources.

Prompt builders are pure functions that return prompt strings.
They never call LLM providers or perform async I/O.
"""
from typing import List, Dict, Any, Optional


def build_case_context_prompt(case) -> str:
    """
    Build a comprehensive context prompt including decision frame,
    inquiries, signals, and current state.

    Used as a system prompt prefix for case-scoped AI interactions.
    """
    sections = []

    # Decision frame
    sections.append("## Decision Context")
    sections.append(f"**Title:** {case.title}")

    if case.decision_question:
        sections.append(f"**Decision Question:** {case.decision_question}")

    if case.position:
        sections.append(f"**Current Position:** {case.position}")

    if case.user_confidence is not None:
        sections.append(f"**Confidence:** {case.user_confidence}%")

    # Constraints
    if case.constraints:
        sections.append("\n**Constraints:**")
        for c in case.constraints:
            sections.append(f"- {c.get('type', 'General')}: {c.get('description', '')}")

    # Success criteria
    if case.success_criteria:
        sections.append("\n**Success Criteria:**")
        for sc in case.success_criteria:
            measurable = f" ({sc.get('measurable')})" if sc.get('measurable') else ""
            sections.append(f"- {sc.get('criterion', '')}{measurable}")

    # Stakeholders
    if case.stakeholders:
        sections.append("\n**Stakeholders:**")
        for s in case.stakeholders:
            sections.append(
                f"- {s.get('name', 'Unknown')}: {s.get('interest', '')} "
                f"(influence: {s.get('influence', 'medium')})"
            )

    # Inquiries
    inquiries = list(case.inquiries.all())
    if inquiries:
        sections.append("\n## Open Questions & Investigations")

        open_inquiries = [i for i in inquiries if i.status in ['open', 'investigating']]
        resolved_inquiries = [i for i in inquiries if i.status == 'resolved']

        if open_inquiries:
            sections.append("\n**Active Inquiries:**")
            for i in open_inquiries[:10]:  # Limit to 10
                status = "🔍" if i.status == 'investigating' else "❓"
                sections.append(f"- {status} {i.title}")

        if resolved_inquiries:
            sections.append("\n**Resolved Inquiries:**")
            for i in resolved_inquiries[:5]:  # Limit to 5
                conf = f" ({int(i.conclusion_confidence * 100)}%)" if i.conclusion_confidence else ""
                sections.append(f"- ✓ {i.title}{conf}")
                if i.conclusion:
                    sections.append(f"  → {i.conclusion[:150]}...")

    return "\n".join(sections)


def build_gap_analysis_prompt(case) -> str:
    """
    Build a prompt to identify missing considerations in a case.

    Returns a prompt that will generate:
    - Missing perspectives
    - Unvalidated assumptions
    - Potential contradictions
    - Evidence gaps
    - Recommendations
    """
    context = build_case_context_prompt(case)

    prompt = f"""{context}

---

## Task: Gap Analysis ("What am I missing?")

Analyze this decision case thoroughly and identify what's missing or potentially problematic.
Think like a critical advisor who wants to help make a well-informed decision.

Please identify:

1. **Missing Perspectives** (3-5 items)
   - What viewpoints or considerations haven't been explored?
   - Who else might have relevant input that hasn't been considered?
   - What alternative interpretations of the evidence exist?

2. **Unvalidated Assumptions** (2-4 items)
   - What beliefs is this decision resting on that haven't been tested?
   - What could be true that would change the recommendation?
   - What "obvious" facts might not actually be true?

3. **Potential Contradictions** (1-3 items)
   - Where does the evidence or reasoning conflict with itself?
   - What conclusions might be premature given the current evidence?
   - Are there any logical inconsistencies?

4. **Evidence Gaps** (2-4 items)
   - What claims or assumptions lack supporting evidence?
   - What data would strengthen or weaken the current position?
   - What questions remain unanswered?

5. **Recommendations** (2-4 items)
   - What specific next steps would improve decision confidence?
   - Prioritize actions that would have the highest impact.

Format your response as JSON:
{{
    "missing_perspectives": ["perspective 1", "perspective 2", ...],
    "unvalidated_assumptions": ["assumption 1", "assumption 2", ...],
    "contradictions": ["contradiction 1", ...],
    "evidence_gaps": ["gap 1", "gap 2", ...],
    "recommendations": ["recommendation 1", "recommendation 2", ...]
}}

Be specific and actionable. Each item should point to something concrete
that could be investigated or addressed. Focus on what matters most for this decision."""

    return prompt


def build_inquiry_suggestion_prompt(case) -> str:
    """
    Build a prompt to suggest new inquiries based on the case state.
    """
    context = build_case_context_prompt(case)

    # Get existing inquiry titles to avoid duplication
    existing_titles = [i.title for i in case.inquiries.all()]

    prompt = f"""{context}

---

## Existing Inquiries
{chr(10).join(f'- {t}' for t in existing_titles) if existing_titles else 'None yet'}

---

## Task: Suggest New Inquiries

Based on the decision context above, suggest 3-5 new inquiries that would help
make this decision with greater confidence.

Good inquiries should:
- Be specific and answerable (not too broad)
- Address a gap or uncertainty in the current analysis
- Be distinct from existing inquiries
- Have a clear path to finding evidence

For each suggestion, provide:
- title: A clear, question-form title (under 80 chars)
- description: Why this inquiry matters and what it would resolve
- reason: Why this inquiry is important for this specific decision
- priority: 1 (low) to 3 (high) based on decision impact

Format as JSON array:
[
    {{
        "title": "What is...",
        "description": "This inquiry would help us understand...",
        "reason": "This is important because...",
        "priority": 2
    }},
    ...
]"""

    return prompt


def build_evidence_suggestion_prompt(case, inquiry) -> str:
    """
    Build a prompt to suggest evidence sources for a specific inquiry.
    """
    context = build_case_context_prompt(case)

    prompt = f"""{context}

---

## Target Inquiry: {inquiry.title}

{inquiry.description if inquiry.description else 'No additional description.'}

**Current Evidence:**
"""
    # Add existing evidence
    evidence_items = inquiry.evidence_items.all()[:10]
    if evidence_items:
        for e in evidence_items:
            direction = "+" if e.direction == 'supports' else "-" if e.direction == 'contradicts' else "○"
            prompt += f"\n{direction} {e.evidence_text[:100]}..."
    else:
        prompt += "\nNo evidence gathered yet."

    prompt += """

---

## Task: Suggest Evidence Sources

Suggest 3-5 types of evidence that could help resolve this inquiry.

For each suggestion:
- suggestion: What to look for or investigate
- source_type: Type of source (document, data, expert, experiment, observation)
- why_helpful: How this evidence would help resolve the inquiry
- how_to_find: Practical steps to find or gather this evidence

Format as JSON array:
[
    {
        "suggestion": "Review quarterly sales reports...",
        "source_type": "document",
        "why_helpful": "Would show whether...",
        "how_to_find": "Ask finance team for..."
    },
    ...
]"""

    return prompt


def build_brief_suggestion_prompt(case, brief_content: str) -> str:
    """
    Build a prompt to suggest improvements to a case brief.
    """
    context = build_case_context_prompt(case)

    prompt = f"""{context}

---

## Current Brief Content

{brief_content[:3000]}  # Limit to avoid token overflow

---

## Task: Suggest Brief Improvements

Analyze this case brief and suggest specific improvements:

1. **Content Gaps**: What important information is missing?
2. **Clarity Issues**: What sections are unclear or could be better explained?
3. **Structure Suggestions**: How could the brief be better organized?
4. **Evidence Links**: What claims need evidence or citations?

For each suggestion, provide:
- section_id: Which section to modify (or "new" for new sections)
- suggestion_type: "add" | "clarify" | "restructure" | "cite"
- content: The specific change or addition
- reason: Why this improves the brief

Format as JSON array:
[
    {{
        "section_id": "summary",
        "suggestion_type": "add",
        "content": "Add a sentence about...",
        "reason": "This context is important because..."
    }},
    ...
]"""

    return prompt


def build_decision_frame_suggestion_prompt(
    title: str,
    position: str,
    conversation_context: Optional[str] = None
) -> str:
    """
    Build a prompt to suggest decision frame components.

    Used when creating a new case or refining an existing one.
    """
    prompt = f"""## Context
Title: {title}
Current Position: {position or 'Not yet defined'}

"""
    if conversation_context:
        prompt += f"""### Conversation Context
{conversation_context[:2000]}

"""

    prompt += """## Task: Suggest Decision Frame

Help define the decision frame by suggesting:

1. **Decision Question**: A clear, answerable question that captures the core decision
   - Should be specific enough to act on
   - Should capture the stakes and scope

2. **Constraints** (2-4): Limitations or boundaries on the decision
   - Budget, timeline, resources, legal, technical constraints

3. **Success Criteria** (2-4): How we'll know if the decision was good
   - Should be measurable where possible
   - Should align with stakeholder interests

4. **Key Stakeholders** (2-4): Who has interest in this decision
   - What they care about
   - Their level of influence

Format as JSON:
{
    "decision_question": "Should we...",
    "constraints": [
        {"type": "budget", "description": "..."},
        ...
    ],
    "success_criteria": [
        {"criterion": "...", "measurable": "..."},
        ...
    ],
    "stakeholders": [
        {"name": "...", "interest": "...", "influence": "high|medium|low"},
        ...
    ]
}"""

    return prompt


# ── Document-level prompt builders ──────────────────────────────────────


def build_content_integration_prompt(
    document_content: str,
    content_to_add: str,
    hint: str = "general",
) -> tuple:
    """
    Build prompt to intelligently integrate new content into a document.

    Returns:
        tuple: (system_prompt, user_prompt)
    """
    system_prompt = (
        "You are an AI editor that helps integrate new information "
        "into structured documents."
    )

    user_prompt = f"""
Current document:
{document_content}

New content to integrate:
"{content_to_add}"

Content type: {hint}

Instructions:
1. Analyze the document structure
2. Find the most appropriate section to add this content
3. Rewrite the content if needed to match document style and flow
4. Add a citation marker: [^chat] at the end
5. Return the FULL updated document with the new content integrated

Return JSON:
{{
    "updated_content": "full updated markdown",
    "insertion_section": "section name where content was added",
    "rewritten_content": "how the content was adapted"
}}
"""
    return system_prompt, user_prompt


def build_assumption_detection_prompt(
    document_content: str,
    inquiries: list,
    assumption_signals: list,
) -> tuple:
    """
    Build prompt to detect assumptions in a document.

    Args:
        document_content: The brief markdown
        inquiries: List of Inquiry model instances (need .title, .status)
        assumption_signals: List of Signal instances (need .text)

    Returns:
        tuple: (system_prompt, user_prompt)
    """
    system_prompt = (
        "You are an AI that identifies and analyzes assumptions "
        "in decision documents."
    )

    inq_lines = [f"- {i.title} (status: {i.status})" for i in inquiries]
    sig_lines = [f"- {s.text}" for s in assumption_signals[:5]]

    user_prompt = f"""
Analyze this case brief and identify ALL assumptions (stated or implied):

Brief:
{document_content}

Existing inquiries being investigated:
{inq_lines}

Previously extracted assumption signals:
{sig_lines}

For each assumption, provide:
1. text: The exact assumption text (quote from document)
2. status: "untested" | "investigating" | "validated"
   - investigating if matching inquiry exists
   - validated if inquiry resolved
   - untested otherwise
3. risk_level: "low" | "medium" | "high" based on impact if assumption is wrong
4. inquiry_id: UUID if matching inquiry exists (match by similarity)
5. validation_approach: Brief suggestion for how to validate

Return JSON array:
[{{
    "text": "assumption text",
    "status": "untested",
    "risk_level": "high",
    "inquiry_id": null,
    "validation_approach": "Research market data"
}}]

Return ONLY the JSON array, no other text.
"""
    return system_prompt, user_prompt


def build_brief_update_prompt(
    brief_content: str,
    inquiry_title: str,
    inquiry_conclusion: str,
    inquiry_id: str,
    conclusion_confidence: Optional[float] = None,
    origin_text: Optional[str] = None,
) -> tuple:
    """
    Build prompt to update a case brief based on an inquiry resolution.

    Returns:
        tuple: (system_prompt, user_prompt)
    """
    system_prompt = (
        "You are an AI editor that updates decision briefs "
        "based on research findings."
    )

    user_prompt = f"""
Original case brief:
{brief_content}

Inquiry that was just resolved:
Question: {inquiry_title}
Conclusion: {inquiry_conclusion}
Confidence: {conclusion_confidence or 'N/A'}

{f'Origin text in brief: "{origin_text}"' if origin_text else ''}

Task:
1. Update the brief to incorporate this inquiry conclusion
2. If origin_text exists, update or replace that assumption
3. If no origin_text, find the most relevant section to add this finding
4. Add citation: [[inquiry:{inquiry_id}]]
5. Maintain markdown formatting and document structure
6. Be concise - don't rewrite sections that don't need updating

Return JSON:
{{
    "updated_content": "full updated markdown brief",
    "changes": [
        {{"type": "replace", "old": "text that changed", "new": "updated text"}},
        {{"type": "add", "section": "section name", "content": "what was added"}}
    ],
    "summary": "brief summary of changes made"
}}
"""
    return system_prompt, user_prompt
