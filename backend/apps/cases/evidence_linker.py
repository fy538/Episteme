"""
Evidence Linker Service

Connects claims in briefs to supporting evidence from signals and documents.
Identifies:
- Claims that can be linked to existing evidence
- Unsubstantiated claims that need evidence
- Confidence levels for linked claims

Uses embeddings for fast pre-filtering, then LLM for precise matching.
"""
import json
import logging

logger = logging.getLogger(__name__)
import uuid
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from asgiref.sync import async_to_sync

from apps.cases.constants import (
    EVIDENCE_MATCH_PREFIX_LEN,
    EVIDENCE_MATCH_LIMIT,
    EVIDENCE_CLAIM_TEXT_LIMIT,
    EVIDENCE_EMBEDDING_SIMILARITY_THRESHOLD,
)

from apps.common.llm_providers import get_llm_provider, stream_json, stream_and_collect, strip_markdown_fences
from apps.common.embeddings import generate_embedding
from apps.signals.similarity import cosine_similarity


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


def persist_evidence_links(
    linked_claims: List[Dict[str, Any]],
    case_id: str,
) -> Dict[str, int]:
    """
    Persist evidence-to-signal relationships from linker results.

    For each substantiated claim with linked signals, find the corresponding
    Evidence record and populate the supports_signals M2M field.

    Strategy:
    1. Fast text prefix match (icontains)
    2. Embedding-based semantic match as fallback

    Returns: {links_created: int, signals_linked: int}
    """
    from apps.projects.models import Evidence as ProjectEvidence
    from apps.signals.models import Signal

    links_created = 0
    signals_linked = set()

    # Pre-fetch all case evidence once to avoid repeated queries
    case_evidence = list(
        ProjectEvidence.objects.filter(
            document__case_id=case_id,
        ).only('id', 'text', 'embedding')[:200]  # Cap for large cases
    )

    if not case_evidence:
        return {'links_created': 0, 'signals_linked': 0}

    for claim in linked_claims:
        if not claim.get('is_substantiated') or not claim.get('linked_signals'):
            continue

        signal_ids = [
            link['signal_id'] for link in claim['linked_signals']
            if link.get('signal_id')
        ]
        if not signal_ids:
            continue

        signals = Signal.objects.filter(id__in=signal_ids)
        if not signals.exists():
            continue

        claim_text = claim.get('text', '')
        if not claim_text:
            continue

        # Strategy 1: Fast text prefix match
        prefix = claim_text[:EVIDENCE_MATCH_PREFIX_LEN].lower()
        matching = [
            e for e in case_evidence
            if prefix in (e.text or '').lower()
        ][:EVIDENCE_MATCH_LIMIT]

        # Strategy 2: Embedding fallback if no text match
        if not matching:
            try:
                claim_embedding = generate_embedding(claim_text[:500])
                if claim_embedding:
                    scored = []
                    for e in case_evidence:
                        e_embedding = getattr(e, 'embedding', None)
                        if e_embedding:
                            score = cosine_similarity(claim_embedding, e_embedding)
                            if score >= EVIDENCE_EMBEDDING_SIMILARITY_THRESHOLD:
                                scored.append((score, e))
                    scored.sort(key=lambda x: x[0], reverse=True)
                    matching = [e for _, e in scored[:EVIDENCE_MATCH_LIMIT]]
            except Exception as e:
                logger.debug("Embedding fallback failed for claim: %s", e)

        for evidence in matching:
            for signal in signals:
                evidence.supports_signals.add(signal)
                links_created += 1
                signals_linked.add(str(signal.id))

    return {
        'links_created': links_created,
        'signals_linked': len(signals_linked),
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

    claims = async_to_sync(stream_json)(
        provider,
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You extract claims from documents for evidence verification.",
        fallback=[],
        description="claim extraction",
    )

    # Find positions in content
    if isinstance(claims, list):
        for claim in claims:
            text = claim.get('text', '')
            idx = content.find(text[:50])  # Partial match
            claim['start_index'] = idx if idx >= 0 else 0
            claim['end_index'] = idx + len(text) if idx >= 0 else len(text)

    return claims if isinstance(claims, list) else []


def _prefilter_signals_by_embedding(
    claim_text: str,
    signals: List[Dict[str, Any]],
    top_k: int = 5,
    threshold: float = 0.4
) -> List[Dict[str, Any]]:
    """
    Pre-filter signals using embedding similarity.

    Returns top_k signals most similar to the claim, sorted by similarity.
    This reduces the number of signals sent to the LLM.
    """
    claim_embedding = generate_embedding(claim_text)
    if not claim_embedding:
        # Fall back to returning first signals if embedding fails
        return signals[:top_k]

    scored_signals = []
    for signal in signals:
        signal_embedding = signal.get('embedding')
        if signal_embedding:
            similarity = cosine_similarity(claim_embedding, signal_embedding)
            if similarity >= threshold:
                scored_signals.append((signal, similarity))

    # Sort by similarity descending
    scored_signals.sort(key=lambda x: x[1], reverse=True)

    # Return top_k signals
    return [s for s, _ in scored_signals[:top_k]]


def _link_claims_to_signals(
    claims: List[Dict[str, Any]],
    signals: List[Dict[str, Any]],
    provider,
    use_embeddings: bool = True
) -> List[Dict[str, Any]]:
    """Link extracted claims to available signals.

    Args:
        claims: List of claims to link
        signals: List of signals to match against
        provider: LLM provider
        use_embeddings: If True, pre-filter signals using embeddings (faster, cheaper)
    """

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

    # If using embeddings, pre-filter signals for each claim
    if use_embeddings:
        # Pre-compute filtered signals for each claim
        claim_signals_map = {}
        for i, claim in enumerate(claims):
            claim_text = claim.get('text', '')
            filtered = _prefilter_signals_by_embedding(claim_text, signals, top_k=5)
            claim_signals_map[i] = filtered

        # Use union of all filtered signals for LLM prompt
        all_filtered_indices = set()
        for i in claim_signals_map:
            for sig in claim_signals_map[i]:
                idx = next((j for j, s in enumerate(signals) if s.get('id') == sig.get('id')), None)
                if idx is not None:
                    all_filtered_indices.add(idx)

        # Create filtered signals list maintaining original indices
        filtered_signals = [(i, signals[i]) for i in sorted(all_filtered_indices)]

        # Format only the filtered signals
        signals_text = "\n".join([
            f"[{i}] Type: {s.get('type', s.get('signal_type', 'unknown'))}\n"
            f"    Content: {s.get('text', s.get('content', ''))[:200]}\n"
            f"    ID: {s.get('id', '')}"
            for i, s in filtered_signals
        ])
    else:
        # Original behavior: use first 20 signals
        signals_text = "\n".join([
            f"[{i}] Type: {s.get('type', s.get('signal_type', 'unknown'))}\n"
            f"    Content: {s.get('text', s.get('content', ''))[:200]}\n"
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

    unlinked_fallback = [
        {
            **claim,
            'linked_signals': [],
            'confidence': 0.3,
            'is_substantiated': False,
            'suggestion': 'Evidence matching failed.'
        }
        for claim in claims
    ]

    matches = async_to_sync(stream_json)(
        provider,
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You match claims to supporting evidence and assess confidence.",
        fallback=None,
        description="claim-signal linking",
    )

    if not isinstance(matches, list):
        return unlinked_fallback

    try:
        # Merge matches back into claims
        result = []
        for match in matches:
            claim_idx = match.get('claim_index', 0)
            if claim_idx < len(claims):
                claim = claims[claim_idx].copy()

                # Resolve signal references
                linked = []
                for link_item in match.get('linked_signals', []):
                    sig_idx = link_item.get('signal_index', 0)
                    if sig_idx < len(signals):
                        linked.append({
                            'signal_id': signals[sig_idx].get('id'),
                            'signal_type': signals[sig_idx].get('type', signals[sig_idx].get('signal_type')),
                            'relevance': link_item.get('relevance', 0.5),
                            'excerpt': link_item.get('excerpt', '')
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
        logger.warning(f"Failed to process claim links: {e}")
        return unlinked_fallback


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

    return async_to_sync(stream_json)(
        provider,
        messages=[{"role": "user", "content": prompt}],
        system_prompt="You suggest evidence sources for decision-making.",
        fallback=[],
        description="evidence suggestions",
    )


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
                f"{s.get('type', s.get('signal_type', 'signal'))}: {s.get('excerpt', '')[:50]}..."
                for s in claim.get('linked_signals', [])[:2]
            ]
            footnotes.append(f"[^{i}]: {'; '.join(sources)}")

    # Add footnotes section
    if footnotes:
        result += "\n\n---\n### Sources\n" + "\n".join(footnotes)

    return result
