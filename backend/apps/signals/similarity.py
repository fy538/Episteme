"""
Similarity search and deduplication using embeddings

This is for READ-TIME processing of signals.
We don't dedupe at write time - we keep everything raw.
"""
import numpy as np
from typing import List, Tuple
from apps.signals.models import Signal


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Compute cosine similarity between two vectors
    
    Args:
        vec1: First vector
        vec2: Second vector
    
    Returns:
        Similarity score (0.0 to 1.0)
    """
    a = np.array(vec1)
    b = np.array(vec2)
    
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(np.dot(a, b) / (norm_a * norm_b))


def find_similar_signals(
    signal: Signal,
    candidates: List[Signal],
    threshold: float = 0.85
) -> List[Tuple[Signal, float]]:
    """
    Find signals similar to the given signal
    
    Args:
        signal: The signal to compare against
        candidates: List of candidate signals to compare
        threshold: Minimum similarity score (0.0-1.0)
    
    Returns:
        List of (signal, similarity_score) tuples above threshold,
        sorted by similarity (highest first)
    """
    if not signal.embedding:
        return []
    
    similar = []
    for candidate in candidates:
        if not candidate.embedding or candidate.id == signal.id:
            continue
        
        similarity = cosine_similarity(signal.embedding, candidate.embedding)
        
        if similarity >= threshold:
            similar.append((candidate, similarity))
    
    # Sort by similarity (highest first)
    similar.sort(key=lambda x: x[1], reverse=True)
    
    return similar


def dedupe_signals_by_embedding(
    signals: List[Signal],
    threshold: float = 0.90
) -> List[Signal]:
    """
    Deduplicate signals using embedding similarity
    
    Uses greedy clustering:
    1. Take first signal as cluster seed
    2. Find all signals similar to seed (above threshold)
    3. Keep highest confidence signal from cluster
    4. Repeat with remaining signals
    
    Args:
        signals: List of signals to deduplicate
        threshold: Similarity threshold for considering duplicates
    
    Returns:
        List of representative signals (one per cluster)
    """
    if not signals:
        return []
    
    # Filter out signals without embeddings
    signals_with_embeddings = [s for s in signals if s.embedding]
    
    if not signals_with_embeddings:
        return list(signals)
    
    # Start with all signals as unclustered
    unclustered = list(signals_with_embeddings)
    clusters = []
    
    while unclustered:
        # Take first signal as cluster seed
        seed = unclustered.pop(0)
        cluster = [seed]
        
        # Find all similar signals
        remaining = []
        for signal in unclustered:
            similarity = cosine_similarity(seed.embedding, signal.embedding)
            if similarity >= threshold:
                cluster.append(signal)
            else:
                remaining.append(signal)
        
        clusters.append(cluster)
        unclustered = remaining
    
    # Return highest confidence signal from each cluster
    representatives = []
    for cluster in clusters:
        # Sort by confidence, then by recency (sequence_index)
        best = max(cluster, key=lambda s: (s.confidence, s.sequence_index))
        representatives.append(best)
    
    return representatives


def cluster_signals_by_similarity(
    signals: List[Signal],
    threshold: float = 0.85
) -> List[List[Signal]]:
    """
    Cluster signals by similarity
    
    Similar to dedupe but returns all clusters (not just representatives)
    
    Args:
        signals: List of signals to cluster
        threshold: Similarity threshold for clustering
    
    Returns:
        List of clusters, each cluster is a list of similar signals
    """
    if not signals:
        return []
    
    signals_with_embeddings = [s for s in signals if s.embedding]
    
    if not signals_with_embeddings:
        return [[s] for s in signals]
    
    unclustered = list(signals_with_embeddings)
    clusters = []
    
    while unclustered:
        seed = unclustered.pop(0)
        cluster = [seed]
        
        remaining = []
        for signal in unclustered:
            similarity = cosine_similarity(seed.embedding, signal.embedding)
            if similarity >= threshold:
                cluster.append(signal)
            else:
                remaining.append(signal)
        
        clusters.append(cluster)
        unclustered = remaining
    
    return clusters
