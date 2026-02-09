"""
Project models - top-level containers for organizing work
"""
from django.db import models
from django.contrib.auth.models import User

from pgvector.django import VectorField, HnswIndex

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
    total_cases = models.IntegerField(default=0)
    total_documents = models.IntegerField(default=0)

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

    scope = models.CharField(
        max_length=16,
        default='project',
        choices=[('project', 'Project'), ('case', 'Case')],
        help_text="project = feeds project graph; case = only visible within owning case",
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

    # Graph extraction status (runs after processing_status reaches 'indexed')
    extraction_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('extracting', 'Extracting Nodes'),
            ('integrating', 'Integrating with Graph'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending',
        help_text="Graph extraction pipeline status"
    )

    extraction_error = models.TextField(
        blank=True,
        help_text="Error details if graph extraction failed"
    )

    # Progressive processing status for SSE streaming
    processing_progress = models.JSONField(
        default=dict,
        blank=True,
        help_text="Progressive processing status for SSE streaming"
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
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', '-created_at']),
            models.Index(fields=['case', '-created_at']),
            models.Index(fields=['user', 'processing_status']),
            models.Index(fields=['project', 'scope']),
        ]
    
    def __str__(self):
        return self.title


class DocumentChunk(UUIDModel, TimestampedModel):
    """
    Semantic chunks for vector search - research-backed design (2024 RAG studies).
    
    Documents are split into chunks for:
    - Vector embedding and semantic search
    - Graph node provenance (Node.source_chunks M2M)
    - RAG retrieval during chat
    - Fast retrieval without full document load

    Design decisions:
    - 512 tokens per chunk, 15% overlap (optimal for retrieval)
    - PostgreSQL + pgvector storage with HNSW index
    - Content-addressable dedup via SHA256 hash
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
    
    embedding = VectorField(
        dimensions=384,
        null=True,
        blank=True,
        help_text="384-dim embedding from sentence-transformers"
    )

    content_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="SHA256 of chunk_text for deduplication"
    )

    class Meta:
        ordering = ['document', 'chunk_index']
        indexes = [
            models.Index(fields=['document', 'chunk_index']),
            HnswIndex(
                name='chunk_embedding_hnsw_idx',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops'],
            ),
        ]

    def __str__(self):
        preview = self.chunk_text[:50] if self.chunk_text else ''
        return f"Chunk {self.chunk_index} of {self.document.title}: {preview}..."
