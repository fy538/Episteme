"""
Project services
"""
import uuid
from typing import Optional
from django.contrib.auth.models import User
from django.db import transaction

from .models import Project, Document
from apps.events.services import EventService
from apps.events.models import EventType, ActorType


class ProjectService:
    """Service for project operations"""
    
    @staticmethod
    @transaction.atomic
    def create_project(user: User, title: str, description: str = "") -> Project:
        """
        Create a new project
        
        Args:
            user: User creating the project
            title: Project title
            description: Project description
        
        Returns:
            Created Project
        """
        project = Project.objects.create(
            user=user,
            title=title,
            description=description,
        )
        
        # Emit event
        EventService.append(
            event_type=EventType.WORKFLOW_STARTED,  # Or create ProjectCreated type
            payload={
                'project_id': str(project.id),
                'title': title,
            },
            actor_type=ActorType.USER,
            actor_id=user.id,
        )
        
        return project
    
    @staticmethod
    def suggest_project_title(case_title: str, max_length: int = 60) -> str:
        """
        Derive a project title from a case title when none is provided.

        This is intentionally simple — projects are higher-level containers
        and users usually name them deliberately. Used only for the
        new-project-with-case creation flow.
        """
        if len(case_title) <= max_length:
            return case_title
        # Truncate at word boundary
        truncated = case_title[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length // 2:
            truncated = truncated[:last_space]
        return truncated.rstrip('.,;:')

    @staticmethod
    def update_project_stats(project_id: uuid.UUID):
        """
        Update cached aggregates for a project
        
        Args:
            project_id: Project to update
        """
        project = Project.objects.get(id=project_id)

        # Count cases
        total_cases = project.cases.count()

        # Count documents
        total_documents = project.documents.count()

        project.total_cases = total_cases
        project.total_documents = total_documents
        project.save(update_fields=[
            'total_cases', 'total_documents', 'updated_at',
        ])


class DocumentService:
    """Service for document operations"""
    
    @staticmethod
    @transaction.atomic
    def create_document(
        user: User,
        project_id: uuid.UUID,
        title: str,
        source_type: str,
        content_text: str = "",
        file_url: str = "",
        case_id: Optional[uuid.UUID] = None,
    ) -> Document:
        """
        Create a new document
        
        Args:
            user: User creating the document
            project_id: Project this document belongs to
            title: Document title
            source_type: 'upload', 'url', or 'text'
            content_text: Text content (for source_type='text')
            file_url: URL (for source_type='url' or 'upload')
            case_id: Optional case to link to
        
        Returns:
            Created Document
        """
        from apps.projects.models import Project
        
        project = Project.objects.get(id=project_id)
        
        document = Document.objects.create(
            user=user,
            project=project,
            case_id=case_id,
            scope='case' if case_id else 'project',
            title=title,
            source_type=source_type,
            content_text=content_text,
            file_url=file_url,
            processing_status='pending',
        )
        
        # Emit event
        EventService.append(
            event_type=EventType.WORKFLOW_STARTED,  # Or DocumentCreated
            payload={
                'document_id': str(document.id),
                'title': title,
                'source_type': source_type,
            },
            actor_type=ActorType.USER,
            actor_id=user.id,
            case_id=case_id,
        )
        
        return document
    
    @staticmethod
    def process_document(document: Document, on_progress=None) -> Document:
        """
        Process document with research-backed pipeline (2024 RAG standards).

        Pipeline:
        1. Extract text from file
        2. Chunk with RecursiveTokenChunker (512 tokens, 15% overlap)
        3. Generate embeddings (sentence-transformers)
        4. Store in PostgreSQL with context linking

        Note: Transaction scope is intentionally narrow — only wraps DB bulk
        writes.  File I/O, ML inference, and LLM calls happen outside
        transactions to avoid holding locks during slow operations.

        Args:
            document: Document to process
            on_progress: Optional callback(stage, label, stage_index, counts)
                for real-time progress reporting.

        Returns:
            Updated document
        """
        import logging as _logging
        from django.utils import timezone
        from apps.projects.document_processor import DocumentProcessor
        from apps.projects.recursive_chunker import RecursiveTokenChunker
        from apps.projects.models import DocumentChunk
        from apps.common.embedding_service import get_embedding_service
        from apps.common.vector_utils import generate_embeddings_batch
        from apps.common.token_utils import count_tokens

        _logger = _logging.getLogger(__name__)

        try:
            # 1. Extract text from file (I/O — outside transaction)
            document.processing_status = 'chunking'
            document.save(update_fields=['processing_status', 'updated_at'])

            if on_progress:
                on_progress('chunking', 'Chunking document...', 1)

            processor = DocumentProcessor()

            # Extract text based on source type
            if document.source_type == 'upload' and document.file_path:
                segments = processor.extract_text(document.file_path.path)
                document.content_text = processor.format_extracted_text(segments)
            elif document.source_type == 'text':
                segments = [{'text': document.content_text, 'type': 'text'}]
            else:
                segments = [{'text': document.content_text, 'type': 'text'}]

            document.save(update_fields=['content_text', 'updated_at'])

            # 2. Chunk with research-backed recursive chunker (CPU — outside transaction)
            chunker = RecursiveTokenChunker(
                chunk_tokens=512,
                overlap_ratio=0.15,
            )

            chunks = chunker.chunk_with_page_info(
                segments,
                metadata={'document_id': str(document.id)}
            )

            if on_progress:
                on_progress('chunking', f'Created {len(chunks)} chunks', 1, {'chunks': len(chunks)})

            # 3. Generate embeddings (ML inference — outside transaction)
            if on_progress:
                on_progress('embedding', 'Generating embeddings...', 2, {'chunks': len(chunks)})

            embedding_service = get_embedding_service()

            # Batch-encode all chunks at once (single GPU/CPU pass)
            import hashlib

            texts = [cd['text'] for cd in chunks]

            # Content-addressable dedup: compute hashes, skip existing
            hashes = [hashlib.sha256(t.encode()).hexdigest() for t in texts]
            existing_hashes = set(
                DocumentChunk.objects.filter(
                    document__project_id=document.project_id,
                    content_hash__in=hashes,
                ).values_list('content_hash', flat=True)
            )

            # Filter to only new chunks
            new_indices = [
                i for i, h in enumerate(hashes)
                if h not in existing_hashes
            ]
            if len(new_indices) < len(chunks):
                skipped = len(chunks) - len(new_indices)
                _logger.info(
                    'Dedup: skipping %d/%d duplicate chunks for doc %s',
                    skipped, len(chunks), document.id,
                )

            new_texts = [texts[i] for i in new_indices]
            new_chunks = [chunks[i] for i in new_indices]
            new_hashes = [hashes[i] for i in new_indices]

            embeddings = generate_embeddings_batch(new_texts) if new_texts else []
            token_counts = [count_tokens(t) for t in new_texts]

            chunk_records = [
                {
                    'chunk_data': cd,
                    'embedding': emb,
                    'token_count': tc,
                    'content_hash': h,
                }
                for cd, emb, tc, h in zip(new_chunks, embeddings, token_counts, new_hashes)
            ]

            # 4. Bulk-write chunks inside a narrow transaction
            with transaction.atomic():
                chunk_objects = [
                    DocumentChunk(
                        document=document,
                        chunk_index=rec['chunk_data']['chunk_index'],
                        chunk_text=rec['chunk_data']['text'],
                        token_count=rec['token_count'],
                        span=rec['chunk_data'].get('span', {}),
                        embedding=rec['embedding'],
                        content_hash=rec['content_hash'],
                    )
                    for rec in chunk_records
                ]
                created_chunks = DocumentChunk.objects.bulk_create(chunk_objects)

            # 5. Embeddings are persisted directly via bulk_create above.
            # No external sync needed — pgvector VectorField stores inline.

            # 6. Update document status (narrow write)
            document.chunk_count = len(created_chunks)
            document.indexed_at = timezone.now()
            document.processing_status = 'indexed'
            document.save(update_fields=[
                'chunk_count', 'indexed_at',
                'processing_status', 'updated_at',
            ])

            return document

        except Exception:
            document.processing_status = 'failed'
            document.save(update_fields=['processing_status', 'updated_at'])
            raise