"""
Brief grounding engine.

Computes grounding status and annotations for brief sections by following
the section → inquiry → signals → evidence chain. Uses GraphAnalyzer
for pattern detection.
"""
import logging
from typing import Dict, List, Any

from django.db import transaction
from django.utils import timezone

from apps.cases.brief_models import (
    BriefSection, BriefAnnotation,
    GroundingStatus, AnnotationType, AnnotationPriority,
)

logger = logging.getLogger(__name__)


class BriefGroundingEngine:
    """
    Computes grounding status and annotations for brief sections.

    Grounding flows from the knowledge graph:
    - BriefSection → Inquiry → Signals + Evidence

    Annotations are generated from graph analysis:
    - Tensions from contradicting signals
    - Blind spots from evidence deserts
    - Ungrounded from orphaned assumptions
    - Well-grounded from strong evidence
    """

    @staticmethod
    def compute_section_grounding(section: BriefSection, evidence_threshold: str = 'medium') -> Dict[str, Any]:
        """
        Compute grounding status for a single section.

        For inquiry_brief sections: follows section → inquiry → signals + evidence.
        For unlinked sections: returns empty grounding.

        Args:
            section: The BriefSection to compute grounding for.
            evidence_threshold: 'low', 'medium', or 'high' — controls STRONG/MODERATE thresholds.

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
            return BriefGroundingEngine._compute_from_inquiry(section.inquiry, result, evidence_threshold)
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
    def _compute_from_inquiry(inquiry, result: Dict, evidence_threshold: str = 'medium') -> Dict:
        """Compute grounding from graph evidence nodes and signals."""
        # Count evidence by direction from graph Node(type=EVIDENCE) + Edges
        try:
            from apps.graph.models import Node, Edge, EdgeType
            from apps.graph.services import GraphService
            case = inquiry.case
            if case and case.project:
                visible_ids = GraphService._get_case_visible_nodes(case.id)
                evidence_nodes = Node.objects.filter(
                    id__in=visible_ids,
                    node_type='evidence',
                )
                result['evidence_count'] = evidence_nodes.count()
                result['supporting'] = Edge.objects.filter(
                    source_node__in=evidence_nodes,
                    edge_type=EdgeType.SUPPORTS,
                ).count()
                result['contradicting'] = Edge.objects.filter(
                    source_node__in=evidence_nodes,
                    edge_type=EdgeType.CONTRADICTS,
                ).count()
                result['neutral'] = max(
                    0,
                    result['evidence_count'] - result['supporting'] - result['contradicting'],
                )

                # Average confidence from evidence nodes
                if result['evidence_count'] > 0:
                    confidences = list(
                        evidence_nodes.filter(confidence__isnull=False)
                        .values_list('confidence', flat=True)
                    )
                    if confidences:
                        result['confidence_avg'] = round(
                            sum(confidences) / len(confidences), 2
                        )
        except Exception:
            pass

        # Count unvalidated assumptions from the graph layer
        # Scoped to case-visible nodes (case-owned + referenced project nodes)
        try:
            from apps.graph.models import Node
            from apps.graph.services import GraphService
            case = inquiry.case
            if case and case.project:
                visible_ids = GraphService._get_case_visible_nodes(case.id)
                assumption_nodes = Node.objects.filter(
                    id__in=visible_ids,
                    node_type='assumption',
                ).exclude(status__in=['confirmed', 'refuted'])
                result['unvalidated_assumptions'] = assumption_nodes.count()
        except Exception:
            pass

        # Count tensions from the graph layer
        # Scoped to case-visible nodes
        try:
            from apps.graph.models import Node
            from apps.graph.services import GraphService
            case = inquiry.case
            if case and case.project:
                visible_ids = GraphService._get_case_visible_nodes(case.id)
                tension_nodes = Node.objects.filter(
                    id__in=visible_ids,
                    node_type='tension',
                )
                result['tensions_count'] = tension_nodes.count()
        except Exception:
            pass

        # Determine status
        result['status'] = BriefGroundingEngine._determine_status(result, evidence_threshold)
        return result

    # Evidence threshold presets: {strong_min, moderate_min, strong_requires_no_unvalidated}
    EVIDENCE_THRESHOLDS = {
        'low': {'strong_min': 1, 'moderate_min': 1, 'strong_requires_no_unvalidated': False},
        'medium': {'strong_min': 3, 'moderate_min': 1, 'strong_requires_no_unvalidated': True},
        'high': {'strong_min': 5, 'moderate_min': 2, 'strong_requires_no_unvalidated': True},
    }

    @staticmethod
    def _determine_status(data: Dict, evidence_threshold: str = 'medium') -> str:
        """Determine GroundingStatus from computed data.

        Args:
            data: Computed grounding data dict.
            evidence_threshold: 'low', 'medium', or 'high' — controls how
                much evidence is required for STRONG / MODERATE.
        """
        evidence = data['evidence_count']
        tensions = data['tensions_count']
        unvalidated = data['unvalidated_assumptions']

        if evidence == 0 and unvalidated == 0:
            return GroundingStatus.EMPTY

        if tensions > 0:
            return GroundingStatus.CONFLICTED

        if evidence == 0 and unvalidated > 0:
            return GroundingStatus.WEAK

        thresholds = BriefGroundingEngine.EVIDENCE_THRESHOLDS.get(
            evidence_threshold,
            BriefGroundingEngine.EVIDENCE_THRESHOLDS['medium'],
        )

        strong_ok = evidence >= thresholds['strong_min']
        if thresholds['strong_requires_no_unvalidated']:
            strong_ok = strong_ok and unvalidated == 0

        if strong_ok:
            return GroundingStatus.STRONG

        if evidence >= thresholds['moderate_min']:
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

        if not section.inquiry:
            return annotations

        inquiry = section.inquiry

        if inquiry:
            # Use inquiry-scoped graph analysis for richer pattern detection
            try:
                from apps.graph.analyzer import GraphAnalyzer
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
        Tensions, assumptions, and claims are now handled by the graph layer.
        """
        annotations = []

        # Evidence desert — count from graph evidence nodes
        try:
            from apps.graph.models import Node
            from apps.graph.services import GraphService
            case = inquiry.case
            visible_ids = GraphService._get_case_visible_nodes(case.id) if case else []
            evidence_count = Node.objects.filter(
                id__in=visible_ids,
                node_type='evidence',
            ).count() if visible_ids else 0
        except Exception:
            evidence_count = 0
        if evidence_count < 2 and inquiry.status in ['open', 'investigating']:
            annotations.append({
                'type': AnnotationType.EVIDENCE_DESERT,
                'description': f'Only {evidence_count} evidence item(s). Consider gathering more evidence.',
                'priority': AnnotationPriority.IMPORTANT,
                'signal_ids': [],
                'inquiry_id': inquiry.id,
            })

        # Tensions and assumptions now come from graph nodes, handled by
        # GraphAnalyzer._annotations_from_patterns (primary path).

        return annotations

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
        sections = BriefSection.objects.filter(brief=brief).select_related('inquiry').prefetch_related(
            'annotations',
        )

        # Read per-case investigation preferences
        prefs = getattr(case, 'investigation_preferences', None) or {}
        evidence_threshold = prefs.get('evidence_threshold', 'medium')

        updated_sections = []
        new_annotations = []
        resolved_annotations = []

        for section in sections:
            # 1. Recompute grounding
            grounding = cls.compute_section_grounding(section, evidence_threshold)
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

        logger.info(
            f"Brief evolved for case {case.id}: "
            f"{len(updated_sections)} sections updated, "
            f"{len(new_annotations)} new annotations, "
            f"{len(resolved_annotations)} resolved"
        )

        return {
            'updated_sections': updated_sections,
            'new_annotations': new_annotations,
            'resolved_annotations': resolved_annotations,
            'sections_updated': len(updated_sections),
            'annotations_created': len(new_annotations),
            'annotations_resolved': len(resolved_annotations),
        }


def _update_locked_sections(brief, sections):
    """
    Update lock state for synthesis/recommendation sections.

    Recommendation unlocks when all inquiry sections are at least 'moderate'.
    Trade-offs/synthesis unlock when at least one inquiry section has evidence.

    If the case's investigation_preferences has disable_locks=True, all
    synthesis/recommendation sections are immediately unlocked.
    """
    # Check for per-case lock override
    case = brief.case
    prefs = getattr(case, 'investigation_preferences', None) or {}
    if prefs.get('disable_locks'):
        for section in sections:
            if section.section_type in ('recommendation', 'synthesis', 'trade_offs'):
                if section.is_locked:
                    section.is_locked = False
                    section.lock_reason = ''
                    section.save(update_fields=['is_locked', 'lock_reason', 'updated_at'])
        return

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


