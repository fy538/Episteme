"""
Signal models - Extracted meaning from events (Phase 1)
"""
import uuid
from django.db import models

from apps.common.models import TimestampedModel, UUIDModel


class SignalType(models.TextChoices):
    """Types of signals extracted from chat messages"""
    DECISION_INTENT = 'DecisionIntent', 'Decision Intent'
    CLAIM = 'Claim', 'Claim'
    GOAL = 'Goal', 'Goal'
    CONSTRAINT = 'Constraint', 'Constraint'
    ASSUMPTION = 'Assumption', 'Assumption'
    QUESTION = 'Question', 'Question'
    EVIDENCE_MENTION = 'EvidenceMention', 'Evidence Mention'


class SignalSourceType(models.TextChoices):
    """Where the signal was extracted from"""
    CHAT_MESSAGE = 'chat_message', 'Chat Message'
    DOCUMENT = 'document', 'Document'
    ARTIFACT = 'artifact', 'Artifact'  # Future
    ANALYSIS = 'analysis', 'Analysis'  # Future: derived from clustering, etc.


class Signal(UUIDModel, TimestampedModel):
    """
    Atomic unit of meaning extracted from any source
    
    Signals are raw extractions from:
    - Chat messages (user conversations)
    - Documents (uploaded PDFs, docs, etc.)
    - Artifacts (user-created outputs) - Future
    - Analysis (derived insights) - Future
    
    No premature deduplication - we keep everything and process at read time.
    
    Signals exist with confidence scores and timestamps. Important signals
    can be elevated to Inquiries for deeper investigation. Users can dismiss
    signals that are not relevant, but they remain in the history.
    """
    # Link to the event that created this signal
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.PROTECT,
        related_name='signals'
    )
    
    # Source tracking (where did this signal come from?)
    source_type = models.CharField(
        max_length=20,
        choices=SignalSourceType.choices,
        default=SignalSourceType.CHAT_MESSAGE
    )
    
    # Signal content
    type = models.CharField(max_length=50, choices=SignalType.choices, db_index=True)
    text = models.TextField(help_text="Original extracted text")
    normalized_text = models.TextField(help_text="Normalized for comparison")
    
    # Span information (where in the message this came from)
    span = models.JSONField(
        help_text="Location info: {message_id, start, end}",
        default=dict
    )
    
    # Extraction metadata
    confidence = models.FloatField(help_text="Extraction confidence 0.0-1.0")
    
    # Sequential positioning (for temporal ordering)
    sequence_index = models.IntegerField(
        help_text="Message position in thread (0, 1, 2...)"
    )
    
    # User actions
    dismissed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="If user marked this signal as not relevant"
    )
    
    # Semantic embedding (for similarity search and deduplication at read time)
    embedding = models.JSONField(
        null=True,
        blank=True,
        help_text="Semantic embedding vector (384 or 768 dim from sentence-transformers)"
    )
    
    # Deduplication (exact-match fast path)
    dedupe_key = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Hash for exact-match deduplication"
    )
    
    # Relationships
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='signals'
    )
    thread = models.ForeignKey(
        'chat.ChatThread',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='signals'
    )
    document = models.ForeignKey(
        'projects.Document',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='signals',
        help_text="If extracted from a document"
    )
    inquiry = models.ForeignKey(
        'inquiries.Inquiry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_signals',
        help_text="If this signal was elevated to or associated with an inquiry"
    )
    
    # Knowledge graph edges (Phase 2.3)
    depends_on = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='dependents',
        blank=True,
        help_text="Signals this signal depends on (assumption chains)"
    )
    
    contradicts = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='contradicted_by',
        blank=True,
        help_text="Signals this signal contradicts"
    )
    
    class Meta:
        ordering = ['sequence_index', '-created_at']  # Temporal order
        indexes = [
            models.Index(fields=['case', 'type']),
            models.Index(fields=['thread', 'sequence_index']),  # Temporal queries
            models.Index(fields=['document', 'sequence_index']),  # Document signals
            models.Index(fields=['case', 'type', 'sequence_index']),
            models.Index(fields=['source_type', 'created_at']),
            models.Index(fields=['dedupe_key', 'case']),
            models.Index(fields=['inquiry', 'created_at']),  # Signals by inquiry
            models.Index(fields=['dismissed_at']),  # Filter dismissed signals
        ]
    
    def __str__(self):
        return f"{self.type}: {self.text[:50]}..."
