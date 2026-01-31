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


class SignalTemperature(models.TextChoices):
    """Memory tier - how readily accessible is this signal"""
    HOT = 'hot', 'Hot (Always in Context)'
    WARM = 'warm', 'Warm (Retrieved on Demand)'
    COLD = 'cold', 'Cold (Archival)'


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
    
    # Memory tier (for retrieval optimization)
    temperature = models.CharField(
        max_length=10,
        choices=SignalTemperature.choices,
        default=SignalTemperature.WARM,
        db_index=True,
        help_text="Memory tier - hot=always loaded, warm=retrieved, cold=archival"
    )
    
    # Access tracking (for adaptive temperature calculation)
    access_count = models.IntegerField(
        default=0,
        help_text="How many times this signal was retrieved for context"
    )
    last_accessed = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time this signal was included in LLM context"
    )
    
    # User can pin signals to hot tier
    pinned_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="User pinned this signal to always include in context"
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
            models.Index(fields=['temperature', 'case']),  # Memory tier queries
            models.Index(fields=['thread', 'temperature']),  # Hot signals per thread
            models.Index(fields=['access_count', 'last_accessed']),  # Frequently accessed
        ]
    
    def __str__(self):
        return f"{self.type}: {self.text[:50]}..."
    
    def calculate_temperature(self):
        """
        Adaptive temperature calculation (ARM-style).
        
        Hot if:
        - User pinned
        - Very recent (< 5 messages ago in thread)
        - High access count (> 10 retrievals)
        - High confidence + recently accessed
        
        Cold if:
        - Dismissed
        - Very old + low access
        - Contradicted + low confidence
        
        Warm otherwise
        """
        from django.utils import timezone
        from datetime import timedelta
        
        # User override
        if self.pinned_at:
            return SignalTemperature.HOT
        
        # Dismissed/archived
        if self.dismissed_at:
            return SignalTemperature.COLD
        
        # Recent in thread (last 5 messages)
        if self.thread:
            from apps.chat.models import Message
            recent_message_count = Message.objects.filter(
                thread=self.thread
            ).count()
            
            # If this signal is from one of the last 5 messages
            if self.sequence_index >= max(0, recent_message_count - 5):
                return SignalTemperature.HOT
        
        # Frequently accessed
        if self.access_count >= 10:
            return SignalTemperature.HOT
        
        # Old + rarely accessed
        age_days = (timezone.now() - self.created_at).days
        if age_days > 30 and self.access_count < 2:
            return SignalTemperature.COLD
        
        # Contradicted + low confidence
        if self.contradicted_by.exists() and self.confidence < 0.5:
            return SignalTemperature.COLD
        
        # Default: warm (retrieved on-demand)
        return SignalTemperature.WARM
    
    def mark_accessed(self):
        """Mark this signal as accessed (for tracking)"""
        from django.utils import timezone
        self.access_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['access_count', 'last_accessed'])
