"""
Chat models - Threads and Messages
"""
import uuid
from django.db import models
from django.contrib.auth.models import User

from apps.common.models import TimestampedModel, UUIDModel


class ChatThread(UUIDModel, TimestampedModel):
    """
    A conversation thread
    """
    title = models.CharField(max_length=500, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_threads')
    
    # Optional: link to a case if this thread is associated with one
    # This is set when a case is created from this thread
    primary_case = models.ForeignKey(
        'cases.Case',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_thread'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return self.title or f"Thread {self.id}"


class MessageRole(models.TextChoices):
    USER = 'user', 'User'
    ASSISTANT = 'assistant', 'Assistant'
    SYSTEM = 'system', 'System'


class Message(UUIDModel, TimestampedModel):
    """
    Individual message in a chat thread
    
    This is a read model (optimized for queries).
    Source of truth is in the Event store.
    """
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=MessageRole.choices)
    content = models.TextField()
    
    # Link back to the event that created this message
    event_id = models.UUIDField(unique=True, db_index=True)
    
    # Optional metadata
    metadata = models.JSONField(default=dict, blank=True)  # model, latency, etc.
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['thread', 'created_at']),
            models.Index(fields=['event_id']),
        ]
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
