"""
Embedding storage abstraction

Supports multiple backends:
- PostgreSQL JSON (Phase 2: simple, works for <100K chunks)
- pgvector (Phase 3: 28x faster, for >100K chunks)
- Pinecone (legacy: for backward compatibility during migration)

Design philosophy:
- Start simple (JSON), scale later (pgvector)
- Avoid vendor lock-in (abstraction layer)
- Support gradual migration (run both during transition)
"""
import uuid
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from django.conf import settings

from apps.common.vector_service import get_vector_service


class EmbeddingBackend:
    """Base class for embedding storage backends"""
    
    def store_embedding(
        self,
        chunk_id: uuid.UUID,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> None:
        raise NotImplementedError
    
    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[uuid.UUID, float]]:
        """Returns list of (chunk_id, similarity_score)"""
        raise NotImplementedError
    
    def delete_embeddings(self, chunk_ids: List[uuid.UUID]) -> None:
        raise NotImplementedError


class PostgreSQLJSONBackend(EmbeddingBackend):
    """
    Store embeddings in PostgreSQL JSONField
    
    Pros:
    - Simple (no extra infrastructure)
    - Works well for <100K chunks
    - Easy to debug and inspect
    
    Cons:
    - Linear scan for similarity search (O(n))
    - Slower than pgvector at scale
    """
    
    def store_embedding(
        self,
        chunk_id: uuid.UUID,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> None:
        """Store embedding in DocumentChunk.embedding JSONField"""
        from apps.projects.models import DocumentChunk
        
        DocumentChunk.objects.filter(id=chunk_id).update(
            embedding=embedding
        )
    
    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[uuid.UUID, float]]:
        """
        Linear scan similarity search
        
        Good enough for <100K chunks. Migrate to pgvector when needed.
        """
        from apps.projects.models import DocumentChunk
        
        # Get candidate chunks
        queryset = DocumentChunk.objects.exclude(embedding__isnull=True)
        
        # Apply filters
        if filters:
            if 'document_id' in filters:
                queryset = queryset.filter(document_id=filters['document_id'])
            if 'case_id' in filters:
                queryset = queryset.filter(document__case_id=filters['case_id'])
        
        # Compute similarity for each
        scored_chunks = []
        query_vec = np.array(query_embedding)
        
        for chunk in queryset:
            chunk_vec = np.array(chunk.embedding)
            
            # Cosine similarity
            similarity = float(
                np.dot(query_vec, chunk_vec) / 
                (np.linalg.norm(query_vec) * np.linalg.norm(chunk_vec))
            )
            
            scored_chunks.append((chunk.id, similarity))
        
        # Sort by similarity and return top K
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]
    
    def delete_embeddings(self, chunk_ids: List[uuid.UUID]) -> None:
        """Clear embeddings"""
        from apps.projects.models import DocumentChunk
        
        DocumentChunk.objects.filter(id__in=chunk_ids).update(embedding=None)


class PgVectorBackend(EmbeddingBackend):
    """
    Store embeddings in pgvector (Phase 3)
    
    Pros:
    - 28x faster than external vector DBs (research-backed)
    - Native PostgreSQL (no extra infrastructure)
    - HNSW index for O(log n) search
    
    Cons:
    - Requires pgvector extension
    - Migration needed from JSON
    
    Use when: >50-100K chunks or query latency becomes issue
    """
    
    def __init__(self):
        # Check if pgvector is available
        try:
            import pgvector
            self.available = True
        except ImportError:
            self.available = False
    
    def store_embedding(self, chunk_id, embedding, metadata):
        """Store in vector column"""
        # Phase 3: Implement when needed
        raise NotImplementedError("pgvector backend not yet implemented")
    
    def search_similar(self, query_embedding, top_k, filters):
        """Vector similarity search with HNSW index"""
        # Phase 3: Implement when needed
        raise NotImplementedError("pgvector backend not yet implemented")


class PineconeBackend(EmbeddingBackend):
    """
    Legacy backend using Pinecone (backward compatibility)
    
    Will be deprecated once migration to pgvector is complete.
    """
    
    def __init__(self):
        self.vector_service = get_vector_service()
    
    def store_embedding(
        self,
        chunk_id: uuid.UUID,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> None:
        """Store in Pinecone"""
        self.vector_service.upsert_chunk(
            chunk_id=str(chunk_id),
            embedding=embedding,
            metadata=metadata
        )
        
        # Also update vector_id in DocumentChunk
        from apps.projects.models import DocumentChunk
        DocumentChunk.objects.filter(id=chunk_id).update(
            vector_id=str(chunk_id)
        )
    
    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[uuid.UUID, float]]:
        """Search in Pinecone"""
        results = self.vector_service.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter=filters
        )
        
        # Parse results
        matches = []
        for match in results.get('matches', []):
            chunk_id = uuid.UUID(match['id'])
            score = match['score']
            matches.append((chunk_id, score))
        
        return matches
    
    def delete_embeddings(self, chunk_ids: List[uuid.UUID]) -> None:
        """Delete from Pinecone"""
        for chunk_id in chunk_ids:
            self.vector_service.delete_chunk(str(chunk_id))


class EmbeddingService:
    """
    Unified interface for embedding storage
    
    Automatically selects backend based on configuration:
    - Default: PostgreSQL JSON (simple, good for initial scale)
    - Optional: Pinecone (for backward compatibility)
    - Future: pgvector (when scale demands it)
    """
    
    def __init__(self, backend: str = 'postgresql'):
        """
        Initialize with specified backend
        
        Args:
            backend: 'postgresql', 'pgvector', or 'pinecone'
        """
        if backend == 'postgresql':
            self.backend = PostgreSQLJSONBackend()
        elif backend == 'pgvector':
            self.backend = PgVectorBackend()
        elif backend == 'pinecone':
            self.backend = PineconeBackend()
        else:
            raise ValueError(f"Unknown backend: {backend}")
        
        self.backend_name = backend
    
    def store_chunk_embedding(
        self,
        chunk_id: uuid.UUID,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store embedding for a chunk
        
        Args:
            chunk_id: DocumentChunk ID
            embedding: Vector embedding (384 or 768 dim)
            metadata: Optional metadata for filtering
        """
        self.backend.store_embedding(
            chunk_id=chunk_id,
            embedding=embedding,
            metadata=metadata or {}
        )
    
    def search_similar_chunks(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        document_id: Optional[uuid.UUID] = None,
        case_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None
    ) -> List[Tuple[uuid.UUID, float]]:
        """
        Search for similar chunks
        
        Args:
            query_embedding: Query vector
            top_k: Number of results
            document_id: Filter by document
            case_id: Filter by case
            project_id: Filter by project
        
        Returns:
            List of (chunk_id, similarity_score) tuples
        """
        filters = {}
        if document_id:
            filters['document_id'] = str(document_id)
        if case_id:
            filters['case_id'] = str(case_id)
        if project_id:
            filters['project_id'] = str(project_id)
        
        return self.backend.search_similar(
            query_embedding=query_embedding,
            top_k=top_k,
            filters=filters if filters else None
        )
    
    def delete_chunk_embeddings(self, chunk_ids: List[uuid.UUID]) -> None:
        """Delete embeddings for chunks"""
        self.backend.delete_embeddings(chunk_ids)


# Singleton instance
_embedding_service = None


def get_embedding_service(backend: str = 'postgresql') -> EmbeddingService:
    """
    Get or create embedding service singleton
    
    Args:
        backend: 'postgresql' (default), 'pgvector', or 'pinecone'
    """
    global _embedding_service
    if _embedding_service is None:
        # Get backend from settings or use default
        backend = getattr(settings, 'EMBEDDING_BACKEND', 'postgresql')
        _embedding_service = EmbeddingService(backend=backend)
    return _embedding_service
