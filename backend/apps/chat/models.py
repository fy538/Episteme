"""
Chat models - Threads and Messages
"""
import uuid
from django.db import models
from django.contrib.auth.models import User
from pgvector.django import VectorField

from apps.common.models import TimestampedModel, UUIDModel


class ChatThread(UUIDModel, TimestampedModel):
    """
    A conversation thread
    
    Multiple threads can be associated with a single case for different purposes
    (general discussion, research, inquiry-specific, document analysis).
    """
    title = models.CharField(max_length=500, blank=True, default='New Chat')
    title_manually_edited = models.BooleanField(
        default=False,
        help_text="True if user manually renamed this thread; suppresses auto-title updates"
    )
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
    
    # Semantic embedding for cross-thread search (384-dim, from latest ConversationStructure)
    embedding = VectorField(
        dimensions=384,
        null=True,
        blank=True,
        help_text="384-dim embedding from latest ConversationStructure.context_summary"
    )

    # Pointer to the current (unsealed) episode being accumulated
    current_episode = models.ForeignKey(
        'ConversationEpisode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text="The active episode being accumulated (unsealed)"
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


class ConversationStructure(UUIDModel, TimestampedModel):
    """
    The organic companion structure for a chat thread.
    Updated by LLM as conversation progresses.
    Not a graph — flexible structure that fits the conversation topic.
    """
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='structures')
    version = models.IntegerField(default=1)

    # The organic structure — shape determined by LLM, not by us
    structure_type = models.CharField(
        max_length=30,
        help_text="e.g. decision_tree, checklist, comparison, exploration_map, flow, constraint_list, pros_cons, concept_map"
    )

    # The actual structure content — flexible JSON, schema depends on structure_type
    content = models.JSONField(default=dict)

    # Conversation state tracking
    established = models.JSONField(
        default=list,
        help_text="Confirmed facts/constraints from the conversation"
    )
    open_questions = models.JSONField(
        default=list,
        help_text="Unresolved questions (explicit and implicit)"
    )
    eliminated = models.JSONField(
        default=list,
        help_text="Eliminated options/branches with reasons"
    )

    # Summary for chat context injection (the clarifying loop)
    context_summary = models.TextField(
        default='',
        help_text="Compact text version for injecting into chat prompt"
    )

    # Rolling digest of older messages (Tier 2 memory)
    rolling_digest = models.TextField(
        default='',
        blank=True,
        help_text="LLM-generated summary of messages beyond the recent window"
    )

    # Tracking
    last_message_id = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Semantic embedding for cross-thread search (384-dim from context_summary)
    embedding = VectorField(
        dimensions=384,
        null=True,
        blank=True,
        help_text="384-dim embedding from context_summary for cross-thread reasoning search"
    )

    class Meta:
        ordering = ['-version']
        indexes = [
            models.Index(fields=['thread', '-version']),
        ]

    def __str__(self):
        return f"Structure v{self.version} ({self.structure_type}) for {self.thread_id}"


class ConversationEpisode(UUIDModel, TimestampedModel):
    """
    A topically coherent segment of conversation within a thread.

    Episodes are created and sealed by the companion service when it detects
    topic shifts. Each episode captures the reasoning state (via a snapshot
    of ConversationStructure) and gets embedded for cross-thread search.

    Lifecycle:
    1. Created as unsealed when companion detects a new topic segment
    2. Messages are linked to the current episode as they arrive
    3. When companion detects a topic shift, the current episode is sealed
       (content_summary populated, embedding generated via signal)
    4. A new episode is created for the new topic segment
    """
    thread = models.ForeignKey(
        ChatThread,
        on_delete=models.CASCADE,
        related_name='episodes'
    )
    episode_index = models.IntegerField(
        default=0,
        help_text="Sequential index within the thread (0-based)"
    )
    topic_label = models.CharField(
        max_length=200,
        blank=True,
        help_text="Brief label for the topic of this episode (3-5 words)"
    )
    content_summary = models.TextField(
        default='',
        help_text="Summary of what was discussed/established during this episode"
    )

    # Message range
    start_message = models.ForeignKey(
        'Message',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text="First message in this episode"
    )
    end_message = models.ForeignKey(
        'Message',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text="Last message in this episode (set when sealed)"
    )
    message_count = models.IntegerField(
        default=0,
        help_text="Number of messages in this episode"
    )

    # Topic shift classification (set by companion LLM)
    shift_type = models.CharField(
        max_length=20,
        choices=[
            ('initial', 'Initial'),
            ('continuous', 'Continuous'),
            ('partial_shift', 'Partial Shift'),
            ('discontinuous', 'Discontinuous'),
        ],
        default='initial',
        help_text="How this episode relates to the previous one"
    )

    # Snapshot of reasoning state when this episode was sealed
    reasoning_snapshot = models.ForeignKey(
        'ConversationStructure',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='episode',
        help_text="ConversationStructure version captured when this episode was sealed"
    )

    # Semantic embedding for cross-thread search (384-dim)
    embedding = VectorField(
        dimensions=384,
        null=True,
        blank=True,
        help_text="384-dim embedding from content_summary for cross-thread episode search"
    )

    # Seal state
    sealed = models.BooleanField(
        default=False,
        help_text="True when this episode is complete and embedding is generated"
    )
    sealed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this episode was sealed"
    )

    class Meta:
        ordering = ['episode_index']
        indexes = [
            models.Index(fields=['thread', 'episode_index']),
            models.Index(fields=['thread', '-sealed_at']),
        ]

    def __str__(self):
        label = self.topic_label or f"Episode {self.episode_index}"
        status = "sealed" if self.sealed else "active"
        return f"{label} ({status}) in {self.thread_id}"


class ResearchResult(UUIDModel, TimestampedModel):
    """Background research finding from the companion agent."""
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='research_results')
    question = models.TextField()
    answer = models.TextField(default='')
    sources = models.JSONField(default=list)
    status = models.CharField(
        max_length=20,
        choices=[
            ('researching', 'Researching'),
            ('complete', 'Complete'),
            ('failed', 'Failed'),
        ],
        default='researching',
    )
    surfaced = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    # Pre-computed embedding for semantic search (384-dim from sentence-transformers)
    embedding = VectorField(
        dimensions=384,
        null=True,
        blank=True,
        help_text="384-dim embedding from sentence-transformers"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['thread', '-created_at']),
            models.Index(fields=['thread', 'status']),
        ]

    def __str__(self):
        return f"Research: {self.question[:60]}... ({self.status})"


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
    CARD_RESEARCH_FINDING = 'card_research_finding', 'Research Finding Card'


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

    # Episode linkage for conversation memory
    episode = models.ForeignKey(
        'ConversationEpisode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages',
        help_text="The conversation episode this message belongs to"
    )

    # Source tracking for RAG-grounded responses
    source_chunks = models.ManyToManyField(
        'projects.DocumentChunk',
        blank=True,
        related_name='cited_in_messages',
        help_text="Document chunks used as RAG context for this response"
    )

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['thread', 'created_at']),
            models.Index(fields=['event_id']),
            models.Index(fields=['content_type']),  # Index for filtering by type
        ]
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
