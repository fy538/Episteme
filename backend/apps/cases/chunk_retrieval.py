"""
CaseChunkRetriever — find relevant document chunks for a case's decision question.

Replaces the conceptual role of GraphService.auto_pull_project_nodes(). Instead
of pulling pre-extracted graph nodes by similarity, this retrieves raw document
chunks that will be fed into the case-level extraction pipeline.

Two retrieval strategies:
1. Direct embedding similarity — pgvector cosine distance on chunk embeddings
2. Hierarchy-aware retrieval — walk the ClusterHierarchy tree, find relevant
   theme/topic clusters, pull all their chunks (catches chunks that individually
   don't match the query but belong to a relevant cluster)
"""
import logging
import uuid
from typing import List

from pgvector.django import CosineDistance

from apps.common.vector_utils import (
    generate_embedding,
    cosine_similarity,
)
from apps.projects.models import DocumentChunk

logger = logging.getLogger(__name__)


class CaseChunkRetriever:
    """Retrieve relevant document chunks for a case's decision question."""

    def retrieve_relevant_chunks(
        self,
        case,
        max_chunks: int = 50,
        similarity_threshold: float = 0.45,
    ) -> List[DocumentChunk]:
        """Find the most relevant chunks from the project's documents
        for this case's decision question.

        Strategy:
        1. Build focus text from case context (decision question, position, constraints)
        2. Embed the focus text
        3. pgvector similarity search across all project chunks
        4. Also pull chunks from relevant theme clusters (hierarchy-aware)
        5. Merge, deduplicate, and rank by relevance
        6. Return top-K chunks

        Args:
            case: Case instance with decision_question, position, constraints
            max_chunks: Maximum number of chunks to return
            similarity_threshold: Minimum cosine similarity for embedding retrieval

        Returns:
            List of DocumentChunk instances ordered by relevance
        """
        focus_text = self._build_focus_text(case)
        if not focus_text:
            logger.info("No focus text for case %s — skipping chunk retrieval", case.id)
            return []

        try:
            focus_embedding = generate_embedding(focus_text)
        except Exception:
            logger.warning(
                "Failed to generate embedding for case focus text",
                exc_info=True,
                extra={'case_id': str(case.id)},
            )
            return []

        # Strategy 1: Direct embedding similarity
        # Materialize the queryset to avoid double-evaluation
        embedding_chunks = list(self._retrieve_by_embedding(
            project_id=case.project_id,
            focus_embedding=focus_embedding,
            max_chunks=max_chunks * 2,  # Get more than needed for merging
            similarity_threshold=similarity_threshold,
        ))

        # Strategy 2: Hierarchy-aware retrieval (if hierarchy exists)
        hierarchy_chunks = self._retrieve_from_hierarchy(
            project_id=case.project_id,
            focus_embedding=focus_embedding,
            max_chunks=max_chunks,
        )

        # Merge, deduplicate, and rank
        merged = self._merge_and_rank(embedding_chunks, hierarchy_chunks, max_chunks)

        logger.info(
            "chunk_retrieval_complete",
            extra={
                'case_id': str(case.id),
                'embedding_matches': len(embedding_chunks),
                'hierarchy_matches': len(hierarchy_chunks),
                'final_count': len(merged),
            },
        )

        return merged

    def _build_focus_text(self, case) -> str:
        """Build a focus text string from case context for embedding.

        Combines decision question, position, constraints, and any
        companion-originated context for maximum relevance matching.
        """
        parts = []

        if case.decision_question:
            parts.append(case.decision_question)
        if case.position:
            parts.append(case.position)

        # Include constraint descriptions
        constraints = case.constraints or []
        for constraint in constraints:
            if isinstance(constraint, dict) and constraint.get('description'):
                parts.append(constraint['description'])
            elif isinstance(constraint, str) and constraint.strip():
                parts.append(constraint)

        # Include companion-originated context if available
        metadata = case.metadata or {}
        companion_state = metadata.get('companion_origin', {})
        if companion_state.get('established'):
            for fact in companion_state['established']:
                if isinstance(fact, str):
                    parts.append(fact)

        return ' '.join(parts).strip()

    def _retrieve_by_embedding(
        self,
        project_id: uuid.UUID,
        focus_embedding: List[float],
        max_chunks: int,
        similarity_threshold: float,
    ):
        """Find chunks via pgvector cosine distance.

        Same pattern as similarity_search() in vector_utils.py but
        operates directly on DocumentChunk.
        """
        return (
            DocumentChunk.objects
            .filter(document__project_id=project_id)
            .exclude(embedding__isnull=True)
            .select_related('document')
            .annotate(distance=CosineDistance('embedding', focus_embedding))
            .filter(distance__lt=(1 - similarity_threshold))
            .order_by('distance')[:max_chunks]
        )

    def _retrieve_from_hierarchy(
        self,
        project_id: uuid.UUID,
        focus_embedding: List[float],
        max_chunks: int,
    ) -> List[DocumentChunk]:
        """Find relevant theme/topic clusters, then pull all their chunks.

        Catches chunks that might not individually match the query
        but belong to a relevant topic cluster.

        Gracefully returns empty if no hierarchy exists (Plan 1 not built yet).
        """
        from django.conf import settings

        extraction_settings = getattr(settings, 'CASE_EXTRACTION_SETTINGS', {})
        theme_threshold = extraction_settings.get('hierarchy_theme_threshold', 0.5)
        topic_threshold = extraction_settings.get('hierarchy_topic_threshold', 0.55)

        try:
            from apps.graph.models import ClusterHierarchy
            hierarchy = ClusterHierarchy.objects.filter(
                project_id=project_id,
                is_current=True,
            ).first()
        except Exception as e:
            logger.warning("Could not load hierarchy for chunk retrieval: %s", e)
            return []

        if not hierarchy:
            return []

        tree = hierarchy.tree or {}
        relevant_chunk_ids = []

        # Walk the tree: Level 2 (themes) → Level 1 (topics) → chunks
        for theme in tree.get('children', []):
            theme_embedding = theme.get('embedding')
            if not theme_embedding:
                continue

            theme_sim = cosine_similarity(focus_embedding, theme_embedding)
            if theme_sim > theme_threshold:
                # Entire theme is relevant — pull all its chunks
                relevant_chunk_ids.extend(self._collect_chunk_ids(theme))
            else:
                # Check individual topics within this theme
                for topic in theme.get('children', []):
                    topic_embedding = topic.get('embedding')
                    if not topic_embedding:
                        continue

                    topic_sim = cosine_similarity(focus_embedding, topic_embedding)
                    if topic_sim > topic_threshold:
                        relevant_chunk_ids.extend(topic.get('chunk_ids', []))

        if not relevant_chunk_ids:
            return []

        # Deduplicate and fetch
        unique_ids = list(set(relevant_chunk_ids))[:max_chunks]
        return list(
            DocumentChunk.objects
            .filter(id__in=unique_ids)
            .select_related('document')
        )

    def _collect_chunk_ids(self, node: dict) -> List[str]:
        """Recursively collect all chunk IDs from a hierarchy node's subtree."""
        ids = list(node.get('chunk_ids', []))
        for child in node.get('children', []):
            ids.extend(self._collect_chunk_ids(child))
        return ids

    def _merge_and_rank(
        self,
        embedding_chunks,
        hierarchy_chunks: List[DocumentChunk],
        max_chunks: int,
    ) -> List[DocumentChunk]:
        """Merge chunks from both strategies, deduplicate, rank by relevance.

        Embedding matches come first (directly relevant), then hierarchy
        matches (contextually relevant via cluster membership).
        """
        seen_ids = set()
        ranked = []

        # Embedding matches first (higher relevance)
        for chunk in embedding_chunks:
            if chunk.id not in seen_ids:
                seen_ids.add(chunk.id)
                ranked.append(chunk)

        # Then hierarchy matches (contextually relevant)
        for chunk in hierarchy_chunks:
            if chunk.id not in seen_ids:
                seen_ids.add(chunk.id)
                ranked.append(chunk)

        return ranked[:max_chunks]
