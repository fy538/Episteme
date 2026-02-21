"""
Fact Promotion Pipeline

Promotes established facts from ConversationStructure (thread-level) to
case-level constraints and project-level insights.

Also contains premortem comparison logic used after decision recording.

Integration:
    Called from CompanionService.update_structure() as async fire-and-forget.
"""
import json
import logging
from typing import Optional

from asgiref.sync import sync_to_async
from django.db import transaction

from apps.common.llm_providers import get_llm_provider, strip_markdown_fences

logger = logging.getLogger(__name__)


class FactPromotionService:
    """Promotes established facts from conversation to case/project level."""

    @staticmethod
    def _canonicalize_fact(fact) -> str:
        """Normalize a fact string for stable comparison across structure versions."""
        return ' '.join(str(fact).lower().strip().split())

    @staticmethod
    async def promote_to_case(thread, structure) -> Optional[dict]:
        """
        Check if any established facts should become case constraints
        or update the case position.

        Only promotes facts with high stability (present in 2+ structure
        versions) to avoid noise from transient conversation states.

        Args:
            thread: ChatThread instance
            structure: Current ConversationStructure instance

        Returns:
            Dict with promotion stats or None if nothing promoted
        """
        from .models import ConversationStructure
        from apps.cases.models import Case

        case_id = getattr(thread, 'primary_case_id', None)
        if not case_id:
            return None

        established = structure.established or []
        if len(established) < 2:
            return None

        # Stability check: only promote facts present in previous version too
        previous = await sync_to_async(
            lambda: ConversationStructure.objects.filter(
                thread=thread,
                version__lt=structure.version,
            ).order_by('-version').first()
        )()

        if not previous:
            return None  # First version — wait for stability

        canonicalize = FactPromotionService._canonicalize_fact
        previous_established = set(
            canonicalize(f) for f in (previous.established or [])
        )
        stable_facts = [
            f for f in established
            if canonicalize(f) in previous_established
        ]

        if not stable_facts:
            return None

        # Pre-load the case once — avoids N+1 queries in sub-methods
        try:
            case = await sync_to_async(Case.objects.get)(id=case_id)
        except Case.DoesNotExist:
            logger.warning("Case %s not found for fact promotion", case_id)
            return None

        # Use LLM to classify facts: 'constraint', 'position_update', or 'skip'
        facts_text = "\n".join(f"- {f}" for f in stable_facts)
        prompt = (
            f"These facts have been established across multiple conversation turns:\n"
            f"{facts_text}\n\n"
            "For each fact, classify as:\n"
            '- "constraint": A hard requirement or boundary the user has confirmed\n'
            '- "position_update": New information that should update the case position\n'
            '- "skip": Not significant enough to promote to case level\n\n'
            "Return JSON: {\"promotions\": [{\"fact\": \"...\", \"type\": \"constraint|position_update|skip\", \"reason\": \"...\"}]}"
        )

        try:
            provider = get_llm_provider('fast')
            result_text = await provider.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You classify established conversation facts. Return ONLY valid JSON.",
                max_tokens=512,
                temperature=0.2,
            )
            cleaned = strip_markdown_fences(result_text.strip())
            result = json.loads(cleaned)
        except Exception as e:
            logger.warning("Fact classification LLM call failed: %s", e)
            return None

        promotions = result.get('promotions', [])
        if not isinstance(promotions, list):
            logger.warning("Fact classification returned non-list promotions: %s", type(promotions))
            return None

        stats = {'constraints_added': 0, 'position_updates': 0, 'skipped': 0}
        position_proposals = []

        for promo in promotions:
            if not isinstance(promo, dict):
                continue
            promo_type = promo.get('type', 'skip')
            fact = promo.get('fact', '')
            if not fact:
                continue

            if promo_type == 'constraint':
                added = await FactPromotionService._add_case_constraint(
                    case.id, fact, reason=promo.get('reason', '')
                )
                if added:
                    stats['constraints_added'] += 1
            elif promo_type == 'position_update':
                stats['position_updates'] += 1
                position_proposals.append({
                    'fact': fact,
                    'reason': promo.get('reason', ''),
                })
            else:
                stats['skipped'] += 1

        # Store position update proposals on the latest assistant message
        # so the frontend can surface them as inline proposal cards.
        if position_proposals:
            await FactPromotionService._store_position_proposal(
                thread, case, position_proposals
            )

        if stats['constraints_added'] > 0 or stats['position_updates'] > 0:
            logger.info(
                "fact_promotion_completed",
                extra={
                    "thread_id": str(thread.id),
                    "case_id": str(case_id),
                    **stats,
                }
            )

        return stats if (stats['constraints_added'] + stats['position_updates']) > 0 else None

    @staticmethod
    async def _add_case_constraint(case_id, fact: str, reason: str = '') -> bool:
        """Append a fact to the case's constraints list as a {type, description} dict.

        Uses select_for_update inside a transaction to prevent concurrent
        read-modify-write races (two fact promotions for the same case).

        Args:
            case_id: Case PK (re-fetched inside transaction for atomicity)
            fact: The fact text to add as a constraint
            reason: LLM classification reason (used for type inference)

        Returns:
            True if constraint was added, False on duplicate or failure.
        """
        from apps.cases.models import Case

        def _do_add() -> bool:
            with transaction.atomic():
                locked_case = Case.objects.select_for_update().get(id=case_id)
                constraints = locked_case.constraints or []

                # Avoid duplicates (compare description for dicts, full string for legacy)
                fact_lower = fact.lower().strip()
                for c in constraints:
                    if isinstance(c, dict):
                        existing = c.get('description', '').lower().strip()
                    else:
                        existing = str(c).lower().strip()
                    if existing == fact_lower:
                        return False

                # Infer constraint type from reason/fact keywords
                constraint_type = 'general'
                combined = (reason + ' ' + fact).lower()
                for keyword in ['timeline', 'budget', 'regulatory', 'technical', 'legal', 'resource']:
                    if keyword in combined:
                        constraint_type = keyword
                        break

                constraints.append({'type': constraint_type, 'description': fact})
                locked_case.constraints = constraints
                locked_case.save(update_fields=['constraints', 'updated_at'])
                return True

        try:
            return await sync_to_async(_do_add)()
        except Exception as e:
            logger.warning("Could not add constraint to case %s: %s", case_id, e)
            return False

    @staticmethod
    async def _store_position_proposal(thread, case, proposals: list):
        """
        Store position update proposals on the latest assistant message metadata.

        The frontend scans loaded messages for 'position_update_proposal' in
        metadata and surfaces them as inline proposal cards (Accept / Dismiss).

        Args:
            thread: ChatThread instance
            case: Case model instance (pre-loaded to avoid N+1 queries)
            proposals: List of {fact, reason} dicts
        """
        from .models import Message

        try:
            current_position = case.position or ''

            # Find the latest assistant message on this thread
            last_msg = await sync_to_async(
                lambda: Message.objects.filter(
                    thread=thread, role='assistant'
                ).order_by('-created_at').first()
            )()

            if not last_msg:
                logger.warning("No assistant message to attach position proposal to (thread %s)", thread.id)
                return

            # Don't overwrite an existing unresolved proposal on the same message
            msg_metadata = last_msg.metadata or {}
            if msg_metadata.get('position_update_proposal'):
                logger.debug("Position proposal already exists on message %s", last_msg.id)
                return

            msg_metadata['position_update_proposal'] = {
                'proposals': proposals,
                'case_id': str(case.id),
                'current_position': current_position,
            }
            last_msg.metadata = msg_metadata
            await sync_to_async(last_msg.save)(update_fields=['metadata'])

            logger.info(
                "position_proposal_stored",
                extra={
                    "thread_id": str(thread.id),
                    "case_id": str(case.id),
                    "message_id": str(last_msg.id),
                    "proposal_count": len(proposals),
                }
            )
        except Exception as e:
            logger.warning("Could not store position proposal: %s", e)

    @staticmethod
    async def promote_to_insight(thread, structure) -> Optional[str]:
        """
        Check if any established fact represents a project-level insight.

        Creates a ProjectInsight with source_type='conversation_promotion'.
        The embedding is auto-generated by the post_save signal hook.

        Returns:
            Created insight ID or None
        """
        if not thread.project_id:
            return None

        established = structure.established or []
        if len(established) < 4:
            return None  # Need substantial evidence before promoting to project level

        # LLM check: is any fact cross-case significant?
        facts_text = "\n".join(f"- {f}" for f in established)
        prompt = (
            f"These facts were established in a case investigation:\n"
            f"{facts_text}\n\n"
            "Is any of these facts significant at the PROJECT level — meaning it would "
            "be useful context for other investigations in this project?\n\n"
            "Return JSON: {\"promote\": true/false, \"fact\": \"the fact to promote\", "
            "\"title\": \"short insight title\", \"content\": \"expanded insight text\"}\n"
            "If no fact is project-significant, return {\"promote\": false}"
        )

        try:
            provider = get_llm_provider('fast')
            result_text = await provider.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You evaluate conversation facts for project-level significance. Return ONLY valid JSON.",
                max_tokens=512,
                temperature=0.2,
            )
            cleaned = strip_markdown_fences(result_text.strip())
            result = json.loads(cleaned)
        except Exception as e:
            logger.warning("Insight promotion classification failed: %s", e)
            return None

        if not result.get('promote'):
            return None

        try:
            from apps.graph.models import ProjectInsight, InsightType, InsightSource

            insight = await sync_to_async(ProjectInsight.objects.create)(
                project_id=thread.project_id,
                insight_type=InsightType.PATTERN if hasattr(InsightType, 'PATTERN') else 'pattern',
                title=result.get('title', result.get('fact', ''))[:200],
                content=result.get('content', result.get('fact', '')),
                source_type=InsightSource.CONVERSATION_PROMOTION,
                source_case_id=getattr(thread, 'primary_case_id', None),
                metadata={
                    'promoted_from_thread': str(thread.id),
                    'original_fact': result.get('fact', ''),
                },
            )

            logger.info(
                "fact_promoted_to_insight",
                extra={
                    "thread_id": str(thread.id),
                    "insight_id": str(insight.id),
                    "title": insight.title[:60],
                }
            )
            return str(insight.id)

        except Exception as e:
            logger.warning("Could not create promoted insight: %s", e)
            return None


# ---------------------------------------------------------------------------
# Premortem comparison (called after decision recording)
# ---------------------------------------------------------------------------

async def compare_decision_to_premortem(record, case) -> Optional[dict]:
    """
    Compare a recorded decision against the case's premortem analysis.

    Identifies risks from the premortem that the decision doesn't address,
    and checks if what_would_change_mind conditions may apply.

    Args:
        record: DecisionRecord instance
        case: Case instance (must have premortem_text)

    Returns:
        Comparison result dict or None
    """
    if not case.premortem_text:
        return None

    prompt_parts = [
        f"DECISION MADE:\n{record.decision_text}\n",
        f"KEY REASONS: {', '.join(record.key_reasons) if record.key_reasons else 'None stated'}\n",
        f"CAVEATS NOTED: {record.caveats or 'None'}\n\n",
        f"PREMORTEM ANALYSIS (written before the decision):\n{case.premortem_text}\n\n",
    ]

    if case.what_would_change_mind:
        prompt_parts.append(
            f"USER SAID THEY WOULD CHANGE THEIR MIND IF:\n{case.what_would_change_mind}\n\n"
        )

    prompt_parts.append(
        "Analyze:\n"
        "1. Which risks from the premortem does the decision NOT address?\n"
        "2. Are any of the 'change my mind' conditions currently met or likely?\n"
        "3. What should the user watch for going forward?\n\n"
        'Return JSON: {"unaddressed_risks": ["..."], "change_mind_flags": ["..."], '
        '"watch_for": ["..."], "overall_assessment": "brief summary"}'
    )

    try:
        provider = get_llm_provider('fast')
        result_text = await provider.generate(
            messages=[{"role": "user", "content": "".join(prompt_parts)}],
            system_prompt=(
                "You compare decisions against premortem analyses to surface "
                "unaddressed risks. Return ONLY valid JSON."
            ),
            max_tokens=1024,
            temperature=0.2,
        )
        cleaned = strip_markdown_fences(result_text.strip())
        comparison = json.loads(cleaned)

        # Store in decision metadata
        from apps.cases.models import DecisionRecord
        metadata = record.metadata if hasattr(record, 'metadata') and record.metadata else {}
        metadata['premortem_comparison'] = comparison
        await sync_to_async(
            lambda: DecisionRecord.objects.filter(pk=record.pk).update(metadata=metadata)
        )()

        logger.info(
            "premortem_comparison_completed",
            extra={
                "decision_id": str(record.id),
                "case_id": str(case.id),
                "unaddressed_risks": len(comparison.get('unaddressed_risks', [])),
            }
        )

        return comparison

    except Exception as e:
        logger.warning("Premortem comparison failed: %s", e)
        return None
