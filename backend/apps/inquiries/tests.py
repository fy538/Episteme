"""
Tests for Inquiry models and services
"""
from django.test import TestCase
from django.utils import timezone

from apps.inquiries.models import Inquiry, InquiryStatus, ElevationReason
from apps.inquiries.services import InquiryService
from apps.cases.models import Case
from apps.events.models import Event, EventType


class InquiryModelTests(TestCase):
    """Test Inquiry model"""
    
    def setUp(self):
        # Create test case
        self.case = Case.objects.create(
            title="Test Case",
            description="Test case for inquiries"
        )
        
        # Create test event
        self.event = Event.objects.create(
            event_type=EventType.CHAT_MESSAGE_SENT,
            payload={"message": "test"}
        )
    
    def test_create_inquiry(self):
        """Test creating an inquiry"""
        inquiry = Inquiry.objects.create(
            case=self.case,
            title="Is PostgreSQL faster?",
            elevation_reason=ElevationReason.USER_CREATED,
            sequence_index=0
        )
        
        self.assertEqual(inquiry.status, InquiryStatus.OPEN)
        self.assertFalse(inquiry.is_resolved())
        self.assertTrue(inquiry.is_active())
    
    def test_resolve_inquiry(self):
        """Test resolving an inquiry"""
        inquiry = Inquiry.objects.create(
            case=self.case,
            title="Is PostgreSQL faster?",
            elevation_reason=ElevationReason.USER_CREATED,
            sequence_index=0
        )
        
        # Resolve
        inquiry.conclusion = "PostgreSQL handles current load"
        inquiry.conclusion_confidence = 0.85
        inquiry.status = InquiryStatus.RESOLVED
        inquiry.resolved_at = timezone.now()
        inquiry.save()
        
        self.assertTrue(inquiry.is_resolved())
        self.assertFalse(inquiry.is_active())
        self.assertEqual(inquiry.conclusion_confidence, 0.85)


class InquiryServiceTests(TestCase):
    """Test InquiryService"""
    
    def setUp(self):
        # Create test case
        self.case = Case.objects.create(
            title="Test Case",
            description="Test case for inquiries"
        )
        
        # Create test event
        self.event = Event.objects.create(
            event_type=EventType.CHAT_MESSAGE_SENT,
            payload={"message": "test"}
        )
    
    def test_resolve_inquiry_service(self):
        """Test resolving inquiry via service"""
        inquiry = Inquiry.objects.create(
            case=self.case,
            title="Is PostgreSQL faster?",
            elevation_reason=ElevationReason.USER_CREATED,
            sequence_index=0
        )
        
        resolved = InquiryService.resolve_inquiry(
            inquiry=inquiry,
            conclusion="PostgreSQL handles current load but not peak",
            conclusion_confidence=0.85
        )
        
        self.assertEqual(resolved.status, InquiryStatus.RESOLVED)
        self.assertEqual(resolved.conclusion_confidence, 0.85)
        self.assertIsNotNone(resolved.resolved_at)
    
    def test_get_case_inquiry_stats(self):
        """Test getting case inquiry statistics"""
        # Create various inquiries
        Inquiry.objects.create(
            case=self.case,
            title="Inquiry 1",
            elevation_reason=ElevationReason.USER_CREATED,
            sequence_index=0,
            status=InquiryStatus.OPEN
        )
        Inquiry.objects.create(
            case=self.case,
            title="Inquiry 2",
            elevation_reason=ElevationReason.REPETITION,
            sequence_index=1,
            status=InquiryStatus.INVESTIGATING
        )
        Inquiry.objects.create(
            case=self.case,
            title="Inquiry 3",
            elevation_reason=ElevationReason.CONFLICT,
            sequence_index=2,
            status=InquiryStatus.RESOLVED,
            priority=5
        )
        
        stats = InquiryService.get_case_inquiry_stats(self.case)
        
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['open'], 1)
        self.assertEqual(stats['investigating'], 1)
        self.assertEqual(stats['resolved'], 1)
        self.assertEqual(stats['high_priority'], 1)
