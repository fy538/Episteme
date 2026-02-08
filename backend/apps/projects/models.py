"""
Project models - top-level containers for organizing work
"""
from typing import Dict, Any
from django.db import models
from django.contrib.auth.models import User

from apps.common.models import TimestampedModel, UUIDModel


class Project(UUIDModel, TimestampedModel):
    """
    Top-level container for related cases, documents, and work
    
    A project aggregates:
    - Multiple cases (investigations)
    - Documents (uploaded/referenced)
    - Artifacts (outputs)
    - Analytics (themes, timelines)
    """
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    
    # Ownership
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    
    # Cached aggregates (updated periodically)
    total_signals = models.IntegerField(default=0)
    total_cases = models.IntegerField(default=0)
    total_documents = models.IntegerField(default=0)
    
    # Top themes (from signal clustering)
    top_themes = models.JSONField(
        default=list,
        blank=True,
        help_text="Top 5 themes across project signals"
    )
    
    # Status
    is_archived = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['user', 'is_archived']),
        ]
    
    def __str__(self):
        return self.title


class Document(UUIDModel, TimestampedModel):
    """
    Uploaded or referenced document
    
    Documents are chunked and indexed for semantic search (Cursor-style).
    Full context is preserved - no lossy signal extraction.
    Documents can be cited as evidence in inquiries.
    """
    title = models.CharField(max_length=500)
    
    # Content
    source_type = models.CharField(
        max_length=20,
        choices=[
            ('upload', 'Uploaded File'),
            ('url', 'External URL'),
            ('text', 'Pasted Text'),
        ]
    )
    
    # Local file storage
    file_path = models.FileField(
        upload_to='documents/',
        null=True,
        blank=True,
        help_text="Local file path for uploaded documents"
    )
    
    file_url = models.CharField(
        max_length=1000,
        blank=True,
        help_text="S3 URL for uploads, or external URL"
    )
    
    content_text = models.TextField(
        blank=True,
        help_text="Extracted text content"
    )
    
    # Metadata
    file_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="pdf, docx, txt, md, etc."
    )
    
    file_size = models.IntegerField(
        null=True,
        blank=True,
        help_text="Size in bytes"
    )
    
    author = models.CharField(
        max_length=500,
        blank=True,
        help_text="Document author"
    )
    
    published_date = models.DateField(
        null=True,
        blank=True,
        help_text="When document was published"
    )
    
    # Relationships
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    
    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        help_text="Optional: link to specific case"
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    
    # Processing status (updated for chunking workflow)
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('chunking', 'Chunking'),
            ('indexed', 'Indexed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    
    # Chunking metadata
    chunk_count = models.IntegerField(
        default=0,
        help_text="Number of chunks created"
    )
    
    indexed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When document was chunked and indexed"
    )
    
    # Credibility (user can adjust)
    user_rating = models.IntegerField(
        null=True,
        blank=True,
        help_text="User's credibility rating 1-5 stars"
    )
    
    notes = models.TextField(
        blank=True,
        help_text="User's notes about this document"
    )
    
    # Evidence extraction metadata (Phase 2.2)
    evidence_count = models.IntegerField(
        default=0,
        help_text="Number of evidence items extracted"
    )
    
    # Deprecated field (kept for migration)
    signals_extracted = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', '-created_at']),
            models.Index(fields=['case', '-created_at']),
            models.Index(fields=['user', 'processing_status']),
        ]
    
    def __str__(self):
        return self.title


class EvidenceType(models.TextChoices):
    """Types of evidence extracted from documents"""
    FACT = 'fact', 'Fact'
    METRIC = 'metric', 'Metric/Data Point'
    CLAIM = 'claim', 'Claim'
    QUOTE = 'quote', 'Direct Quote'
    BENCHMARK = 'benchmark', 'Benchmark Result'


class RetrievalMethod(models.TextChoices):
    """How evidence entered the system"""
    DOCUMENT_UPLOAD = 'document_upload', 'Document Upload'
    RESEARCH_LOOP = 'research_loop', 'Research Loop'
    EXTERNAL_PASTE = 'external_paste', 'External Paste'
    URL_FETCH = 'url_fetch', 'URL Fetch'
    USER_OBSERVATION = 'user_observation', 'User Observation'
    CHAT_BRIDGED = 'chat_bridged', 'Bridged from Chat Evidence'


class Evidence(UUIDModel, TimestampedModel):
    """
    Extracted fact from a document chunk.

    Key distinction from Signal:
    - Signal = User's thought ("I assume writes are append-only")
    - Evidence = External fact ("Benchmark shows 50k writes/sec")

    Evidence provides "receipts" that can support or contradict user signals.
    This prevents circular extraction (AI docs don't create new signals).
    """
    # Content
    text = models.TextField(help_text="The extracted fact or claim")
    type = models.CharField(
        max_length=20,
        choices=EvidenceType.choices,
        help_text="Type of evidence"
    )

    # Source (pointer to exact location in document)
    chunk = models.ForeignKey(
        'DocumentChunk',
        on_delete=models.CASCADE,
        related_name='evidence',
        help_text="Chunk this evidence was extracted from"
    )

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='evidence',
        help_text="Document this evidence came from"
    )

    # Credibility
    extraction_confidence = models.FloatField(
        help_text="How confident the LLM was in this extraction (0.0-1.0)"
    )

    user_credibility_rating = models.IntegerField(
        null=True,
        blank=True,
        help_text="User's rating of this evidence (1-5 stars)"
    )

    # Embedding (for similarity search)
    embedding = models.JSONField(
        null=True,
        blank=True,
        help_text="Semantic embedding (384-dim)"
    )

    # Provenance — how and where this evidence was found
    source_url = models.URLField(
        max_length=2000,
        blank=True,
        help_text="URL where this evidence was found"
    )
    source_title = models.CharField(
        max_length=500,
        blank=True,
        help_text="Title of the source (article, paper, page)"
    )
    source_domain = models.CharField(
        max_length=255,
        blank=True,
        help_text="Domain of the source URL"
    )
    source_published_date = models.DateField(
        null=True,
        blank=True,
        help_text="Publication date of the source"
    )
    retrieval_method = models.CharField(
        max_length=30,
        choices=RetrievalMethod.choices,
        default=RetrievalMethod.DOCUMENT_UPLOAD,
        help_text="How this evidence entered the system"
    )

    # Cross-link to inquiry evidence (for bridged evidence)
    inquiry_evidence = models.ForeignKey(
        'inquiries.Evidence',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_evidence',
        help_text="If bridged from inquiry evidence"
    )

    # Metadata
    extracted_at = models.DateTimeField(auto_now_add=True)

    # Knowledge graph edges — Link to Signals
    supports_signals = models.ManyToManyField(
        'signals.Signal',
        related_name='supported_by_evidence',
        blank=True,
        help_text="Signals this evidence supports (provides receipts for)"
    )

    contradicts_signals = models.ManyToManyField(
        'signals.Signal',
        related_name='contradicted_by_evidence',
        blank=True,
        help_text="Signals this evidence contradicts"
    )

    class Meta:
        ordering = ['-extracted_at']
        indexes = [
            models.Index(fields=['document', 'type']),
            models.Index(fields=['chunk', '-extracted_at']),
            models.Index(fields=['type', '-extracted_at']),
            models.Index(fields=['document', 'user_credibility_rating']),
            models.Index(fields=['source_domain', '-extracted_at']),
            models.Index(fields=['retrieval_method', '-extracted_at']),
        ]

    def __str__(self):
        return f"{self.type}: {self.text[:50]}..."


class DocumentChunk(UUIDModel, TimestampedModel):
    """
    Semantic chunks for vector search - research-backed design (2024 RAG studies).
    
    Documents are split into chunks for:
    - Vector embedding and semantic search
    - Precise citation in evidence
    - Context expansion (prev/next chunks)
    - Fast retrieval without full document load
    
    Design decisions based on research:
    - 256-512 tokens per chunk (optimal for retrieval)
    - 10-20% overlap (balances context and efficiency)
    - PostgreSQL storage (28x faster than external vector DBs)
    - Context linking (critical for quality)
    """
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='chunks'
    )
    
    # Chunk content
    chunk_index = models.IntegerField(
        help_text="Order in document (0, 1, 2...)"
    )
    
    chunk_text = models.TextField(
        help_text="The actual chunk content"
    )
    
    token_count = models.IntegerField(
        help_text="Number of tokens in chunk (using tiktoken)"
    )
    
    # Location in original document
    span = models.JSONField(
        default=dict,
        help_text="Location info: {page, paragraph, start_char, end_char}"
    )
    
    # NEW: Store embeddings in PostgreSQL (JSON for Phase 2, pgvector for Phase 3)
    embedding = models.JSONField(
        null=True,
        blank=True,
        help_text="Vector embedding (384-dim from sentence-transformers). JSON now, pgvector later at scale"
    )
    
    # NEW: Context linking (research-validated pattern for "fetch surrounding chunks")
    prev_chunk_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Previous chunk ID for context expansion"
    )
    
    next_chunk_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Next chunk ID for context expansion"
    )
    
    # NEW: Track chunking strategy
    chunking_strategy = models.CharField(
        max_length=50,
        default='recursive_token',
        choices=[
            ('recursive_token', 'Recursive Token-Based'),
            ('semantic', 'Semantic Chunking'),
            ('page_level', 'Page-Level'),
            ('paragraph', 'Paragraph-Based'),
        ],
        help_text="Chunking method used (for experimentation and versioning)"
    )
    
    # Optional: LLM-generated summary
    summary = models.TextField(
        blank=True,
        help_text="AI-generated summary of chunk"
    )
    
    class Meta:
        ordering = ['document', 'chunk_index']
        indexes = [
            models.Index(fields=['document', 'chunk_index']),
            models.Index(fields=['document', 'prev_chunk_id']),  # Context navigation
            models.Index(fields=['document', 'next_chunk_id']),  # Context navigation
        ]
    
    def __str__(self):
        preview = self.chunk_text[:50] if self.chunk_text else ''
        return f"Chunk {self.chunk_index} of {self.document.title}: {preview}..."
    
    def get_with_context(self, window: int = 1) -> Dict[str, Any]:
        """
        Get this chunk with surrounding context.
        
        Research shows context expansion improves retrieval quality.
        
        Args:
            window: Number of chunks before/after to include
        
        Returns:
            Dict with this chunk + context chunks
        """
        result = {
            'main': self,
            'before': [],
            'after': [],
        }
        
        # Get previous chunks
        if self.prev_chunk_id:
            prev_chunks = DocumentChunk.objects.filter(
                document=self.document,
                chunk_index__lt=self.chunk_index,
                chunk_index__gte=self.chunk_index - window
            ).order_by('chunk_index')
            result['before'] = list(prev_chunks)
        
        # Get next chunks
        if self.next_chunk_id:
            next_chunks = DocumentChunk.objects.filter(
                document=self.document,
                chunk_index__gt=self.chunk_index,
                chunk_index__lte=self.chunk_index + window
            ).order_by('chunk_index')
            result['after'] = list(next_chunks)
        
        return result
