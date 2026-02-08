"""
Background Analysis Service

Provides continuous background analysis of case documents:
- Periodic re-analysis when content changes
- Proactive suggestion generation
- Evidence gap detection
- Claim verification
"""
import hashlib
import json
import logging

from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.core.cache import cache

from apps.common.llm_providers import get_llm_provider


# Cache keys
def _analysis_cache_key(doc_id: str) -> str:
    return f"doc_analysis:{doc_id}"


def _content_hash_key(doc_id: str) -> str:
    return f"doc_hash:{doc_id}"


def get_content_hash(content: str) -> str:
    """Generate hash of content for change detection."""
    return hashlib.md5(content.encode()).hexdigest()


def should_reanalyze(doc_id: str, current_content: str) -> bool:
    """Check if document needs re-analysis based on content changes."""
    current_hash = get_content_hash(current_content)
    cached_hash = cache.get(_content_hash_key(doc_id))

    if cached_hash is None or cached_hash != current_hash:
        return True

    # Also check if analysis is stale (older than 10 minutes)
    cached_analysis = cache.get(_analysis_cache_key(doc_id))
    if cached_analysis is None:
        return True

    return False


def get_cached_analysis(doc_id: str) -> Optional[Dict[str, Any]]:
    """Get cached analysis results if available."""
    return cache.get(_analysis_cache_key(doc_id))


def cache_analysis(doc_id: str, content: str, analysis: Dict[str, Any], ttl: int = 600):
    """Cache analysis results with content hash."""
    cache.set(_analysis_cache_key(doc_id), analysis, ttl)
    cache.set(_content_hash_key(doc_id), get_content_hash(content), ttl)


def run_background_analysis(
    document_id: str,
    content: str,
    case_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Run comprehensive background analysis on a document.

    Returns:
    {
        analyzed_at: str,
        content_hash: str,
        health_score: int (0-100),
        issues: [{type, severity, message, location}],
        suggestions: [{id, type, content, reason, confidence}],
        evidence_gaps: [{claim, location, suggestion}],
        unlinked_claims: [{text, location, potential_sources}],
        metrics: {
            claim_count: int,
            linked_claim_count: int,
            assumption_count: int,
            validated_assumption_count: int
        }
    }
    """
    provider = get_llm_provider('fast')

    prompt = _build_analysis_prompt(content, case_context)

    async def analyze():
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="""You are an AI analyst that reviews decision documents for quality, completeness, and rigor.
You identify:
1. Claims without supporting evidence
2. Assumptions that need validation
3. Logical gaps or inconsistencies
4. Missing perspectives
5. Opportunities for improvement

You provide actionable, specific feedback."""
        ):
            full_response += chunk.content

        try:
            response_text = full_response.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            result = json.loads(response_text)
            result['analyzed_at'] = datetime.utcnow().isoformat()
            result['content_hash'] = get_content_hash(content)
            return result
        except Exception as e:
            logger.warning(f"Failed to parse analysis: {e}")
            return {
                'analyzed_at': datetime.utcnow().isoformat(),
                'content_hash': get_content_hash(content),
                'health_score': 50,
                'issues': [],
                'suggestions': [],
                'evidence_gaps': [],
                'unlinked_claims': [],
                'metrics': {
                    'claim_count': 0,
                    'linked_claim_count': 0,
                    'assumption_count': 0,
                    'validated_assumption_count': 0
                }
            }

    analysis = async_to_sync(analyze)()

    # Cache the results
    cache_analysis(document_id, content, analysis)

    return analysis


def _build_analysis_prompt(content: str, case_context: Dict[str, Any]) -> str:
    """Build the comprehensive analysis prompt."""

    decision_question = case_context.get('decision_question', '')
    inquiries = case_context.get('inquiries', [])
    signals = case_context.get('signals', [])

    inquiries_text = "\n".join([
        f"- {i.get('title', 'Untitled')} (status: {i.get('status', 'unknown')})"
        for i in inquiries
    ]) if inquiries else "No inquiries"

    signals_text = "\n".join([
        f"- [{s.get('signal_type', 'unknown')}] {s.get('content', '')[:80]}..."
        for s in signals[:15]
    ]) if signals else "No signals"

    return f"""Analyze this decision brief comprehensively.

## Decision Context
Question: {decision_question or "Not specified"}

## Brief Content
{content}

## Active Inquiries
{inquiries_text}

## Available Evidence (Signals)
{signals_text}

## Analysis Tasks

1. **Health Score** (0-100): Overall document quality considering:
   - Evidence backing for claims
   - Logical coherence
   - Completeness of analysis
   - Clarity of reasoning

2. **Issues**: Problems that need attention
   - type: "unsupported_claim" | "logical_gap" | "missing_perspective" | "assumption_risk" | "contradiction"
   - severity: "low" | "medium" | "high"
   - message: Clear description
   - location: Quote the relevant text

3. **Suggestions**: Specific improvements
   - id: unique identifier
   - type: "add" | "replace" | "clarify" | "cite"
   - content: The suggested text
   - reason: Why this helps
   - confidence: 0.0-1.0

4. **Evidence Gaps**: Claims needing evidence
   - claim: The claim text
   - location: Where in document
   - suggestion: How to find/add evidence

5. **Unlinked Claims**: Claims that could be linked to existing signals
   - text: The claim
   - location: Where in document
   - potential_sources: Which signals might support this

6. **Metrics**:
   - claim_count: Total claims made
   - linked_claim_count: Claims with evidence
   - assumption_count: Total assumptions
   - validated_assumption_count: Assumptions with validation

Return as JSON:
{{
    "health_score": 72,
    "issues": [...],
    "suggestions": [...],
    "evidence_gaps": [...],
    "unlinked_claims": [...],
    "metrics": {{...}}
}}

Return ONLY the JSON object."""


def get_document_health(doc_id: str) -> Optional[Dict[str, Any]]:
    """Get quick health metrics from cached analysis."""
    analysis = get_cached_analysis(doc_id)
    if not analysis:
        return None

    return {
        'health_score': analysis.get('health_score', 0),
        'issue_count': len(analysis.get('issues', [])),
        'suggestion_count': len(analysis.get('suggestions', [])),
        'evidence_gap_count': len(analysis.get('evidence_gaps', [])),
        'analyzed_at': analysis.get('analyzed_at'),
    }
