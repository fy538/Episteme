"""
Tests for Inquiry models and services
"""
from django.test import TestCase
from django.utils import timezone

from apps.inquiries.models import Inquiry, InquiryStatus, ElevationReason
from apps.inquiries.services import InquiryService
from apps.signals.models import Signal, SignalType
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
    
    def test_should_promote_high_confidence_claim(self):
        """Test auto-promotion for high confidence claims"""
        signal = Signal.objects.create(
            event=self.event,
            case=self.case,
            type=SignalType.CLAIM,
            text="PostgreSQL is faster for writes",
            normalized_text="postgresql faster writes",
            confidence=0.9,
            dedupe_key="claim-pg-fast",
            sequence_index=0
        )
        
        should_promote, reason, title = InquiryService.should_promote_to_inquiry(signal, self.case)
        
        self.assertTrue(should_promote)
        self.assertEqual(reason, ElevationReason.HIGH_STRENGTH)
    
    def test_should_promote_repeated_signal(self):
        """Test auto-promotion for repeated signals"""
        # Create 3 signals with same dedupe_key
        for i in range(3):
            Signal.objects.create(
                event=self.event,
                case=self.case,
                type=SignalType.ASSUMPTION,
                text="Users will accept eventual consistency",
                normalized_text="users accept eventual consistency",
                confidence=0.7,
                dedupe_key="assumption-eventual-consistency",
                sequence_index=i
            )
        
        signal = Signal.objects.filter(dedupe_key="assumption-eventual-consistency").first()
        should_promote, reason, title = InquiryService.should_promote_to_inquiry(signal, self.case)
        
        self.assertTrue(should_promote)
        self.assertEqual(reason, ElevationReason.REPETITION)
    
    def test_create_inquiry_from_signal(self):
        """Test creating inquiry from signal"""
        signal = Signal.objects.create(
            event=self.event,
            case=self.case,
            type=SignalType.CLAIM,
            text="PostgreSQL is faster for writes",
            normalized_text="postgresql faster writes",
            confidence=0.9,
            dedupe_key="claim-pg-fast",
            sequence_index=0
        )
        
        inquiry = InquiryService.create_inquiry_from_signal(
            signal=signal,
            case=self.case,
            elevation_reason=ElevationReason.HIGH_STRENGTH
        )
        
        self.assertIsNotNone(inquiry)
        self.assertEqual(inquiry.case, self.case)
        self.assertEqual(inquiry.elevation_reason, ElevationReason.HIGH_STRENGTH)
        
        # Signal should be linked to inquiry
        signal.refresh_from_db()
        self.assertEqual(signal.inquiry, inquiry)
    
    def test_link_similar_signals_to_inquiry(self):
        """Test that similar signals are auto-linked to inquiry"""
        # Create 3 similar signals
        signals = []
        for i in range(3):
            sig = Signal.objects.create(
                event=self.event,
                case=self.case,
                type=SignalType.CLAIM,
                text="PostgreSQL is faster for writes",
                normalized_text="postgresql faster writes",
                confidence=0.9,
                dedupe_key="claim-pg-fast",
                sequence_index=i
            )
            signals.append(sig)
        
        # Promote first signal
        inquiry = InquiryService.create_inquiry_from_signal(
            signal=signals[0],
            case=self.case,
            elevation_reason=ElevationReason.REPETITION
        )
        
        # All signals should be linked
        for signal in signals:
            signal.refresh_from_db()
            self.assertEqual(signal.inquiry, inquiry)
        
        # Inquiry should have all related signals
        self.assertEqual(inquiry.related_signals.count(), 3)
    
    def test_get_promotion_suggestions(self):
        """Test getting promotion suggestions"""
        # Create high-confidence claim
        Signal.objects.create(
            event=self.event,
            case=self.case,
            type=SignalType.CLAIM,
            text="PostgreSQL is faster",
            normalized_text="postgresql faster",
            confidence=0.95,
            dedupe_key="claim-pg-fast",
            sequence_index=0
        )
        
        # Create repeated assumption (3x)
        for i in range(3):
            Signal.objects.create(
                event=self.event,
                case=self.case,
                type=SignalType.ASSUMPTION,
                text="Users accept eventual consistency",
                normalized_text="users accept eventual consistency",
                confidence=0.7,
                dedupe_key="assumption-eventual",
                sequence_index=i + 1
            )
        
        suggestions = InquiryService.get_promotion_suggestions(self.case)
        
        # Should have 2 suggestions
        self.assertEqual(len(suggestions), 2)
        
        # Check that each has required fields
        for suggestion in suggestions:
            self.assertIn('signal', suggestion)
            self.assertIn('reason', suggestion)
            self.assertIn('suggested_title', suggestion)
            self.assertIn('similar_count', suggestion)
    
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
