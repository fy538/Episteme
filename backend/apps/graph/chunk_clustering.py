"""
ChunkClusteringService — cluster document chunks by embedding similarity.

Used for thematic summary generation (pre-graph-extraction tier).
Operates on DocumentChunk embeddings, NOT graph nodes.

The existing ClusteringService in clustering.py uses Leiden community detection
on graph edges. This service uses agglomerative clustering on raw embeddings
because at thematic-summary time, no graph edges exist yet.

For large projects (>MAX_DIRECT_CLUSTER chunks), a two-phase approach is used:
1. Sample a representative subset, cluster that directly
2. Assign remaining chunks to nearest cluster centroid
This keeps memory bounded at ~15MB regardless of project size.
"""
import logging
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Projects above this threshold use sampled two-phase clustering.
# Read from SUMMARY_SETTINGS at call-time; this constant is the fallback.
_DEFAULT_MAX_DIRECT_CLUSTER = 5000


def _get_chunk_clustering_config() -> dict:
    """Return chunk_clustering config from Django settings with safe fallbacks."""
    try:
        from django.conf import settings as django_settings
        return getattr(django_settings, 'SUMMARY_SETTINGS', {}).get('chunk_clustering', {})
    except Exception:
        return {}


class ChunkClusteringService:
    """Cluster document chunks by embedding cosine similarity."""

    @staticmethod
    def cluster_project_chunks(
        project_id: uuid.UUID,
        document_ids: Optional[List[uuid.UUID]] = None,
        distance_threshold: Optional[float] = None,
        min_cluster_size: int = 2,
    ) -> Dict[str, Any]:
        """
        Cluster document chunks by embedding cosine similarity.

        Uses agglomerative clustering with cosine metric and average linkage.
        The distance_threshold controls cluster granularity — lower values
        produce more, tighter clusters.

        For projects with >5000 chunks, uses a two-phase approach:
        cluster a sample, then assign remaining chunks to nearest centroid.

        Args:
            project_id: Project to cluster.
            document_ids: Optional subset of documents. If None, clusters
                          all chunks in the project.
            distance_threshold: Cosine distance threshold for merging.
                                0.65 ≈ cosine similarity ≥ 0.35 to merge.
            min_cluster_size: Minimum chunks per cluster. Smaller groups
                              are treated as orphans.

        Returns:
            {
                'clusters': [{
                    'cluster_id': int,
                    'chunk_ids': [str, ...],
                    'representative_chunks': [
                        {'chunk_id': str, 'text': str, 'document_title': str},
                        ...  (up to 3)
                    ],
                    'document_distribution': {doc_title: chunk_count, ...},
                    'chunk_count': int,
                    'coverage_pct': float,
                }],
                'orphan_chunk_ids': [str, ...],
                'total_chunks': int,
                'total_documents': int,
            }
        """
        from apps.projects.models import DocumentChunk

        # Resolve defaults from SUMMARY_SETTINGS if not explicitly provided
        cfg = _get_chunk_clustering_config()
        if distance_threshold is None:
            distance_threshold = cfg.get('distance_threshold', 0.65)
        max_direct = cfg.get('max_direct_cluster', _DEFAULT_MAX_DIRECT_CLUSTER)

        # 1. Load chunks with embeddings
        qs = DocumentChunk.objects.filter(
            document__project_id=project_id,
            embedding__isnull=False,
        ).select_related('document')

        if document_ids:
            qs = qs.filter(document_id__in=document_ids)

        chunks = list(qs.order_by('document', 'chunk_index'))

        total_chunks = len(chunks)
        total_documents = len(set(c.document_id for c in chunks))

        if total_chunks < 3:
            # Too few chunks to cluster meaningfully
            return {
                'clusters': [],
                'orphan_chunk_ids': [str(c.id) for c in chunks],
                'total_chunks': total_chunks,
                'total_documents': total_documents,
            }

        # 2. Build embedding matrix and normalize
        embeddings = np.array([c.embedding for c in chunks])
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        normalized = embeddings / norms

        # 3. Cluster — direct or sampled depending on size
        if total_chunks <= max_direct:
            labels = ChunkClusteringService._cluster_direct(
                normalized, distance_threshold,
            )
        else:
            labels = ChunkClusteringService._cluster_sampled(
                normalized, distance_threshold, sample_size=max_direct,
            )
            logger.info(
                "chunk_clustering_used_sampling",
                extra={
                    'project_id': str(project_id),
                    'total_chunks': total_chunks,
                    'sample_size': max_direct,
                },
            )

        # 4. Group chunks by cluster label
        cluster_map: Dict[int, List[int]] = defaultdict(list)
        for idx, label in enumerate(labels):
            cluster_map[int(label)].append(idx)

        # 5. Build result clusters and orphans
        result_clusters = []
        orphan_ids = []

        for label, indices in sorted(cluster_map.items()):
            if len(indices) < min_cluster_size:
                for idx in indices:
                    orphan_ids.append(str(chunks[idx].id))
                continue

            cluster_chunks = [chunks[i] for i in indices]
            cluster_embeddings = normalized[indices]

            # Pick up to 3 representatives: closest to centroid
            centroid = cluster_embeddings.mean(axis=0)
            centroid_norm = np.linalg.norm(centroid)
            if centroid_norm > 0:
                centroid = centroid / centroid_norm
            sims = cluster_embeddings @ centroid
            top_k = min(3, len(indices))
            top_k_indices = np.argsort(sims)[-top_k:][::-1]

            representatives = []
            for ki in top_k_indices:
                c = cluster_chunks[ki]
                representatives.append({
                    'chunk_id': str(c.id),
                    'text': c.chunk_text[:300],
                    'document_title': c.document.title,
                })

            # Document distribution
            doc_dist: Dict[str, int] = defaultdict(int)
            for c in cluster_chunks:
                doc_dist[c.document.title] += 1

            result_clusters.append({
                'cluster_id': int(label),
                'chunk_ids': [str(c.id) for c in cluster_chunks],
                'representative_chunks': representatives,
                'document_distribution': dict(doc_dist),
                'chunk_count': len(cluster_chunks),
                'coverage_pct': round(
                    len(cluster_chunks) / total_chunks * 100, 1
                ),
            })

        # Sort by coverage descending
        result_clusters.sort(key=lambda c: c['chunk_count'], reverse=True)

        logger.info(
            "chunk_clustering_complete",
            extra={
                'project_id': str(project_id),
                'total_chunks': total_chunks,
                'cluster_count': len(result_clusters),
                'orphan_count': len(orphan_ids),
            },
        )

        return {
            'clusters': result_clusters,
            'orphan_chunk_ids': orphan_ids,
            'total_chunks': total_chunks,
            'total_documents': total_documents,
        }

    # ── Clustering strategies ──────────────────────────────────────

    @staticmethod
    def _cluster_direct(
        normalized: np.ndarray,
        distance_threshold: float,
    ) -> np.ndarray:
        """
        Direct agglomerative clustering — used when chunk count ≤ MAX_DIRECT_CLUSTER.
        """
        # sklearn requires ≥2 samples; single-vector case is trivially one cluster
        if len(normalized) < 2:
            return np.zeros(len(normalized), dtype=int)

        try:
            from sklearn.cluster import AgglomerativeClustering

            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=distance_threshold,
                metric='cosine',
                linkage='average',
            )
            return clustering.fit_predict(normalized)
        except ImportError:
            logger.warning(
                "sklearn not available for chunk clustering, "
                "falling back to simple threshold-based clustering"
            )
            return ChunkClusteringService._fallback_cluster(
                normalized, distance_threshold
            )

    @staticmethod
    def _cluster_sampled(
        normalized: np.ndarray,
        distance_threshold: float,
        sample_size: int = 5000,
    ) -> np.ndarray:
        """
        Two-phase sampled clustering for large projects.

        Phase 1: Randomly sample `sample_size` chunks and cluster directly.
        Phase 2: Assign remaining chunks to the nearest cluster centroid.

        This keeps memory bounded (AgglomerativeClustering needs O(n²) memory
        for the distance matrix) while producing equivalent results for the
        representative chunks and cluster centroids used by the LLM prompt.
        """
        n = len(normalized)
        rng = np.random.default_rng(42)  # deterministic for reproducibility
        sample_indices = rng.choice(n, size=min(sample_size, n), replace=False)
        sample_indices.sort()

        # Phase 1: cluster the sample
        sample_embeddings = normalized[sample_indices]
        sample_labels = ChunkClusteringService._cluster_direct(
            sample_embeddings, distance_threshold,
        )

        # Compute centroids from sample clusters
        unique_labels = set(int(l) for l in sample_labels)
        centroids: Dict[int, np.ndarray] = {}
        for label in unique_labels:
            mask = sample_labels == label
            centroid = sample_embeddings[mask].mean(axis=0)
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
            centroids[label] = centroid

        centroid_labels = sorted(centroids.keys())
        centroid_matrix = np.array([centroids[l] for l in centroid_labels])

        # Phase 2: assign all chunks (including sampled) to nearest centroid
        labels = np.full(n, -1, dtype=int)

        # Process in batches of 2000 to bound memory
        batch_size = 2000
        for start in range(0, n, batch_size):
            end = min(start + batch_size, n)
            batch = normalized[start:end]
            sims = batch @ centroid_matrix.T  # (batch, num_centroids)
            best_centroid_idx = np.argmax(sims, axis=1)
            best_sims = sims[np.arange(len(batch)), best_centroid_idx]

            for j in range(len(batch)):
                # Only assign if close enough; otherwise leave as orphan (-1)
                if (1 - best_sims[j]) < distance_threshold:
                    labels[start + j] = centroid_labels[best_centroid_idx[j]]
                else:
                    labels[start + j] = -(start + j + 1)  # unique orphan label

        return labels

    @staticmethod
    def _fallback_cluster(
        normalized: np.ndarray,
        distance_threshold: float,
    ) -> np.ndarray:
        """
        Simple greedy clustering fallback when sklearn is unavailable.

        Assigns each embedding to the nearest existing cluster centroid
        if within threshold, otherwise creates a new cluster.
        """
        n = len(normalized)
        labels = np.full(n, -1, dtype=int)
        centroids: List[np.ndarray] = []
        cluster_counts: List[int] = []
        next_label = 0

        for i in range(n):
            vec = normalized[i]

            if centroids:
                centroid_matrix = np.array(centroids)
                sims = centroid_matrix @ vec
                best_idx = int(np.argmax(sims))
                best_sim = sims[best_idx]

                if (1 - best_sim) < distance_threshold:
                    labels[i] = best_idx
                    # Update centroid incrementally
                    count = cluster_counts[best_idx]
                    centroids[best_idx] = (
                        centroids[best_idx] * count + vec
                    ) / (count + 1)
                    norm = np.linalg.norm(centroids[best_idx])
                    if norm > 0:
                        centroids[best_idx] /= norm
                    cluster_counts[best_idx] += 1
                    continue

            # Create new cluster
            labels[i] = next_label
            centroids.append(vec.copy())
            cluster_counts.append(1)
            next_label += 1

        return labels
