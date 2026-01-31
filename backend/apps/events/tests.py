"""
Tests for events app
"""
import uuid
from django.test import TestCase
from django.contrib.auth.models import User

from .models import Event, EventType, ActorType
from .services import EventService


class EventServiceTest(TestCase):
    """Test EventService"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_append_event(self):
        """Test appending an event"""
        event = EventService.append(
            event_type=EventType.USER_MESSAGE_CREATED,
            payload={'content': 'Hello, world!'},
            actor_type=ActorType.USER,
            actor_id=self.user.id,
        )
        
        self.assertIsNotNone(event.id)
        self.assertEqual(event.type, EventType.USER_MESSAGE_CREATED)
        self.assertEqual(event.payload['content'], 'Hello, world!')
        self.assertEqual(event.actor_type, ActorType.USER)
    
    def test_events_are_immutable(self):
        """Test that events cannot be updated"""
        event = EventService.append(
            event_type=EventType.WORKFLOW_STARTED,
            payload={'name': 'test'},
        )
        
        # Try to update
        with self.assertRaises(ValueError):
            event.type = EventType.WORKFLOW_COMPLETED
            event.save()
    
    def test_events_cannot_be_deleted(self):
        """Test that events cannot be deleted"""
        event = EventService.append(
            event_type=EventType.WORKFLOW_STARTED,
            payload={'name': 'test'},
        )
        
        with self.assertRaises(ValueError):
            event.delete()
    
    def test_get_case_timeline(self):
        """Test getting case timeline"""
        case_id = uuid.uuid4()
        
        # Create some events
        EventService.append(
            event_type=EventType.CASE_CREATED,
            payload={'title': 'Test Case'},
            case_id=case_id,
        )
        
        EventService.append(
            event_type=EventType.CASE_PATCHED,
            payload={'changes': {}},
            case_id=case_id,
        )
        
        # Get timeline
        timeline = EventService.get_case_timeline(case_id)
        
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[0].type, EventType.CASE_CREATED)
        self.assertEqual(timeline[1].type, EventType.CASE_PATCHED)
