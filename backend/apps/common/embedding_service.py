"""
Embedding storage abstraction.

Embeddings stored in pgvector VectorField on DocumentChunk model.
Uses CosineDistance with HNSW index for O(log n) similarity search.
"""
import uuid
from typing import List, Dict, Any, Optional, Tuple

from django.conf import settings
from pgvector.django import CosineDistance


class EmbeddingBackend:
    """Base class for embedding storage backends"""

    def store_embedding(
        self,
        chunk_id: uuid.UUID,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        raise NotImplementedError

    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[uuid.UUID, float]]:
        """Returns list of (chunk_id, similarity_score)"""
        raise NotImplementedError

    def delete_embeddings(self, chunk_ids: List[uuid.UUID]) -> None:
        raise NotImplementedError


class PostgreSQLBackend(EmbeddingBackend):
    """
    Store embeddings using Django's VectorField (pgvector).

    Uses CosineDistance annotation for indexed similarity search.
    Requires the pgvector extension and a VectorField on DocumentChunk.
    """

    def store_embedding(
        self,
        chunk_id: uuid.UUID,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        """Store embedding in DocumentChunk.embedding VectorField."""
        from apps.projects.models import DocumentChunk

        DocumentChunk.objects.filter(id=chunk_id).update(embedding=embedding)

    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[uuid.UUID, float]]:
        """
        Similarity search using pgvector CosineDistance.

        Returns (chunk_id, similarity_score) tuples sorted by relevance.
        """
        from apps.projects.models import DocumentChunk

        queryset = DocumentChunk.objects.exclude(embedding__isnull=True)

        if filters:
            if 'document_id' in filters:
                queryset = queryset.filter(document_id=filters['document_id'])
            if 'case_id' in filters:
                queryset = queryset.filter(document__case_id=filters['case_id'])
            if 'project_id' in filters:
                queryset = queryset.filter(document__project_id=filters['project_id'])

        results = (
            queryset
            .annotate(distance=CosineDistance('embedding', query_embedding))
            .order_by('distance')[:top_k]
        )

        return [(r.id, 1.0 - r.distance) for r in results]

    def delete_embeddings(self, chunk_ids: List[uuid.UUID]) -> None:
        """Clear embeddings"""
        from apps.projects.models import DocumentChunk

        DocumentChunk.objects.filter(id__in=chunk_ids).update(embedding=None)


class EmbeddingService:
    """
    Unified interface for embedding storage.

    Uses PostgreSQL with pgvector as the sole backend.
    """

    def __init__(self):
        self.backend = PostgreSQLBackend()

    def store_chunk_embedding(
        self,
        chunk_id: uuid.UUID,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store embedding for a chunk."""
        self.backend.store_embedding(
            chunk_id=chunk_id,
            embedding=embedding,
            metadata=metadata or {},
        )

    def search_similar_chunks(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        document_id: Optional[uuid.UUID] = None,
        case_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
    ) -> List[Tuple[uuid.UUID, float]]:
        """Search for similar chunks using pgvector CosineDistance."""
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
            filters=filters if filters else None,
        )

    def delete_chunk_embeddings(self, chunk_ids: List[uuid.UUID]) -> None:
        """Delete embeddings for chunks."""
        self.backend.delete_embeddings(chunk_ids)


# Singleton instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get or create embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
