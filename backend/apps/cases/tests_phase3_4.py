"""
Tests for Phase 3 (Premortem, WWCYM) and Phase 4 (Section Judgment) endpoints.

Covers:
- CaseViewSet.premortem: save premortem text, timestamp idempotency
- CaseViewSet.what_changed_mind_response: save WWCYM response, validation
- WorkingDocumentViewSet.section_confidence: set/clear per-section confidence
- CaseViewSet.section_judgment_summary: mismatch detection between user judgment and grounding
"""
import uuid

from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status

from apps.events.models import Event, EventType, ActorType
from apps.projects.models import Project
from apps.cases.models import (
    Case, WorkingDocument, CaseStatus, DocumentType, EditFriction,
)
from apps.cases.brief_models import (
    BriefSection, SectionType, GroundingStatus,
)


class Phase34TestMixin:
    """Shared helpers for creating test fixtures."""

    def _create_user(self, username=None):
        return User.objects.create_user(
            username=username or f'testuser-{uuid.uuid4().hex[:8]}',
            password='testpass123',
        )

    def _create_event(self, case=None, event_type=EventType.CASE_CREATED):
        return Event.objects.create(
            actor_type=ActorType.SYSTEM,
            type=event_type,
            payload={},
            case_id=case.id if case else None,
        )

    def _create_project(self, user):
        return Project.objects.create(title='Test Project', user=user)

    def _create_case(self, user, project):
        event = self._create_event(event_type=EventType.CASE_CREATED)
        return Case.objects.create(
            title='Test Case',
            user=user,
            project=project,
            position='Test position',
            created_from_event_id=event.id,
        )

    def _create_case_with_brief(self, user, project):
        """Create a case with a main brief document and return (case, brief)."""
        case = self._create_case(user, project)
        brief = WorkingDocument.objects.create(
            case=case,
            document_type=DocumentType.CASE_BRIEF,
            title='Brief',
            content_markdown='# Test Brief\n',
            edit_friction=EditFriction.LOW,
            created_by=user,
        )
        case.main_brief = brief
        case.save(update_fields=['main_brief'])
        return case, brief

    def _create_section(self, brief, heading='Test Section',
                        section_type=SectionType.CUSTOM, order=0,
                        grounding_status=GroundingStatus.EMPTY):
        """Create a BriefSection with specified grounding status."""
        section = BriefSection.objects.create(
            brief=brief,
            section_id=BriefSection.generate_section_id(),
            heading=heading,
            order=order,
            section_type=section_type,
            grounding_status=grounding_status,
            grounding_data={},
        )
        return section


# ---------------------------------------------------------------------------
# Phase 3a: Premortem
# ---------------------------------------------------------------------------

class TestPremortem(Phase34TestMixin, APITestCase):
    """Tests for PATCH /api/cases/{id}/premortem/."""

    def setUp(self):
        self.user = self._create_user()
        self.project = self._create_project(self.user)
        self.case = self._create_case(self.user, self.project)
        self.client.force_authenticate(user=self.user)
        self.url = f'/api/cases/{self.case.id}/premortem/'

    def test_save_premortem_success(self):
        """PATCH with premortem_text saves the text and returns it."""
        response = self.client.patch(self.url, {
            'premortem_text': 'We failed because we ignored market signals.',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['premortem_text'],
            'We failed because we ignored market signals.',
        )
        self.assertIsNotNone(response.data['premortem_at'])

        # Verify persistence
        self.case.refresh_from_db()
        self.assertEqual(
            self.case.premortem_text,
            'We failed because we ignored market signals.',
        )
        self.assertIsNotNone(self.case.premortem_at)

    def test_save_premortem_sets_timestamp_once(self):
        """Second save does not update premortem_at if already set."""
        # First save — sets premortem_at
        self.client.patch(self.url, {
            'premortem_text': 'First premortem draft.',
        }, format='json')
        self.case.refresh_from_db()
        first_ts = self.case.premortem_at

        # Second save — premortem_at should NOT change
        self.client.patch(self.url, {
            'premortem_text': 'Revised premortem draft.',
        }, format='json')
        self.case.refresh_from_db()
        second_ts = self.case.premortem_at

        self.assertEqual(first_ts, second_ts)
        self.assertEqual(self.case.premortem_text, 'Revised premortem draft.')

    def test_save_premortem_empty_text_accepted_but_no_timestamp(self):
        """Empty string is accepted (field is blank=True) but does not set premortem_at."""
        response = self.client.patch(self.url, {
            'premortem_text': '',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['premortem_text'], '')
        # Empty text should not trigger timestamp
        self.assertIsNone(response.data['premortem_at'])

    def test_premortem_in_serializer(self):
        """Verify premortem fields appear in case serialization (GET)."""
        self.case.premortem_text = 'Premortem content'
        from django.utils import timezone
        self.case.premortem_at = timezone.now()
        self.case.save(update_fields=['premortem_text', 'premortem_at'])

        response = self.client.get(f'/api/cases/{self.case.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('premortem_text', response.data)
        self.assertIn('premortem_at', response.data)
        self.assertEqual(response.data['premortem_text'], 'Premortem content')
        self.assertIsNotNone(response.data['premortem_at'])


# ---------------------------------------------------------------------------
# Phase 3b: WWCYM Response
# ---------------------------------------------------------------------------

class TestWWCYMResponse(Phase34TestMixin, APITestCase):
    """Tests for PATCH /api/cases/{id}/what-changed-mind-response/."""

    def setUp(self):
        self.user = self._create_user()
        self.project = self._create_project(self.user)
        self.case = self._create_case(self.user, self.project)
        self.client.force_authenticate(user=self.user)
        self.url = f'/api/cases/{self.case.id}/what-changed-mind-response/'

    def test_save_wwcym_response_success(self):
        """PATCH with valid response type saves and returns it."""
        response = self.client.patch(self.url, {
            'response': 'updated_view',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['what_changed_mind_response'], 'updated_view')
        self.assertIsNotNone(response.data['what_changed_mind_response_at'])

        # Verify persistence
        self.case.refresh_from_db()
        self.assertEqual(self.case.what_changed_mind_response, 'updated_view')
        self.assertIsNotNone(self.case.what_changed_mind_response_at)

    def test_save_wwcym_response_all_valid_choices(self):
        """All three valid response choices are accepted."""
        for choice in ['updated_view', 'proceeding_anyway', 'not_materialized']:
            response = self.client.patch(self.url, {
                'response': choice,
            }, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK, f'Failed for choice: {choice}')
            self.assertEqual(response.data['what_changed_mind_response'], choice)

    def test_save_wwcym_response_invalid_choice(self):
        """Invalid response type is rejected with 400."""
        response = self.client.patch(self.url, {
            'response': 'invalid_choice',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_save_wwcym_response_empty_rejected(self):
        """Empty string response is rejected with 400."""
        response = self.client.patch(self.url, {
            'response': '',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wwcym_response_in_serializer(self):
        """Verify WWCYM response fields appear in case serialization (GET)."""
        from django.utils import timezone
        self.case.what_changed_mind_response = 'proceeding_anyway'
        self.case.what_changed_mind_response_at = timezone.now()
        self.case.save(update_fields=[
            'what_changed_mind_response',
            'what_changed_mind_response_at',
        ])

        response = self.client.get(f'/api/cases/{self.case.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('what_changed_mind_response', response.data)
        self.assertIn('what_changed_mind_response_at', response.data)
        self.assertEqual(response.data['what_changed_mind_response'], 'proceeding_anyway')
        self.assertIsNotNone(response.data['what_changed_mind_response_at'])


# ---------------------------------------------------------------------------
# Phase 4: Section Confidence
# ---------------------------------------------------------------------------

class TestSectionConfidence(Phase34TestMixin, APITestCase):
    """Tests for PATCH /api/cases/documents/{id}/section-confidence/."""

    def setUp(self):
        self.user = self._create_user()
        self.project = self._create_project(self.user)
        self.case, self.brief = self._create_case_with_brief(self.user, self.project)
        self.section = self._create_section(
            self.brief, heading='Key Finding', order=0,
        )
        self.client.force_authenticate(user=self.user)
        self.url = f'/api/cases/documents/{self.brief.id}/section-confidence/'

    def test_set_section_confidence_success(self):
        """PATCH with section_id and confidence 1-4 saves the rating."""
        response = self.client.patch(self.url, {
            'section_id': self.section.section_id,
            'confidence': 3,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['section_id'], self.section.section_id)
        self.assertEqual(response.data['user_confidence'], 3)
        self.assertIsNotNone(response.data['user_confidence_at'])

        # Verify persistence
        self.section.refresh_from_db()
        self.assertEqual(self.section.user_confidence, 3)
        self.assertIsNotNone(self.section.user_confidence_at)

    def test_set_section_confidence_all_valid_values(self):
        """All valid confidence values (1-4) are accepted."""
        for value in [1, 2, 3, 4]:
            response = self.client.patch(self.url, {
                'section_id': self.section.section_id,
                'confidence': value,
            }, format='json')
            self.assertEqual(
                response.status_code, status.HTTP_200_OK,
                f'Failed for confidence={value}',
            )
            self.assertEqual(response.data['user_confidence'], value)

    def test_set_section_confidence_null_clears(self):
        """confidence=null clears the rating and timestamp."""
        # First set a confidence value
        self.client.patch(self.url, {
            'section_id': self.section.section_id,
            'confidence': 4,
        }, format='json')

        # Now clear it
        response = self.client.patch(self.url, {
            'section_id': self.section.section_id,
            'confidence': None,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['user_confidence'])
        self.assertIsNone(response.data['user_confidence_at'])

        # Verify persistence
        self.section.refresh_from_db()
        self.assertIsNone(self.section.user_confidence)
        self.assertIsNone(self.section.user_confidence_at)

    def test_set_section_confidence_invalid_range(self):
        """confidence=5 or 0 is rejected with 400."""
        for invalid_value in [0, 5, -1, 10]:
            response = self.client.patch(self.url, {
                'section_id': self.section.section_id,
                'confidence': invalid_value,
            }, format='json')
            self.assertEqual(
                response.status_code, status.HTTP_400_BAD_REQUEST,
                f'Expected 400 for confidence={invalid_value}, got {response.status_code}',
            )

    def test_set_section_confidence_missing_section_id(self):
        """Missing section_id is rejected with 400."""
        response = self.client.patch(self.url, {
            'confidence': 3,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_set_section_confidence_nonexistent_section(self):
        """Non-existent section_id returns 404."""
        response = self.client.patch(self.url, {
            'section_id': 'sf-nonexistent',
            'confidence': 3,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Phase 4: Section Judgment Summary
# ---------------------------------------------------------------------------

class TestSectionJudgmentSummary(Phase34TestMixin, APITestCase):
    """Tests for GET /api/cases/{id}/section-judgment-summary/."""

    def setUp(self):
        self.user = self._create_user()
        self.project = self._create_project(self.user)
        self.case, self.brief = self._create_case_with_brief(self.user, self.project)
        self.client.force_authenticate(user=self.user)
        self.url = f'/api/cases/{self.case.id}/section-judgment-summary/'

    def test_section_judgment_summary_basic(self):
        """GET returns sections with user_confidence and grounding_status."""
        section = self._create_section(
            self.brief, heading='Analysis',
            section_type=SectionType.INQUIRY_BRIEF, order=0,
            grounding_status=GroundingStatus.MODERATE,
        )
        section.user_confidence = 3
        section.grounding_data = {'evidence_count': 2, 'tensions_count': 0}
        section.save(update_fields=['user_confidence', 'grounding_data'])

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('sections', response.data)
        self.assertIn('mismatches', response.data)
        self.assertIn('rated_count', response.data)
        self.assertIn('total_count', response.data)

        sections = response.data['sections']
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]['section_id'], section.section_id)
        self.assertEqual(sections[0]['heading'], 'Analysis')
        self.assertEqual(sections[0]['grounding_status'], 'moderate')
        self.assertEqual(sections[0]['user_confidence'], 3)
        self.assertEqual(sections[0]['evidence_count'], 2)
        self.assertEqual(sections[0]['tensions_count'], 0)
        self.assertEqual(response.data['rated_count'], 1)
        self.assertEqual(response.data['total_count'], 1)

    def test_section_judgment_summary_excludes_decision_frame(self):
        """Decision frame sections are excluded from the summary."""
        self._create_section(
            self.brief, heading='Decision Frame',
            section_type=SectionType.DECISION_FRAME, order=0,
        )
        self._create_section(
            self.brief, heading='Regular Section',
            section_type=SectionType.INQUIRY_BRIEF, order=1,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        headings = [s['heading'] for s in response.data['sections']]
        self.assertNotIn('Decision Frame', headings)
        self.assertIn('Regular Section', headings)
        self.assertEqual(response.data['total_count'], 1)

    def test_section_judgment_summary_no_brief_returns_empty(self):
        """Case with no main_brief returns empty sections and mismatches."""
        case_no_brief = self._create_case(self.user, self.project)
        url = f'/api/cases/{case_no_brief.id}/section-judgment-summary/'

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sections'], [])
        self.assertEqual(response.data['mismatches'], [])

    def test_section_judgment_summary_unrated_sections(self):
        """Sections without user_confidence have null and are not counted as rated."""
        self._create_section(
            self.brief, heading='Unrated',
            section_type=SectionType.INQUIRY_BRIEF, order=0,
            grounding_status=GroundingStatus.MODERATE,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sections = response.data['sections']
        self.assertEqual(len(sections), 1)
        self.assertIsNone(sections[0]['user_confidence'])
        self.assertEqual(response.data['rated_count'], 0)
        self.assertEqual(response.data['total_count'], 1)
        # No mismatches when unrated
        self.assertEqual(response.data['mismatches'], [])

    def test_section_judgment_summary_mismatch_overconfident(self):
        """Overconfident mismatch: user rates high (3-4) but grounding is weak/empty."""
        section = self._create_section(
            self.brief, heading='Weak Section',
            section_type=SectionType.INQUIRY_BRIEF, order=0,
            grounding_status=GroundingStatus.WEAK,
        )
        section.user_confidence = 4
        section.grounding_data = {'evidence_count': 0, 'tensions_count': 0}
        section.save(update_fields=['user_confidence', 'grounding_data'])

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mismatches = response.data['mismatches']
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]['type'], 'overconfident')
        self.assertEqual(mismatches[0]['section_id'], section.section_id)
        self.assertEqual(mismatches[0]['user_confidence'], 4)
        self.assertEqual(mismatches[0]['grounding_status'], 'weak')

    def test_section_judgment_summary_mismatch_underconfident(self):
        """Underconfident mismatch: user rates low (1-2) but grounding is strong."""
        section = self._create_section(
            self.brief, heading='Strong Section',
            section_type=SectionType.INQUIRY_BRIEF, order=0,
            grounding_status=GroundingStatus.STRONG,
        )
        section.user_confidence = 1
        section.grounding_data = {'evidence_count': 5, 'tensions_count': 0}
        section.save(update_fields=['user_confidence', 'grounding_data'])

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mismatches = response.data['mismatches']
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]['type'], 'underconfident')
        self.assertEqual(mismatches[0]['section_id'], section.section_id)
        self.assertEqual(mismatches[0]['user_confidence'], 1)
        self.assertEqual(mismatches[0]['grounding_status'], 'strong')

    def test_section_judgment_summary_no_mismatch_when_aligned(self):
        """No mismatch when user confidence aligns with grounding strength."""
        # High confidence + strong grounding = aligned
        section = self._create_section(
            self.brief, heading='Aligned Section',
            section_type=SectionType.INQUIRY_BRIEF, order=0,
            grounding_status=GroundingStatus.STRONG,
        )
        section.user_confidence = 4
        section.grounding_data = {'evidence_count': 5, 'tensions_count': 0}
        section.save(update_fields=['user_confidence', 'grounding_data'])

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['mismatches'], [])

    def test_section_judgment_summary_multiple_sections_mixed(self):
        """Multiple sections with mixed alignments produce correct mismatches."""
        # Overconfident: user=3, grounding=empty
        s1 = self._create_section(
            self.brief, heading='Over',
            section_type=SectionType.INQUIRY_BRIEF, order=0,
            grounding_status=GroundingStatus.EMPTY,
        )
        s1.user_confidence = 3
        s1.grounding_data = {'evidence_count': 0, 'tensions_count': 0}
        s1.save(update_fields=['user_confidence', 'grounding_data'])

        # Aligned: user=2, grounding=moderate
        s2 = self._create_section(
            self.brief, heading='Aligned',
            section_type=SectionType.INQUIRY_BRIEF, order=1,
            grounding_status=GroundingStatus.MODERATE,
        )
        s2.user_confidence = 2
        s2.grounding_data = {'evidence_count': 2, 'tensions_count': 0}
        s2.save(update_fields=['user_confidence', 'grounding_data'])

        # Underconfident: user=1, grounding=strong
        s3 = self._create_section(
            self.brief, heading='Under',
            section_type=SectionType.INQUIRY_BRIEF, order=2,
            grounding_status=GroundingStatus.STRONG,
        )
        s3.user_confidence = 1
        s3.grounding_data = {'evidence_count': 5, 'tensions_count': 0}
        s3.save(update_fields=['user_confidence', 'grounding_data'])

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['sections']), 3)
        self.assertEqual(response.data['rated_count'], 3)
        self.assertEqual(response.data['total_count'], 3)

        mismatches = response.data['mismatches']
        self.assertEqual(len(mismatches), 2)
        mismatch_types = {m['section_id']: m['type'] for m in mismatches}
        self.assertEqual(mismatch_types[s1.section_id], 'overconfident')
        self.assertEqual(mismatch_types[s3.section_id], 'underconfident')
