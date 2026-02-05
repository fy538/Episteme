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

    # Default embedding dimension (sentence-transformers)
    EMBEDDING_DIM = 384

    def __init__(self):
        """Initialize and check pgvector availability"""
        from django.db import connection
        self.connection = connection
        self._extension_available = None
        self._vector_column_exists = None

    @property
    def extension_available(self) -> bool:
        """Check if pgvector extension is available in PostgreSQL"""
        if self._extension_available is None:
            try:
                with self.connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                    )
                    self._extension_available = cursor.fetchone()[0]
            except Exception:
                self._extension_available = False
        return self._extension_available

    @property
    def vector_column_exists(self) -> bool:
        """Check if embedding_vector column exists on DocumentChunk"""
        if self._vector_column_exists is None:
            try:
                with self.connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'projects_documentchunk'
                            AND column_name = 'embedding_vector'
                        )
                    """)
                    self._vector_column_exists = cursor.fetchone()[0]
            except Exception:
                self._vector_column_exists = False
        return self._vector_column_exists

    def ensure_setup(self) -> bool:
        """
        Ensure pgvector is set up. Call this before any operation.

        Returns True if ready, False if not available.
        """
        if not self.extension_available:
            return False

        # Create vector column if it doesn't exist
        if not self.vector_column_exists:
            self._create_vector_column()
            self._vector_column_exists = True

        return True

    def _create_vector_column(self):
        """Add embedding_vector column and HNSW index"""
        with self.connection.cursor() as cursor:
            # Add vector column
            cursor.execute(f"""
                ALTER TABLE projects_documentchunk
                ADD COLUMN IF NOT EXISTS embedding_vector vector({self.EMBEDDING_DIM})
            """)

            # Create HNSW index for fast cosine similarity search
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS documentchunk_embedding_hnsw_idx
                ON projects_documentchunk
                USING hnsw (embedding_vector vector_cosine_ops)
            """)

    def store_embedding(
        self,
        chunk_id: uuid.UUID,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> None:
        """Store embedding in vector column"""
        if not self.ensure_setup():
            raise RuntimeError("pgvector extension not available")

        # Convert list to vector format
        embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'

        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE projects_documentchunk
                SET embedding_vector = %s::vector
                WHERE id = %s
                """,
                [embedding_str, str(chunk_id)]
            )

    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[uuid.UUID, float]]:
        """
        Vector similarity search using HNSW index.

        Uses cosine distance (1 - similarity) for ordering.
        Returns similarity scores (higher is better).
        """
        if not self.ensure_setup():
            raise RuntimeError("pgvector extension not available")

        # Convert query to vector format
        query_str = '[' + ','.join(str(x) for x in query_embedding) + ']'

        # Build SQL with optional filters
        sql = """
            SELECT id, 1 - (embedding_vector <=> %s::vector) as similarity
            FROM projects_documentchunk
            WHERE embedding_vector IS NOT NULL
        """
        params = [query_str]

        if filters:
            if 'document_id' in filters:
                sql += " AND document_id = %s"
                params.append(filters['document_id'])
            if 'case_id' in filters:
                sql += " AND document_id IN (SELECT id FROM projects_document WHERE case_id = %s)"
                params.append(filters['case_id'])

        sql += " ORDER BY embedding_vector <=> %s::vector LIMIT %s"
        params.extend([query_str, top_k])

        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            results = cursor.fetchall()

        return [(uuid.UUID(str(row[0])), float(row[1])) for row in results]

    def delete_embeddings(self, chunk_ids: List[uuid.UUID]) -> None:
        """Clear vector embeddings"""
        if not self.ensure_setup():
            return

        if not chunk_ids:
            return

        placeholders = ','.join(['%s'] * len(chunk_ids))
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE projects_documentchunk
                SET embedding_vector = NULL
                WHERE id IN ({placeholders})
                """,
                [str(cid) for cid in chunk_ids]
            )

    def migrate_from_json(self, batch_size: int = 1000) -> int:
        """
        Migrate embeddings from JSON field to vector column.

        Call this to migrate existing data in batches.
        Returns number of migrated chunks in this batch.
        """
        if not self.ensure_setup():
            raise RuntimeError("pgvector extension not available")

        from apps.projects.models import DocumentChunk

        # Find chunks with JSON embedding but no vector embedding yet
        # Use raw SQL to check for NULL vector column
        with self.connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT id, embedding
                FROM projects_documentchunk
                WHERE embedding IS NOT NULL
                  AND embedding != '[]'::jsonb
                  AND (embedding_vector IS NULL)
                LIMIT %s
            """, [batch_size])
            chunks = cursor.fetchall()

        migrated = 0
        for chunk_id, embedding in chunks:
            if embedding and len(embedding) == self.EMBEDDING_DIM:
                self.store_embedding(uuid.UUID(str(chunk_id)), embedding, {})
                migrated += 1

        return migrated


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

    def migrate_to_pgvector(self, batch_size: int = 1000) -> int:
        """
        Migrate embeddings from JSON to pgvector.

        Only works when using pgvector backend.
        Returns number of migrated chunks.
        """
        if not isinstance(self.backend, PgVectorBackend):
            raise ValueError("Migration only works with pgvector backend")
        return self.backend.migrate_from_json(batch_size)

    def is_pgvector_available(self) -> bool:
        """Check if pgvector is available and ready to use"""
        if isinstance(self.backend, PgVectorBackend):
            return self.backend.extension_available
        return False


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
