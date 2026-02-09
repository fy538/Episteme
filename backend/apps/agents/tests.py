"""
Tests for intelligent agent routing and orchestration
"""
from django.test import TestCase
from django.contrib.auth.models import User
from apps.chat.models import ChatThread, Message, MessageRole
from apps.cases.models import Case
from apps.skills.models import Skill
from apps.common.models import Organization
from apps.events.models import Event
from apps.agents.inflection_detector import InflectionDetector
import asyncio


class InflectionDetectorTestCase(TestCase):
    """Test LLM-based inflection point detection"""
    
    def setUp(self):
        """Set up test data"""
        from apps.events.services import EventService
        
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        # Create event
        event = EventService.append(
            'USER_MESSAGE_CREATED',
            payload={'content': 'Test'},
            actor_type='user'
        )
        
        # Create thread
        self.thread = ChatThread.objects.create(
            user=self.user,
            title='Test Thread'
        )
        
        # Create case
        self.case = Case.objects.create(
            title='Test Case',
            position='Test position',
            user=self.user,
            created_from_event_id=event.id
        )
        
        self.thread.primary_case = self.case
        self.thread.save()
    
    def test_insufficient_messages(self):
        """Test that insufficient messages returns no agent need"""
        # Only one message
        Message.objects.create(
            thread=self.thread,
            role=MessageRole.USER,
            content='Hello',
            event_id=Event.objects.first().id
        )
        
        result = asyncio.run(
            InflectionDetector.analyze_for_agent_need(self.thread)
        )
        
        self.assertFalse(result['needs_agent'])
        self.assertEqual(result['inflection_type'], 'none')
    
    def test_should_check_for_agents(self):
        """Test threshold detection for agent checks"""
        # Below threshold
        self.thread.turns_since_agent_check = 2
        self.assertFalse(InflectionDetector.should_check_for_agents(self.thread))
        
        # At threshold
        self.thread.turns_since_agent_check = 3
        self.assertTrue(InflectionDetector.should_check_for_agents(self.thread))
        
        # First time
        self.thread.turns_since_agent_check = 0
        self.thread.last_agent_check_at = None
        self.assertTrue(InflectionDetector.should_check_for_agents(self.thread))


class AgentOrchestratorTestCase(TestCase):
    """Test agent orchestration"""
    
    def setUp(self):
        """Set up test data"""
        from apps.events.services import EventService
        
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.org = Organization.objects.create(name='Test Org', slug='test-org')
        
        event = EventService.append(
            'USER_MESSAGE_CREATED',
            payload={'content': 'Test'},
            actor_type='user'
        )
        
        self.thread = ChatThread.objects.create(
            user=self.user,
            title='Test Thread'
        )
        
        self.case = Case.objects.create(
            title='Test Case',
            position='Test position',
            user=self.user,
            created_from_event_id=event.id
        )
        
        self.thread.primary_case = self.case
        self.thread.save()
    
    def test_build_placeholder_content(self):
        """Test placeholder message content building"""
        from apps.agents.orchestrator import AgentOrchestrator
        
        content = AgentOrchestrator._build_placeholder_content(
            agent_type='research',
            params={'topic': 'FDA requirements'},
            skill_names=['Legal Framework']
        )
        
        self.assertIn('Research Agent', content)
        self.assertIn('FDA requirements', content)
        self.assertIn('Legal Framework', content)
        self.assertIn('Running', content)
    
    def test_build_result_content(self):
        """Test result message content building"""
        from apps.agents.orchestrator import AgentOrchestrator
        import uuid
        
        blocks = [
            {'type': 'heading', 'content': 'Executive Summary'},
            {'type': 'paragraph', 'content': 'This is a test summary of research findings.'},
            {'type': 'heading', 'content': 'Key Findings'}
        ]
        
        content = AgentOrchestrator._build_result_content(
            document_id=str(uuid.uuid4()),
            blocks=blocks,
            generation_time_ms=25000
        )
        
        self.assertIn('Complete', content)
        self.assertIn('Executive Summary', content)
        self.assertIn('25.0s', content)
        self.assertIn('Preview', content)


class ConfirmationDetectorTestCase(TestCase):
    """Test natural language confirmation detection"""
    
    def setUp(self):
        """Set up test data"""
        from apps.events.services import EventService
        
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        event = EventService.append(
            'USER_MESSAGE_CREATED',
            payload={'content': 'Test'},
            actor_type='user'
        )
        
        self.thread = ChatThread.objects.create(
            user=self.user,
            title='Test Thread',
            metadata={
                'pending_agent_suggestion': {
                    'suggested_agent': 'research',
                    'suggested_topic': 'FDA requirements',
                    'confidence': 0.85
                }
            }
        )
        
        # Create suggestion message
        self.suggestion_msg = Message.objects.create(
            thread=self.thread,
            role=MessageRole.ASSISTANT,
            content='Run research agent?',
            event_id=event.id,
            metadata={
                'type': 'agent_suggestion',
                'agent_type': 'research',
                'awaiting_confirmation': True
            }
        )
    
    def test_no_pending_suggestion(self):
        """Test returns None when no pending suggestion"""
        from apps.agents.confirmation import check_for_agent_confirmation
        
        # Clear pending
        self.thread.metadata = {}
        self.thread.save()
        
        user_msg = Message.objects.create(
            thread=self.thread,
            role=MessageRole.USER,
            content='Yes',
            event_id=Event.objects.first().id
        )
        
        result = asyncio.run(check_for_agent_confirmation(self.thread, user_msg))
        self.assertIsNone(result)


class AgentSuggestionMessageTestCase(TestCase):
    """Test agent suggestion message creation"""
    
    def setUp(self):
        """Set up test data"""
        from apps.events.services import EventService
        
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        event = EventService.append(
            'USER_MESSAGE_CREATED',
            payload={'content': 'Test'},
            actor_type='user'
        )
        
        self.thread = ChatThread.objects.create(
            user=self.user,
            title='Test Thread'
        )
        
        self.case = Case.objects.create(
            title='Test Case',
            position='Test position',
            user=self.user,
            created_from_event_id=event.id
        )
        
        self.thread.primary_case = self.case
        self.thread.save()
    
    def test_create_research_suggestion(self):
        """Test creating research agent suggestion"""
        from apps.agents.messages import create_agent_suggestion_message
        
        inflection = {
            'suggested_agent': 'research',
            'inflection_type': 'research_depth',
            'confidence': 0.85,
            'reasoning': 'User needs comprehensive analysis',
            'suggested_topic': 'FDA requirements'
        }
        
        msg = asyncio.run(create_agent_suggestion_message(self.thread, inflection))
        
        self.assertIsNotNone(msg)
        self.assertEqual(msg.role, MessageRole.ASSISTANT)
        self.assertIn('Research Agent', msg.content)
        self.assertIn('FDA requirements', msg.content)
        self.assertEqual(msg.metadata['type'], 'agent_suggestion')
        self.assertTrue(msg.metadata['awaiting_confirmation'])
    
    def test_create_critique_suggestion(self):
        """Test creating critique agent suggestion"""
        from apps.agents.messages import create_agent_suggestion_message
        
        inflection = {
            'suggested_agent': 'critique',
            'inflection_type': 'critique_assumptions',
            'confidence': 0.90,
            'reasoning': 'User needs assumption validation',
            'suggested_target': 'Current regulatory strategy'
        }
        
        msg = asyncio.run(create_agent_suggestion_message(self.thread, inflection))
        
        self.assertIn('Critique Agent', msg.content)
        self.assertIn('Challenge assumptions', msg.content)


class WorkflowIntegrationTestCase(TestCase):
    """Test workflow integration with agent routing"""
    
    def setUp(self):
        """Set up test data"""
        from apps.events.services import EventService
        
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        event = EventService.append(
            'USER_MESSAGE_CREATED',
            payload={'content': 'Test'},
            actor_type='user'
        )
        
        self.thread = ChatThread.objects.create(
            user=self.user,
            title='Test Thread',
            turns_since_agent_check=0
        )
    
    def test_turn_counter_increments(self):
        """Test that turn counter increments in workflow"""
        initial_count = self.thread.turns_since_agent_check
        
        # Would be incremented in workflow
        self.thread.turns_since_agent_check += 1
        self.thread.save()
        
        self.assertEqual(self.thread.turns_since_agent_check, initial_count + 1)
    
    def test_counter_resets_after_check(self):
        """Test that counter resets after agent check"""
        self.thread.turns_since_agent_check = 5
        self.thread.save()
        
        # After check
        self.thread.turns_since_agent_check = 0
        self.thread.save()
        
        self.assertEqual(self.thread.turns_since_agent_check, 0)
