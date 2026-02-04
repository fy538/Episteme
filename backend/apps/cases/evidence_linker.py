"""
Evidence Linker Service

Connects claims in briefs to supporting evidence from signals and documents.
Identifies:
- Claims that can be linked to existing evidence
- Unsubstantiated claims that need evidence
- Confidence levels for linked claims
"""
import json
import asyncio
import uuid
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from apps.common.llm_providers import get_llm_provider


@dataclass
class LinkedClaim:
    """A claim with its evidence links."""
    id: str
    text: str
    location: str  # Quote or section reference
    start_index: int
    end_index: int
    claim_type: str  # fact, assumption, opinion, prediction
    linked_signals: List[Dict[str, Any]]  # [{signal_id, relevance, excerpt}]
    confidence: float  # 0-1, based on evidence strength
    is_substantiated: bool
    suggestion: Optional[str]  # How to strengthen if weak


def extract_and_link_claims(
    document_content: str,
    signals: List[Dict[str, Any]],
    inquiries: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Extract claims from a document and link them to available evidence.

    Returns:
    {
        claims: [{
            id, text, location, claim_type,
            linked_signals, confidence, is_substantiated, suggestion
        }],
        summary: {
            total_claims: int,
            substantiated: int,
            unsubstantiated: int,
            average_confidence: float
        },
        evidence_coverage: float  # 0-1, how well-evidenced the document is
    }
    """
    provider = get_llm_provider('fast')

    # Step 1: Extract claims from document
    claims = _extract_claims(document_content, provider)

    # Step 2: Match claims to signals
    linked_claims = _link_claims_to_signals(claims, signals, provider)

    # Step 3: Calculate summary stats
    substantiated = [c for c in linked_claims if c['is_substantiated']]
    total = len(linked_claims)

    summary = {
        'total_claims': total,
        'substantiated': len(substantiated),
        'unsubstantiated': total - len(substantiated),
        'average_confidence': (
            sum(c['confidence'] for c in linked_claims) / total
            if total > 0 else 0
        )
    }

    evidence_coverage = len(substantiated) / total if total > 0 else 0

    return {
        'claims': linked_claims,
        'summary': summary,
        'evidence_coverage': evidence_coverage,
    }


def _extract_claims(content: str, provider) -> List[Dict[str, Any]]:
    """Extract claims from document content."""

    prompt = f"""Extract all claims from this document. A claim is any statement that:
- Asserts a fact or statistic
- Makes a prediction or projection
- States an assumption
- Draws a conclusion

## Document
{content}

## Instructions
For each claim, identify:
- text: The exact claim text (quote from document)
- location: Where in the document (section name or nearby heading)
- claim_type: "fact" | "assumption" | "opinion" | "prediction" | "conclusion"
- importance: "high" | "medium" | "low" (how critical is this to the argument)

Return JSON array:
[
  {{
    "id": "claim_1",
    "text": "Revenue is expected to grow 40% year-over-year",
    "location": "Financial Analysis section",
    "claim_type": "prediction",
    "importance": "high"
  }}
]

Focus on substantive claims, not trivial statements.
Return ONLY the JSON array."""

    async def extract():
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You extract claims from documents for evidence verification."
        ):
            full_response += chunk.content

        try:
            response_text = full_response.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            claims = json.loads(response_text)

            # Find positions in content
            for claim in claims:
                text = claim.get('text', '')
                idx = content.find(text[:50])  # Partial match
                claim['start_index'] = idx if idx >= 0 else 0
                claim['end_index'] = idx + len(text) if idx >= 0 else len(text)

            return claims
        except Exception as e:
            print(f"Failed to extract claims: {e}")
            return []

    return asyncio.run(extract())


def _link_claims_to_signals(
    claims: List[Dict[str, Any]],
    signals: List[Dict[str, Any]],
    provider
) -> List[Dict[str, Any]]:
    """Link extracted claims to available signals."""

    if not claims:
        return []

    if not signals:
        # No signals to link, all claims unsubstantiated
        return [
            {
                **claim,
                'linked_signals': [],
                'confidence': 0.2,
                'is_substantiated': False,
                'suggestion': 'No evidence available. Consider gathering supporting data.'
            }
            for claim in claims
        ]

    # Format signals for matching
    signals_text = "\n".join([
        f"[{i}] Type: {s.get('signal_type', 'unknown')}\n"
        f"    Content: {s.get('content', '')[:200]}\n"
        f"    ID: {s.get('id', '')}"
        for i, s in enumerate(signals[:20])
    ])

    claims_text = "\n".join([
        f"[{i}] {c.get('text', '')}"
        for i, c in enumerate(claims)
    ])

    prompt = f"""Match these claims to the available evidence signals.

## Claims to Verify
{claims_text}

## Available Evidence (Signals)
{signals_text}

## Instructions
For each claim, determine:
1. Which signals (if any) support it
2. How strong the support is (relevance: 0-1)
3. Overall confidence in the claim (0-1)
4. Whether it's substantiated (confidence > 0.6)
5. Suggestion for strengthening weak claims

Return JSON array matching claim indices:
[
  {{
    "claim_index": 0,
    "linked_signals": [
      {{"signal_index": 2, "relevance": 0.85, "excerpt": "relevant quote from signal"}}
    ],
    "confidence": 0.8,
    "is_substantiated": true,
    "suggestion": null
  }},
  {{
    "claim_index": 1,
    "linked_signals": [],
    "confidence": 0.3,
    "is_substantiated": false,
    "suggestion": "Look for market research data to support this growth projection"
  }}
]

Return ONLY the JSON array."""

    async def link():
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You match claims to supporting evidence and assess confidence."
        ):
            full_response += chunk.content

        try:
            response_text = full_response.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            matches = json.loads(response_text)

            # Merge matches back into claims
            result = []
            for match in matches:
                claim_idx = match.get('claim_index', 0)
                if claim_idx < len(claims):
                    claim = claims[claim_idx].copy()

                    # Resolve signal references
                    linked = []
                    for link in match.get('linked_signals', []):
                        sig_idx = link.get('signal_index', 0)
                        if sig_idx < len(signals):
                            linked.append({
                                'signal_id': signals[sig_idx].get('id'),
                                'signal_type': signals[sig_idx].get('signal_type'),
                                'relevance': link.get('relevance', 0.5),
                                'excerpt': link.get('excerpt', '')
                            })

                    claim['linked_signals'] = linked
                    claim['confidence'] = match.get('confidence', 0.5)
                    claim['is_substantiated'] = match.get('is_substantiated', False)
                    claim['suggestion'] = match.get('suggestion')
                    result.append(claim)

            # Add any claims that weren't in the matches
            matched_indices = {m.get('claim_index') for m in matches}
            for i, claim in enumerate(claims):
                if i not in matched_indices:
                    result.append({
                        **claim,
                        'linked_signals': [],
                        'confidence': 0.3,
                        'is_substantiated': False,
                        'suggestion': 'No matching evidence found.'
                    })

            return result
        except Exception as e:
            print(f"Failed to link claims: {e}")
            # Return claims without links
            return [
                {
                    **claim,
                    'linked_signals': [],
                    'confidence': 0.3,
                    'is_substantiated': False,
                    'suggestion': 'Evidence matching failed.'
                }
                for claim in claims
            ]

    return asyncio.run(link())


def get_evidence_suggestions(
    unsubstantiated_claims: List[Dict[str, Any]],
    case_context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Generate suggestions for gathering evidence for unsubstantiated claims.
    """
    if not unsubstantiated_claims:
        return []

    provider = get_llm_provider('fast')

    claims_text = "\n".join([
        f"- {c.get('text', '')}"
        for c in unsubstantiated_claims[:10]
    ])

    prompt = f"""Suggest how to find evidence for these unsubstantiated claims.

## Decision Context
{case_context.get('decision_question', 'Not specified')}

## Claims Needing Evidence
{claims_text}

## Instructions
For each claim, suggest:
1. What type of evidence would support it
2. Where to find this evidence
3. How critical is getting this evidence

Return JSON array:
[
  {{
    "claim_text": "...",
    "evidence_type": "market_data" | "expert_opinion" | "case_study" | "financial_data" | "research",
    "sources": ["Where to look for evidence"],
    "priority": "high" | "medium" | "low",
    "search_query": "Suggested search terms"
  }}
]

Return ONLY the JSON array."""

    async def suggest():
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You suggest evidence sources for decision-making."
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

    return asyncio.run(suggest())


def create_inline_citations(
    document_content: str,
    linked_claims: List[Dict[str, Any]]
) -> str:
    """
    Add inline citation markers to document content.

    Transforms claims like:
    "Revenue grew 40%" -> "Revenue grew 40% [^1]"

    And adds footnotes at the end.
    """
    if not linked_claims:
        return document_content

    # Sort by position (reverse to avoid index shifting)
    substantiated = [
        c for c in linked_claims
        if c.get('is_substantiated') and c.get('linked_signals')
    ]

    if not substantiated:
        return document_content

    # Sort by start_index descending
    substantiated.sort(key=lambda c: c.get('start_index', 0), reverse=True)

    result = document_content
    footnotes = []

    for i, claim in enumerate(substantiated, 1):
        text = claim.get('text', '')
        if text in result:
            # Add citation marker
            result = result.replace(text, f"{text} [^{i}]", 1)

            # Build footnote
            sources = [
                f"{s.get('signal_type', 'signal')}: {s.get('excerpt', '')[:50]}..."
                for s in claim.get('linked_signals', [])[:2]
            ]
            footnotes.append(f"[^{i}]: {'; '.join(sources)}")

    # Add footnotes section
    if footnotes:
        result += "\n\n---\n### Sources\n" + "\n".join(footnotes)

    return result
