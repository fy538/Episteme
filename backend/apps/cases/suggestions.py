"""
Brief Suggestion Service

Generates actionable suggestions for brief content based on:
- Gap analysis
- Assumption detection
- Evidence linking
- Confidence improvements
"""
import json
import logging

logger = logging.getLogger(__name__)
import asyncio
import uuid
from typing import List, Dict, Any, Optional

from apps.common.llm_providers import get_llm_provider


def generate_brief_suggestions(
    brief_content: str,
    case_context: Dict[str, Any],
    max_suggestions: int = 5
) -> List[Dict[str, Any]]:
    """
    Generate actionable suggestions for improving a brief.

    Returns list of suggestions in format:
    {
        id: str,
        section_id: str,
        suggestion_type: 'add' | 'replace' | 'delete' | 'cite' | 'clarify',
        current_content: str | None,
        suggested_content: str,
        reason: str,
        linked_signal_id: str | None,
        confidence: float,
        status: 'pending'
    }
    """
    provider = get_llm_provider('fast')

    # Build the prompt
    prompt = _build_suggestion_prompt(brief_content, case_context, max_suggestions)

    async def generate():
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="""You are an AI editor that reviews decision briefs and suggests specific improvements.
You identify:
1. Unsubstantiated claims that need evidence
2. Missing perspectives or considerations
3. Unclear or ambiguous statements
4. Contradictions between sections
5. Opportunities to strengthen arguments

Your suggestions are actionable and specific. Each suggestion includes:
- The exact text to modify (for replacements)
- The new text to add
- A clear reason why this improves the brief
- A confidence score based on how certain you are this is helpful"""
        ):
            full_response += chunk.content

        # Parse JSON response
        try:
            response_text = full_response.strip()
            # Handle markdown code blocks
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            suggestions = json.loads(response_text)

            # Add IDs and ensure required fields
            for s in suggestions:
                s['id'] = str(uuid.uuid4())
                s['status'] = 'pending'
                if 'confidence' not in s:
                    s['confidence'] = 0.7
                if 'section_id' not in s:
                    s['section_id'] = 'general'

            return suggestions[:max_suggestions]
        except Exception as e:
            logger.warning(f"Failed to parse suggestions: {e}")
            return []

    return asyncio.run(generate())


def _build_suggestion_prompt(
    brief_content: str,
    case_context: Dict[str, Any],
    max_suggestions: int
) -> str:
    """Build the prompt for suggestion generation."""

    decision_question = case_context.get('decision_question', '')
    inquiries = case_context.get('inquiries', [])
    signals = case_context.get('signals', [])
    gaps = case_context.get('gaps', {})

    inquiries_text = "\n".join([
        f"- {i.get('title', 'Untitled')} (status: {i.get('status', 'unknown')})"
        for i in inquiries
    ]) if inquiries else "No inquiries yet"

    signals_text = "\n".join([
        f"- [{s.get('signal_type', 'unknown')}] {s.get('content', '')[:100]}"
        for s in signals[:10]
    ]) if signals else "No signals yet"

    gaps_text = ""
    if gaps:
        if gaps.get('missing_perspectives'):
            gaps_text += f"\nMissing perspectives: {', '.join(gaps['missing_perspectives'][:3])}"
        if gaps.get('unvalidated_assumptions'):
            gaps_text += f"\nUnvalidated assumptions: {', '.join(gaps['unvalidated_assumptions'][:3])}"
        if gaps.get('contradictions'):
            gaps_text += f"\nContradictions: {', '.join(gaps['contradictions'][:3])}"

    # Build grounding context from section annotations
    grounding = case_context.get('grounding', [])
    grounding_text = ""
    if grounding:
        lines = []
        for sec in grounding:
            section_line = f"- **{sec['heading']}** ({sec['section_id']}): grounding={sec['grounding_status']}"
            if sec.get('annotations'):
                ann_types = [a['type'] for a in sec['annotations']]
                section_line += f" | annotations: {', '.join(ann_types)}"
            lines.append(section_line)
        grounding_text = "\n".join(lines)

        # Identify high-priority issues for targeted suggestions
        tensions = [s for s in grounding if any(a['type'] == 'tension' for a in s.get('annotations', []))]
        evidence_deserts = [s for s in grounding if any(a['type'] == 'evidence_desert' for a in s.get('annotations', []))]
        blind_spots = [s for s in grounding if any(a['type'] == 'blind_spot' for a in s.get('annotations', []))]
        ungrounded = [s for s in grounding if s.get('grounding_status') in ('empty', 'weak')]

        if tensions:
            grounding_text += f"\n\n⚠️ TENSIONS DETECTED in: {', '.join(s['heading'] for s in tensions)}"
            grounding_text += "\nPrioritize suggestions that resolve conflicting evidence."
        if evidence_deserts:
            grounding_text += f"\n\n🏜️ EVIDENCE DESERTS in: {', '.join(s['heading'] for s in evidence_deserts)}"
            grounding_text += "\nPrioritize suggestions that add evidence or citations to these sections."
        if blind_spots:
            grounding_text += f"\n\n👁️ BLIND SPOTS in: {', '.join(s['heading'] for s in blind_spots)}"
            grounding_text += "\nPrioritize suggestions that address missing perspectives."
        if ungrounded:
            grounding_text += f"\n\n📉 WEAKLY GROUNDED sections: {', '.join(s['heading'] for s in ungrounded)}"
            grounding_text += "\nPrioritize suggestions that strengthen these sections."

    return f"""Analyze this decision brief and generate up to {max_suggestions} specific suggestions for improvement.

## Decision Context
Decision question: {decision_question or "Not specified"}

## Current Brief Content
{brief_content}

## Active Inquiries
{inquiries_text}

## Extracted Signals
{signals_text}

## Identified Gaps
{gaps_text or "No gaps analysis available"}

## Section Grounding & Annotations
{grounding_text or "No grounding data available (sections may not be linked to inquiries yet)"}

## Instructions
Generate suggestions that will make this brief more:
1. Evidence-based (add citations, link to signals)
2. Complete (address gaps, missing perspectives)
3. Clear (clarify ambiguous statements)
4. Rigorous (identify and address assumptions)

**IMPORTANT:** If there are tensions, evidence deserts, blind spots, or weakly grounded sections identified above, your suggestions MUST prioritize addressing those issues first. These are the most impactful improvements.

For each suggestion, provide:
- section_id: Which section of the brief this applies to
- suggestion_type: "add" | "replace" | "delete" | "cite" | "clarify"
- current_content: The exact text to modify (for replace/delete), null for add
- suggested_content: The new text to add or replace with
- reason: Why this improves the brief (1-2 sentences)
- linked_signal_id: UUID of related signal if applicable, null otherwise
- confidence: 0.0-1.0 how confident you are this is helpful

Return as JSON array:
[
  {{
    "section_id": "analysis",
    "suggestion_type": "add",
    "current_content": null,
    "suggested_content": "Market research shows that...",
    "reason": "This section lacks quantitative support for the claim",
    "linked_signal_id": null,
    "confidence": 0.85
  }}
]

Return ONLY the JSON array, no other text."""


def generate_inline_suggestions(
    brief_content: str,
    cursor_position: int,
    context_before: str,
    context_after: str
) -> List[Dict[str, str]]:
    """
    Generate inline suggestions for a specific cursor position.
    Used for ghost text / tab completion.

    Returns list of possible completions.
    """
    provider = get_llm_provider('fast')

    prompt = f"""You are helping write a decision brief. The user's cursor is at [CURSOR].

Context:
{context_before}[CURSOR]{context_after}

Suggest 1-3 natural completions for the text at the cursor position.
Consider:
- What the user is likely trying to write
- The document's existing style and tone
- Completions that add value (evidence, structure, clarity)

Return JSON array of completions:
[
  {{"text": "completion text", "confidence": 0.9}},
  {{"text": "alternative completion", "confidence": 0.7}}
]

Return ONLY the JSON array."""

    async def generate():
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You suggest inline text completions for documents."
        ):
            full_response += chunk.content

        try:
            response_text = full_response.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            return json.loads(response_text)
        except Exception:
            return []

    return asyncio.run(generate())


def get_inline_completion(
    context_before: str,
    context_after: str,
    max_length: int = 50
) -> Optional[str]:
    """
    Generate an inline completion for ghost text.

    Returns a short completion to insert at cursor position, or None.
    """
    provider = get_llm_provider('fast')

    prompt = f"""Complete the text at [CURSOR]. Provide a natural continuation.

Text before cursor:
{context_before[-300:]}[CURSOR]

Text after cursor:
{context_after[:100]}

Instructions:
- Provide ONLY the completion text (no [CURSOR] marker)
- Keep it short (under {max_length} characters)
- Match the style and tone of the surrounding text
- If completion is not natural, return empty string

Return ONLY the completion text, nothing else."""

    async def generate():
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You complete text naturally. Return only the completion."
        ):
            full_response += chunk.content
            # Early exit if we have enough
            if len(full_response) > max_length * 2:
                break

        completion = full_response.strip()
        # Validate completion
        if len(completion) > max_length or len(completion) < 2:
            return None
        if completion.startswith('[') or completion.startswith('{'):
            return None
        return completion

    return asyncio.run(generate())


def apply_suggestion(
    document_content: str,
    suggestion: Dict[str, Any]
) -> str:
    """
    Apply a suggestion to document content.

    Returns the updated content.
    """
    suggestion_type = suggestion.get('suggestion_type')
    current_content = suggestion.get('current_content')
    suggested_content = suggestion.get('suggested_content', '')

    if suggestion_type == 'replace' and current_content:
        # Replace the current content with suggested content
        return document_content.replace(current_content, suggested_content, 1)

    elif suggestion_type == 'delete' and current_content:
        # Remove the content
        return document_content.replace(current_content, '', 1)

    elif suggestion_type == 'add':
        # For add, we need context about where to add
        # If section_id is provided, try to find that section
        section_id = suggestion.get('section_id', '')

        # Simple heuristic: look for section header
        if section_id:
            section_markers = [
                f"## {section_id.title()}",
                f"# {section_id.title()}",
                f"### {section_id.title()}"
            ]
            for marker in section_markers:
                if marker in document_content:
                    # Find end of section header line and add after
                    idx = document_content.find(marker)
                    newline_idx = document_content.find('\n', idx)
                    if newline_idx != -1:
                        return (
                            document_content[:newline_idx + 1] +
                            suggested_content + '\n' +
                            document_content[newline_idx + 1:]
                        )

        # Fallback: append to end
        return document_content + '\n\n' + suggested_content

    elif suggestion_type in ['cite', 'clarify']:
        # These work like replace if current_content exists
        if current_content:
            return document_content.replace(current_content, suggested_content, 1)
        # Otherwise append
        return document_content + '\n\n' + suggested_content

    # No change if type not recognized
    return document_content
