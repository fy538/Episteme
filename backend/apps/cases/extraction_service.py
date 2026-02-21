"""
CaseExtractionService — extract case-scoped nodes from document chunks.

This is the core of objective-driven extraction. Given relevant chunks
and a case's decision question, it extracts Claims, Evidence, Assumptions,
and Tensions focused on the specific decision.

Reuses the extraction tool schema, validation, and chunk matching from
the existing project-level extraction pipeline (apps.graph.extraction).
"""
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from asgiref.sync import async_to_sync

from apps.common.vector_utils import generate_embeddings_batch
from apps.graph.extraction import (
    EXTRACTION_TOOL,
    _validate_extraction_item,
    _validate_extraction_edge,
    _match_source_chunks,
    _normalize_extraction_result,
)
from apps.graph.models import Node, Edge, GraphDelta
from apps.graph.services import GraphService
from apps.projects.models import DocumentChunk

from .extraction_prompts import (
    build_case_extraction_system_prompt,
    build_case_extraction_user_prompt,
    build_incremental_extraction_system_prompt,
)

logger = logging.getLogger(__name__)


class ExtractionLLMError(Exception):
    """Raised when the extraction LLM call fails.

    Distinguishes an LLM/network failure (should be retried or reported)
    from a legitimate empty result (LLM found nothing to extract).
    """
    pass


@dataclass
class CaseExtractionResult:
    """Results from case-level extraction."""
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    delta: Optional[GraphDelta] = None
    chunk_count: int = 0

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


class CaseExtractionService:
    """Extract case-scoped nodes from document chunks using LLM."""

    def extract_case_graph(
        self,
        case,
        chunks: List[DocumentChunk],
    ) -> CaseExtractionResult:
        """Extract Claims/Evidence/Assumptions/Tensions from relevant chunks,
        focused on the case's decision question.

        Args:
            case: Case instance with decision_question, position, constraints
            chunks: List of relevant DocumentChunk instances

        Returns:
            CaseExtractionResult with nodes, edges, delta, chunk_count
        """
        if not chunks:
            logger.info("No chunks provided for case %s extraction", case.id)
            return CaseExtractionResult()

        # 1. Group chunks by document for context
        chunks_by_doc = self._group_by_document(chunks)

        # 2. Build prompt with decision question as lens
        system_prompt = build_case_extraction_system_prompt(case)

        companion_state = (case.metadata or {}).get('companion_origin')
        user_prompt = build_case_extraction_user_prompt(
            case, chunks_by_doc, companion_state
        )

        # 3. Call LLM with tool_use
        raw_result = self._call_extraction_llm(system_prompt, user_prompt)
        if not raw_result or not raw_result.get('nodes'):
            logger.info("No nodes extracted for case %s", case.id)
            return CaseExtractionResult(chunk_count=len(chunks))

        # 4. Create nodes, edges, and provenance
        nodes, edges = self._create_nodes_and_edges(case, raw_result, chunks)

        # 5. Create GraphDelta
        delta = self._create_delta(case, nodes, edges)

        logger.info(
            "case_extraction_complete",
            extra={
                'case_id': str(case.id),
                'nodes_created': len(nodes),
                'edges_created': len(edges),
                'chunks_used': len(chunks),
            },
        )

        return CaseExtractionResult(
            nodes=nodes,
            edges=edges,
            delta=delta,
            chunk_count=len(chunks),
        )

    def incremental_extract(
        self,
        case,
        new_chunks: List[DocumentChunk],
        existing_nodes: List[Node],
    ) -> CaseExtractionResult:
        """Extract from new chunks, aware of existing case graph.

        The prompt includes existing node summaries so the LLM doesn't
        duplicate and can create edges to existing nodes.
        """
        if not new_chunks:
            return CaseExtractionResult()

        # Build existing node summaries for the prompt
        node_summaries = []
        for node in existing_nodes:
            node_summaries.append(
                f"- [existing-{node.id}] ({node.node_type}) {node.content[:200]}"
            )
        existing_summaries_text = "\n".join(node_summaries) if node_summaries else "(No existing nodes)"

        chunks_by_doc = self._group_by_document(new_chunks)

        system_prompt = build_incremental_extraction_system_prompt(
            case, existing_summaries_text
        )
        companion_state = (case.metadata or {}).get('companion_origin')
        user_prompt = build_case_extraction_user_prompt(
            case, chunks_by_doc, companion_state
        )

        raw_result = self._call_extraction_llm(system_prompt, user_prompt)
        if not raw_result or not raw_result.get('nodes'):
            return CaseExtractionResult(chunk_count=len(new_chunks))

        # Create nodes and edges, handling existing node references
        nodes, edges = self._create_nodes_and_edges(
            case, raw_result, new_chunks, existing_nodes=existing_nodes
        )

        delta = self._create_delta(case, nodes, edges)

        return CaseExtractionResult(
            nodes=nodes,
            edges=edges,
            delta=delta,
            chunk_count=len(new_chunks),
        )

    def _group_by_document(
        self,
        chunks: List[DocumentChunk],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group chunks by their document title for prompt formatting."""
        grouped = defaultdict(list)
        for chunk in chunks:
            doc_title = chunk.document.title if hasattr(chunk, 'document') and chunk.document else "Unknown"
            grouped[doc_title].append({
                'chunk_text': chunk.chunk_text,
                'chunk_index': chunk.chunk_index,
                'document_title': doc_title,
            })

        # Sort chunks within each document by index
        for doc_title in grouped:
            grouped[doc_title].sort(key=lambda c: c['chunk_index'])

        return dict(grouped)

    def _call_extraction_llm(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Dict[str, Any]:
        """Call the extraction LLM with tool_use for structured output.

        Mirrors the pattern from graph/extraction.py:_call_extraction_llm().

        Raises ExtractionLLMError on LLM/network failures so the caller
        (run_case_extraction_pipeline) can set extraction_status='failed'
        with an error message. A legitimate empty result (LLM returned
        no nodes) returns {'nodes': [], 'edges': []} without raising.
        """
        from apps.common.llm_providers import get_llm_provider
        provider = get_llm_provider('extraction')

        async def _call():
            return await provider.generate_with_tools(
                messages=[{"role": "user", "content": user_prompt}],
                tools=[EXTRACTION_TOOL],
                system_prompt=system_prompt,
                max_tokens=8192,
                temperature=0.2,
            )

        try:
            parsed = async_to_sync(_call)()
        except Exception as e:
            logger.exception("Case extraction LLM call failed")
            raise ExtractionLLMError(
                f"LLM extraction call failed: {type(e).__name__}: {e}"
            ) from e

        if not parsed:
            # LLM returned empty — legitimate "nothing to extract"
            return {'nodes': [], 'edges': []}

        return _normalize_extraction_result(parsed)

    def _create_nodes_and_edges(
        self,
        case,
        raw_result: Dict[str, Any],
        chunks: List[DocumentChunk],
        existing_nodes: Optional[List[Node]] = None,
    ) -> Tuple[List[Node], List[Edge]]:
        """Validate, create nodes/edges, match source chunks, generate embeddings.

        Follows the same pattern as extract_nodes_from_document() in
        graph/extraction.py but creates nodes with scope='case'.
        """
        from apps.graph.embedding_state import mark_embedding_failed, clear_embedding_failure

        # Build existing node lookup for incremental extraction
        existing_node_map = {}
        if existing_nodes:
            for node in existing_nodes:
                existing_node_map[f"existing-{node.id}"] = node

        temp_id_to_node = {}
        created_nodes = []

        for item in raw_result.get('nodes', []):
            try:
                validated = _validate_extraction_item(item)
                if not validated:
                    continue

                # Merge importance and document_role into properties
                properties = validated.get('properties', {})
                properties['importance'] = validated.get('importance', 2)
                properties['document_role'] = validated.get('document_role', 'detail')

                node = GraphService.create_node(
                    project=case.project,
                    node_type=validated['type'],
                    content=validated['content'],
                    source_type='document_extraction',
                    status=validated.get('status'),
                    properties=properties,
                    case=case,
                    confidence=validated.get('confidence', 0.8),
                    created_by=case.user,
                    generate_embed=False,  # Defer — batch below
                )

                # Match and set source chunks
                chunk_ids = _match_source_chunks(validated, chunks)
                if chunk_ids:
                    node.source_chunks.set(
                        DocumentChunk.objects.filter(id__in=chunk_ids)
                    )

                temp_id = validated.get('id', '')
                if temp_id:
                    temp_id_to_node[temp_id] = node

                created_nodes.append(node)

            except Exception:
                logger.exception("Failed to create case extraction node")

        # Generate embeddings first (CPU-bound, local sentence-transformers),
        # then create edges. Sequential is simpler and avoids concurrent DB
        # writes to different tables from thread pool workers. The parallel
        # gain was negligible since embeddings are CPU-bound (GIL) and edge
        # creation is sequential DB I/O.
        if created_nodes:
            try:
                contents = [n.content for n in created_nodes]
                embeddings = generate_embeddings_batch(contents)

                for node, emb in zip(created_nodes, embeddings):
                    if emb is not None:
                        node.embedding = emb
                        node.properties = clear_embedding_failure(node.properties)
                    else:
                        node.embedding = None
                        node.properties = mark_embedding_failed(
                            node.properties, "batch_embedding_missing"
                        )

                Node.objects.bulk_update(created_nodes, ['embedding', 'properties'])
            except Exception:
                logger.warning(
                    "Batch embedding generation failed for case extraction nodes",
                    exc_info=True,
                )

        edges_created = []
        for edge_spec in raw_result.get('edges', []):
            try:
                valid_edge = _validate_extraction_edge(edge_spec)
                if not valid_edge:
                    continue

                # Resolve source and target — could be new or existing
                source_node = (
                    temp_id_to_node.get(valid_edge['source_id'])
                    or existing_node_map.get(valid_edge['source_id'])
                )
                target_node = (
                    temp_id_to_node.get(valid_edge['target_id'])
                    or existing_node_map.get(valid_edge['target_id'])
                )

                if source_node and target_node:
                    edge = GraphService.create_edge(
                        source_node=source_node,
                        target_node=target_node,
                        edge_type=valid_edge['edge_type'],
                        source_type='document_extraction',
                        provenance=valid_edge.get('provenance', ''),
                        created_by=case.user,
                    )
                    edges_created.append(edge)
            except Exception:
                logger.exception("Failed to create case extraction edge")

        return created_nodes, edges_created

    def _create_delta(
        self,
        case,
        nodes: List[Node],
        edges: List[Edge],
    ) -> Optional[GraphDelta]:
        """Create a GraphDelta recording this extraction."""
        if not nodes:
            return None

        try:
            from apps.graph.delta_service import GraphDeltaService
            return GraphDeltaService.create_delta(
                project_id=str(case.project_id),
                trigger='case_extraction',
                case_id=case.id,
                nodes_added=nodes,
                edges_added=edges,
                tensions_surfaced=sum(1 for n in nodes if n.node_type == 'tension'),
                assumptions_challenged=0,
            )
        except Exception:
            logger.exception("Failed to create GraphDelta for case extraction")
            return None
