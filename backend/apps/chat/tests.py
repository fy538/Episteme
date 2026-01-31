"""
Tests for chat app
"""
from django.test import TestCase
from django.contrib.auth.models import User

from .models import ChatThread, Message, MessageRole
from .services import ChatService
from apps.events.models import Event, EventType


class ChatServiceTest(TestCase):
    """Test ChatService"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_create_thread(self):
        """Test creating a chat thread"""
        thread = ChatService.create_thread(
            user=self.user,
            title='Test Thread'
        )
        
        self.assertIsNotNone(thread.id)
        self.assertEqual(thread.title, 'Test Thread')
        self.assertEqual(thread.user, self.user)
    
    def test_create_user_message(self):
        """Test creating a user message"""
        thread = ChatService.create_thread(user=self.user)
        
        message = ChatService.create_user_message(
            thread_id=thread.id,
            content='Hello, world!',
            user=self.user
        )
        
        self.assertIsNotNone(message.id)
        self.assertEqual(message.content, 'Hello, world!')
        self.assertEqual(message.role, MessageRole.USER)
        self.assertEqual(message.thread, thread)
        
        # Check event was created
        event = Event.objects.get(id=message.event_id)
        self.assertEqual(event.type, EventType.USER_MESSAGE_CREATED)
        self.assertEqual(event.payload['content'], 'Hello, world!')
    
    def test_create_assistant_message(self):
        """Test creating an assistant message"""
        thread = ChatService.create_thread(user=self.user)
        
        message = ChatService.create_assistant_message(
            thread_id=thread.id,
            content='I am an assistant',
            metadata={'model': 'test'}
        )
        
        self.assertIsNotNone(message.id)
        self.assertEqual(message.content, 'I am an assistant')
        self.assertEqual(message.role, MessageRole.ASSISTANT)
        self.assertEqual(message.metadata['model'], 'test')
