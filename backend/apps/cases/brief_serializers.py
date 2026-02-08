"""
Serializers for BriefSection and BriefAnnotation models.
"""
import logging
import re

from django.db.models import Count
from rest_framework import serializers

logger = logging.getLogger(__name__)

from apps.cases.brief_models import (
    BriefSection,
    BriefAnnotation,
    SectionType,
    GroundingStatus,
    SectionCreator,
    AnnotationType,
    AnnotationPriority,
)


class BriefAnnotationSerializer(serializers.ModelSerializer):
    """Read-only serializer for annotations."""
    source_signal_ids = serializers.SerializerMethodField()

    class Meta:
        model = BriefAnnotation
        fields = [
            'id',
            'annotation_type',
            'description',
            'priority',
            'source_signal_ids',
            'source_inquiry',
            'created_at',
            'dismissed_at',
            'resolved_at',
            'resolved_by',
        ]
        read_only_fields = fields

    def get_source_signal_ids(self, obj):
        return [str(s.id) for s in obj.source_signals.all()]


class BriefSectionSerializer(serializers.ModelSerializer):
    """
    Full section serializer with nested annotations.

    Annotations are filtered to active-only by default
    (not dismissed, not resolved).
    """
    annotations = serializers.SerializerMethodField()
    subsections = serializers.SerializerMethodField()
    inquiry_title = serializers.SerializerMethodField()
    content_preview = serializers.SerializerMethodField()

    class Meta:
        model = BriefSection
        fields = [
            'id',
            'section_id',
            'heading',
            'order',
            'section_type',
            'inquiry',
            'inquiry_title',
            'parent_section',
            'depth',
            'created_by',
            'is_linked',
            'grounding_status',
            'grounding_data',
            'user_confidence',
            'user_confidence_at',
            'is_locked',
            'lock_reason',
            'is_collapsed',
            'annotations',
            'subsections',
            'content_preview',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'section_id', 'is_linked', 'grounding_status',
            'grounding_data', 'created_at', 'updated_at',
        ]

    def get_annotations(self, obj):
        """Return only active annotations (not dismissed/resolved).

        Filters in Python from prefetched queryset to avoid N+1 queries.
        If annotations were not prefetched, falls back to a DB filter.
        """
        # Use prefetched cache if available (avoids N+1)
        if 'annotations' in obj._prefetched_objects_cache:
            active = [
                a for a in obj.annotations.all()
                if a.dismissed_at is None and a.resolved_at is None
            ]
            return BriefAnnotationSerializer(active, many=True).data
        # Fallback for non-prefetched contexts (e.g., single section responses)
        active_annotations = obj.annotations.filter(
            dismissed_at__isnull=True,
            resolved_at__isnull=True
        )
        return BriefAnnotationSerializer(active_annotations, many=True).data

    def get_subsections(self, obj):
        """Return nested subsections.

        Uses prefetched cache when available to avoid N+1 queries.
        """
        # Use prefetched cache if available
        children = list(obj.subsections.all())
        children.sort(key=lambda s: s.order)
        if not children:
            return []
        return BriefSectionSerializer(children, many=True, context=self.context).data

    def get_inquiry_title(self, obj):
        """Denormalized inquiry title for display."""
        if obj.inquiry:
            return obj.inquiry.title
        return None

    def get_content_preview(self, obj):
        """
        Extract 1-2 lines of prose from the brief markdown for this section.

        Looks for content between <!-- section:SECTION_ID --> and the next
        section marker or end of document. Strips markdown formatting and
        returns the first ~200 characters of prose.
        """
        try:
            brief = obj.brief
            if not brief or not brief.content_markdown:
                return None

            markdown = brief.content_markdown
            section_marker = f'<!-- section:{obj.section_id} -->'
            marker_pos = markdown.find(section_marker)
            if marker_pos == -1:
                logger.warning(
                    'Section %s (%s) marker not found in brief %s content',
                    obj.section_id, obj.heading, brief.id,
                )
                return None

            # Start after the marker
            content_start = marker_pos + len(section_marker)

            # Find the next section marker or end of document
            next_marker = re.search(
                r'<!-- section:[a-zA-Z0-9_-]+ -->',
                markdown[content_start:]
            )
            if next_marker:
                content_end = content_start + next_marker.start()
            else:
                content_end = len(markdown)

            raw_content = markdown[content_start:content_end].strip()
            if not raw_content:
                return None

            # Strip markdown formatting for preview
            # Remove headings
            preview = re.sub(r'^#{1,6}\s+.*$', '', raw_content, flags=re.MULTILINE)
            # Remove bold/italic markers
            preview = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', preview)
            # Remove links, keep text
            preview = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', preview)
            # Remove HTML comments
            preview = re.sub(r'<!--.*?-->', '', preview, flags=re.DOTALL)
            # Collapse whitespace
            preview = re.sub(r'\n{2,}', '\n', preview).strip()
            # Take first ~200 chars, break at word boundary
            if len(preview) > 200:
                preview = preview[:200].rsplit(' ', 1)[0] + '...'

            return preview if preview else None
        except Exception:
            return None


class BriefSectionCreateSerializer(serializers.Serializer):
    """Serializer for creating a new brief section."""
    heading = serializers.CharField(max_length=500)
    section_type = serializers.ChoiceField(
        choices=SectionType.choices,
        default=SectionType.CUSTOM
    )
    order = serializers.IntegerField(required=False)
    parent_section = serializers.UUIDField(required=False, allow_null=True)
    inquiry = serializers.UUIDField(required=False, allow_null=True)
    after_section_id = serializers.CharField(
        required=False,
        help_text='Insert after this section (by section_id). Adjusts order automatically.'
    )


class BriefSectionUpdateSerializer(serializers.Serializer):
    """Serializer for updating a brief section."""
    heading = serializers.CharField(max_length=500, required=False)
    order = serializers.IntegerField(required=False)
    section_type = serializers.ChoiceField(
        choices=SectionType.choices,
        required=False
    )
    inquiry = serializers.UUIDField(required=False, allow_null=True)
    parent_section = serializers.UUIDField(required=False, allow_null=True)
    is_collapsed = serializers.BooleanField(required=False)


class BriefSectionReorderSerializer(serializers.Serializer):
    """Serializer for bulk reordering sections."""
    sections = serializers.ListField(
        child=serializers.DictField(),
        help_text='List of {id: UUID, order: int}'
    )

    def validate_sections(self, value):
        for item in value:
            if 'id' not in item or 'order' not in item:
                raise serializers.ValidationError(
                    "Each item must have 'id' and 'order' fields"
                )
        return value


class BriefOverviewSerializer(serializers.Serializer):
    """
    Lightweight brief overview — sections with grounding status
    and annotation counts only. Used for dashboard/summary views.

    Optimized to use prefetch_related + annotate to avoid N+1 queries.
    Previous implementation: ~5 queries per section (annotations filter,
    3 priority counts, subsection count). Now: 3 queries total.
    """
    sections = serializers.SerializerMethodField()
    overall_grounding = serializers.SerializerMethodField()

    def _get_top_level_sections(self, brief):
        """Fetch top-level sections with prefetched annotations and annotated counts.

        Caches result on self to avoid duplicate queries between
        get_sections() and get_overall_grounding().
        """
        if not hasattr(self, '_cached_sections'):
            self._cached_sections = list(
                BriefSection.objects.filter(
                    brief=brief,
                    parent_section__isnull=True
                ).prefetch_related(
                    'annotations'
                ).annotate(
                    subsection_count_db=Count('subsections')
                ).order_by('order')
            )
        return self._cached_sections

    def get_sections(self, brief):
        """Return sections with just status + counts."""
        sections = self._get_top_level_sections(brief)

        result = []
        for section in sections:
            # Filter active annotations in Python from prefetched set
            active = [
                a for a in section.annotations.all()
                if a.dismissed_at is None and a.resolved_at is None
            ]
            blocking = sum(1 for a in active if a.priority == AnnotationPriority.BLOCKING)
            important = sum(1 for a in active if a.priority == AnnotationPriority.IMPORTANT)
            info = sum(1 for a in active if a.priority == AnnotationPriority.INFO)

            result.append({
                'id': str(section.id),
                'section_id': section.section_id,
                'heading': section.heading,
                'section_type': section.section_type,
                'grounding_status': section.grounding_status,
                'is_locked': section.is_locked,
                'is_linked': section.is_linked,
                'annotation_counts': {
                    'blocking': blocking,
                    'important': important,
                    'info': info,
                },
                'subsection_count': section.subsection_count_db,
            })
        return result

    def get_overall_grounding(self, brief):
        """Compute aggregate grounding across all sections.

        Reuses cached sections from get_sections() to avoid a second query.
        Note: this counts only top-level sections. If subsections should
        contribute to the score, the query in _get_top_level_sections
        should be adjusted to include them.
        """
        sections = self._get_top_level_sections(brief)
        total = len(sections)
        if total == 0:
            return {'score': 0, 'total_sections': 0}

        status_counts = {}
        for section in sections:
            s = section.grounding_status
            status_counts[s] = status_counts.get(s, 0) + 1

        # Simple scoring: strong=100, moderate=60, weak=30, empty=0, conflicted=20
        score_map = {
            GroundingStatus.STRONG: 100,
            GroundingStatus.MODERATE: 60,
            GroundingStatus.WEAK: 30,
            GroundingStatus.CONFLICTED: 20,
            GroundingStatus.EMPTY: 0,
        }
        total_score = sum(
            score_map.get(s.grounding_status, 0) for s in sections
        )
        avg_score = total_score / total

        return {
            'score': round(avg_score),
            'total_sections': total,
            'status_counts': status_counts,
        }
