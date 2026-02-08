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
        
        # Count signals across all cases in project
        from apps.signals.models import Signal
        total_signals = Signal.objects.filter(case__project=project).count()
        
        # Count cases
        total_cases = project.cases.count()
        
        # Count documents
        total_documents = project.documents.count()
        
        project.total_signals = total_signals
        project.total_cases = total_cases
        project.total_documents = total_documents
        project.save(update_fields=[
            'total_signals', 'total_cases', 'total_documents', 'updated_at',
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
    def process_document(document: Document) -> Document:
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

        Returns:
            Updated document
        """
        import logging as _logging
        from django.utils import timezone
        from sentence_transformers import SentenceTransformer
        from asgiref.sync import async_to_sync

        from apps.projects.document_processor import DocumentProcessor
        from apps.projects.recursive_chunker import RecursiveTokenChunker
        from apps.projects.models import DocumentChunk, Evidence
        from apps.common.embedding_service import get_embedding_service
        from apps.common.token_utils import count_tokens

        _logger = _logging.getLogger(__name__)

        try:
            # 1. Extract text from file (I/O — outside transaction)
            document.processing_status = 'chunking'
            document.save(update_fields=['processing_status', 'updated_at'])

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

            # 3. Generate embeddings (ML inference — outside transaction)
            embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            embedding_service = get_embedding_service('postgresql')

            # Pre-compute embeddings and token counts before DB writes
            chunk_records = []
            for i, chunk_data in enumerate(chunks):
                embedding_vector = embedding_model.encode(
                    chunk_data['text'],
                    convert_to_numpy=True,
                ).tolist()
                token_count = count_tokens(chunk_data['text'])
                chunk_records.append({
                    'chunk_data': chunk_data,
                    'embedding': embedding_vector,
                    'token_count': token_count,
                })

            # 4. Bulk-write chunks inside a narrow transaction
            created_chunks = []
            with transaction.atomic():
                for rec in chunk_records:
                    cd = rec['chunk_data']
                    chunk = DocumentChunk.objects.create(
                        document=document,
                        chunk_index=cd['chunk_index'],
                        chunk_text=cd['text'],
                        token_count=rec['token_count'],
                        span=cd.get('span', {}),
                        embedding=rec['embedding'],
                        chunking_strategy='recursive_token',
                    )
                    created_chunks.append(chunk)

                # Link chunks (prev/next) for context expansion
                for i, chunk in enumerate(created_chunks):
                    if i > 0:
                        chunk.prev_chunk_id = created_chunks[i - 1].id
                    if i < len(created_chunks) - 1:
                        chunk.next_chunk_id = created_chunks[i + 1].id
                    chunk.save(update_fields=['prev_chunk_id', 'next_chunk_id', 'updated_at'])

            # 5. Store in embedding service (external service — outside transaction)
            for chunk in created_chunks:
                embedding_service.store_chunk_embedding(
                    chunk_id=chunk.id,
                    embedding=chunk.embedding,
                    metadata={
                        'document_id': str(document.id),
                        'chunk_index': chunk.chunk_index,
                        'case_id': str(document.case_id) if document.case_id else None,
                        'project_id': str(document.project_id),
                    }
                )

            # 6. Extract Evidence from chunks (LLM calls — outside transaction)
            from apps.projects.evidence_extractor import get_evidence_extractor

            evidence_extractor = get_evidence_extractor()
            total_evidence = evidence_extractor.extract_from_document(document)

            # 7. Auto-reasoning (LLM calls — outside transaction)
            try:
                from apps.reasoning.auto_reasoning import get_auto_reasoning_pipeline

                pipeline = get_auto_reasoning_pipeline()
                evidence_items = Evidence.objects.filter(document=document)

                for evidence in evidence_items:
                    results = async_to_sync(pipeline.process_new_evidence)(evidence)

                    if results['contradictions_detected']:
                        _logger.info(
                            "auto_reasoning_contradictions",
                            extra={
                                'document_id': str(document.id),
                                'evidence_id': str(evidence.id),
                                'count': len(results['contradictions_detected']),
                            }
                        )
            except Exception:
                _logger.exception(
                    "auto_reasoning_failed",
                    extra={'document_id': str(document.id)}
                )

            # 8. Update document status (narrow write)
            document.chunk_count = len(created_chunks)
            document.evidence_count = total_evidence
            document.indexed_at = timezone.now()
            document.processing_status = 'indexed'
            document.save(update_fields=[
                'chunk_count', 'evidence_count', 'indexed_at',
                'processing_status', 'updated_at',
            ])

            return document

        except Exception:
            document.processing_status = 'failed'
            document.save(update_fields=['processing_status', 'updated_at'])
            raise