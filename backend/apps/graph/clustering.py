"""
ClusteringService — server-side node clustering for graph visualization and summaries.

Primary algorithm: Leiden community detection (via leidenalg/igraph).
Fallback: Union-Find connected components (no external dependency).
Post-processing: semantic refinement using embedding similarity.
"""
import logging
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from .models import Node, Edge, EdgeType
from .services import GraphService

logger = logging.getLogger(__name__)


class ClusteringService:
    """Server-side node clustering for graph layout and summary generation."""

    @staticmethod
    def cluster_project_nodes(
        project_id: uuid.UUID,
        min_cluster_size: int = 2,
        similarity_threshold: float = 0.6,
        resolution: float = 1.0,
        semantic_variance_threshold: float = 0.7,
        merge_threshold: float = 0.75,
    ) -> List[Dict[str, Any]]:
        """
        Cluster project nodes into thematic groups.

        Pipeline:
        1. Leiden community detection on supports/depends_on edges
           (falls back to Union-Find if leidenalg not installed)
        2. Semantic refinement: split high-variance clusters, merge small ones
        3. Assign remaining orphans by embedding similarity
        4. Build result dicts with centroid, edge counts, type breakdown

        Returns:
            List of cluster dicts: [{
                'node_ids': [str, ...],
                'centroid_node_id': str,
                'edge_count': int,
                'node_types': {claim: N, evidence: N, ...},
            }]
        """
        graph = GraphService.get_project_graph(project_id)
        nodes = graph['nodes']
        edges = graph['edges']

        if not nodes:
            return []

        nodes_by_id = {n.id: n for n in nodes}

        # Step 1: Community detection
        try:
            components = ClusteringService._build_leiden_communities(
                nodes, edges, resolution=resolution,
            )
            logger.info(
                "leiden_clustering_complete",
                extra={
                    'project_id': str(project_id),
                    'communities': len(components),
                    'resolution': resolution,
                },
            )
        except ImportError:
            logger.info("leidenalg not available, falling back to Union-Find")
            components = ClusteringService._build_connected_components(nodes, edges)

        # Step 2: Separate real clusters from orphans
        clusters: List[Set[uuid.UUID]] = []
        orphan_nodes: List[Node] = []

        for component in components:
            if len(component) >= min_cluster_size:
                clusters.append(component)
            else:
                for node_id in component:
                    if node_id in nodes_by_id:
                        orphan_nodes.append(nodes_by_id[node_id])

        # Step 3: Semantic refinement — split high-variance, merge small
        if clusters:
            clusters = ClusteringService._semantic_refinement(
                clusters, nodes_by_id,
                variance_threshold=semantic_variance_threshold,
                merge_threshold=merge_threshold,
                min_cluster_size=min_cluster_size,
            )

        # Step 4: Assign orphans by embedding similarity
        if orphan_nodes and clusters:
            clusters = ClusteringService._assign_orphans_by_embedding(
                orphan_nodes, clusters, nodes_by_id, similarity_threshold,
            )
        elif orphan_nodes and not clusters:
            for node in orphan_nodes:
                clusters.append({node.id})

        # Step 5: Build result dicts
        edge_index: Dict[uuid.UUID, Set[uuid.UUID]] = defaultdict(set)
        for edge in edges:
            edge_index[edge.source_node_id].add(edge.target_node_id)
            edge_index[edge.target_node_id].add(edge.source_node_id)

        result = []
        for cluster_set in clusters:
            node_ids = list(cluster_set) if isinstance(cluster_set, set) else list(cluster_set)
            if not node_ids:
                continue

            node_types: Dict[str, int] = defaultdict(int)
            for nid in node_ids:
                node = nodes_by_id.get(nid)
                if node:
                    node_types[node.node_type] = node_types.get(node.node_type, 0) + 1

            node_id_set = set(node_ids)
            internal_edges = 0
            for nid in node_ids:
                for neighbor in edge_index.get(nid, set()):
                    if neighbor in node_id_set:
                        internal_edges += 1
            internal_edges //= 2

            centroid_id = max(
                node_ids,
                key=lambda nid: len(edge_index.get(nid, set())),
            )

            # Generate a lightweight label from the centroid node's content
            centroid_node = nodes_by_id.get(centroid_id)
            label = centroid_node.content[:50] if centroid_node else f'Cluster'

            result.append({
                'node_ids': [str(nid) for nid in node_ids],
                'centroid_node_id': str(centroid_id),
                'edge_count': internal_edges,
                'node_types': dict(node_types),
                'label': label,
            })

        result.sort(key=lambda c: len(c['node_ids']), reverse=True)
        return result

    # ── Leiden community detection ────────────────────────────────

    @staticmethod
    def _build_leiden_communities(
        nodes: List[Node],
        edges: List[Edge],
        resolution: float = 1.0,
    ) -> List[Set[uuid.UUID]]:
        """
        Leiden community detection via igraph + leidenalg.

        Uses RBConfigurationVertexPartition (modularity with resolution parameter).
        Only supports/depends_on edges are used for clustering;
        contradicts edges connect opposing nodes and should not cluster together.

        Raises ImportError if leidenalg is not installed.
        """
        import igraph as ig
        import leidenalg as la

        node_ids = [n.id for n in nodes]
        id_to_idx = {nid: idx for idx, nid in enumerate(node_ids)}

        g = ig.Graph(n=len(node_ids), directed=False)

        clustering_types = {EdgeType.SUPPORTS, EdgeType.DEPENDS_ON}
        edge_list = []
        edge_weights = []

        for edge in edges:
            if edge.edge_type not in clustering_types:
                continue
            src_idx = id_to_idx.get(edge.source_node_id)
            tgt_idx = id_to_idx.get(edge.target_node_id)
            if src_idx is not None and tgt_idx is not None and src_idx != tgt_idx:
                edge_list.append((src_idx, tgt_idx))
                edge_weights.append(edge.strength if edge.strength is not None else 1.0)

        if edge_list:
            g.add_edges(edge_list)
            g.es['weight'] = edge_weights

        partition = la.find_partition(
            g,
            la.RBConfigurationVertexPartition,
            weights='weight' if edge_list else None,
            resolution_parameter=resolution,
        )

        communities: List[Set[uuid.UUID]] = []
        for community_indices in partition:
            community = {node_ids[idx] for idx in community_indices}
            communities.append(community)

        return communities

    # ── Union-Find fallback ──────────────────────────────────────

    @staticmethod
    def _build_connected_components(
        nodes: List[Node],
        edges: List[Edge],
    ) -> List[Set[uuid.UUID]]:
        """
        Union-Find over supports/depends_on edges (fallback when leidenalg unavailable).

        contradicts edges are excluded because they connect opposing nodes
        that should NOT be in the same theme cluster.
        """
        parent: Dict[uuid.UUID, uuid.UUID] = {}

        def find(x: uuid.UUID) -> uuid.UUID:
            while parent.get(x, x) != x:
                parent[x] = parent.get(parent[x], parent[x])
                x = parent[x]
            return x

        def union(a: uuid.UUID, b: uuid.UUID):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for node in nodes:
            parent[node.id] = node.id

        clustering_types = {EdgeType.SUPPORTS, EdgeType.DEPENDS_ON}
        for edge in edges:
            if edge.edge_type in clustering_types:
                if edge.source_node_id in parent and edge.target_node_id in parent:
                    union(edge.source_node_id, edge.target_node_id)

        components: Dict[uuid.UUID, Set[uuid.UUID]] = defaultdict(set)
        for node_id in parent:
            root = find(node_id)
            components[root].add(node_id)

        return list(components.values())

    # ── Semantic refinement ──────────────────────────────────────

    @staticmethod
    def _semantic_refinement(
        clusters: List[Set[uuid.UUID]],
        nodes_by_id: Dict[uuid.UUID, Node],
        variance_threshold: float = 0.7,
        merge_threshold: float = 0.75,
        min_cluster_size: int = 2,
    ) -> List[Set[uuid.UUID]]:
        """
        Post-Leiden semantic refinement:
        1. Split clusters with high embedding variance (semantically diverse)
        2. Merge small clusters whose centroids are semantically close
        """
        from apps.common.vector_utils import cosine_similarity

        refined: List[Set[uuid.UUID]] = []

        # Phase 1: Split high-variance clusters
        for cluster in clusters:
            embeddings = {}
            for nid in cluster:
                node = nodes_by_id.get(nid)
                if node and node.embedding is not None:
                    embeddings[nid] = np.array(node.embedding)

            if len(embeddings) < 4:
                refined.append(cluster)
                continue

            # Compute intra-cluster variance (mean pairwise cosine distance)
            emb_list = list(embeddings.values())
            emb_matrix = np.stack(emb_list)
            norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)
            normalized = emb_matrix / norms
            sim_matrix = normalized @ normalized.T
            n = len(emb_list)
            triu_indices = np.triu_indices(n, k=1)
            mean_sim = float(np.mean(sim_matrix[triu_indices])) if len(triu_indices[0]) > 0 else 1.0
            variance = 1.0 - mean_sim

            if variance > variance_threshold:
                nid_list = list(embeddings.keys())
                sub_a, sub_b = ClusteringService._split_2means(nid_list, embeddings)
                no_emb = cluster - set(embeddings.keys())
                if len(sub_a) >= len(sub_b):
                    sub_a |= no_emb
                else:
                    sub_b |= no_emb
                refined.append(sub_a)
                refined.append(sub_b)
            else:
                refined.append(cluster)

        # Phase 2: Merge small clusters with similar centroids
        cluster_centroids: List[Optional[np.ndarray]] = []
        for cluster in refined:
            embs = []
            for nid in cluster:
                node = nodes_by_id.get(nid)
                if node and node.embedding is not None:
                    embs.append(np.array(node.embedding))
            if embs:
                cluster_centroids.append(np.mean(embs, axis=0))
            else:
                cluster_centroids.append(None)

        merged_into: Dict[int, int] = {}
        for i in range(len(refined)):
            if i in merged_into:
                continue
            if len(refined[i]) >= min_cluster_size:
                continue
            if cluster_centroids[i] is None:
                continue

            best_sim = -1.0
            best_j = -1
            for j in range(len(refined)):
                if i == j or j in merged_into:
                    continue
                if cluster_centroids[j] is None:
                    continue
                sim = cosine_similarity(
                    cluster_centroids[i].tolist(),
                    cluster_centroids[j].tolist(),
                )
                if sim > best_sim:
                    best_sim = sim
                    best_j = j

            if best_sim >= merge_threshold and best_j >= 0:
                merged_into[i] = best_j

        final: List[Set[uuid.UUID]] = []
        for i, cluster in enumerate(refined):
            if i in merged_into:
                target = merged_into[i]
                refined[target] = refined[target] | cluster
            else:
                final.append(cluster)

        return final

    @staticmethod
    def _split_2means(
        node_ids: List[uuid.UUID],
        embeddings: Dict[uuid.UUID, np.ndarray],
        max_iterations: int = 10,
    ) -> Tuple[Set[uuid.UUID], Set[uuid.UUID]]:
        """
        Simple 2-means clustering on embeddings. No sklearn dependency.
        """
        emb_matrix = np.stack([embeddings[nid] for nid in node_ids])

        centroid_a = emb_matrix[0].copy()
        distances = np.linalg.norm(emb_matrix - centroid_a, axis=1)
        far_idx = int(np.argmax(distances))
        centroid_b = emb_matrix[far_idx].copy()

        assignments = np.zeros(len(node_ids), dtype=int)

        for _ in range(max_iterations):
            dist_a = np.linalg.norm(emb_matrix - centroid_a, axis=1)
            dist_b = np.linalg.norm(emb_matrix - centroid_b, axis=1)
            new_assignments = (dist_b < dist_a).astype(int)

            if np.array_equal(new_assignments, assignments):
                break
            assignments = new_assignments

            mask_a = assignments == 0
            mask_b = assignments == 1
            if mask_a.any():
                centroid_a = emb_matrix[mask_a].mean(axis=0)
            if mask_b.any():
                centroid_b = emb_matrix[mask_b].mean(axis=0)

        set_a = {node_ids[i] for i in range(len(node_ids)) if assignments[i] == 0}
        set_b = {node_ids[i] for i in range(len(node_ids)) if assignments[i] == 1}

        return set_a, set_b

    # ── Orphan assignment ────────────────────────────────────────

    @staticmethod
    def _assign_orphans_by_embedding(
        orphan_nodes: List[Node],
        clusters: List[Set[uuid.UUID]],
        all_nodes_by_id: Dict[uuid.UUID, Node],
        similarity_threshold: float,
    ) -> List[Set[uuid.UUID]]:
        """
        Assign orphaned nodes to the nearest cluster by embedding cosine similarity.
        Nodes below the threshold remain as singletons.

        Centroids are computed once upfront using numpy vectorized ops,
        then incrementally updated as orphans are assigned.
        """
        from apps.common.vector_utils import cosine_similarity

        # Pre-compute cluster centroids and embedding counts (vectorized)
        cluster_centroids: List[Optional[np.ndarray]] = []
        cluster_emb_counts: List[int] = []
        for cluster_set in clusters:
            embs = []
            for nid in cluster_set:
                node = all_nodes_by_id.get(nid)
                if node and node.embedding is not None:
                    embs.append(np.array(node.embedding))
            if embs:
                cluster_centroids.append(np.mean(embs, axis=0))
                cluster_emb_counts.append(len(embs))
            else:
                cluster_centroids.append(None)
                cluster_emb_counts.append(0)

        for orphan in orphan_nodes:
            if orphan.embedding is None:
                clusters.append({orphan.id})
                cluster_centroids.append(None)
                cluster_emb_counts.append(0)
                continue

            orphan_emb = np.array(orphan.embedding)
            best_sim = -1.0
            best_idx = -1

            for idx, centroid in enumerate(cluster_centroids):
                if centroid is None:
                    continue
                sim = cosine_similarity(orphan_emb.tolist(), centroid.tolist())
                if sim > best_sim:
                    best_sim = sim
                    best_idx = idx

            if best_sim >= similarity_threshold and best_idx >= 0:
                clusters[best_idx].add(orphan.id)
                # Incrementally update centroid: new_mean = (old_mean * n + new) / (n + 1)
                n = cluster_emb_counts[best_idx]
                cluster_centroids[best_idx] = (cluster_centroids[best_idx] * n + orphan_emb) / (n + 1)
                cluster_emb_counts[best_idx] = n + 1
            else:
                clusters.append({orphan.id})
                cluster_centroids.append(None)
                cluster_emb_counts.append(0)

        return clusters

    # ── Cluster quality metrics ──────────────────────────────────

    @staticmethod
    def compute_cluster_quality(
        clusters: List[Dict[str, Any]],
        edges: List[Edge],
    ) -> Dict[str, Any]:
        """
        Compute per-cluster conductance and overall modularity.

        Conductance = cut(S) / min(vol(S), vol(V\\S))
        where cut(S) = edges with exactly one endpoint in S,
              vol(S) = sum of degrees of nodes in S.
        """
        all_node_ids: Set[str] = set()
        for c in clusters:
            all_node_ids.update(c['node_ids'])

        degree: Dict[str, int] = defaultdict(int)
        edge_endpoints: List[Tuple[str, str]] = []
        for e in edges:
            src = str(e.source_node_id)
            tgt = str(e.target_node_id)
            if src in all_node_ids and tgt in all_node_ids:
                degree[src] += 1
                degree[tgt] += 1
                edge_endpoints.append((src, tgt))

        total_edges = len(edge_endpoints)
        total_vol = sum(degree.values())

        per_cluster = []
        for idx, cluster in enumerate(clusters):
            node_set = set(cluster['node_ids'])
            n = len(node_set)

            vol_s = sum(degree.get(nid, 0) for nid in node_set)
            vol_complement = total_vol - vol_s

            cut = 0
            internal = 0
            for src, tgt in edge_endpoints:
                src_in = src in node_set
                tgt_in = tgt in node_set
                if src_in and tgt_in:
                    internal += 1
                elif src_in or tgt_in:
                    cut += 1

            min_vol = min(vol_s, vol_complement) if vol_complement > 0 else vol_s
            conductance = cut / min_vol if min_vol > 0 else 0.0

            max_possible = n * (n - 1) / 2
            density = internal / max_possible if max_possible > 0 else 0.0

            per_cluster.append({
                'cluster_index': idx,
                'conductance': round(conductance, 4),
                'density': round(density, 4),
                'node_count': n,
            })

        mean_conductance = (
            sum(c['conductance'] for c in per_cluster) / len(per_cluster)
            if per_cluster else 0.0
        )

        # Modularity: Q = sum_c[ e_c/m - (a_c/2m)^2 ]
        modularity = 0.0
        if total_edges > 0:
            m2 = 2 * total_edges
            for cluster in clusters:
                node_set = set(cluster['node_ids'])
                e_c = sum(1 for src, tgt in edge_endpoints
                          if src in node_set and tgt in node_set)
                a_c = sum(degree.get(nid, 0) for nid in node_set)
                modularity += e_c / m2 - (a_c / m2) ** 2

        return {
            'modularity': round(modularity, 4),
            'mean_conductance': round(mean_conductance, 4),
            'per_cluster': per_cluster,
        }

    # ── Cluster labeling ─────────────────────────────────────────

    @staticmethod
    async def label_clusters(
        clusters: List[Dict[str, Any]],
        all_nodes_by_id: Dict[uuid.UUID, Node],
        previous_clusters: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate short theme labels for each cluster using LLM.

        Reuses labels from previous clusters when node overlap (Jaccard) > 0.5.
        Only calls LLM for new or significantly changed clusters.
        """
        from apps.common.llm_providers.anthropic_provider import AnthropicProvider

        prev_lookup = {}
        if previous_clusters:
            for pc in previous_clusters:
                if 'label' in pc and 'node_ids' in pc:
                    prev_lookup[pc['label']] = set(pc['node_ids'])

        needs_labeling = []
        for cluster in clusters:
            current_ids = set(cluster['node_ids'])
            matched_label = None

            for label, prev_ids in prev_lookup.items():
                intersection = current_ids & prev_ids
                union = current_ids | prev_ids
                jaccard = len(intersection) / len(union) if union else 0
                if jaccard > 0.5:
                    matched_label = label
                    break

            if matched_label:
                cluster['label'] = matched_label
            else:
                needs_labeling.append(cluster)

        if not needs_labeling:
            return clusters

        prompt_parts = [
            "Generate a short theme label (2-5 words) for each cluster of knowledge graph nodes.",
            "Return one label per line, in order. Labels should be concise and descriptive.",
            "",
        ]
        for i, cluster in enumerate(needs_labeling):
            node_contents = []
            for nid_str in cluster['node_ids'][:8]:
                nid = uuid.UUID(nid_str)
                node = all_nodes_by_id.get(nid)
                if node:
                    node_contents.append(f"  [{node.node_type}] {node.content[:100]}")
            prompt_parts.append(f"Cluster {i + 1}:")
            prompt_parts.extend(node_contents)
            prompt_parts.append("")

        try:
            provider = AnthropicProvider()
            response = await provider.generate(
                messages=[{"role": "user", "content": "\n".join(prompt_parts)}],
                system_prompt="You are a concise labeler. For each cluster, output ONLY a 2-5 word theme label on its own line. No numbering, no explanation.",
                max_tokens=256,
                temperature=0.3,
            )
            labels = [
                line.strip()
                for line in response.strip().split('\n')
                if line.strip()
            ]

            for i, cluster in enumerate(needs_labeling):
                if i < len(labels):
                    cluster['label'] = labels[i]
                else:
                    cluster['label'] = f"Theme {i + 1}"
        except Exception:
            logger.warning("Failed to generate cluster labels via LLM", exc_info=True)
            for i, cluster in enumerate(needs_labeling):
                if 'label' not in cluster:
                    types = cluster.get('node_types', {})
                    dominant = max(types, key=types.get) if types else 'mixed'
                    cluster['label'] = f"{dominant.title()} cluster"

        return clusters
