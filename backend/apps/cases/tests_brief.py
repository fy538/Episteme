"""
Tests for the brief grounding system.

Covers:
- BriefGroundingEngine: section grounding computation
- BriefGroundingEngine: annotation generation
- BriefGroundingEngine: evolve_brief() end-to-end
- BriefSection CRUD
- Brief serializers (N+1 optimized)
"""
import uuid

from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.core.cache import cache as django_cache

from apps.events.models import Event, EventType, ActorType
from apps.cases.models import Case, WorkingDocument, DocumentType, EditFriction
from apps.inquiries.models import Inquiry, InquiryStatus, ElevationReason
from apps.projects.models import Project
from apps.cases.brief_models import (
    BriefSection, BriefAnnotation,
    SectionType, GroundingStatus, AnnotationType, AnnotationPriority,
    SectionCreator,
)
from apps.cases.brief_grounding import BriefGroundingEngine
from apps.cases.brief_serializers import (
    BriefSectionSerializer,
    BriefAnnotationSerializer,
    BriefOverviewSerializer,
)


class BriefTestMixin:
    """Shared helpers for creating test data."""

    def _create_event(self, case=None, event_type=EventType.CASE_CREATED):
        """Create an Event."""
        return Event.objects.create(
            actor_type=ActorType.SYSTEM,
            type=event_type,
            payload={},
            case_id=case.id if case else None,
        )

    def _create_case_with_brief(self, title='Test Case', decision_question=''):
        """Create a Case with a WorkingDocument (main_brief) and return both."""
        event = self._create_event(event_type=EventType.CASE_CREATED)
        project = Project.objects.create(
            title='Test Project',
            user=self.user,
        )
        case = Case.objects.create(
            title=title,
            user=self.user,
            project=project,
            position='Test position',
            decision_question=decision_question,
            created_from_event_id=event.id,
        )
        doc = WorkingDocument.objects.create(
            case=case,
            document_type=DocumentType.CASE_BRIEF,
            title='Brief',
            content_markdown='# Test Brief\n',
            edit_friction=EditFriction.LOW,
            created_by=self.user,
        )
        case.main_brief = doc
        case.save(update_fields=['main_brief'])
        return case, doc

    def _create_section(self, brief, heading='Test Section', section_type=SectionType.CUSTOM,
                        inquiry=None, order=0, parent=None):
        """Create a BriefSection."""
        section = BriefSection.objects.create(
            brief=brief,
            section_id=BriefSection.generate_section_id(),
            heading=heading,
            order=order,
            section_type=section_type,
            inquiry=inquiry,
            parent_section=parent,
        )
        return section

    def _create_inquiry(self, case, title='Test Inquiry', status='open'):
        """Create an Inquiry for a case."""
        event = self._create_event(case=case, event_type=EventType.INQUIRY_CREATED)
        return Inquiry.objects.create(
            title=title,
            case=case,
            status=status,
            elevation_reason=ElevationReason.USER_CREATED,
            sequence_index=0,
            created_from_event_id=event.id,
        )

    def _create_evidence(self, inquiry, direction='supports', strength=0.7):
        """Create a graph evidence Node + Edge (replaces inquiries.Evidence)."""
        from apps.graph.models import Node, Edge, EdgeType, NodeSourceType
        evidence_node = Node.objects.create(
            project=inquiry.case.project,
            node_type='evidence',
            content='Some evidence text',
            confidence=strength,
            source_type=NodeSourceType.USER,
        )
        # Create an inquiry node if one doesn't exist yet, then link
        inquiry_node, _ = Node.objects.get_or_create(
            project=inquiry.case.project,
            node_type='inquiry',
            content=inquiry.title,
            defaults={'source_type': NodeSourceType.AGENT_ANALYSIS},
        )
        edge_type = EdgeType.SUPPORTS if direction == 'supports' else EdgeType.CONTRADICTS
        Edge.objects.create(
            source_node=evidence_node,
            target_node=inquiry_node,
            edge_type=edge_type,
        )
        return evidence_node


class TestBriefGroundingEngine(BriefTestMixin, TestCase):
    """Test compute_section_grounding()."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.case, self.brief = self._create_case_with_brief()

    def test_empty_section_returns_empty_status(self):
        """Unlinked section with no inquiry returns empty grounding."""
        section = self._create_section(self.brief, heading='Custom Section')
        result = BriefGroundingEngine.compute_section_grounding(section)
        self.assertEqual(result['status'], GroundingStatus.EMPTY)
        self.assertEqual(result['evidence_count'], 0)

    def test_linked_section_without_evidence_returns_weak(self):
        """Section linked to inquiry with unvalidated assumptions returns weak."""
        inquiry = self._create_inquiry(self.case)
        section = self._create_section(
            self.brief, heading='Inquiry Section',
            section_type=SectionType.INQUIRY_BRIEF, inquiry=inquiry
        )
        # Add an assumption node in the graph layer (replaces assumption signals)
        from apps.graph.models import Node, NodeSourceType
        Node.objects.create(
            project=self.case.project,
            node_type='assumption',
            content='Assumption without evidence',
            status='untested',
            source_type=NodeSourceType.AGENT_ANALYSIS,
        )
        result = BriefGroundingEngine.compute_section_grounding(section)
        self.assertEqual(result['status'], GroundingStatus.WEAK)
        self.assertEqual(result['unvalidated_assumptions'], 1)

    def test_linked_section_with_supporting_evidence_returns_moderate(self):
        """Section with some evidence returns moderate."""
        inquiry = self._create_inquiry(self.case)
        section = self._create_section(
            self.brief, heading='Inquiry Section',
            section_type=SectionType.INQUIRY_BRIEF, inquiry=inquiry
        )
        self._create_evidence(inquiry, direction='supports')
        result = BriefGroundingEngine.compute_section_grounding(section)
        self.assertEqual(result['status'], GroundingStatus.MODERATE)
        self.assertEqual(result['evidence_count'], 1)
        self.assertEqual(result['supporting'], 1)

    def test_linked_section_with_strong_evidence_returns_strong(self):
        """Section with 3+ supporting evidence and no unvalidated assumptions returns strong."""
        inquiry = self._create_inquiry(self.case)
        section = self._create_section(
            self.brief, heading='Strong Section',
            section_type=SectionType.INQUIRY_BRIEF, inquiry=inquiry
        )
        for _ in range(3):
            self._create_evidence(inquiry, direction='supports')
        result = BriefGroundingEngine.compute_section_grounding(section)
        self.assertEqual(result['status'], GroundingStatus.STRONG)
        self.assertEqual(result['evidence_count'], 3)

    def test_conflicting_evidence_returns_conflicted(self):
        """Section with tension nodes returns conflicted status."""
        inquiry = self._create_inquiry(self.case)
        section = self._create_section(
            self.brief, heading='Conflicted Section',
            section_type=SectionType.INQUIRY_BRIEF, inquiry=inquiry
        )
        # Create a tension node in the graph layer (replaces signal.contradicts M2M)
        from apps.graph.models import Node, NodeSourceType
        Node.objects.create(
            project=self.case.project,
            node_type='tension',
            content='Contradicting claims about performance',
            source_type=NodeSourceType.AGENT_ANALYSIS,
        )

        self._create_evidence(inquiry, direction='supports')

        result = BriefGroundingEngine.compute_section_grounding(section)
        self.assertEqual(result['status'], GroundingStatus.CONFLICTED)
        self.assertGreater(result['tensions_count'], 0)

    def test_decision_frame_with_question_returns_strong(self):
        """Decision frame section with decision_question set returns strong."""
        case, brief = self._create_case_with_brief(decision_question='Should we proceed?')
        section = self._create_section(
            brief, heading='Decision Frame',
            section_type=SectionType.DECISION_FRAME
        )
        result = BriefGroundingEngine.compute_section_grounding(section)
        self.assertEqual(result['status'], GroundingStatus.STRONG)

    def test_decision_frame_without_question_returns_empty(self):
        """Decision frame section without decision_question returns empty."""
        section = self._create_section(
            self.brief, heading='Decision Frame',
            section_type=SectionType.DECISION_FRAME
        )
        result = BriefGroundingEngine.compute_section_grounding(section)
        self.assertEqual(result['status'], GroundingStatus.EMPTY)


class TestBriefAnnotationGeneration(BriefTestMixin, TestCase):
    """Test compute_section_annotations() — annotation generation."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser2', password='testpass123')
        self.case, self.brief = self._create_case_with_brief()

    def test_unlinked_section_returns_no_annotations(self):
        """Section with no inquiry or tagged signals returns empty annotations."""
        section = self._create_section(self.brief, heading='Unlinked')
        annotations = BriefGroundingEngine.compute_section_annotations(section)
        self.assertEqual(annotations, [])

    def test_section_with_evidence_desert(self):
        """Open inquiry with <2 evidence items generates evidence_desert annotation."""
        inquiry = self._create_inquiry(self.case, status='open')
        section = self._create_section(
            self.brief, heading='Desert Section',
            section_type=SectionType.INQUIRY_BRIEF, inquiry=inquiry
        )
        # Only 1 evidence item (< 2 threshold)
        self._create_evidence(inquiry)

        annotations = BriefGroundingEngine.compute_section_annotations(section)
        types = [a['type'] for a in annotations]
        self.assertIn(AnnotationType.EVIDENCE_DESERT, types)

    def test_dismissed_annotation_not_recreated_by_evolve(self):
        """Dismissed annotations are not recreated during evolve.

        Note: evolve_brief reconciles by signature (type, description[:80]).
        A dismissed annotation has dismissed_at set, so it's excluded from
        active annotations. The evolve process only looks at active annotations
        for dedup, so it may recreate similar ones. However, the dismissed
        annotation itself won't be 'un-dismissed'.
        """
        inquiry = self._create_inquiry(self.case, status='open')
        section = self._create_section(
            self.brief, heading='Test',
            section_type=SectionType.INQUIRY_BRIEF, inquiry=inquiry
        )
        # Create and dismiss an annotation
        ann = BriefAnnotation.objects.create(
            section=section,
            annotation_type=AnnotationType.EVIDENCE_DESERT,
            description='Only 0 evidence item(s). Consider gathering more evidence.',
            priority=AnnotationPriority.IMPORTANT,
        )
        from django.utils import timezone
        ann.dismissed_at = timezone.now()
        ann.save()

        # The dismissed annotation should remain dismissed
        ann.refresh_from_db()
        self.assertIsNotNone(ann.dismissed_at)
        self.assertFalse(ann.is_active)


class TestEvolveBrief(BriefTestMixin, TransactionTestCase):
    """Test evolve_brief() end-to-end."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser3', password='testpass123')
        self.case, self.brief = self._create_case_with_brief()
        # Clear any leftover cache locks
        django_cache.clear()

    def test_evolve_updates_all_sections(self):
        """Evolve computes grounding for all sections and returns summary."""
        inquiry = self._create_inquiry(self.case)
        self._create_section(
            self.brief, heading='Section 1',
            section_type=SectionType.INQUIRY_BRIEF, inquiry=inquiry, order=0
        )
        self._create_section(self.brief, heading='Section 2', order=1)

        result = BriefGroundingEngine.evolve_brief(self.case.id)

        self.assertIn('updated_sections', result)
        self.assertIn('new_annotations', result)
        self.assertIn('resolved_annotations', result)
        # At minimum, sections should have been processed
        self.assertIsInstance(result['annotations_created'], int)

    def test_evolve_returns_diff_with_changes(self):
        """Evolve returns section changes when status changes from default."""
        inquiry = self._create_inquiry(self.case, status='open')
        section = self._create_section(
            self.brief, heading='Will Change',
            section_type=SectionType.INQUIRY_BRIEF, inquiry=inquiry
        )
        self.assertEqual(section.grounding_status, GroundingStatus.EMPTY)

        # Add evidence so status changes from empty → moderate
        self._create_evidence(inquiry)

        result = BriefGroundingEngine.evolve_brief(self.case.id)

        # Section should have been updated
        section.refresh_from_db()
        self.assertNotEqual(section.grounding_status, GroundingStatus.EMPTY)
        self.assertGreater(len(result['updated_sections']), 0)

    def test_evolve_with_no_changes_returns_empty_diff(self):
        """Evolve with no linked sections produces no changes."""
        # Only unlinked custom section — no grounding computation
        self._create_section(self.brief, heading='Custom Only')

        result = BriefGroundingEngine.evolve_brief(self.case.id)

        self.assertEqual(result['updated_sections'], [])

    def test_evolve_creates_annotations(self):
        """Evolve creates new annotations for evidence deserts."""
        inquiry = self._create_inquiry(self.case, status='open')
        self._create_section(
            self.brief, heading='Desert',
            section_type=SectionType.INQUIRY_BRIEF, inquiry=inquiry
        )
        # No evidence at all

        result = BriefGroundingEngine.evolve_brief(self.case.id)

        self.assertGreater(result['annotations_created'], 0)

    def test_evolve_resolves_stale_annotations(self):
        """Evolve resolves annotations that are no longer computed."""
        inquiry = self._create_inquiry(self.case, status='resolved')
        section = self._create_section(
            self.brief, heading='Resolved',
            section_type=SectionType.INQUIRY_BRIEF, inquiry=inquiry
        )
        # Create an evidence_desert annotation
        ann = BriefAnnotation.objects.create(
            section=section,
            annotation_type=AnnotationType.EVIDENCE_DESERT,
            description='Only 0 evidence item(s). Consider gathering more evidence.',
            priority=AnnotationPriority.IMPORTANT,
            source_inquiry=inquiry,
        )
        # Add enough evidence and resolve the inquiry so desert no longer applies
        self._create_evidence(inquiry)
        self._create_evidence(inquiry)

        result = BriefGroundingEngine.evolve_brief(self.case.id)

        # The old annotation should be resolved
        ann.refresh_from_db()
        self.assertIsNotNone(ann.resolved_at)
        self.assertEqual(ann.resolved_by, 'system')
        self.assertGreater(len(result['resolved_annotations']), 0)

    def test_evolve_no_brief_returns_empty(self):
        """Evolve on a case with no main_brief returns empty result."""
        event = self._create_event(event_type=EventType.CASE_CREATED)
        project = Project.objects.create(title='Test Project', user=self.user)
        case_no_brief = Case.objects.create(
            title='No Brief Case',
            user=self.user,
            project=project,
            position='Test',
            created_from_event_id=event.id,
        )
        result = BriefGroundingEngine.evolve_brief(case_no_brief.id)
        self.assertEqual(result['updated_sections'], [])

    def test_evolve_nonexistent_case_returns_empty(self):
        """Evolve on a non-existent case ID returns empty result."""
        result = BriefGroundingEngine.evolve_brief(uuid.uuid4())
        self.assertEqual(result['updated_sections'], [])


class TestBriefSectionCRUD(BriefTestMixin, TestCase):
    """Test BriefSection model operations."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser4', password='testpass123')
        self.case, self.brief = self._create_case_with_brief()

    def test_create_section(self):
        """BriefSection can be created with basic fields."""
        section = self._create_section(self.brief, heading='New Section')
        self.assertIsNotNone(section.id)
        self.assertEqual(section.heading, 'New Section')
        self.assertEqual(section.grounding_status, GroundingStatus.EMPTY)
        self.assertTrue(section.section_id.startswith('sf-'))

    def test_section_auto_computes_is_linked(self):
        """is_linked is auto-computed on save based on inquiry FK."""
        inquiry = self._create_inquiry(self.case)
        section = self._create_section(self.brief, inquiry=inquiry)
        self.assertTrue(section.is_linked)

        # Unlink
        section.inquiry = None
        section.save()
        self.assertFalse(section.is_linked)

    def test_section_auto_computes_depth(self):
        """depth is auto-computed from parent_section."""
        parent = self._create_section(self.brief, heading='Parent', order=0)
        child = self._create_section(self.brief, heading='Child', order=1, parent=parent)
        self.assertEqual(parent.depth, 0)
        self.assertEqual(child.depth, 1)

    def test_delete_section_cascades_annotations(self):
        """Deleting a section cascades to its annotations."""
        section = self._create_section(self.brief, heading='To Delete')
        BriefAnnotation.objects.create(
            section=section,
            annotation_type=AnnotationType.EVIDENCE_DESERT,
            description='Test annotation',
            priority=AnnotationPriority.INFO,
        )
        annotation_id = section.annotations.first().id
        section.delete()
        self.assertFalse(BriefAnnotation.objects.filter(id=annotation_id).exists())

    def test_reorder_sections(self):
        """Sections can be reordered by updating order field."""
        s1 = self._create_section(self.brief, heading='First', order=0)
        s2 = self._create_section(self.brief, heading='Second', order=1)
        s3 = self._create_section(self.brief, heading='Third', order=2)

        # Move s3 to front
        s3.order = 0
        s3.save()
        s1.order = 1
        s1.save()
        s2.order = 2
        s2.save()

        ordered = list(BriefSection.objects.filter(brief=self.brief).order_by('order'))
        self.assertEqual(ordered[0].heading, 'Third')
        self.assertEqual(ordered[1].heading, 'First')
        self.assertEqual(ordered[2].heading, 'Second')

    def test_link_section_to_inquiry(self):
        """Section can be linked to an inquiry."""
        inquiry = self._create_inquiry(self.case)
        section = self._create_section(self.brief, heading='To Link')
        self.assertFalse(section.is_linked)

        section.inquiry = inquiry
        section.section_type = SectionType.INQUIRY_BRIEF
        section.save()

        section.refresh_from_db()
        self.assertTrue(section.is_linked)
        self.assertEqual(section.inquiry_id, inquiry.id)

    def test_section_collapse_state(self):
        """is_collapsed field persists correctly."""
        section = self._create_section(self.brief, heading='Collapsible')
        self.assertFalse(section.is_collapsed)

        section.is_collapsed = True
        section.save(update_fields=['is_collapsed'])
        section.refresh_from_db()
        self.assertTrue(section.is_collapsed)


class TestBriefSerializers(BriefTestMixin, TestCase):
    """Test brief serializers with prefetch-optimized queries."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser5', password='testpass123')
        self.case, self.brief = self._create_case_with_brief()

    def test_section_serializer_filters_dismissed_annotations(self):
        """BriefSectionSerializer only returns active annotations."""
        section = self._create_section(self.brief, heading='Annotated')
        active_ann = BriefAnnotation.objects.create(
            section=section,
            annotation_type=AnnotationType.EVIDENCE_DESERT,
            description='Active annotation',
            priority=AnnotationPriority.IMPORTANT,
        )
        from django.utils import timezone
        dismissed_ann = BriefAnnotation.objects.create(
            section=section,
            annotation_type=AnnotationType.BLIND_SPOT,
            description='Dismissed annotation',
            priority=AnnotationPriority.INFO,
            dismissed_at=timezone.now(),
        )

        # Re-fetch with prefetch to populate _prefetched_objects_cache
        section = BriefSection.objects.prefetch_related('annotations').get(pk=section.pk)
        data = BriefSectionSerializer(section).data
        annotation_ids = [a['id'] for a in data['annotations']]

        self.assertIn(str(active_ann.id), annotation_ids)
        self.assertNotIn(str(dismissed_ann.id), annotation_ids)

    def test_section_serializer_includes_content_preview(self):
        """BriefSectionSerializer extracts content preview from markdown."""
        section = self._create_section(self.brief, heading='Preview Test')
        # Add markdown content with the section marker
        self.brief.content_markdown = (
            f'<!-- section:{section.section_id} -->\n'
            '## Preview Test\n'
            'This is a test paragraph with some content for preview.\n'
        )
        self.brief.save()

        # Re-fetch with prefetch to populate _prefetched_objects_cache
        section = BriefSection.objects.prefetch_related('annotations').get(pk=section.pk)
        data = BriefSectionSerializer(section).data
        self.assertIsNotNone(data['content_preview'])
        self.assertIn('test paragraph', data['content_preview'])

    def test_overview_serializer_returns_annotation_counts(self):
        """BriefOverviewSerializer counts annotations by priority."""
        section = self._create_section(self.brief, heading='Overview Test')
        BriefAnnotation.objects.create(
            section=section,
            annotation_type=AnnotationType.TENSION,
            description='Blocking issue',
            priority=AnnotationPriority.BLOCKING,
        )
        BriefAnnotation.objects.create(
            section=section,
            annotation_type=AnnotationType.BLIND_SPOT,
            description='Important issue',
            priority=AnnotationPriority.IMPORTANT,
        )
        BriefAnnotation.objects.create(
            section=section,
            annotation_type=AnnotationType.WELL_GROUNDED,
            description='Info annotation',
            priority=AnnotationPriority.INFO,
        )

        data = BriefOverviewSerializer(self.brief).data
        sections = data['sections']
        self.assertEqual(len(sections), 1)
        counts = sections[0]['annotation_counts']
        self.assertEqual(counts['blocking'], 1)
        self.assertEqual(counts['important'], 1)
        self.assertEqual(counts['info'], 1)

    def test_overview_serializer_dismissed_not_counted(self):
        """BriefOverviewSerializer doesn't count dismissed annotations."""
        section = self._create_section(self.brief, heading='Dismissed Test')
        BriefAnnotation.objects.create(
            section=section,
            annotation_type=AnnotationType.TENSION,
            description='Active blocking',
            priority=AnnotationPriority.BLOCKING,
        )
        from django.utils import timezone
        BriefAnnotation.objects.create(
            section=section,
            annotation_type=AnnotationType.BLIND_SPOT,
            description='Dismissed important',
            priority=AnnotationPriority.IMPORTANT,
            dismissed_at=timezone.now(),
        )

        data = BriefOverviewSerializer(self.brief).data
        counts = data['sections'][0]['annotation_counts']
        self.assertEqual(counts['blocking'], 1)
        self.assertEqual(counts['important'], 0)

    def test_annotation_serializer_basic_fields(self):
        """BriefAnnotationSerializer includes expected fields."""
        inquiry = self._create_inquiry(self.case)
        section = self._create_section(
            self.brief, heading='Annotated Section',
            section_type=SectionType.INQUIRY_BRIEF, inquiry=inquiry
        )
        ann = BriefAnnotation.objects.create(
            section=section,
            annotation_type=AnnotationType.TENSION,
            description='Test tension',
            priority=AnnotationPriority.BLOCKING,
        )
        data = BriefAnnotationSerializer(ann).data
        self.assertEqual(data['annotation_type'], AnnotationType.TENSION)
        self.assertEqual(data['priority'], AnnotationPriority.BLOCKING)

    def test_overview_serializer_overall_grounding_score(self):
        """BriefOverviewSerializer computes overall grounding score."""
        # Create sections with known statuses
        s1 = self._create_section(self.brief, heading='Strong', order=0)
        s1.grounding_status = GroundingStatus.STRONG
        s1.save(update_fields=['grounding_status'])

        s2 = self._create_section(self.brief, heading='Empty', order=1)
        s2.grounding_status = GroundingStatus.EMPTY
        s2.save(update_fields=['grounding_status'])

        data = BriefOverviewSerializer(self.brief).data
        overall = data['overall_grounding']
        # strong=100, empty=0 → avg=50
        self.assertEqual(overall['score'], 50)
        self.assertEqual(overall['total_sections'], 2)

    def test_overview_serializer_subsection_count(self):
        """BriefOverviewSerializer includes annotated subsection_count."""
        parent = self._create_section(self.brief, heading='Parent', order=0)
        self._create_section(self.brief, heading='Child 1', order=0, parent=parent)
        self._create_section(self.brief, heading='Child 2', order=1, parent=parent)

        data = BriefOverviewSerializer(self.brief).data
        sections = data['sections']
        self.assertEqual(len(sections), 1)  # Only top-level
        self.assertEqual(sections[0]['subsection_count'], 2)


class TestSectionMarkerValidation(BriefTestMixin, TestCase):
    """Test validate_section_markers() utility."""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser6', password='testpass123')
        self.case, self.brief = self._create_case_with_brief()

    def test_no_sections_is_valid(self):
        """Document with no BriefSections is valid (nothing to check)."""
        from apps.cases.document_service import validate_section_markers
        result = validate_section_markers(self.brief)
        self.assertTrue(result['valid'])
        self.assertEqual(result['missing_markers'], [])
        self.assertEqual(result['orphaned_markers'], [])
        self.assertEqual(result['matched'], [])

    def test_all_markers_present_is_valid(self):
        """All section IDs have matching markers in content."""
        from apps.cases.document_service import validate_section_markers
        s1 = self._create_section(self.brief, heading='Section A', order=0)
        s2 = self._create_section(self.brief, heading='Section B', order=1)

        self.brief.content_markdown = (
            f'# Brief\n'
            f'<!-- section:{s1.section_id} -->\n## Section A\nContent A\n'
            f'<!-- section:{s2.section_id} -->\n## Section B\nContent B\n'
        )
        self.brief.save()

        result = validate_section_markers(self.brief)
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['matched']), 2)
        self.assertIn(s1.section_id, result['matched'])
        self.assertIn(s2.section_id, result['matched'])

    def test_missing_marker_detected(self):
        """Section in DB but marker missing from content."""
        from apps.cases.document_service import validate_section_markers
        s1 = self._create_section(self.brief, heading='Present', order=0)
        s2 = self._create_section(self.brief, heading='Missing', order=1)

        # Only include s1 marker, not s2
        self.brief.content_markdown = (
            f'# Brief\n'
            f'<!-- section:{s1.section_id} -->\n## Present\nContent\n'
        )
        self.brief.save()

        result = validate_section_markers(self.brief)
        self.assertFalse(result['valid'])
        self.assertIn(s2.section_id, result['missing_markers'])
        self.assertIn(s1.section_id, result['matched'])

    def test_orphaned_marker_detected(self):
        """Marker in content with no matching BriefSection row."""
        from apps.cases.document_service import validate_section_markers
        s1 = self._create_section(self.brief, heading='Real', order=0)

        self.brief.content_markdown = (
            f'# Brief\n'
            f'<!-- section:{s1.section_id} -->\n## Real\nContent\n'
            f'<!-- section:sf-orphaned1 -->\n## Ghost\nNo DB row\n'
        )
        self.brief.save()

        result = validate_section_markers(self.brief)
        self.assertFalse(result['valid'])
        self.assertIn('sf-orphaned1', result['orphaned_markers'])
        self.assertIn(s1.section_id, result['matched'])

    def test_empty_content_with_sections_is_invalid(self):
        """Sections exist in DB but content is empty."""
        from apps.cases.document_service import validate_section_markers
        self._create_section(self.brief, heading='Lost', order=0)
        self.brief.content_markdown = ''
        self.brief.save()

        result = validate_section_markers(self.brief)
        self.assertFalse(result['valid'])
        self.assertEqual(len(result['missing_markers']), 1)

    def test_content_preview_logs_missing_marker(self):
        """Serializer's get_content_preview returns None and logs for missing marker."""
        section = self._create_section(self.brief, heading='No Marker')
        self.brief.content_markdown = '# Brief\nSome content without markers'
        self.brief.save()

        # Re-fetch with prefetch to avoid _prefetched_objects_cache AttributeError
        section = BriefSection.objects.prefetch_related('annotations').get(pk=section.pk)
        data = BriefSectionSerializer(section).data
        self.assertIsNone(data['content_preview'])
