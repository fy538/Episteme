"""
Challenge Context Service

Surfaces specific, grounded challenge priorities for companion injection.
Pulls untested assumptions from the investigation plan and unresolved
tensions from the knowledge graph, then formats them as concise directives
the LLM can weave into its response naturally.

Integration:
    - ContextAssemblyService.assemble() step 5 injects the output
      alongside companion context when a case is linked.
"""
import logging
from typing import List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

MAX_ITEMS = 3
MAX_CONTENT_LENGTH = 120


class ChallengeContextService:
    """Assembles challenge priorities from plan assumptions and graph nodes."""

    @staticmethod
    def get_challenge_context(
        case_id,
        open_questions: Optional[List[str]] = None,
    ) -> str:
        """
        Build a challenge context block for LLM injection.

        Queries the case's investigation plan for untested/high-risk assumptions
        and the knowledge graph for unresolved tensions. Formats as a compact
        block of 1-3 prioritized challenge directives.

        Args:
            case_id: UUID of the case
            open_questions: Open questions from ConversationStructure (already in memory)

        Returns:
            Formatted challenge block string, or empty string if nothing to surface.
        """
        items = []

        # --- Plan assumptions (untested + risky) ---
        try:
            items.extend(_get_plan_assumption_items(case_id))
        except Exception as e:
            logger.debug(f"Plan assumption query failed for case {case_id}: {e}")

        # --- Graph tension nodes ---
        try:
            items.extend(_get_graph_tension_items(case_id))
        except Exception as e:
            logger.debug(f"Graph tension query failed for case {case_id}: {e}")

        # --- Open questions (from companion structure, already in memory) ---
        if open_questions and len(items) < MAX_ITEMS:
            for q in open_questions[:1]:
                if q and isinstance(q, str):
                    items.append({
                        'priority': 2,
                        'text': f'OPEN GAP: The user hasn\'t investigated "{_truncate(q)}" — consider probing this.',
                    })

        if not items:
            return ""

        # Sort by priority (lower = higher priority), take top N
        items.sort(key=lambda x: x['priority'])
        top_items = items[:MAX_ITEMS]

        lines = ["CHALLENGE PRIORITIES (address the most relevant one naturally in your response):"]
        for item in top_items:
            lines.append(f"- {item['text']}")

        return "\n".join(lines)


def _get_plan_assumption_items(case_id) -> List[dict]:
    """Query plan assumptions that are untested and medium/high risk."""
    from apps.cases.models import InvestigationPlan, PlanVersion

    plan = InvestigationPlan.objects.filter(case_id=case_id).first()
    if not plan:
        return []

    version = PlanVersion.objects.filter(
        plan=plan, version_number=plan.current_version
    ).first()
    if not version or not version.content:
        return []

    assumptions = version.content.get('assumptions', [])

    # Filter to untested/challenged + medium/high risk
    risky = [
        a for a in assumptions
        if a.get('status') in ('untested', 'challenged')
        and a.get('risk_level') in ('medium', 'high')
    ]

    # Sort: high risk first, then challenged before untested
    status_order = {'challenged': 0, 'untested': 1}
    risk_order = {'high': 0, 'medium': 1}
    risky.sort(key=lambda a: (
        risk_order.get(a.get('risk_level'), 2),
        status_order.get(a.get('status'), 2),
    ))

    items = []
    for a in risky[:2]:  # Max 2 assumptions
        status = a.get('status', 'untested').upper()
        risk = a.get('risk_level', 'medium')
        text = _truncate(a.get('text', ''))
        label = f"{status} ASSUMPTION ({risk} risk)"

        detail = "no evidence supports or contradicts this yet"
        if a.get('status') == 'challenged':
            summary = a.get('evidence_summary', '')
            detail = f"evidence is mixed: {_truncate(summary)}" if summary else "conflicting evidence exists"

        items.append({
            'priority': 0 if risk == 'high' else 1,
            'text': f'{label}: "{text}" — {detail}.',
        })

    return items


def _get_graph_tension_items(case_id) -> List[dict]:
    """Query unresolved tension nodes from the case graph."""
    from apps.graph.models import Node

    tensions = list(
        Node.objects.filter(
            case_id=case_id,
            node_type='tension',
            status__in=['surfaced', 'acknowledged'],
        ).only(
            'content', 'status', 'properties',
        ).order_by('-created_at')[:3]
    )

    items = []
    for t in tensions[:2]:  # Max 2 tensions
        content = _truncate(t.content)
        items.append({
            'priority': 1,
            'text': f'UNRESOLVED TENSION: "{content}" — this is unresolved and may affect the decision.',
        })

    return items


def _truncate(text: str, length: int = MAX_CONTENT_LENGTH) -> str:
    """Truncate text to max length with ellipsis."""
    if not text:
        return ""
    text = text.strip()
    if len(text) <= length:
        return text
    return text[:length - 1] + "\u2026"
