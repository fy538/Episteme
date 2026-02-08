"""
Brief Export Service — Assembles the BriefExportGraph intermediate representation.

Traverses: Case → Brief → Sections → Inquiries → Evidence/Signals
Packages the full reasoning chain into a structured JSON IR suitable
for rendering into slides, memos, reports, or any other output format.

The key insight: every claim has a provenance chain (evidence → source),
every recommendation depends on explicit assumptions, and every gap is
surfaced. This is what makes Episteme-powered output categorically better
than generic AI document generation.
"""
import logging
import re
import uuid
from typing import Optional

from django.utils import timezone

from apps.cases.models import Case
from apps.cases.brief_models import (
    BriefSection, GroundingStatus, AnnotationType,
)
from apps.signals.models import SignalType

logger = logging.getLogger(__name__)

# Grounding status → numeric score for aggregation
GROUNDING_SCORES = {
    GroundingStatus.EMPTY: 0,
    GroundingStatus.WEAK: 25,
    GroundingStatus.MODERATE: 50,
    GroundingStatus.STRONG: 100,
    GroundingStatus.CONFLICTED: 30,
    # Handle raw string values too
    'empty': 0,
    'weak': 25,
    'moderate': 50,
    'strong': 100,
    'conflicted': 30,
}


class BriefExportService:
    """
    Assembles the BriefExportGraph intermediate representation.

    The IR captures the full reasoning chain per section:
    - Claims with evidence provenance
    - Assumptions with validation status
    - Tensions and contradictions
    - Evidence quality metrics
    - Annotations and objections

    Supports three export types:
    - full: Complete IR with all details
    - executive_summary: Top claims only, no full evidence items
    - per_section: Specific sections only
    """

    EXPORT_VERSION = "1.0"

    @classmethod
    def export(
        cls,
        case_id: uuid.UUID,
        export_type: str = 'full',
        section_ids: Optional[list[str]] = None,
        user=None,
    ) -> dict:
        """
        Build the complete export IR for a case.

        Args:
            case_id: UUID of the case to export
            export_type: 'full', 'executive_summary', or 'per_section'
            section_ids: For per_section type, list of section_id strings to include
            user: User requesting the export (ownership check)

        Returns:
            Complete BriefExportGraph as a dict

        Raises:
            ValueError: If case has no main brief
            Case.DoesNotExist: If case not found or not owned by user
        """
        filters = {'id': case_id}
        if user is not None:
            filters['user'] = user
        case = Case.objects.select_related(
            'main_brief', 'project'
        ).prefetch_related(
            'active_skills'
        ).get(**filters)

        brief = case.main_brief
        if not brief:
            raise ValueError(f"Case {case_id} has no main brief")

        # Build each piece
        case_data = cls._build_case_data(case)
        sections_data = cls._build_sections(brief, export_type, section_ids)
        brief_health = cls._build_brief_health(sections_data)
        global_patterns = cls._compute_global_patterns(sections_data)
        generation_hints = cls._build_generation_hints(case, sections_data, global_patterns)

        return {
            'version': cls.EXPORT_VERSION,
            'export_type': export_type,
            'generated_at': timezone.now().isoformat(),
            'case': case_data,
            'brief_health': brief_health,
            'sections': sections_data,
            'global_patterns': global_patterns,
            'generation_hints': generation_hints,
        }

    # ─── Case Data ────────────────────────────────────────────────────

    @staticmethod
    def _build_case_data(case: Case) -> dict:
        """Serialize case-level fields."""
        skill_names = list(
            case.active_skills.filter(status='active').values_list('name', flat=True)
        )
        return {
            'id': str(case.id),
            'title': case.title,
            'decision_question': case.decision_question or '',
            'position': case.position or '',
            'stakes': case.stakes or 'medium',
            'user_confidence': case.user_confidence,
            'constraints': case.constraints or [],
            'success_criteria': case.success_criteria or [],
            'stakeholders': case.stakeholders or [],
            'premortem_text': getattr(case, 'premortem_text', '') or '',
            'what_would_change_mind': getattr(case, 'what_would_change_mind', '') or '',
            'skills_used': skill_names,
        }

    # ─── Brief Health ─────────────────────────────────────────────────

    @staticmethod
    def _build_brief_health(sections_data: list[dict]) -> dict:
        """Compute overall brief health from section data."""
        status_counts = {
            'strong': 0, 'moderate': 0, 'weak': 0, 'empty': 0, 'conflicted': 0,
        }
        total_score = 0
        scorable_sections = 0

        for section in sections_data:
            gs = section.get('grounding_status', 'empty')
            if gs in status_counts:
                status_counts[gs] += 1
            score = GROUNDING_SCORES.get(gs, 0)
            total_score += score
            scorable_sections += 1

        overall_score = round(total_score / scorable_sections) if scorable_sections else 0

        return {
            'overall_grounding_score': overall_score,
            'total_sections': len(sections_data),
            'grounding_status_counts': status_counts,
        }

    # ─── Sections ─────────────────────────────────────────────────────

    @classmethod
    def _build_sections(
        cls,
        brief,
        export_type: str,
        section_ids: Optional[list[str]],
    ) -> list[dict]:
        """Build section data for all relevant sections."""
        # Prefetch everything in one queryset
        qs = BriefSection.objects.filter(
            brief=brief,
            parent_section__isnull=True,
        ).select_related(
            'inquiry',
        ).prefetch_related(
            'annotations',
            'annotations__source_signals',
            'inquiry__evidence_items',
            'inquiry__evidence_items__source_document',
            'inquiry__related_signals',
            'inquiry__related_signals__supported_by_evidence',
            'inquiry__related_signals__contradicted_by_evidence',
            'inquiry__related_signals__contradicts',
            'inquiry__related_signals__depends_on',
            'inquiry__objections',
            'tagged_signals',
            'tagged_signals__supported_by_evidence',
            'tagged_signals__contradicted_by_evidence',
            'subsections',
        ).order_by('order')

        if section_ids:
            qs = qs.filter(section_id__in=section_ids)

        # Get the brief markdown for content extraction
        brief_markdown = brief.content_markdown or ''

        sections = []
        for section in qs:
            section_data = cls._build_section_data(
                section, brief_markdown, export_type
            )
            sections.append(section_data)

        return sections

    @classmethod
    def _build_section_data(
        cls,
        section: BriefSection,
        brief_markdown: str,
        export_type: str,
    ) -> dict:
        """Build data for a single section including its reasoning chain."""
        # Extract content from markdown
        content = cls._extract_section_content(section.section_id, brief_markdown)

        # Build reasoning chain
        reasoning_chain = cls._build_reasoning_chain(section, export_type)

        # Active annotations
        annotations = [
            {
                'type': ann.annotation_type,
                'description': ann.description,
                'priority': ann.priority,
            }
            for ann in section.annotations.all()
            if ann.is_active
        ]

        # Objections (from inquiry if linked)
        objections = []
        if section.inquiry:
            for obj in section.inquiry.objections.filter(status='active'):
                objections.append({
                    'text': obj.objection_text,
                    'type': obj.objection_type,
                    'status': obj.status,
                })

        return {
            'id': str(section.id),
            'section_id': section.section_id,
            'heading': section.heading,
            'section_type': section.section_type,
            'order': section.order,
            'grounding_status': section.grounding_status,
            'user_confidence': section.user_confidence,
            'content_markdown': content,
            'reasoning_chain': reasoning_chain,
            'annotations': annotations,
            'objections': objections,
        }

    @staticmethod
    def _extract_section_content(section_id: str, markdown: str) -> str:
        """
        Extract the markdown content for a section between its marker
        and the next section marker (or end of document).
        """
        marker = f'<!-- section:{section_id} -->'
        start_idx = markdown.find(marker)
        if start_idx == -1:
            return ''

        # Start after the marker line
        content_start = markdown.find('\n', start_idx)
        if content_start == -1:
            return ''
        content_start += 1

        # Find next section marker or end
        next_marker = re.search(r'<!-- section:\S+ -->', markdown[content_start:])
        if next_marker:
            content = markdown[content_start:content_start + next_marker.start()]
        else:
            content = markdown[content_start:]

        return content.strip()

    # ─── Reasoning Chain ──────────────────────────────────────────────

    @classmethod
    def _build_reasoning_chain(cls, section: BriefSection, export_type: str) -> dict:
        """Build the reasoning chain for a section from its linked signals and evidence."""
        claims = []
        assumptions = []
        tensions = []
        evidence_quality = {
            'total': 0,
            'high_confidence': 0,
            'low_confidence': 0,
            'supporting': 0,
            'contradicting': 0,
            'neutral': 0,
        }

        # Get signals — from inquiry or tagged_signals
        signals = []
        if section.inquiry:
            signals = list(section.inquiry.related_signals.filter(dismissed_at__isnull=True))

            # Build evidence quality from inquiry evidence items
            for ev in section.inquiry.evidence_items.all():
                evidence_quality['total'] += 1
                if ev.direction == 'supports':
                    evidence_quality['supporting'] += 1
                elif ev.direction == 'contradicts':
                    evidence_quality['contradicting'] += 1
                else:
                    evidence_quality['neutral'] += 1

                strength = ev.strength or 0
                if strength >= 0.7:
                    evidence_quality['high_confidence'] += 1
                elif strength > 0:
                    evidence_quality['low_confidence'] += 1

        elif section.tagged_signals.exists():
            signals = list(section.tagged_signals.filter(dismissed_at__isnull=True))

        # Use cached grounding_data if available (for evidence quality fallback)
        if evidence_quality['total'] == 0 and section.grounding_data:
            gd = section.grounding_data
            evidence_quality['total'] = gd.get('evidence_count', 0)
            evidence_quality['supporting'] = gd.get('supporting', 0)
            evidence_quality['contradicting'] = gd.get('contradicting', 0)
            evidence_quality['neutral'] = gd.get('neutral', 0)

        # Categorize signals
        seen_tension_pairs = set()

        for signal in signals:
            if signal.type == SignalType.ASSUMPTION:
                assumptions.append(cls._build_assumption(signal))
            elif signal.type in (SignalType.CLAIM, SignalType.EVIDENCE_MENTION):
                claim = cls._build_claim(signal, section, export_type)
                claims.append(claim)

            # Detect tensions (contradicting pairs)
            for contra in signal.contradicts.filter(dismissed_at__isnull=True):
                pair = tuple(sorted([str(signal.id), str(contra.id)]))
                if pair not in seen_tension_pairs:
                    seen_tension_pairs.add(pair)
                    both_high = (
                        (signal.confidence or 0) >= 0.7 and
                        (contra.confidence or 0) >= 0.7
                    )
                    tensions.append({
                        'description': f'"{signal.text[:60]}..." vs "{contra.text[:60]}..."',
                        'signal_a': {'id': str(signal.id), 'text': signal.text},
                        'signal_b': {'id': str(contra.id), 'text': contra.text},
                        'both_high_confidence': both_high,
                        'priority': 'blocking' if both_high else 'important',
                    })

        # For executive_summary, limit to top 3 claims by confidence
        if export_type == 'executive_summary' and len(claims) > 3:
            claims.sort(key=lambda c: c.get('confidence', 0), reverse=True)
            claims = claims[:3]

        return {
            'claims': claims,
            'assumptions': assumptions,
            'tensions': tensions,
            'evidence_quality': evidence_quality,
        }

    @classmethod
    def _build_claim(cls, signal, section: BriefSection, export_type: str) -> dict:
        """Build a claim entry with evidence support."""
        supporting = list(signal.supported_by_evidence.all())
        contradicting = list(signal.contradicted_by_evidence.all())

        # Determine claim status
        if len(supporting) >= 2 and len(contradicting) == 0:
            claim_status = 'well_grounded'
        elif len(contradicting) > 0:
            claim_status = 'contested'
        elif len(supporting) == 0:
            claim_status = 'ungrounded'
        else:
            claim_status = 'well_grounded' if len(supporting) >= 1 else 'ungrounded'

        evidence_items = []

        # Only include full evidence in non-executive exports
        if export_type != 'executive_summary':
            # Also pull inquiry-level evidence if available
            if section.inquiry:
                for ev in section.inquiry.evidence_items.all():
                    source_info = {}
                    if ev.source_document:
                        source_info = {
                            'document_id': str(ev.source_document.id),
                            'document_title': ev.source_document.title,
                        }
                    evidence_items.append({
                        'id': str(ev.id),
                        'text': ev.evidence_text or '',
                        'direction': ev.direction,
                        'strength': ev.strength,
                        'credibility': ev.credibility,
                        'source': source_info,
                    })

        return {
            'id': str(signal.id),
            'text': signal.text,
            'type': signal.type,
            'confidence': signal.confidence,
            'evidence_support': {
                'supporting_count': len(supporting),
                'contradicting_count': len(contradicting),
                'evidence_items': evidence_items,
            },
            'status': claim_status,
        }

    @staticmethod
    def _build_assumption(signal) -> dict:
        """Build an assumption entry."""
        has_evidence = signal.supported_by_evidence.exists()
        depends_on_ids = [str(s.id) for s in signal.depends_on.all()]
        contradicted_by_ids = [str(s.id) for s in signal.contradicts.filter(dismissed_at__isnull=True)]

        return {
            'id': str(signal.id),
            'text': signal.text,
            'confidence': signal.confidence,
            'assumption_status': getattr(signal, 'assumption_status', 'untested') or 'untested',
            'has_evidence': has_evidence,
            'depends_on': depends_on_ids,
            'contradicted_by': contradicted_by_ids,
        }

    # ─── Global Patterns ──────────────────────────────────────────────

    @staticmethod
    def _compute_global_patterns(sections_data: list[dict]) -> dict:
        """Aggregate patterns across all sections."""
        ungrounded_assumptions = 0
        unresolved_tensions = 0
        well_grounded_claims = 0
        evidence_total = 0
        strongest_section = None
        weakest_section = None
        best_score = -1
        worst_score = 101

        for section in sections_data:
            rc = section.get('reasoning_chain', {})

            # Count assumptions without evidence
            for assumption in rc.get('assumptions', []):
                if not assumption.get('has_evidence'):
                    ungrounded_assumptions += 1

            # Count unresolved tensions
            unresolved_tensions += len(rc.get('tensions', []))

            # Count well-grounded claims
            for claim in rc.get('claims', []):
                if claim.get('status') == 'well_grounded':
                    well_grounded_claims += 1

            # Sum evidence
            eq = rc.get('evidence_quality', {})
            evidence_total += eq.get('total', 0)

            # Track strongest/weakest
            gs = section.get('grounding_status', 'empty')
            score = GROUNDING_SCORES.get(gs, 0)
            heading = section.get('heading', '')

            if score > best_score:
                best_score = score
                strongest_section = heading
            if score < worst_score:
                worst_score = score
                weakest_section = heading

        return {
            'ungrounded_assumption_count': ungrounded_assumptions,
            'unresolved_tension_count': unresolved_tensions,
            'well_grounded_claim_count': well_grounded_claims,
            'evidence_total': evidence_total,
            'strongest_section': strongest_section,
            'weakest_section': weakest_section,
        }

    # ─── Generation Hints ─────────────────────────────────────────────

    @classmethod
    def _build_generation_hints(
        cls,
        case: Case,
        sections_data: list[dict],
        global_patterns: dict,
    ) -> dict:
        """
        Derive hints for future slide/document generation.

        These hints tell an LLM what to emphasize, what to caveat,
        and how to structure the output.
        """
        # Key takeaways: strong claims from recommendation section, or top claims overall
        key_takeaways = []
        for section in sections_data:
            if section.get('section_type') == 'recommendation':
                for claim in section.get('reasoning_chain', {}).get('claims', []):
                    if claim.get('status') == 'well_grounded':
                        key_takeaways.append(claim['text'][:200])

        # If no recommendation claims, use top claims from any section
        if not key_takeaways:
            all_claims = []
            for section in sections_data:
                for claim in section.get('reasoning_chain', {}).get('claims', []):
                    if claim.get('status') == 'well_grounded':
                        all_claims.append((claim.get('confidence', 0), claim['text'][:200]))
            all_claims.sort(reverse=True)
            key_takeaways = [text for _, text in all_claims[:5]]

        # Infer narrative arc from section types
        section_types = [s.get('section_type') for s in sections_data]
        if 'recommendation' in section_types:
            narrative_arc = 'recommendation'
        elif 'trade_offs' in section_types:
            narrative_arc = 'comparison'
        else:
            narrative_arc = 'problem_solution'

        # Estimate slides: 1 title + 1 per section + 1 summary
        estimated_slides = 2 + len(sections_data)

        return {
            'suggested_title': case.title,
            'key_takeaways': key_takeaways,
            'narrative_arc': narrative_arc,
            'audience_level': 'executive',
            'estimated_slides': estimated_slides,
        }
