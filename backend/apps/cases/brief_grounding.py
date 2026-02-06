"""
Brief grounding engine.

Computes grounding status and annotations for brief sections by following
the section → inquiry → signals → evidence chain. Uses existing GraphAnalyzer
and GraphUtils for pattern detection.

Also derives readiness checklist items from grounding gaps, completing
the three-way feedback loop: Knowledge Graph → Brief → Readiness.
"""
import logging
from typing import Dict, List, Any

from django.db import models, transaction
from django.utils import timezone

from apps.cases.brief_models import (
    BriefSection, BriefAnnotation,
    GroundingStatus, AnnotationType, AnnotationPriority,
)
from apps.common.graph_utils import GraphUtils
from apps.signals.models import Signal

logger = logging.getLogger(__name__)


class BriefGroundingEngine:
    """
    Computes grounding status and annotations for brief sections.

    Grounding flows from the knowledge graph:
    - BriefSection → Inquiry → Signals + Evidence
    - For custom sections: BriefSection → tagged_signals

    Annotations are generated from graph analysis:
    - Tensions from contradicting signals
    - Blind spots from evidence deserts
    - Ungrounded from orphaned assumptions
    - Well-grounded from strong evidence
    """

    @staticmethod
    def compute_section_grounding(section: BriefSection) -> Dict[str, Any]:
        """
        Compute grounding status for a single section.

        For inquiry_brief sections: follows section → inquiry → signals + evidence.
        For custom sections with tagged_signals: computes from tagged signals.
        For unlinked sections: returns empty grounding.

        Returns:
            {
                'status': GroundingStatus value,
                'evidence_count': int,
                'supporting': int,
                'contradicting': int,
                'neutral': int,
                'unvalidated_assumptions': int,
                'tensions_count': int,
                'confidence_avg': float | None,
            }
        """
        result = {
            'status': GroundingStatus.EMPTY,
            'evidence_count': 0,
            'supporting': 0,
            'contradicting': 0,
            'neutral': 0,
            'unvalidated_assumptions': 0,
            'tensions_count': 0,
            'confidence_avg': None,
        }

        if section.inquiry:
            return BriefGroundingEngine._compute_from_inquiry(section.inquiry, result)
        elif section.is_linked and section.tagged_signals.exists():
            return BriefGroundingEngine._compute_from_signals(
                section.tagged_signals.all(), result
            )
        else:
            # Decision frame sections get "set" status if decision_question exists
            if section.section_type == 'decision_frame':
                case = section.brief.case
                if case.decision_question:
                    result['status'] = GroundingStatus.STRONG
                else:
                    result['status'] = GroundingStatus.EMPTY
            return result

    @staticmethod
    def _compute_from_inquiry(inquiry, result: Dict) -> Dict:
        """Compute grounding from an inquiry's evidence and signals."""
        # Count evidence by direction
        evidence_items = inquiry.evidence_items.all()
        for evidence in evidence_items:
            result['evidence_count'] += 1
            if evidence.direction == 'supports':
                result['supporting'] += 1
            elif evidence.direction == 'contradicts':
                result['contradicting'] += 1
            else:
                result['neutral'] += 1

        # Count unvalidated assumptions
        assumptions = Signal.objects.filter(
            inquiry=inquiry,
            type='Assumption',
            dismissed_at__isnull=True,
        )
        for assumption in assumptions:
            has_evidence = assumption.supported_by_evidence.exists()
            if not has_evidence:
                result['unvalidated_assumptions'] += 1

        # Count tensions (contradicting signals)
        signals = inquiry.related_signals.filter(dismissed_at__isnull=True)
        tension_count = 0
        for signal in signals:
            contradictions = signal.contradicts.filter(dismissed_at__isnull=True)
            contradicted_by = signal.contradicted_by.filter(dismissed_at__isnull=True)
            if contradictions.exists() or contradicted_by.exists():
                tension_count += 1
        # Deduplicate (A contradicts B counts once, not twice)
        result['tensions_count'] = tension_count // 2 if tension_count > 1 else tension_count

        # Average confidence from evidence
        if result['evidence_count'] > 0:
            confidences = [e.strength for e in evidence_items if e.strength]
            if confidences:
                result['confidence_avg'] = round(sum(confidences) / len(confidences), 2)

        # Determine status
        result['status'] = BriefGroundingEngine._determine_status(result)
        return result

    @staticmethod
    def _compute_from_signals(signals, result: Dict) -> Dict:
        """Compute grounding from tagged signals (custom sections)."""
        for signal in signals:
            # Check for evidence
            supporting = signal.supported_by_evidence.count()
            contradicting = signal.contradicted_by_evidence.count()
            result['supporting'] += supporting
            result['contradicting'] += contradicting
            result['evidence_count'] += supporting + contradicting

            # Check for unvalidated assumptions
            if signal.type == 'Assumption' and not signal.supported_by_evidence.exists():
                result['unvalidated_assumptions'] += 1

            # Check for tensions
            if signal.contradicts.exists() or signal.contradicted_by.exists():
                result['tensions_count'] += 1

        result['status'] = BriefGroundingEngine._determine_status(result)
        return result

    @staticmethod
    def _determine_status(data: Dict) -> str:
        """Determine GroundingStatus from computed data."""
        evidence = data['evidence_count']
        tensions = data['tensions_count']
        unvalidated = data['unvalidated_assumptions']

        if evidence == 0 and unvalidated == 0:
            return GroundingStatus.EMPTY

        if tensions > 0:
            return GroundingStatus.CONFLICTED

        if evidence == 0 and unvalidated > 0:
            return GroundingStatus.WEAK

        if evidence >= 3 and unvalidated == 0:
            return GroundingStatus.STRONG

        if evidence >= 1:
            return GroundingStatus.MODERATE

        return GroundingStatus.WEAK

    @staticmethod
    def compute_section_annotations(section: BriefSection) -> List[Dict[str, Any]]:
        """
        Generate annotations for a section based on graph analysis.

        Uses GraphAnalyzer's inquiry-scoped methods for richer pattern
        detection when available, falling back to inline analysis.

        Returns a list of annotation data dicts, not yet persisted.
        Each dict: {type, description, priority, signal_ids, inquiry_id}
        """
        annotations = []

        if not section.inquiry and not section.tagged_signals.exists():
            return annotations

        inquiry = section.inquiry

        if inquiry:
            # Use inquiry-scoped graph analysis for richer pattern detection
            try:
                from apps.companion.graph_analyzer import GraphAnalyzer
                analyzer = GraphAnalyzer()
                patterns = analyzer.find_patterns_for_inquiry(inquiry.id)
                annotations = BriefGroundingEngine._annotations_from_patterns(
                    patterns, inquiry
                )
            except Exception as e:
                logger.warning(
                    f"Inquiry-scoped analysis failed for {inquiry.id}, "
                    f"falling back to inline: {e}"
                )
                annotations = BriefGroundingEngine._annotations_inline(
                    section, inquiry
                )

        return annotations

    @staticmethod
    def _annotations_from_patterns(
        patterns: Dict, inquiry
    ) -> List[Dict[str, Any]]:
        """
        Convert GraphAnalyzer patterns into annotation dicts.

        Leverages the richer inquiry-scoped analysis for better annotations:
        - High-confidence contradictions get BLOCKING priority
        - Regular contradictions get IMPORTANT priority
        - Recurring themes surface as informational annotations
        """
        annotations = []
        import uuid as uuid_module

        # Tensions — from contradictions
        for contradiction in patterns.get('contradictions', []):
            # High-confidence contradictions are blocking
            priority = (
                AnnotationPriority.BLOCKING
                if contradiction.get('both_high_confidence')
                else AnnotationPriority.IMPORTANT
            )
            signal_ids = []
            for sid in [contradiction.get('signal_id'), contradiction.get('contradicts_id')]:
                if sid:
                    try:
                        signal_ids.append(uuid_module.UUID(sid))
                    except (ValueError, TypeError):
                        pass

            desc_prefix = 'High-confidence conflict' if contradiction.get('both_high_confidence') else 'Conflict'
            annotations.append({
                'type': AnnotationType.TENSION,
                'description': (
                    f'{desc_prefix}: "{contradiction["signal_text"][:60]}..." '
                    f'vs "{contradiction["contradicts_text"][:60]}..."'
                ),
                'priority': priority,
                'signal_ids': signal_ids,
                'inquiry_id': inquiry.id,
            })

        # Ungrounded assumptions
        for assumption in patterns.get('ungrounded_assumptions', []):
            try:
                signal_id = uuid_module.UUID(assumption['id'])
            except (ValueError, TypeError):
                signal_id = None

            annotations.append({
                'type': AnnotationType.UNGROUNDED,
                'description': f'Unvalidated assumption: "{assumption["text"][:80]}..."',
                'priority': AnnotationPriority.IMPORTANT,
                'signal_ids': [signal_id] if signal_id else [],
                'inquiry_id': inquiry.id,
            })

        # Evidence desert
        eq = patterns.get('evidence_quality', {})
        total_evidence = eq.get('total', 0)
        if total_evidence < 2 and inquiry.status in ['open', 'investigating']:
            annotations.append({
                'type': AnnotationType.EVIDENCE_DESERT,
                'description': f'Only {total_evidence} evidence item(s). Consider gathering more evidence.',
                'priority': AnnotationPriority.IMPORTANT,
                'signal_ids': [],
                'inquiry_id': inquiry.id,
            })

        # Well-grounded claims
        for claim in patterns.get('strong_claims', []):
            try:
                signal_id = uuid_module.UUID(claim['id'])
            except (ValueError, TypeError):
                signal_id = None

            annotations.append({
                'type': AnnotationType.WELL_GROUNDED,
                'description': (
                    f'Well-supported claim ({claim["evidence_count"]} evidence, '
                    f'{claim["avg_confidence"]:.0%} confidence): "{claim["text"][:60]}..."'
                ),
                'priority': AnnotationPriority.INFO,
                'signal_ids': [signal_id] if signal_id else [],
                'inquiry_id': inquiry.id,
            })

        # Stale detection: evidence that's all low-confidence
        if total_evidence > 0 and eq.get('low_confidence', 0) == total_evidence:
            annotations.append({
                'type': AnnotationType.STALE,
                'description': 'All evidence has low confidence. Consider finding stronger sources.',
                'priority': AnnotationPriority.IMPORTANT,
                'signal_ids': [],
                'inquiry_id': inquiry.id,
            })

        return annotations

    @staticmethod
    def _annotations_inline(
        section: BriefSection, inquiry
    ) -> List[Dict[str, Any]]:
        """
        Fallback inline annotation computation (no GraphAnalyzer dependency).

        Used when inquiry-scoped graph analysis is unavailable.
        """
        annotations = []
        signals = inquiry.related_signals.filter(dismissed_at__isnull=True)

        # Tensions
        seen_pairs = set()
        for signal in signals:
            for contra in signal.contradicts.filter(dismissed_at__isnull=True):
                pair = tuple(sorted([str(signal.id), str(contra.id)]))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    annotations.append({
                        'type': AnnotationType.TENSION,
                        'description': f'"{signal.text[:60]}..." conflicts with "{contra.text[:60]}..."',
                        'priority': AnnotationPriority.BLOCKING,
                        'signal_ids': [signal.id, contra.id],
                        'inquiry_id': inquiry.id,
                    })

        # Ungrounded assumptions
        for assumption in signals.filter(type='Assumption'):
            if not assumption.supported_by_evidence.exists():
                annotations.append({
                    'type': AnnotationType.UNGROUNDED,
                    'description': f'Unvalidated assumption: "{assumption.text[:80]}..."',
                    'priority': AnnotationPriority.IMPORTANT,
                    'signal_ids': [assumption.id],
                    'inquiry_id': inquiry.id,
                })

        # Evidence desert
        evidence_count = inquiry.evidence_items.count()
        if evidence_count < 2 and inquiry.status in ['open', 'investigating']:
            annotations.append({
                'type': AnnotationType.EVIDENCE_DESERT,
                'description': f'Only {evidence_count} evidence item(s). Consider gathering more evidence.',
                'priority': AnnotationPriority.IMPORTANT,
                'signal_ids': [],
                'inquiry_id': inquiry.id,
            })

        # Well-grounded claims
        for claim in signals.filter(type='Claim'):
            supporting = claim.supported_by_evidence.count()
            if supporting >= 2 and not claim.contradicted_by_evidence.exists():
                annotations.append({
                    'type': AnnotationType.WELL_GROUNDED,
                    'description': f'Well-supported claim ({supporting} evidence): "{claim.text[:60]}..."',
                    'priority': AnnotationPriority.INFO,
                    'signal_ids': [claim.id],
                    'inquiry_id': inquiry.id,
                })

        return annotations

    @staticmethod
    def derive_readiness_items(section: BriefSection) -> List[Dict[str, Any]]:
        """
        Convert grounding gaps into readiness checklist item data.

        Returns list of dicts suitable for ReadinessChecklistItem creation:
        {description, is_required, why_important, item_type, linked_inquiry_id}
        """
        items = []
        grounding = section.grounding_data

        if not grounding:
            return items

        inquiry = section.inquiry

        # No evidence → investigation item
        if grounding.get('evidence_count', 0) == 0 and inquiry:
            items.append({
                'description': f'Gather evidence for: {section.heading}',
                'is_required': True,
                'why_important': 'This section has no supporting evidence yet.',
                'item_type': 'investigation',
                'linked_inquiry_id': str(inquiry.id) if inquiry else None,
            })

        # Unvalidated assumptions → validation items
        if grounding.get('unvalidated_assumptions', 0) > 0:
            count = grounding['unvalidated_assumptions']
            items.append({
                'description': f'Validate {count} assumption(s) in: {section.heading}',
                'is_required': True,
                'why_important': f'{count} assumption(s) lack supporting evidence.',
                'item_type': 'validation',
                'linked_inquiry_id': str(inquiry.id) if inquiry else None,
            })

        # Tensions → resolution items
        if grounding.get('tensions_count', 0) > 0:
            count = grounding['tensions_count']
            items.append({
                'description': f'Resolve {count} tension(s) in: {section.heading}',
                'is_required': True,
                'why_important': f'{count} conflicting source(s) need resolution.',
                'item_type': 'analysis',
                'linked_inquiry_id': str(inquiry.id) if inquiry else None,
            })

        return items

    @classmethod
    def evolve_brief(cls, case_id) -> Dict[str, Any]:
        """
        Recompute grounding for all BriefSections in a case.

        1. Get all BriefSections for case's main_brief
        2. For each linked section: compute grounding
        3. Update grounding_status + grounding_data
        4. Refresh annotations (create new, resolve stale)
        5. Return delta summary

        Args:
            case_id: UUID of the case

        Returns:
            Dict with: updated_sections, new_annotations, resolved_annotations
        """
        from apps.cases.models import Case

        try:
            case = Case.objects.get(id=case_id)
        except Case.DoesNotExist:
            logger.error(f"Case {case_id} not found for brief evolution")
            return {'updated_sections': [], 'new_annotations': [], 'resolved_annotations': []}

        if not case.main_brief:
            logger.warning(f"Case {case_id} has no main brief")
            return {'updated_sections': [], 'new_annotations': [], 'resolved_annotations': []}

        # Wrap entire evolution in a transaction so partial failures don't
        # leave grounding_status / annotations in an inconsistent state.
        with transaction.atomic():
            return cls._evolve_brief_inner(case)

    @classmethod
    def _evolve_brief_inner(cls, case) -> Dict[str, Any]:
        """Inner evolution logic, runs within a transaction."""
        brief = case.main_brief
        sections = BriefSection.objects.filter(brief=brief).select_related('inquiry')

        updated_sections = []
        new_annotations = []
        resolved_annotations = []

        for section in sections:
            # 1. Recompute grounding
            grounding = cls.compute_section_grounding(section)
            old_status = section.grounding_status
            new_status = grounding.pop('status')

            section.grounding_status = new_status
            section.grounding_data = grounding
            section.save(update_fields=['grounding_status', 'grounding_data', 'updated_at'])

            if old_status != new_status:
                updated_sections.append({
                    'id': str(section.id),
                    'heading': section.heading,
                    'old_status': old_status,
                    'new_status': new_status,
                })

            # 2. Compute new annotations
            computed_annotations = cls.compute_section_annotations(section)

            # 3. Reconcile with existing annotations
            existing_active = section.annotations.filter(
                dismissed_at__isnull=True,
                resolved_at__isnull=True,
            )

            # Build a set of existing annotation "signatures" for dedup
            existing_signatures = set()
            for ann in existing_active:
                sig = (ann.annotation_type, ann.description[:80])
                existing_signatures.add(sig)

            # Create new annotations that don't already exist
            for ann_data in computed_annotations:
                sig = (ann_data['type'], ann_data['description'][:80])
                if sig not in existing_signatures:
                    annotation = BriefAnnotation.objects.create(
                        section=section,
                        annotation_type=ann_data['type'],
                        description=ann_data['description'],
                        priority=ann_data['priority'],
                        source_inquiry_id=ann_data.get('inquiry_id'),
                    )
                    # Link source signals
                    if ann_data.get('signal_ids'):
                        annotation.source_signals.set(
                            Signal.objects.filter(id__in=ann_data['signal_ids'])
                        )
                    new_annotations.append({
                        'id': str(annotation.id),
                        'type': annotation.annotation_type,
                        'section_heading': section.heading,
                    })

            # 4. Resolve stale annotations (no longer computed)
            computed_signatures = set()
            for ann_data in computed_annotations:
                sig = (ann_data['type'], ann_data['description'][:80])
                computed_signatures.add(sig)

            for existing_ann in existing_active:
                sig = (existing_ann.annotation_type, existing_ann.description[:80])
                if sig not in computed_signatures:
                    existing_ann.resolved_at = timezone.now()
                    existing_ann.resolved_by = 'system'
                    existing_ann.save(update_fields=['resolved_at', 'resolved_by', 'updated_at'])
                    resolved_annotations.append({
                        'id': str(existing_ann.id),
                        'type': existing_ann.annotation_type,
                        'section_heading': section.heading,
                    })

        # 5. Update locked state for synthesis/recommendation sections
        _update_locked_sections(brief, sections)

        # 6. Derive readiness checklist items from grounding gaps
        readiness_changes = _sync_readiness_from_grounding(case, sections)

        logger.info(
            f"Brief evolved for case {case.id}: "
            f"{len(updated_sections)} sections updated, "
            f"{len(new_annotations)} new annotations, "
            f"{len(resolved_annotations)} resolved, "
            f"{readiness_changes.get('created', 0)} readiness items created, "
            f"{readiness_changes.get('auto_completed', 0)} auto-completed"
        )

        return {
            'updated_sections': updated_sections,
            'new_annotations': new_annotations,
            'resolved_annotations': resolved_annotations,
            'sections_updated': len(updated_sections),
            'annotations_created': len(new_annotations),
            'annotations_resolved': len(resolved_annotations),
            'readiness_created': readiness_changes.get('created', 0),
            'readiness_auto_completed': readiness_changes.get('auto_completed', 0),
        }


def _update_locked_sections(brief, sections):
    """
    Update lock state for synthesis/recommendation sections.

    Recommendation unlocks when all inquiry sections are at least 'moderate'.
    Trade-offs/synthesis unlock when at least one inquiry section has evidence.
    """
    inquiry_sections = [s for s in sections if s.section_type == 'inquiry_brief']

    # Count inquiry grounding states
    all_moderate_or_better = all(
        s.grounding_status in (GroundingStatus.MODERATE, GroundingStatus.STRONG)
        for s in inquiry_sections
    ) if inquiry_sections else False

    any_has_evidence = any(
        s.grounding_data.get('evidence_count', 0) > 0
        for s in inquiry_sections
    )

    has_unresolved_tensions = any(
        s.grounding_status == GroundingStatus.CONFLICTED
        for s in inquiry_sections
    )

    for section in sections:
        if section.section_type == 'recommendation':
            if not inquiry_sections:
                section.is_locked = True
                section.lock_reason = 'Create inquiries to begin building toward a recommendation'
            elif has_unresolved_tensions:
                tension_count = sum(
                    1 for s in inquiry_sections
                    if s.grounding_status == GroundingStatus.CONFLICTED
                )
                section.is_locked = True
                section.lock_reason = f'Resolve {tension_count} tension(s) to unlock'
            elif not all_moderate_or_better:
                weak_count = sum(
                    1 for s in inquiry_sections
                    if s.grounding_status in (GroundingStatus.EMPTY, GroundingStatus.WEAK)
                )
                section.is_locked = True
                section.lock_reason = f'Strengthen {weak_count} inquiry section(s) to unlock'
            else:
                section.is_locked = False
                section.lock_reason = ''
            section.save(update_fields=['is_locked', 'lock_reason', 'updated_at'])

        elif section.section_type in ('synthesis', 'trade_offs'):
            if not any_has_evidence:
                section.is_locked = True
                section.lock_reason = 'Gather evidence in at least one inquiry to unlock'
            else:
                section.is_locked = False
                section.lock_reason = ''
            section.save(update_fields=['is_locked', 'lock_reason', 'updated_at'])


def _sync_readiness_from_grounding(case, sections) -> Dict[str, int]:
    """
    Derive readiness checklist items from brief section grounding gaps.

    Completes the three-way feedback loop:
      Knowledge Graph → Brief Grounding → Readiness Checklist

    Logic:
    1. For each linked section, derive checklist items from grounding gaps.
    2. Upsert: create new items if description doesn't already exist.
    3. Auto-complete items whose gaps have been resolved (e.g., evidence
       gathered, assumptions validated, tensions resolved).
    4. Mark auto-completed items with a completion_note explaining why.

    Returns:
        Dict with 'created' and 'auto_completed' counts.
    """
    from apps.cases.models import ReadinessChecklistItem

    created = 0
    auto_completed = 0

    # Get existing brief-derived checklist items (AI-generated ones linked to inquiries)
    existing_items = ReadinessChecklistItem.objects.filter(
        case=case,
        created_by_ai=True,
    ).select_related('linked_inquiry')

    # Build lookup: (item_type, linked_inquiry_id) → item
    existing_lookup = {}
    for item in existing_items:
        key = (item.item_type, str(item.linked_inquiry_id) if item.linked_inquiry_id else None)
        existing_lookup[key] = item

    # Track which items we derive this cycle (for auto-completion detection)
    derived_keys = set()

    # Calculate next order value
    max_order = ReadinessChecklistItem.objects.filter(case=case).aggregate(
        max_order=models.Max('order')
    )['max_order'] or 0

    for section in sections:
        # Only derive from linked sections with grounding data
        if not section.is_linked or not section.grounding_data:
            continue

        items_data = BriefGroundingEngine.derive_readiness_items(section)

        for item_data in items_data:
            inquiry_id_str = item_data.get('linked_inquiry_id')
            key = (item_data['item_type'], inquiry_id_str)
            derived_keys.add(key)

            # Check if this item already exists
            existing = existing_lookup.get(key)

            if existing:
                # Update description if it changed (grounding evolved)
                if existing.description != item_data['description']:
                    existing.description = item_data['description']
                    existing.why_important = item_data.get('why_important', '')
                    existing.save(update_fields=['description', 'why_important', 'updated_at'])
            else:
                # Create new checklist item
                max_order += 1
                ReadinessChecklistItem.objects.create(
                    case=case,
                    description=item_data['description'],
                    is_required=item_data.get('is_required', True),
                    why_important=item_data.get('why_important', ''),
                    item_type=item_data.get('item_type', 'custom'),
                    linked_inquiry_id=inquiry_id_str,
                    order=max_order,
                    created_by_ai=True,
                )
                created += 1

    # Auto-complete items whose gaps no longer exist
    # If an item was previously derived but is NOT in this cycle's derived set,
    # its gap has been resolved — auto-complete it.
    for key, item in existing_lookup.items():
        if key not in derived_keys and not item.is_complete:
            item.is_complete = True
            item.completed_at = timezone.now()
            item.completion_note = _auto_completion_reason(key[0])
            item.save(update_fields=[
                'is_complete', 'completed_at', 'completion_note', 'updated_at'
            ])
            auto_completed += 1

    return {'created': created, 'auto_completed': auto_completed}


def _auto_completion_reason(item_type: str) -> str:
    """Human-readable reason for auto-completing a readiness item."""
    reasons = {
        'investigation': 'Evidence has been gathered — gap resolved by brief grounding.',
        'validation': 'Assumption(s) now have supporting evidence.',
        'analysis': 'Tension(s) have been resolved.',
    }
    return reasons.get(item_type, 'Gap resolved — auto-completed by brief evolution.')
