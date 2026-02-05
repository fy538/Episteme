"""
Vector database service - abstraction for Pinecone/Weaviate

DEPRECATED: This module is deprecated in favor of pgvector.
Use apps/common/embedding_service.py with EMBEDDING_BACKEND='pgvector' instead.

pgvector provides 28x faster vector search with no external dependencies,
using native PostgreSQL HNSW indexes.

This module is kept for backward compatibility during migration.
"""
import os
import warnings

warnings.warn(
    "vector_service.py is deprecated. Use embedding_service.py with "
    "EMBEDDING_BACKEND='pgvector' for better performance and no external dependencies.",
    DeprecationWarning,
    stacklevel=2
)
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec


class VectorService:
    """
    Abstraction for vector database operations.
    
    Currently uses Pinecone for managed vector search.
    Can be swapped for Weaviate or other vector DBs.
    """
    
    def __init__(self):
        api_key = os.getenv('PINECONE_API_KEY')
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable not set")
        
        self.client = Pinecone(api_key=api_key)
        self.index_name = 'episteme-documents'
        self.index = None
    
    def initialize_index(self, dimension: int = 384) -> None:
        """
        Create or connect to Pinecone index.
        
        Args:
            dimension: Vector dimension (384 for all-MiniLM-L6-v2, 1536 for OpenAI)
        """
        existing_indexes = self.client.list_indexes().names()
        
        if self.index_name not in existing_indexes:
            # Create new index
            self.client.create_index(
                name=self.index_name,
                dimension=dimension,
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region=os.getenv('PINECONE_ENVIRONMENT', 'us-east-1')
                )
            )
        
        # Connect to index
        self.index = self.client.Index(self.index_name)
    
    def upsert_chunk(
        self,
        chunk_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> None:
        """
        Store or update a chunk embedding.
        
        Args:
            chunk_id: Unique identifier for chunk
            embedding: Vector embedding
            metadata: Associated metadata (document_id, chunk_index, text_preview)
        """
        if not self.index:
            self.initialize_index()
        
        self.index.upsert(vectors=[(
            chunk_id,
            embedding,
            metadata
        )])
    
    def upsert_chunks_batch(
        self,
        chunks: List[tuple[str, List[float], Dict[str, Any]]]
    ) -> None:
        """
        Batch upsert multiple chunks for efficiency.
        
        Args:
            chunks: List of (chunk_id, embedding, metadata) tuples
        """
        if not self.index:
            self.initialize_index()
        
        # Pinecone supports batch operations
        self.index.upsert(vectors=chunks)
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for similar chunks.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filter: Optional metadata filters (e.g., {'document_id': 'uuid'})
        
        Returns:
            Search results with matches and scores
        """
        if not self.index:
            self.initialize_index()
        
        return self.index.query(
            vector=query_embedding,
            top_k=top_k,
            filter=filter,
            include_metadata=True
        )
    
    def delete_chunk(self, chunk_id: str) -> None:
        """Delete a single chunk from index."""
        if not self.index:
            self.initialize_index()
        
        self.index.delete(ids=[chunk_id])
    
    def delete_document_chunks(self, document_id: str) -> None:
        """
        Remove all chunks for a document.
        
        Args:
            document_id: Document UUID to delete chunks for
        """
        if not self.index:
            self.initialize_index()
        
        # Delete by metadata filter
        self.index.delete(filter={'document_id': document_id})
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector index."""
        if not self.index:
            self.initialize_index()
        
        return self.index.describe_index_stats()


# Singleton instance
_vector_service = None


def get_vector_service() -> VectorService:
    """Get or create vector service singleton."""
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService()
    return _vector_service
