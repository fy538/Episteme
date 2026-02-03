"""
Tests for companion app
"""
from django.test import TestCase
from django.contrib.auth.models import User
from apps.chat.models import ChatThread, Message, MessageRole
from apps.signals.models import Signal, SignalType
from apps.inquiries.models import Inquiry
from apps.companion.models import Reflection, InquiryHistory, ReflectionTriggerType
from apps.companion.services import CompanionService
from apps.companion.graph_analyzer import GraphAnalyzer


class ReflectionModelTest(TestCase):
    """Test Reflection model"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.thread = ChatThread.objects.create(user=self.user, title="Test Thread")
    
    def test_create_reflection(self):
        """Test creating a reflection"""
        reflection = Reflection.objects.create(
            thread=self.thread,
            reflection_text="This is a test reflection.",
            trigger_type=ReflectionTriggerType.USER_MESSAGE,
            analyzed_messages=['msg-1', 'msg-2'],
            analyzed_signals=['sig-1', 'sig-2']
        )
        
        self.assertEqual(reflection.thread, self.thread)
        self.assertEqual(reflection.trigger_type, ReflectionTriggerType.USER_MESSAGE)
        self.assertTrue(reflection.is_visible)
        self.assertIsNotNone(reflection.id)
    
    def test_reflection_ordering(self):
        """Test reflections are ordered by created_at desc"""
        r1 = Reflection.objects.create(
            thread=self.thread,
            reflection_text="First",
            trigger_type=ReflectionTriggerType.USER_MESSAGE
        )
        r2 = Reflection.objects.create(
            thread=self.thread,
            reflection_text="Second",
            trigger_type=ReflectionTriggerType.PERIODIC
        )
        
        reflections = list(Reflection.objects.filter(thread=self.thread))
        self.assertEqual(reflections[0].id, r2.id)  # Most recent first
        self.assertEqual(reflections[1].id, r1.id)


class InquiryHistoryTest(TestCase):
    """Test InquiryHistory model"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        from apps.projects.models import Project
        from apps.cases.models import Case
        
        self.project = Project.objects.create(
            user=self.user,
            title="Test Project"
        )
        self.case = Case.objects.create(
            user=self.user,
            project=self.project,
            title="Test Case",
            position="Test position",
            created_from_event_id='00000000-0000-0000-0000-000000000000'
        )
        self.inquiry = Inquiry.objects.create(
            case=self.case,
            title="Test Inquiry",
            elevation_reason='user_created',
            sequence_index=0
        )
    
    def test_create_history_entry(self):
        """Test creating inquiry history entry"""
        history = InquiryHistory.objects.create(
            inquiry=self.inquiry,
            confidence=0.75,
            reason="Initial confidence set"
        )
        
        self.assertEqual(history.inquiry, self.inquiry)
        self.assertEqual(history.confidence, 0.75)
        self.assertIsNotNone(history.timestamp)
    
    def test_confidence_tracking_signal(self):
        """Test automatic confidence tracking on inquiry save"""
        # Update inquiry confidence
        self.inquiry.conclusion_confidence = 0.80
        self.inquiry.save()
        
        # Should auto-create history entry
        history = InquiryHistory.objects.filter(inquiry=self.inquiry).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.confidence, 0.80)
    
    def test_multiple_confidence_updates(self):
        """Test tracking multiple confidence changes"""
        # Update confidence multiple times
        self.inquiry.conclusion_confidence = 0.70
        self.inquiry.save()
        
        self.inquiry.conclusion_confidence = 0.85
        self.inquiry.save()
        
        self.inquiry.conclusion_confidence = 0.60
        self.inquiry.save()
        
        # Should have 3 history entries
        history = InquiryHistory.objects.filter(inquiry=self.inquiry).order_by('-timestamp')
        self.assertEqual(history.count(), 3)
        self.assertEqual(history[0].confidence, 0.60)  # Most recent
        self.assertEqual(history[1].confidence, 0.85)
        self.assertEqual(history[2].confidence, 0.70)  # Oldest


class GraphAnalyzerTest(TestCase):
    """Test GraphAnalyzer pattern detection"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        from apps.projects.models import Project
        from apps.cases.models import Case
        
        self.project = Project.objects.create(
            user=self.user,
            title="Test Project"
        )
        self.case = Case.objects.create(
            user=self.user,
            project=self.project,
            title="Test Case",
            position="Test position",
            created_from_event_id='00000000-0000-0000-0000-000000000000'
        )
        self.thread = ChatThread.objects.create(
            user=self.user,
            title="Test Thread",
            primary_case=self.case
        )
        self.analyzer = GraphAnalyzer()
    
    def test_find_ungrounded_assumptions(self):
        """Test finding assumptions without evidence"""
        # Create assumption without evidence
        from apps.events.models import Event, EventType, ActorType
        event = Event.objects.create(
            type=EventType.SIGNAL_EXTRACTED,
            actor_type=ActorType.SYSTEM,
            payload={}
        )
        
        Signal.objects.create(
            event=event,
            thread=self.thread,
            case=self.case,
            type=SignalType.ASSUMPTION,
            text="We need better performance",
            normalized_text="we need better performance",
            confidence=0.8
        )
        
        # Run analyzer (sync wrapper for async)
        import asyncio
        patterns = asyncio.run(self.analyzer.find_patterns(self.thread.id))
        
        self.assertEqual(len(patterns['ungrounded_assumptions']), 1)
        self.assertIn('We need better performance', patterns['ungrounded_assumptions'][0]['text'])


class CompanionServiceTest(TestCase):
    """Test CompanionService"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.thread = ChatThread.objects.create(user=self.user, title="Test Thread")
        self.service = CompanionService()
    
    def test_track_background_work_empty(self):
        """Test tracking with no recent activity"""
        import asyncio
        
        activity = asyncio.run(self.service.track_background_work(self.thread.id))
        
        self.assertEqual(activity['signals_extracted']['count'], 0)
        self.assertEqual(activity['evidence_linked']['count'], 0)
        self.assertEqual(activity['connections_built']['count'], 0)
        self.assertEqual(len(activity['confidence_updates']), 0)
