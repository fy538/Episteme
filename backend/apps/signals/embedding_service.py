"""
Shared embedding service to avoid loading the model multiple times.

The SentenceTransformer model is ~100MB in memory, so we use a singleton
pattern to share it across extractors and query engine.
"""
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """
    Singleton service for generating embeddings.
    
    Uses sentence-transformers 'all-MiniLM-L6-v2' model:
    - 384 dimensions
    - Fast inference
    - Good quality for semantic similarity
    - ~100MB model size
    
    Alternative: 'all-mpnet-base-v2' (768 dim, slower, better quality)
    """
    
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only load model once
        if self._model is None:
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
    
    @property
    def model(self):
        """Get the embedding model"""
        return self._model
    
    def encode(self, text, **kwargs):
        """
        Encode text to embedding vector.
        
        Args:
            text: Text to encode (str or list of str)
            **kwargs: Additional arguments passed to model.encode()
            
        Returns:
            Numpy array of embeddings
        """
        return self._model.encode(text, **kwargs)


# Singleton instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get or create singleton embedding service"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
