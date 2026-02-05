"""
Mode-aware prompts for companion reflection

Different prompts based on current chat mode:
- casual: General Socratic questioning
- case: Case-focused ("Which inquiry should you tackle first?")
- inquiry_focus: Specific ("What would increase your confidence here?")
"""
from typing import List, Dict, Optional


def get_casual_prompt(
    signals: List[Dict],
    messages: List[Dict],
    patterns: Optional[Dict] = None
) -> str:
    """
    Generate casual mode reflection prompt.

    General Socratic questioning for exploratory conversations.

    Args:
        signals: Current signals extracted
        messages: Recent conversation messages
        patterns: Optional graph patterns

    Returns:
        System prompt for casual reflection
    """
    # Extract context
    claims = [s for s in signals if s.get('type') == 'Claim']
    assumptions = [s for s in signals if s.get('type') == 'Assumption']
    questions = [s for s in signals if s.get('type') == 'Question']

    # Format signals
    signals_text = ""
    if claims:
        signals_text += "Claims made:\n"
        for c in claims[:3]:
            signals_text += f"- \"{c.get('text', '')[:60]}\"\n"

    if assumptions:
        signals_text += "\nAssumptions:\n"
        for a in assumptions[:3]:
            signals_text += f"- \"{a.get('text', '')[:60]}\"\n"

    if questions:
        signals_text += "\nOpen questions:\n"
        for q in questions[:3]:
            signals_text += f"- \"{q.get('text', '')[:60]}\"\n"

    # Format patterns
    patterns_text = ""
    if patterns:
        ungrounded = len(patterns.get('ungrounded_assumptions', []))
        contradictions = len(patterns.get('contradictions', []))
        if ungrounded > 0 or contradictions > 0:
            patterns_text = f"\nPatterns: {ungrounded} ungrounded assumption(s), {contradictions} contradiction(s)\n"

    return f"""You are a thoughtful companion in a casual conversation.

{signals_text}
{patterns_text}

Your role is to help the user think more deeply through Socratic questioning.

Guidelines:
- Ask probing questions that reveal assumptions
- Point out what hasn't been considered
- Challenge claims gently
- Reframe questions when helpful
- Be curious and conversational
- Write 2-3 short paragraphs maximum

Remember: You're helping them THINK, not giving answers.

Write your reflection:"""


def get_case_prompt(
    case_title: str,
    case_position: Optional[str],
    open_inquiries: List[Dict],
    unvalidated_assumptions: List[Dict],
    evidence_gaps: int = 0
) -> str:
    """
    Generate case mode reflection prompt.

    Case-focused questioning about which inquiry to tackle, risky assumptions.

    Args:
        case_title: Title of the case
        case_position: User's current position
        open_inquiries: List of open inquiries
        unvalidated_assumptions: List of unvalidated assumptions
        evidence_gaps: Number of evidence gaps

    Returns:
        System prompt for case reflection
    """
    # Format inquiries
    inquiries_text = ""
    if open_inquiries:
        inquiries_text = "Open inquiries:\n"
        for inq in open_inquiries[:5]:
            title = inq.get('title', 'Untitled')
            evidence_count = inq.get('evidence_count', 0)
            inquiries_text += f"- \"{title}\" ({evidence_count} evidence)\n"
    else:
        inquiries_text = "No open inquiries yet.\n"

    # Format assumptions
    assumptions_text = ""
    if unvalidated_assumptions:
        assumptions_text = "\nUnvalidated assumptions:\n"
        for a in unvalidated_assumptions[:5]:
            text = a.get('text', '')[:60]
            assumptions_text += f"- \"{text}\"\n"

    # Position text
    position_text = ""
    if case_position:
        position_text = f"Current position: {case_position}\n"

    return f"""You are a thoughtful companion helping with a decision case.

Case: {case_title}
{position_text}
{inquiries_text}
{assumptions_text}

Evidence gaps: {evidence_gaps}

Your role is to help the user make progress on this decision.

Case-focused questions:
- Which inquiry should they tackle first and why?
- Which assumption carries the most risk if wrong?
- What evidence would most change their confidence?
- Is their current position well-supported?

Guidelines:
- Be specific to this case, not generic
- Help prioritize next steps
- Point out the riskiest unknown
- Write 2-3 short paragraphs maximum

Remember: Help them make progress, not just think in circles.

Write your reflection:"""


def get_inquiry_focus_prompt(
    inquiry_title: str,
    inquiry_evidence: List[Dict],
    confidence_level: Optional[float] = None,
    case_context: Optional[str] = None
) -> str:
    """
    Generate inquiry focus mode reflection prompt.

    Specific questioning about what would increase confidence on this inquiry.

    Args:
        inquiry_title: Title of the focused inquiry
        inquiry_evidence: Evidence gathered for this inquiry
        confidence_level: Current confidence (0-1)
        case_context: Broader case context

    Returns:
        System prompt for inquiry focus reflection
    """
    # Format evidence
    evidence_text = ""
    if inquiry_evidence:
        supporting = [e for e in inquiry_evidence if e.get('direction') == 'supporting']
        contradicting = [e for e in inquiry_evidence if e.get('direction') == 'contradicting']

        if supporting:
            evidence_text += f"Supporting evidence ({len(supporting)}):\n"
            for e in supporting[:3]:
                evidence_text += f"- \"{e.get('content', '')[:60]}\"\n"

        if contradicting:
            evidence_text += f"\nContradicting evidence ({len(contradicting)}):\n"
            for e in contradicting[:3]:
                evidence_text += f"- \"{e.get('content', '')[:60]}\"\n"
    else:
        evidence_text = "No evidence gathered yet.\n"

    # Confidence text
    confidence_text = ""
    if confidence_level is not None:
        pct = int(confidence_level * 100)
        confidence_text = f"Current confidence: {pct}%\n"

    return f"""You are a thoughtful companion helping investigate a specific inquiry.

Inquiry: {inquiry_title}
{confidence_text}
{evidence_text}

Your role is to help gather the RIGHT evidence for this inquiry.

Inquiry-focused questions:
- What would increase confidence the MOST here?
- What evidence would definitively answer this?
- Is there a shortcut to resolving this inquiry?
- What are we assuming without checking?

Guidelines:
- Stay focused on THIS inquiry, not tangents
- Suggest specific evidence to gather
- Point out if confidence should be higher/lower based on evidence
- Write 2-3 short paragraphs maximum

Remember: Help them resolve this inquiry efficiently.

Write your reflection:"""


def get_mode_prompt(
    mode: str,
    mode_context: Dict,
    signals: List[Dict],
    messages: List[Dict],
    patterns: Optional[Dict] = None
) -> str:
    """
    Get the appropriate prompt based on mode.

    Router function that calls the appropriate mode-specific prompt generator.

    Args:
        mode: Current chat mode ('casual', 'case', 'inquiry_focus')
        mode_context: Mode-specific context data
        signals: Current signals
        messages: Recent messages
        patterns: Graph patterns

    Returns:
        System prompt for reflection
    """
    if mode == 'casual':
        return get_casual_prompt(signals, messages, patterns)

    elif mode == 'case':
        return get_case_prompt(
            case_title=mode_context.get('case_name', 'Untitled Case'),
            case_position=mode_context.get('case_position'),
            open_inquiries=mode_context.get('open_inquiries', []),
            unvalidated_assumptions=mode_context.get('unvalidated_assumptions', []),
            evidence_gaps=mode_context.get('evidence_gaps', 0)
        )

    elif mode == 'inquiry_focus':
        return get_inquiry_focus_prompt(
            inquiry_title=mode_context.get('inquiry_title', 'Untitled Inquiry'),
            inquiry_evidence=mode_context.get('inquiry_evidence', []),
            confidence_level=mode_context.get('confidence_level'),
            case_context=mode_context.get('case_name')
        )

    else:
        # Default to casual
        return get_casual_prompt(signals, messages, patterns)
