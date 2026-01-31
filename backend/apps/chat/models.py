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
    title = models.CharField(max_length=500, blank=True, default='New Chat')
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

    # Optional project association
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_threads'
    )

    # Archive flag for hiding old conversations
    archived = models.BooleanField(default=False)
    
    # Signal extraction batching (Phase 1 optimization)
    last_extraction_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time signals were extracted from this thread"
    )
    chars_since_extraction = models.IntegerField(
        default=0,
        help_text="Character count accumulated since last extraction"
    )
    turns_since_extraction = models.IntegerField(
        default=0,
        help_text="User message count since last extraction"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return self.title or f"Thread {self.id}"
    
    def should_extract_signals(self, char_threshold=500, turn_threshold=5):
        """
        Check if extraction threshold is met.
        
        Threshold = chars_since_extraction >= char_threshold OR
                    turns_since_extraction >= turn_threshold
        
        Args:
            char_threshold: Minimum characters to accumulate (default: 500)
            turn_threshold: Minimum turns to accumulate (default: 5)
            
        Returns:
            Boolean indicating if extraction should be triggered
        """
        return (
            self.chars_since_extraction >= char_threshold or
            self.turns_since_extraction >= turn_threshold
        )
    
    def accumulate_for_extraction(self, message_length: int):
        """
        Accumulate message stats for batched extraction.
        
        Called after each user message to track when to extract.
        
        Args:
            message_length: Length of user message in characters
        """
        self.chars_since_extraction += message_length
        self.turns_since_extraction += 1
        self.save(update_fields=['chars_since_extraction', 'turns_since_extraction'])
    
    def reset_extraction_counters(self):
        """
        Reset counters after extraction is complete.
        
        Called after batch extraction to start accumulating again.
        """
        from django.utils import timezone
        self.last_extraction_at = timezone.now()
        self.chars_since_extraction = 0
        self.turns_since_extraction = 0
        self.save(update_fields=[
            'last_extraction_at',
            'chars_since_extraction',
            'turns_since_extraction'
        ])


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
