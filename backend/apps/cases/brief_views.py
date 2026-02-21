"""
Brief-related viewset actions, extracted from CaseViewSet for maintainability.

Provides a mixin class with all brief-section endpoints:
  - generate_brief_outline
  - brief_sections (list/create)
  - brief_section_detail (update/delete)
  - brief_sections_reorder
  - brief_section_link_inquiry / unlink_inquiry
  - brief_section_dismiss_annotation
  - evolve_brief
  - brief_overview
  - section_judgment_summary
"""
import logging

from django.db import models, transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from .brief_models import BriefSection, BriefAnnotation
from .brief_serializers import (
    BriefSectionSerializer,
    BriefSectionCreateSerializer,
    BriefSectionUpdateSerializer,
    BriefSectionReorderSerializer,
    BriefOverviewSerializer,
)

logger = logging.getLogger(__name__)


class BriefActionsMixin:
    """Mixin providing brief-section actions for CaseViewSet."""

    @action(detail=True, methods=['post'], url_path='generate-brief-outline')
    def generate_brief_outline(self, request, pk=None):
        """
        Generate an AI-powered brief outline for a new case.

        POST /api/cases/{id}/generate-brief-outline/
        """
        case = self.get_object()

        outline = f"""# {case.title}

## Position
{case.position or '_Describe your current position or thesis_'}

## Stakes
This is a **{case.stakes}** stakes decision.

## Background
_Provide context about this decision_

## Key Questions
- _What are the main questions to resolve?_
- _What assumptions are critical?_
- _What evidence would change your mind?_

## Analysis
_Your research and thinking goes here_

## Decision Criteria
_What factors will determine the right choice?_

## Next Steps
_What actions follow from this decision?_
"""

        return Response({
            'outline': outline,
            'case_id': str(case.id)
        })

    @action(detail=True, methods=['get', 'post'], url_path='brief-sections')
    def brief_sections(self, request, pk=None):
        """
        List or create brief sections for this case's main brief.

        GET /api/cases/{id}/brief-sections/
        POST /api/cases/{id}/brief-sections/
        Body: {heading, section_type?, order?, parent_section?, inquiry?, after_section_id?}
        """
        case = self.get_object()

        if not case.main_brief:
            return Response(
                {'error': 'Case has no main brief document'},
                status=status.HTTP_404_NOT_FOUND
            )

        brief = case.main_brief

        if request.method == 'GET':
            sections = BriefSection.objects.filter(
                brief=brief,
                parent_section__isnull=True
            ).select_related(
                'inquiry'
            ).prefetch_related(
                'annotations',
                'subsections',
                'subsections__annotations',
                'subsections__inquiry',
            ).order_by('order')

            serializer = BriefSectionSerializer(sections, many=True)
            return Response({
                'sections': serializer.data,
                'brief_id': str(brief.id),
            })

        elif request.method == 'POST':
            serializer = BriefSectionCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            with transaction.atomic():
                if 'after_section_id' in data and data['after_section_id']:
                    try:
                        after_section = BriefSection.objects.select_for_update().get(
                            brief=brief, section_id=data['after_section_id']
                        )
                        order = after_section.order + 1
                        BriefSection.objects.filter(
                            brief=brief, order__gte=order
                        ).update(order=models.F('order') + 1)
                    except BriefSection.DoesNotExist:
                        order = data.get('order', 0)
                elif 'order' in data:
                    order = data['order']
                else:
                    max_order = BriefSection.objects.filter(
                        brief=brief
                    ).order_by('-order').values_list('order', flat=True).first() or 0
                    order = max_order + 1

            parent_section = None
            if data.get('parent_section'):
                try:
                    parent_section = BriefSection.objects.get(
                        id=data['parent_section'], brief=brief
                    )
                except BriefSection.DoesNotExist:
                    logger.debug("Parent section %s not found, skipping", data.get('parent_section'))

            inquiry = None
            if data.get('inquiry'):
                from apps.inquiries.models import Inquiry
                try:
                    inquiry = Inquiry.objects.get(id=data['inquiry'], case=case)
                except Inquiry.DoesNotExist:
                    return Response(
                        {'error': 'Inquiry not found in this case'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            section_id = BriefSection.generate_section_id()
            section = BriefSection.objects.create(
                brief=brief,
                section_id=section_id,
                heading=data['heading'],
                order=order,
                section_type=data.get('section_type', 'custom'),
                inquiry=inquiry,
                parent_section=parent_section,
                created_by='user',
                is_linked=bool(inquiry),
            )

            marker = f'\n<!-- section:{section_id} -->\n## {data["heading"]}\n\n'
            if brief.content_markdown:
                brief.content_markdown += marker
            else:
                brief.content_markdown = marker
            brief.save(update_fields=['content_markdown', 'updated_at'])

            from apps.events.services import EventService
            from apps.events.models import EventType, ActorType
            EventService.append(
                event_type=EventType.BRIEF_SECTION_WRITTEN,
                payload={
                    'section_id': str(section.id),
                    'section_title': section.heading,
                    'section_type': section.section_type,
                    'authored_by': 'user',
                },
                actor_type=ActorType.USER,
                actor_id=request.user.id,
                case_id=case.id,
            )

            return Response(
                BriefSectionSerializer(section).data,
                status=status.HTTP_201_CREATED
            )

    @action(detail=True, methods=['patch', 'delete'], url_path=r'brief-sections/(?P<section_id>[^/.]+)')
    def brief_section_detail(self, request, pk=None, section_id=None):
        """
        Update or delete a specific brief section.

        PATCH /api/cases/{id}/brief-sections/{section_id}/
        DELETE /api/cases/{id}/brief-sections/{section_id}/
        """
        case = self.get_object()
        if not case.main_brief:
            return Response(
                {'error': 'Case has no main brief document'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            section = BriefSection.objects.get(id=section_id, brief=case.main_brief)
        except BriefSection.DoesNotExist:
            return Response(
                {'error': 'Brief section not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.method == 'DELETE':
            marker_tag = f'<!-- section:{section.section_id} -->'
            if case.main_brief.content_markdown:
                case.main_brief.content_markdown = case.main_brief.content_markdown.replace(
                    marker_tag, ''
                )
                case.main_brief.save(update_fields=['content_markdown', 'updated_at'])
            section.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # PATCH
        serializer = BriefSectionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if 'heading' in data:
            old_heading = section.heading
            new_heading = data['heading']
            if case.main_brief.content_markdown and old_heading:
                case.main_brief.content_markdown = case.main_brief.content_markdown.replace(
                    f'## {old_heading}', f'## {new_heading}', 1
                )
                case.main_brief.save(update_fields=['content_markdown', 'updated_at'])
            section.heading = new_heading

        if 'order' in data:
            section.order = data['order']
        if 'section_type' in data:
            section.section_type = data['section_type']
        if 'is_collapsed' in data:
            section.is_collapsed = data['is_collapsed']

        if 'parent_section' in data:
            if data['parent_section']:
                try:
                    parent = BriefSection.objects.get(
                        id=data['parent_section'], brief=case.main_brief
                    )
                    section.parent_section = parent
                except BriefSection.DoesNotExist:
                    logger.debug("Parent section %s not found, skipping", data.get('parent_section'))
            else:
                section.parent_section = None

        if 'inquiry' in data:
            if data['inquiry']:
                from apps.inquiries.models import Inquiry
                try:
                    inquiry = Inquiry.objects.get(id=data['inquiry'], case=case)
                    section.inquiry = inquiry
                    section.is_linked = True
                except Inquiry.DoesNotExist:
                    return Response(
                        {'error': 'Inquiry not found in this case'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                section.inquiry = None
                section.is_linked = False

        content_changed = 'heading' in data or 'section_type' in data or 'inquiry' in data
        _section_update_fields = ['updated_at']
        for _f in ('heading', 'order', 'section_type', 'is_collapsed',
                    'parent_section', 'inquiry', 'is_linked'):
            if _f in data or _f == 'is_linked':
                _section_update_fields.append(_f)
        section.save(update_fields=_section_update_fields)

        if content_changed:
            from apps.events.services import EventService
            from apps.events.models import EventType, ActorType
            EventService.append(
                event_type=EventType.BRIEF_SECTION_REVISED,
                payload={
                    'section_id': str(section.id),
                    'section_title': section.heading,
                    'revised_by': 'user',
                },
                actor_type=ActorType.USER,
                actor_id=request.user.id,
                case_id=case.id,
            )

        return Response(BriefSectionSerializer(section).data)

    @action(detail=True, methods=['post'], url_path='brief-sections/reorder')
    def brief_sections_reorder(self, request, pk=None):
        """
        Bulk reorder brief sections.

        POST /api/cases/{id}/brief-sections/reorder/
        Body: {sections: [{id, order}, ...]}
        """
        case = self.get_object()
        if not case.main_brief:
            return Response(
                {'error': 'Case has no main brief document'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = BriefSectionReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for item in serializer.validated_data['sections']:
            BriefSection.objects.filter(
                id=item['id'], brief=case.main_brief
            ).update(order=item['order'])

        return Response({'status': 'reordered'})

    @action(detail=True, methods=['post'], url_path=r'brief-sections/(?P<section_id>[^/.]+)/link-inquiry')
    def brief_section_link_inquiry(self, request, pk=None, section_id=None):
        """
        Link a brief section to an inquiry.

        POST /api/cases/{id}/brief-sections/{section_id}/link-inquiry/
        Body: {inquiry_id: UUID}
        """
        case = self.get_object()
        if not case.main_brief:
            return Response(
                {'error': 'Case has no main brief document'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            section = BriefSection.objects.get(id=section_id, brief=case.main_brief)
        except BriefSection.DoesNotExist:
            return Response(
                {'error': 'Brief section not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        inquiry_id = request.data.get('inquiry_id')
        if not inquiry_id:
            return Response(
                {'error': 'inquiry_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from apps.inquiries.models import Inquiry
        try:
            inquiry = Inquiry.objects.get(id=inquiry_id, case=case)
        except Inquiry.DoesNotExist:
            return Response(
                {'error': 'Inquiry not found in this case'},
                status=status.HTTP_404_NOT_FOUND
            )

        section.inquiry = inquiry
        section.is_linked = True
        section.section_type = 'inquiry_brief'
        section.save(update_fields=['inquiry', 'is_linked', 'section_type', 'updated_at'])

        return Response(BriefSectionSerializer(section).data)

    @action(detail=True, methods=['post'], url_path=r'brief-sections/(?P<section_id>[^/.]+)/unlink-inquiry')
    def brief_section_unlink_inquiry(self, request, pk=None, section_id=None):
        """
        Unlink a brief section from its inquiry.

        POST /api/cases/{id}/brief-sections/{section_id}/unlink-inquiry/
        """
        case = self.get_object()
        if not case.main_brief:
            return Response(
                {'error': 'Case has no main brief document'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            section = BriefSection.objects.get(id=section_id, brief=case.main_brief)
        except BriefSection.DoesNotExist:
            return Response(
                {'error': 'Brief section not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        with transaction.atomic():
            section.inquiry = None
            section.is_linked = False
            section.grounding_status = 'empty'
            section.grounding_data = {}
            section.save(update_fields=[
                'inquiry', 'is_linked', 'grounding_status',
                'grounding_data', 'updated_at',
            ])
            section.annotations.filter(source_inquiry__isnull=False).delete()

        return Response(BriefSectionSerializer(section).data)

    @action(
        detail=True, methods=['post'],
        url_path=r'brief-sections/(?P<section_id>[^/.]+)/dismiss-annotation/(?P<annotation_id>[^/.]+)'
    )
    def brief_section_dismiss_annotation(self, request, pk=None, section_id=None, annotation_id=None):
        """
        Dismiss an annotation on a brief section.

        POST /api/cases/{id}/brief-sections/{section_id}/dismiss-annotation/{annotation_id}/
        """
        case = self.get_object()
        if not case.main_brief:
            return Response(
                {'error': 'Case has no main brief document'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            section = BriefSection.objects.get(id=section_id, brief=case.main_brief)
            annotation = section.annotations.get(id=annotation_id)
        except (BriefSection.DoesNotExist, BriefAnnotation.DoesNotExist):
            return Response(
                {'error': 'Section or annotation not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        annotation.dismissed_at = timezone.now()
        annotation.save(update_fields=['dismissed_at', 'updated_at'])

        return Response({'status': 'dismissed'})

    @action(detail=True, methods=['post'], url_path='evolve-brief')
    def evolve_brief(self, request, pk=None):
        """
        Trigger brief grounding recomputation.

        POST /api/cases/{id}/evolve-brief/
        """
        from django.core.cache import cache as django_cache

        case = self.get_object()
        if not case.main_brief:
            return Response(
                {'error': 'Case has no main brief document'},
                status=status.HTTP_404_NOT_FOUND
            )

        lock_key = f"evolve_brief_lock:{case.id}"
        if not django_cache.add(lock_key, True, timeout=120):
            return Response(
                {'status': 'already_evolving', 'message': 'Brief evolution already in progress'},
                status=status.HTTP_409_CONFLICT
            )

        try:
            from apps.cases.brief_grounding import BriefGroundingEngine
            delta = BriefGroundingEngine.evolve_brief(case.id)

            section_changes = []
            for s in delta.get('updated_sections', []):
                section_changes.append({
                    'id': s['id'],
                    'heading': s['heading'],
                    'old_status': s.get('old_status', ''),
                    'new_status': s.get('new_status', ''),
                })

            new_anns = []
            for a in delta.get('new_annotations', []):
                new_anns.append({
                    'id': a['id'],
                    'type': a['type'],
                    'section_heading': a.get('section_heading', ''),
                })

            resolved_anns = []
            for a in delta.get('resolved_annotations', []):
                resolved_anns.append({
                    'id': a['id'],
                    'type': a['type'],
                    'section_heading': a.get('section_heading', ''),
                })

            return Response({
                'status': 'evolved',
                'updated_sections': len(section_changes),
                'new_annotations': len(new_anns),
                'resolved_annotations': len(resolved_anns),
                'readiness_created': delta.get('readiness_created', 0),
                'readiness_auto_completed': delta.get('readiness_auto_completed', 0),
                'diff': {
                    'section_changes': section_changes,
                    'new_annotations': new_anns,
                    'resolved_annotations': resolved_anns,
                },
            })
        except Exception as e:
            logger.exception("Failed to evolve brief for case %s", case.id)
            return Response(
                {'error': 'Failed to evolve brief. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            django_cache.delete(lock_key)

    @action(detail=True, methods=['get'], url_path='brief-overview')
    def brief_overview(self, request, pk=None):
        """
        Get lightweight brief overview with grounding status.

        GET /api/cases/{id}/brief-overview/
        """
        case = self.get_object()
        if not case.main_brief:
            return Response(
                {'error': 'Case has no main brief document'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = BriefOverviewSerializer(case.main_brief)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='section-judgment-summary')
    def section_judgment_summary(self, request, pk=None):
        """
        Get synthesis summary comparing user judgment vs structural grounding.

        GET /api/cases/{id}/section-judgment-summary/
        """
        from apps.cases.brief_models import BriefSection as BriefSectionModel

        case = self.get_object()
        if not case.main_brief:
            return Response({'sections': [], 'mismatches': []})

        sections = BriefSectionModel.objects.filter(
            brief=case.main_brief,
        ).exclude(section_type='decision_frame').order_by('order')

        grounding_strength = {
            'empty': 0,
            'weak': 1,
            'moderate': 2,
            'strong': 3,
            'conflicted': 1,
        }

        results = []
        mismatches = []

        for section in sections:
            structural_strength = grounding_strength.get(section.grounding_status, 0)
            user_rating = section.user_confidence

            section_data = {
                'section_id': section.section_id,
                'heading': section.heading,
                'section_type': section.section_type,
                'grounding_status': section.grounding_status,
                'grounding_strength': structural_strength,
                'user_confidence': user_rating,
                'evidence_count': section.grounding_data.get('evidence_count', 0),
                'tensions_count': section.grounding_data.get('tensions_count', 0),
            }
            results.append(section_data)

            if user_rating is not None:
                if user_rating >= 3 and structural_strength <= 1:
                    mismatches.append({
                        'section_id': section.section_id,
                        'heading': section.heading,
                        'type': 'overconfident',
                        'description': f'You rated high confidence but evidence is {section.grounding_status}',
                        'user_confidence': user_rating,
                        'grounding_status': section.grounding_status,
                    })
                elif user_rating <= 2 and structural_strength >= 3:
                    mismatches.append({
                        'section_id': section.section_id,
                        'heading': section.heading,
                        'type': 'underconfident',
                        'description': 'You rated low confidence but evidence is strong',
                        'user_confidence': user_rating,
                        'grounding_status': section.grounding_status,
                    })

        return Response({
            'sections': results,
            'mismatches': mismatches,
            'rated_count': sum(1 for s in results if s['user_confidence'] is not None),
            'total_count': len(results),
        })
