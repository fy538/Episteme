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
        project.save()


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
    @transaction.atomic
    def process_document(document: Document) -> Document:
        """
        Process document with research-backed pipeline (2024 RAG standards).
        
        Pipeline:
        1. Extract text from file
        2. Chunk with RecursiveTokenChunker (512 tokens, 15% overlap)
        3. Generate embeddings (sentence-transformers)
        4. Store in PostgreSQL with context linking
        
        Args:
            document: Document to process
        
        Returns:
            Updated document
        """
        from django.utils import timezone
        from sentence_transformers import SentenceTransformer
        
        from apps.projects.document_processor import DocumentProcessor
        from apps.projects.recursive_chunker import RecursiveTokenChunker
        from apps.projects.models import DocumentChunk
        from apps.common.embedding_service import get_embedding_service
        from apps.common.token_utils import count_tokens
        
        try:
            # 1. Extract text from file
            document.processing_status = 'chunking'
            document.save()
            
            processor = DocumentProcessor()
            
            # Extract text based on source type
            if document.source_type == 'upload' and document.file_path:
                # Extract from uploaded file
                segments = processor.extract_text(document.file_path.path)
                document.content_text = processor.format_extracted_text(segments)
            elif document.source_type == 'text':
                # Text already provided
                segments = [{'text': document.content_text, 'type': 'text'}]
            else:
                # For URL type, content_text should be pre-filled
                segments = [{'text': document.content_text, 'type': 'text'}]
            
            document.save()
            
            # 2. Chunk with research-backed recursive chunker
            chunker = RecursiveTokenChunker(
                chunk_tokens=512,      # Optimal from research
                overlap_ratio=0.15,    # 15% overlap (research: 10-20%)
            )
            
            chunks = chunker.chunk_with_page_info(
                segments,
                metadata={'document_id': str(document.id)}
            )
            
            # 3. Generate embeddings
            embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            embedding_service = get_embedding_service('postgresql')
            
            # Create chunks with embeddings and context linking
            created_chunks = []
            
            for i, chunk_data in enumerate(chunks):
                # Generate embedding
                embedding_vector = embedding_model.encode(
                    chunk_data['text'],
                    convert_to_numpy=True
                ).tolist()
                
                # Count tokens accurately
                token_count = count_tokens(chunk_data['text'])
                
                # Create chunk record
                chunk = DocumentChunk.objects.create(
                    document=document,
                    chunk_index=chunk_data['chunk_index'],
                    chunk_text=chunk_data['text'],
                    token_count=token_count,
                    span=chunk_data.get('span', {}),
                    embedding=embedding_vector,  # Store in PostgreSQL
                    chunking_strategy='recursive_token',
                )
                
                created_chunks.append(chunk)
            
            # 4. Link chunks (prev/next) for context expansion
            for i, chunk in enumerate(created_chunks):
                if i > 0:
                    chunk.prev_chunk_id = created_chunks[i - 1].id
                if i < len(created_chunks) - 1:
                    chunk.next_chunk_id = created_chunks[i + 1].id
                chunk.save()
            
            # 5. Store in embedding service (supports multiple backends)
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
            
            # 6. Extract Evidence from chunks (Phase 2.2)
            # Only for user-uploaded documents, NOT AI-generated artifacts
            from apps.projects.evidence_extractor import get_evidence_extractor
            
            evidence_extractor = get_evidence_extractor()
            total_evidence = evidence_extractor.extract_from_document(document)
            
            # 7. Auto-reasoning: Build knowledge graph from evidence
            # Find relationships, detect contradictions, update confidence
            try:
                from apps.reasoning.auto_reasoning import get_auto_reasoning_pipeline
                import asyncio
                
                pipeline = get_auto_reasoning_pipeline()
                evidence_items = Evidence.objects.filter(document=document)
                
                # Process each evidence item through auto-reasoning
                for evidence in evidence_items:
                    results = asyncio.run(pipeline.process_new_evidence(evidence))
                    
                    # Log results
                    if results['contradictions_detected']:
                        logger.info(
                            f"Auto-reasoning detected {len(results['contradictions_detected'])} contradictions",
                            extra={
                                'document_id': str(document.id),
                                'evidence_id': str(evidence.id)
                            }
                        )
            except Exception as e:
                logger.exception(
                    "auto_reasoning_failed",
                    extra={'document_id': str(document.id)}
                )
                # Don't fail document processing if auto-reasoning fails
            
            # 8. Update document status
            document.chunk_count = len(created_chunks)
            document.evidence_count = total_evidence
            document.indexed_at = timezone.now()
            document.processing_status = 'indexed'
            document.save()
            
            return document
            
        except Exception as e:
            document.processing_status = 'failed'
            document.save()
            raise