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
    
    Multiple threads can be associated with a single case for different purposes
    (general discussion, research, inquiry-specific, document analysis).
    """
    title = models.CharField(max_length=500, blank=True, default='New Chat')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_threads')
    
    # Thread type for categorization
    thread_type = models.CharField(
        max_length=20,
        choices=[
            ('general', 'General Discussion'),
            ('research', 'Research Thread'),
            ('inquiry', 'Inquiry-Specific'),
            ('document', 'Document Analysis'),
        ],
        default='general',
        help_text="Type of conversation thread"
    )
    
    # Optional: link to a case if this thread is associated with one
    # Multiple threads can link to the same case (many-to-one relationship)
    primary_case = models.ForeignKey(
        'cases.Case',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_threads',  # Changed from 'primary_thread' to 'chat_threads'
        help_text="Case this thread is about (many threads per case supported)"
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
    
    # Agent routing state (mirrors signal extraction pattern)
    last_agent_check_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time thread was analyzed for agent needs"
    )
    turns_since_agent_check = models.IntegerField(
        default=0,
        help_text="User message count since last agent check"
    )
    last_suggested_agent = models.CharField(
        max_length=20,
        blank=True,
        help_text="Last agent type suggested (research/critique/brief)"
    )
    
    # Flexible metadata for agent state
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Flexible storage for pending agents, suggestions, etc."
    )
    
    class Meta:
        ordering = ['-updated_at']  # Sort by most recently active
        indexes = [
            models.Index(fields=['user', '-updated_at']),
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


class MessageContentType(models.TextChoices):
    """Types of message content"""
    TEXT = 'text', 'Plain Text'
    CARD_SIGNAL_EXTRACTION = 'card_signal_extraction', 'Signal Extraction Card'
    CARD_CASE_SUGGESTION = 'card_case_suggestion', 'Case Suggestion Card'
    CARD_STRUCTURE_PREVIEW = 'card_structure_preview', 'Structure Preview Card'
    CARD_RESEARCH_STATUS = 'card_research_status', 'Research Status Card'
    CARD_EVIDENCE_MAP = 'card_evidence_map', 'Evidence Map Card'
    CARD_ACTION_PROMPT = 'card_action_prompt', 'Action Prompt Card'
    CARD_ASSUMPTION_VALIDATOR = 'card_assumption_validator', 'Assumption Validator Card'


class Message(UUIDModel, TimestampedModel):
    """
    Individual message in a chat thread
    
    This is a read model (optimized for queries).
    Source of truth is in the Event store.
    """
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=MessageRole.choices)
    content = models.TextField()
    
    # Content type for rich messages
    content_type = models.CharField(
        max_length=50,
        choices=MessageContentType.choices,
        default=MessageContentType.TEXT,
        help_text="Type of message content (text or card)"
    )
    
    # Structured content for interactive cards
    structured_content = models.JSONField(
        default=None,
        null=True,
        blank=True,
        help_text="Structured data for rich message types (cards, forms, etc.)"
    )
    
    # Link back to the event that created this message
    event_id = models.UUIDField(unique=True, db_index=True)
    
    # Optional metadata
    metadata = models.JSONField(default=dict, blank=True)  # model, latency, etc.
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['thread', 'created_at']),
            models.Index(fields=['event_id']),
            models.Index(fields=['content_type']),  # Index for filtering by type
        ]
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
