"""
HierarchicalClusteringService — recursive agglomerative clustering
with LLM summaries at each level.

Builds a multi-level cluster tree from document chunk embeddings:
    Level 0 (Leaves): Raw DocumentChunks
    Level 1 (Topics): 10-30 clusters of chunks, each with LLM summary
    Level 2 (Themes): 3-7 super-clusters of topics
    Level 3 (Root):   Single project overview

The tree is stored as a JSON blob in ClusterHierarchy.tree for fast
retrieval by the frontend landscape view.
"""
import asyncio
import logging
import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Configuration defaults ────────────────────────────────────────

LEVEL_THRESHOLDS = {
    # level: cosine distance threshold for agglomerative clustering
    1: 0.65,   # Level 0→1: chunk → topic (same as ChunkClusteringService)
    2: 0.55,   # Level 1→2: topic → theme (tighter, summaries are more abstract)
    3: 0.45,   # Level 2→3: theme merge pass (only if >7 themes)
}

MAX_CLUSTERS_BEFORE_RECURSE = 7
MAX_LEVEL = 3
MAX_CONCURRENT_LLM = 5  # semaphore cap for parallel LLM calls
MAX_REPRESENTATIVE_CHUNKS = 5  # chunks sent to LLM per topic cluster


# ── Data structures ───────────────────────────────────────────────

@dataclass
class ClusterTreeNode:
    """A node in the hierarchical cluster tree."""
    id: str
    level: int              # 0=chunk, 1=topic, 2=theme, 3=root
    label: str              # LLM-generated label (2-5 words)
    summary: str            # LLM-generated summary
    children: List['ClusterTreeNode'] = field(default_factory=list)
    chunk_ids: List[str] = field(default_factory=list)
    document_ids: List[str] = field(default_factory=list)
    chunk_count: int = 0
    coverage_pct: float = 0.0
    # Embedding used during building and stored for Level 1-2 nodes in the
    # serialized tree (as 'embedding') so CaseChunkRetriever can do
    # hierarchy-aware similarity matching.
    _embedding: Optional[List[float]] = field(default=None, repr=False)


# ── Service ───────────────────────────────────────────────────────

class HierarchicalClusteringService:
    """Build a hierarchical cluster tree from a project's document chunks."""

    async def build_hierarchy(self, project_id: uuid.UUID) -> dict:
        """
        Main entry point. Loads chunks, clusters recursively, and returns
        the tree as a JSON-serializable dict.

        Returns:
            dict with 'tree' (serialized ClusterTreeNode) and 'metadata'.
            Level 1-2 nodes include 'embedding' for hierarchy-aware retrieval.
        """
        start_time = time.time()

        # 1. Load chunks
        chunks, total_chunks, total_documents, project_title, project_description = (
            self._load_chunks(project_id)
        )

        # Build document manifest for change detection (Plan 6)
        document_manifest = self._build_document_manifest(chunks)

        if total_chunks < 3:
            root = ClusterTreeNode(
                id=str(uuid.uuid4()),
                level=3,
                label=project_title or 'Project Overview',
                summary='Too few document passages to build a meaningful hierarchy.',
                chunk_ids=[str(c['id']) for c in chunks],
                document_ids=list(set(str(c['document_id']) for c in chunks)),
                chunk_count=total_chunks,
                coverage_pct=100.0,
            )
            return self._serialize_tree(
                root, start_time, total_chunks, 0, 1,
                document_manifest=document_manifest,
            )

        # 2. Build embedding matrix
        embeddings = np.array([c['embedding'] for c in chunks])
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        normalized = embeddings / norms

        # 3. Level 0→1: Cluster chunks into topics
        level1_nodes = self._build_level1(chunks, normalized, total_chunks)

        if not level1_nodes:
            root = ClusterTreeNode(
                id=str(uuid.uuid4()),
                level=3,
                label=project_title or 'Project Overview',
                summary='Could not identify meaningful clusters in the documents.',
                chunk_ids=[str(c['id']) for c in chunks],
                document_ids=list(set(str(c['document_id']) for c in chunks)),
                chunk_count=total_chunks,
                coverage_pct=100.0,
            )
            return self._serialize_tree(
                root, start_time, total_chunks, 0, 1,
                document_manifest=document_manifest,
            )

        # 4. Summarize Level 1 topics (parallel LLM calls)
        await self._summarize_nodes_batch(level1_nodes, level=1, chunks=chunks)

        # 5. Generate embeddings for Level 1 summaries
        self._embed_node_summaries(level1_nodes)

        # 6. Level 1→2: Cluster topics into themes (if needed)
        if len(level1_nodes) > MAX_CLUSTERS_BEFORE_RECURSE:
            level2_nodes = self._cluster_nodes(level1_nodes, level=2)
            await self._summarize_nodes_batch(level2_nodes, level=2)
            self._embed_node_summaries(level2_nodes)

            # Extra merge pass if still too many themes
            if len(level2_nodes) > MAX_CLUSTERS_BEFORE_RECURSE:
                level2_nodes = self._cluster_nodes(level2_nodes, level=2)
                await self._summarize_nodes_batch(level2_nodes, level=2)
                self._embed_node_summaries(level2_nodes)
        else:
            # Promote Level 1 nodes to Level 2 (they ARE the themes)
            level2_nodes = []
            for node in level1_nodes:
                theme = ClusterTreeNode(
                    id=str(uuid.uuid4()),
                    level=2,
                    label=node.label,
                    summary=node.summary,
                    children=[node],
                    chunk_ids=node.chunk_ids[:],
                    document_ids=node.document_ids[:],
                    chunk_count=node.chunk_count,
                    coverage_pct=node.coverage_pct,
                    _embedding=node._embedding,
                )
                level2_nodes.append(theme)

        # 7. Build root (Level 3)
        root = await self._build_root(
            level2_nodes, total_chunks, project_title, project_description,
        )

        total_clusters = len(level1_nodes) + len(level2_nodes) + 1
        levels = 3 if len(level2_nodes) != len(level1_nodes) else 2

        logger.info(
            "hierarchical_clustering_complete",
            extra={
                'project_id': str(project_id),
                'total_chunks': total_chunks,
                'level1_topics': len(level1_nodes),
                'level2_themes': len(level2_nodes),
                'duration_ms': int((time.time() - start_time) * 1000),
            },
        )

        return self._serialize_tree(
            root, start_time, total_chunks, total_clusters, levels,
            document_manifest=document_manifest,
        )

    # ── Document manifest ────────────────────────────────────────

    @staticmethod
    def _build_document_manifest(chunks: list) -> list:
        """Build a manifest of documents included in this hierarchy build.

        Returns a list of dicts with document_id, document_title, and chunk_count.
        Used for diff computation between hierarchy versions (Plan 6).
        """
        from collections import Counter

        doc_chunks: Counter = Counter()
        doc_titles: Dict[str, str] = {}

        for chunk in chunks:
            doc_id = chunk['document_id']
            doc_chunks[doc_id] += 1
            doc_titles[doc_id] = chunk['document_title']

        return [
            {
                'document_id': doc_id,
                'document_title': doc_titles[doc_id],
                'chunk_count': count,
            }
            for doc_id, count in doc_chunks.items()
        ]

    # ── Chunk loading ─────────────────────────────────────────────

    def _load_chunks(self, project_id: uuid.UUID):
        """Load all project chunks with embeddings. Returns (chunks_list, total, doc_count, title, desc)."""
        from apps.projects.models import DocumentChunk, Project

        project = Project.objects.filter(id=project_id).first()
        project_title = project.title if project else ''
        project_description = project.description if project else ''

        qs = (
            DocumentChunk.objects
            .filter(document__project_id=project_id, embedding__isnull=False)
            .select_related('document')
            .order_by('document', 'chunk_index')
        )

        chunks = []
        for c in qs:
            chunks.append({
                'id': str(c.id),
                'document_id': str(c.document_id),
                'document_title': c.document.title,
                'text': c.chunk_text[:500],
                'embedding': list(c.embedding),
            })

        total_chunks = len(chunks)
        total_documents = len(set(c['document_id'] for c in chunks))

        return chunks, total_chunks, total_documents, project_title, project_description

    # ── Level 0→1: Chunk clustering ──────────────────────────────

    def _build_level1(
        self,
        chunks: List[dict],
        normalized: np.ndarray,
        total_chunks: int,
    ) -> List[ClusterTreeNode]:
        """Cluster chunks into Level 1 topic nodes.

        Singleton clusters are assigned to the nearest multi-member cluster
        by centroid cosine similarity so no content is silently dropped.
        """
        threshold = LEVEL_THRESHOLDS[1]
        labels = self._agglomerative_cluster(normalized, threshold)

        # Group chunks by cluster label
        cluster_map: Dict[int, List[int]] = defaultdict(list)
        for idx, label in enumerate(labels):
            cluster_map[int(label)].append(idx)

        # Separate real clusters (≥2 members) from orphans (singletons)
        real_clusters: Dict[int, List[int]] = {}
        orphan_indices: List[int] = []
        for label, indices in cluster_map.items():
            if len(indices) >= 2:
                real_clusters[label] = indices
            else:
                orphan_indices.extend(indices)

        # Assign orphans to nearest real cluster by centroid similarity
        if orphan_indices and real_clusters:
            # Compute centroids for each real cluster
            centroids = {}
            for label, indices in real_clusters.items():
                centroid = normalized[indices].mean(axis=0)
                norm = np.linalg.norm(centroid)
                if norm > 0:
                    centroid = centroid / norm
                centroids[label] = centroid

            centroid_labels = sorted(centroids.keys())
            centroid_matrix = np.array([centroids[l] for l in centroid_labels])

            for orphan_idx in orphan_indices:
                sims = centroid_matrix @ normalized[orphan_idx]
                best = centroid_labels[int(np.argmax(sims))]
                real_clusters[best].append(orphan_idx)

            if orphan_indices:
                logger.debug(
                    "orphan_chunks_assigned",
                    extra={
                        'orphan_count': len(orphan_indices),
                        'cluster_count': len(real_clusters),
                    },
                )

        # Build Level 1 nodes from real clusters (now including absorbed orphans)
        level1_nodes = []
        for label, indices in sorted(real_clusters.items()):
            cluster_chunks = [chunks[i] for i in indices]
            chunk_ids = [c['id'] for c in cluster_chunks]
            document_ids = list(set(c['document_id'] for c in cluster_chunks))

            # Pick representative chunks (closest to centroid)
            cluster_embeddings = normalized[indices]
            centroid = cluster_embeddings.mean(axis=0)
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
            sims = cluster_embeddings @ centroid
            top_k = min(MAX_REPRESENTATIVE_CHUNKS, len(indices))
            top_indices = np.argsort(sims)[-top_k:][::-1]

            node = ClusterTreeNode(
                id=str(uuid.uuid4()),
                level=1,
                label='',  # Filled by LLM
                summary='',  # Filled by LLM
                chunk_ids=chunk_ids,
                document_ids=document_ids,
                chunk_count=len(chunk_ids),
                coverage_pct=round(len(chunk_ids) / total_chunks * 100, 1),
            )
            # Store representative texts for later summarization
            node._representative_texts = [
                cluster_chunks[int(ti)]['text'] for ti in top_indices
            ]
            node._representative_doc_titles = [
                cluster_chunks[int(ti)]['document_title'] for ti in top_indices
            ]
            level1_nodes.append(node)

        # Sort by coverage descending
        level1_nodes.sort(key=lambda n: n.chunk_count, reverse=True)
        return level1_nodes

    # ── Higher-level clustering ──────────────────────────────────

    def _cluster_nodes(
        self,
        nodes: List[ClusterTreeNode],
        level: int,
    ) -> List[ClusterTreeNode]:
        """Cluster existing tree nodes by their summary embeddings into higher-level nodes."""
        if len(nodes) < 2:
            return nodes

        # Build embedding matrix from node summaries
        embeddings = []
        for node in nodes:
            if node._embedding:
                embeddings.append(node._embedding)
            else:
                # Fallback: zero vector (shouldn't happen)
                embeddings.append([0.0] * 384)

        emb_matrix = np.array(embeddings)
        norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        normalized = emb_matrix / norms

        threshold = LEVEL_THRESHOLDS.get(level, 0.50)
        labels = self._agglomerative_cluster(normalized, threshold)

        # Group nodes by cluster label
        cluster_map: Dict[int, List[int]] = defaultdict(list)
        for idx, label in enumerate(labels):
            cluster_map[int(label)].append(idx)

        # Build parent nodes
        parent_nodes = []
        for label, indices in sorted(cluster_map.items()):
            children = [nodes[i] for i in indices]

            all_chunk_ids = []
            all_document_ids = set()
            total_count = 0
            total_coverage = 0.0

            for child in children:
                all_chunk_ids.extend(child.chunk_ids)
                all_document_ids.update(child.document_ids)
                total_count += child.chunk_count
                total_coverage += child.coverage_pct

            parent = ClusterTreeNode(
                id=str(uuid.uuid4()),
                level=level,
                label='',  # Filled by LLM
                summary='',  # Filled by LLM
                children=children,
                chunk_ids=all_chunk_ids,
                document_ids=list(all_document_ids),
                chunk_count=total_count,
                coverage_pct=round(total_coverage, 1),
            )
            parent_nodes.append(parent)

        parent_nodes.sort(key=lambda n: n.chunk_count, reverse=True)
        return parent_nodes

    # ── Agglomerative clustering ─────────────────────────────────

    @staticmethod
    def _agglomerative_cluster(
        normalized: np.ndarray,
        distance_threshold: float,
    ) -> np.ndarray:
        """Run agglomerative clustering on normalized embeddings."""
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
            # Greedy fallback
            logger.warning("sklearn unavailable, using greedy clustering fallback")
            return HierarchicalClusteringService._greedy_cluster(
                normalized, distance_threshold,
            )

    @staticmethod
    def _greedy_cluster(
        normalized: np.ndarray,
        distance_threshold: float,
    ) -> np.ndarray:
        """Simple greedy clustering fallback."""
        n = len(normalized)
        labels = np.full(n, -1, dtype=int)
        centroids = []
        counts = []
        next_label = 0

        for i in range(n):
            vec = normalized[i]
            if centroids:
                centroid_matrix = np.array(centroids)
                sims = centroid_matrix @ vec
                best_idx = int(np.argmax(sims))
                if (1 - sims[best_idx]) < distance_threshold:
                    labels[i] = best_idx
                    count = counts[best_idx]
                    centroids[best_idx] = (centroids[best_idx] * count + vec) / (count + 1)
                    norm = np.linalg.norm(centroids[best_idx])
                    if norm > 0:
                        centroids[best_idx] /= norm
                    counts[best_idx] += 1
                    continue

            labels[i] = next_label
            centroids.append(vec.copy())
            counts.append(1)
            next_label += 1

        return labels

    # ── LLM summarization ────────────────────────────────────────

    async def _summarize_nodes_batch(
        self,
        nodes: List[ClusterTreeNode],
        level: int,
        chunks: Optional[List[dict]] = None,
    ):
        """Summarize all nodes at a given level using parallel LLM calls."""
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_LLM)

        async def _summarize_one(node: ClusterTreeNode):
            async with semaphore:
                try:
                    label, summary = await self._summarize_node(node, level, chunks)
                    node.label = label
                    node.summary = summary
                except Exception:
                    logger.warning(
                        "hierarchy_summarize_failed",
                        extra={'node_id': node.id, 'level': level},
                        exc_info=True,
                    )
                    node.label = f'Topic {node.id[:8]}'
                    node.summary = f'Cluster of {node.chunk_count} passages.'

        await asyncio.gather(*[_summarize_one(n) for n in nodes])

    async def _summarize_node(
        self,
        node: ClusterTreeNode,
        level: int,
        chunks: Optional[List[dict]] = None,
    ) -> tuple[str, str]:
        """Single LLM call to summarize a node. Returns (label, summary)."""
        from apps.common.llm_providers.factory import get_llm_provider
        from apps.intelligence.hierarchy_prompts import (
            build_topic_summary_prompt,
            build_theme_synthesis_prompt,
        )

        provider = get_llm_provider('fast')

        if level == 1:
            # Use representative chunk texts stored during _build_level1
            chunk_texts = getattr(node, '_representative_texts', [])
            doc_titles = getattr(node, '_representative_doc_titles', [])
            system_prompt, user_prompt = build_topic_summary_prompt(chunk_texts, doc_titles)
        elif level >= 2:
            # Use children's labels and summaries
            topic_summaries = [
                {
                    'label': child.label,
                    'summary': child.summary,
                    'chunk_count': child.chunk_count,
                }
                for child in node.children
            ]
            system_prompt, user_prompt = build_theme_synthesis_prompt(topic_summaries)
        else:
            return f'Cluster {node.id[:8]}', ''

        response = await provider.generate(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            max_tokens=256,
            temperature=0.3,
        )

        return self._parse_label_summary(response)

    @staticmethod
    def _parse_label_summary(response: str) -> tuple[str, str]:
        """Parse <label>...</label><summary>...</summary> from LLM response."""
        label_match = re.search(r'<label>(.*?)</label>', response, re.DOTALL)
        summary_match = re.search(r'<summary>(.*?)</summary>', response, re.DOTALL)

        label = label_match.group(1).strip() if label_match else 'Unlabeled'
        summary = summary_match.group(1).strip() if summary_match else response.strip()

        return label, summary

    # ── Embedding generation ─────────────────────────────────────

    def _embed_node_summaries(self, nodes: List[ClusterTreeNode]):
        """Generate embeddings for node summaries using sentence-transformers."""
        from apps.common.vector_utils import generate_embeddings_batch

        texts = [node.summary for node in nodes]
        embeddings = generate_embeddings_batch(texts)

        for node, emb in zip(nodes, embeddings):
            node._embedding = emb

    # ── Root synthesis ────────────────────────────────────────────

    async def _build_root(
        self,
        level2_nodes: List[ClusterTreeNode],
        total_chunks: int,
        project_title: str,
        project_description: str,
    ) -> ClusterTreeNode:
        """Build the root node (Level 3) from Level 2 themes."""
        from apps.common.llm_providers.factory import get_llm_provider
        from apps.intelligence.hierarchy_prompts import build_project_overview_prompt

        theme_summaries = [
            {
                'label': node.label,
                'summary': node.summary,
                'coverage_pct': node.coverage_pct,
            }
            for node in level2_nodes
        ]

        system_prompt, user_prompt = build_project_overview_prompt(
            theme_summaries, project_title, project_description,
        )

        provider = get_llm_provider('fast')
        try:
            response = await provider.generate(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
                max_tokens=512,
                temperature=0.3,
            )
            label, summary = self._parse_label_summary(response)
        except Exception:
            logger.warning("hierarchy_root_synthesis_failed", exc_info=True)
            label = project_title or 'Project Overview'
            summary = f'Project spans {len(level2_nodes)} themes across {total_chunks} passages.'

        all_chunk_ids = []
        all_document_ids = set()
        for node in level2_nodes:
            all_chunk_ids.extend(node.chunk_ids)
            all_document_ids.update(node.document_ids)

        return ClusterTreeNode(
            id=str(uuid.uuid4()),
            level=3,
            label=label,
            summary=summary,
            children=level2_nodes,
            chunk_ids=all_chunk_ids,
            document_ids=list(all_document_ids),
            chunk_count=total_chunks,
            coverage_pct=100.0,
        )

    # ── Serialization ────────────────────────────────────────────

    def _serialize_tree(
        self,
        root: ClusterTreeNode,
        start_time: float,
        total_chunks: int,
        total_clusters: int,
        levels: int,
        document_manifest: Optional[list] = None,
    ) -> dict:
        """
        Convert ClusterTreeNode tree to a JSON-serializable dict.
        Strips internal fields (_representative_texts, etc.).

        Preserves embeddings for Level 1 (topic) and Level 2 (theme)
        nodes so CaseChunkRetriever can do hierarchy-aware similarity
        matching without recomputing them.

        Includes document_manifest in metadata for change detection (Plan 6).
        """
        def _clean_node(node: ClusterTreeNode) -> dict:
            result = {
                'id': node.id,
                'level': node.level,
                'label': node.label,
                'summary': node.summary,
                'children': [_clean_node(child) for child in node.children],
                'chunk_ids': node.chunk_ids,
                'document_ids': node.document_ids,
                'chunk_count': node.chunk_count,
                'coverage_pct': node.coverage_pct,
            }
            # Store embeddings for topic/theme nodes (Level 1-2) so the
            # case chunk retriever can match against them. ~1.5KB per node
            # (384 floats × 4 bytes), negligible in the JSON blob.
            if node.level in (1, 2) and node._embedding:
                result['embedding'] = node._embedding
            return result

        manifest = document_manifest or []
        return {
            'tree': _clean_node(root),
            'metadata': {
                'total_chunks': total_chunks,
                'total_clusters': total_clusters,
                'levels': levels,
                'duration_ms': int((time.time() - start_time) * 1000),
                'document_manifest': manifest,
                'document_count': len(manifest),
            },
        }
