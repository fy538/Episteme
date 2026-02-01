"""
Query engine for semantic search across signals

Universal query interface across:
- Signals from chat
- Signals from documents  
- Signals from any source

Uses embeddings for semantic similarity search.
"""
import uuid
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import numpy as np

from apps.signals.models import Signal, SignalType
from apps.signals.similarity import cosine_similarity
from apps.signals.embedding_service import get_embedding_service


@dataclass
class QueryScope:
    """Defines the scope of a query"""
    thread_id: Optional[uuid.UUID] = None
    case_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    document_id: Optional[uuid.UUID] = None
    
    def get_filters(self) -> Dict[str, Any]:
        """Get Django ORM filters for this scope"""
        filters = {}
        
        if self.thread_id:
            filters['thread_id'] = self.thread_id
        if self.case_id:
            filters['case_id'] = self.case_id
        if self.project_id:
            filters['case__project_id'] = self.project_id
        if self.document_id:
            filters['document_id'] = self.document_id
        
        return {k: v for k, v in filters.items() if v is not None}


@dataclass
class QueryResult:
    """Result of a signal query"""
    signals: List[Signal]
    scores: List[float]  # Similarity scores
    query_embedding: List[float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict"""
        return {
            'signals': [
                {
                    'id': str(s.id),
                    'type': s.type,
                    'text': s.text,
                    'confidence': s.confidence,
                    'source_type': s.source_type,
                    'sequence_index': s.sequence_index,
                    'score': score,
                }
                for s, score in zip(self.signals, self.scores)
            ],
            'count': len(self.signals),
        }


class SignalQueryEngine:
    """
    Query engine for semantic search across signals
    
    Supports:
    - Natural language queries
    - Filtering by scope (thread, case, project)
    - Filtering by signal type
    - Similarity threshold
    """
    
    def __init__(self):
        # Use shared embedding service (singleton)
        self.embedding_service = get_embedding_service()
    
    def query(
        self,
        query_text: str,
        scope: QueryScope,
        signal_types: Optional[List[SignalType]] = None,
        top_k: int = 10,
        threshold: float = 0.5,
        status_filter: Optional[List[str]] = None,
    ) -> QueryResult:
        """
        Query signals semantically
        
        Args:
            query_text: Natural language query
            scope: Query scope (thread, case, project)
            signal_types: Filter by signal types (e.g., ['Assumption', 'Question'])
            top_k: Number of results to return
            threshold: Minimum similarity score (0.0-1.0)
            status_filter: Filter by status (e.g., ['confirmed', 'suggested'])
        
        Returns:
            QueryResult with ranked signals
        """
        # 1. Embed query
        query_embedding = self.embedding_service.encode(
            query_text,
            convert_to_numpy=True
        )
        
        # 2. Get candidate signals in scope
        candidates = Signal.objects.filter(**scope.get_filters())
        
        # Apply filters
        if signal_types:
            candidates = candidates.filter(type__in=signal_types)
        
        if status_filter:
            candidates = candidates.filter(status__in=status_filter)
        
        # Only signals with embeddings
        candidates = candidates.exclude(embedding__isnull=True)
        
        # 3. Rank by similarity
        scored_signals = []
        for signal in candidates:
            if not signal.embedding:
                continue
            
            similarity = cosine_similarity(
                query_embedding.tolist(),
                signal.embedding
            )
            
            if similarity >= threshold:
                scored_signals.append((signal, similarity))
        
        # Sort by similarity (highest first)
        scored_signals.sort(key=lambda x: x[1], reverse=True)
        
        # Take top K
        top_results = scored_signals[:top_k]
        
        if not top_results:
            return QueryResult(
                signals=[],
                scores=[],
                query_embedding=query_embedding.tolist()
            )
        
        signals, scores = zip(*top_results)
        
        return QueryResult(
            signals=list(signals),
            scores=list(scores),
            query_embedding=query_embedding.tolist()
        )
    
    def query_by_example(
        self,
        example_signal: Signal,
        scope: QueryScope,
        top_k: int = 10,
        threshold: float = 0.7,
    ) -> QueryResult:
        """
        Find signals similar to an example signal
        
        Args:
            example_signal: Example signal to match
            scope: Query scope
            top_k: Number of results
            threshold: Minimum similarity
        
        Returns:
            QueryResult with similar signals
        """
        if not example_signal.embedding:
            return QueryResult(signals=[], scores=[], query_embedding=[])
        
        # Use signal's embedding as query
        query_embedding = np.array(example_signal.embedding)
        
        # Get candidates (exclude the example itself)
        candidates = Signal.objects.filter(**scope.get_filters()).exclude(
            id=example_signal.id
        ).exclude(embedding__isnull=True)
        
        # Rank
        scored_signals = []
        for signal in candidates:
            similarity = cosine_similarity(
                example_signal.embedding,
                signal.embedding
            )
            
            if similarity >= threshold:
                scored_signals.append((signal, similarity))
        
        scored_signals.sort(key=lambda x: x[1], reverse=True)
        top_results = scored_signals[:top_k]
        
        if not top_results:
            return QueryResult(
                signals=[],
                scores=[],
                query_embedding=example_signal.embedding
            )
        
        signals, scores = zip(*top_results)
        
        return QueryResult(
            signals=list(signals),
            scores=list(scores),
            query_embedding=example_signal.embedding
        )


# Singleton
_query_engine_instance = None


def get_query_engine() -> SignalQueryEngine:
    """Get or create singleton query engine"""
    global _query_engine_instance
    if _query_engine_instance is None:
        _query_engine_instance = SignalQueryEngine()
    return _query_engine_instance
