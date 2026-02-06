"""
Similarity search and deduplication using embeddings

This is for READ-TIME processing of signals.
We don't dedupe at write time - we keep everything raw.
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)
from typing import List, Tuple, Optional
import uuid
from apps.signals.models import Signal
from apps.common.embeddings import generate_embedding


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


def batch_cosine_similarity(
    query: List[float],
    embeddings: List[List[float]]
) -> np.ndarray:
    """
    Compute cosine similarity between one query and multiple embeddings.

    Vectorized implementation - much faster than calling cosine_similarity
    in a loop when comparing against many embeddings.

    Args:
        query: Single query embedding vector
        embeddings: List of embedding vectors to compare against

    Returns:
        Numpy array of similarity scores (same order as input)
    """
    if not embeddings:
        return np.array([])

    # Convert to numpy arrays
    query_vec = np.array(query)
    embed_matrix = np.array(embeddings)

    # Compute norms
    query_norm = np.linalg.norm(query_vec)
    if query_norm == 0:
        return np.zeros(len(embeddings))

    # Vectorized norm computation for all embeddings at once
    embed_norms = np.linalg.norm(embed_matrix, axis=1)

    # Avoid division by zero
    embed_norms = np.where(embed_norms == 0, 1, embed_norms)

    # Vectorized dot product: query @ embeddings.T gives all similarities
    similarities = np.dot(embed_matrix, query_vec) / (embed_norms * query_norm)

    return similarities


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


def search_signals_by_text(
    query: str,
    case_id: Optional[uuid.UUID] = None,
    signal_type: Optional[str] = None,
    top_k: int = 10,
    threshold: float = 0.5
) -> List[Tuple[Signal, float]]:
    """
    Search for signals semantically similar to a text query.

    Args:
        query: Text to search for (will be embedded)
        case_id: Optional case UUID to scope search
        signal_type: Optional signal type filter ('claim', 'assumption', 'evidence', etc.)
        top_k: Maximum number of results to return
        threshold: Minimum similarity score (0.0-1.0)

    Returns:
        List of (signal, similarity_score) tuples, sorted by similarity (highest first)

    Example:
        >>> results = search_signals_by_text("market size", case_id=my_case.id)
        >>> for signal, score in results:
        ...     print(f"{score:.2f}: {signal.text[:50]}")
    """
    # Generate embedding for query
    query_embedding = generate_embedding(query)
    if not query_embedding:
        return []

    # Build queryset
    filters = {'embedding__isnull': False}
    if case_id:
        filters['case_id'] = case_id
    if signal_type:
        filters['type'] = signal_type

    signals = Signal.objects.filter(**filters)

    # Calculate similarities
    results = []
    for signal in signals:
        if signal.embedding:
            similarity = cosine_similarity(query_embedding, signal.embedding)
            if similarity >= threshold:
                results.append((signal, similarity))

    # Sort by similarity (highest first) and limit
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


def ensure_signal_embedding(signal: Signal, save: bool = True) -> bool:
    """
    Ensure a signal has an embedding, generating one if needed.

    Args:
        signal: Signal instance to embed
        save: Whether to save the signal after embedding

    Returns:
        True if embedding exists or was generated, False if generation failed
    """
    if signal.embedding:
        return True

    embedding = generate_embedding(signal.text)
    if embedding:
        signal.embedding = embedding
        if save:
            signal.save(update_fields=['embedding'])
        return True

    return False


def backfill_embeddings(
    case_id: Optional[uuid.UUID] = None,
    batch_size: int = 100,
    verbose: bool = True
) -> dict:
    """
    Backfill embeddings for signals that don't have them.

    Args:
        case_id: Optional case UUID to scope backfill
        batch_size: Number of signals to process at once
        verbose: Whether to print progress

    Returns:
        Dict with counts: {'processed': N, 'embedded': N, 'failed': N}
    """
    from apps.common.embeddings import generate_embeddings_batch

    filters = {'embedding__isnull': True}
    if case_id:
        filters['case_id'] = case_id

    signals = list(Signal.objects.filter(**filters))

    if verbose:
        logger.info(f"Found {len(signals)} signals without embeddings")

    stats = {'processed': 0, 'embedded': 0, 'failed': 0}

    # Process in batches
    for i in range(0, len(signals), batch_size):
        batch = signals[i:i + batch_size]
        texts = [s.text for s in batch]

        embeddings = generate_embeddings_batch(texts)

        to_update = []
        for signal, embedding in zip(batch, embeddings):
            stats['processed'] += 1
            if embedding:
                signal.embedding = embedding
                to_update.append(signal)
                stats['embedded'] += 1
            else:
                stats['failed'] += 1

        # Bulk update
        if to_update:
            Signal.objects.bulk_update(to_update, ['embedding'], batch_size=batch_size)

        if verbose:
            logger.info(f"Processed {stats['processed']}/{len(signals)} signals")

    return stats
