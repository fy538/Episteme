"""
Phase B: Integrate new nodes with the existing knowledge graph.

After Phase A extracts nodes from a document, Phase B:
1. Finds relevant existing nodes (via pgvector similarity for large graphs)
2. Calls LLM to discover relationships, tensions, and status updates
3. Creates edges, tension nodes, and applies updates via GraphService
"""
import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Set

from asgiref.sync import async_to_sync
from django.conf import settings

from apps.common.vector_utils import similarity_search

from .models import Node, Edge, NodeType, NodeStatus, EdgeType, NodeSourceType
from .services import GraphService
from .serialization import GraphSerializationService

logger = logging.getLogger(__name__)

# Threshold for "small graph" — full context to LLM
SMALL_GRAPH_THRESHOLD = 30

# Max existing nodes to include as context for large graphs
MAX_CONTEXT_NODES = 30

# Similarity threshold for finding relevant existing nodes
SIMILARITY_THRESHOLD = 0.5

# Tool schema for structured integration output
INTEGRATION_TOOL = {
    "name": "integrate_graph_nodes",
    "description": "Discover relationships, tensions, and status updates between new and existing graph nodes",
    "input_schema": {
        "type": "object",
        "properties": {
            "edges": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source_id": {"type": "string"},
                        "target_id": {"type": "string"},
                        "edge_type": {"type": "string", "enum": ["supports", "contradicts", "depends_on"]},
                        "strength": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "provenance": {"type": "string"},
                    },
                    "required": ["source_id", "target_id", "edge_type"],
                },
            },
            "tensions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "between_nodes": {"type": "array", "items": {"type": "string"}},
                        "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                    },
                    "required": ["content", "between_nodes"],
                },
            },
            "status_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "node_id": {"type": "string"},
                        "new_status": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["node_id", "new_status", "reason"],
                },
            },
            "gaps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["claim", "assumption"]},
                        "content": {"type": "string"},
                        "gap_type": {"type": "string", "enum": ["missing_evidence", "untested_assumption"]},
                    },
                    "required": ["content", "gap_type"],
                },
            },
            "delta_narrative": {"type": "string"},
        },
        "required": ["edges", "tensions", "status_updates", "delta_narrative"],
    },
}


def integrate_new_nodes(
    project_id: uuid.UUID,
    new_node_ids: List[uuid.UUID],
    *,
    source_document=None,
    created_by=None,
    case_id=None,
) -> Dict[str, List]:
    """
    Phase B entry point: integrate new nodes with the existing graph.

    When case_id is provided, integration is scoped to the case's visible graph
    (case-own nodes + referenced project nodes) rather than the full project graph.

    Returns:
        {'edges': [Edge IDs], 'tensions': [Tension Node IDs], 'updated_nodes': [Node IDs]}
    """
    from apps.projects.models import Project

    project = Project.objects.get(id=project_id)
    new_nodes = list(Node.objects.filter(id__in=new_node_ids))

    if not new_nodes:
        return {'edges': [], 'tensions': [], 'updated_nodes': []}

    # Get existing nodes — scoped to case or full project
    if case_id:
        from .models import CaseNodeReference

        case_own = Node.objects.filter(
            case_id=case_id, scope='case'
        ).exclude(id__in=new_node_ids)

        ref_ids = CaseNodeReference.objects.filter(
            case_id=case_id, excluded=False
        ).values_list('node_id', flat=True)
        referenced = Node.objects.filter(
            id__in=ref_ids
        ).exclude(id__in=new_node_ids)

        existing_nodes = list(case_own) + list(referenced)
    else:
        existing_nodes = list(
            Node.objects.filter(project_id=project_id)
            .exclude(id__in=new_node_ids)
        )

    # Assemble context — for small graphs, use all; for large, use similarity
    if len(existing_nodes) <= SMALL_GRAPH_THRESHOLD:
        context_nodes = existing_nodes
    else:
        context_nodes = _assemble_integration_context(
            project_id, new_nodes, existing_nodes, case_id=case_id
        )

    if not context_nodes and not new_nodes:
        return {'edges': [], 'tensions': [], 'updated_nodes': []}

    # Serialize for LLM
    graph_context = _serialize_context_for_integration(context_nodes, new_nodes)

    # Call LLM for integration analysis
    integration_result = _call_integration_llm(graph_context, new_nodes)
    if not integration_result:
        return {'edges': [], 'tensions': [], 'updated_nodes': []}

    # Build a lookup map: all nodes by ID
    all_nodes_map = {str(n.id): n for n in existing_nodes + new_nodes}

    # Apply results
    created_edges = []
    created_tensions = []
    updated_nodes = []

    # 1. Create edges
    for edge_spec in integration_result.get('edges', []):
        try:
            edge = _create_edge_from_spec(
                edge_spec, all_nodes_map,
                source_document=source_document,
                created_by=created_by,
            )
            if edge:
                created_edges.append(edge.id)
        except Exception:
            logger.exception("Failed to create edge from integration", extra=edge_spec)

    # 2. Create tension nodes
    for tension_spec in integration_result.get('tensions', []):
        try:
            tension = _create_tension_from_spec(
                tension_spec, project, all_nodes_map,
                source_document=source_document,
                created_by=created_by,
            )
            if tension:
                created_tensions.append(tension.id)
        except Exception:
            logger.exception("Failed to create tension from integration")

    # 3. Apply status updates
    for update_spec in integration_result.get('status_updates', []):
        try:
            node_id = _resolve_node_id(update_spec.get('node_id', ''), all_nodes_map)
            if node_id:
                new_status = update_spec.get('new_status', '')
                if new_status:
                    node = GraphService.update_node(node_id, status=new_status)
                    updated_nodes.append(node.id)
        except Exception:
            logger.exception("Failed to apply status update from integration")

    # 4. Create gap nodes (unsubstantiated claims, untested assumptions)
    for gap_spec in integration_result.get('gaps', []):
        try:
            gap_node = GraphService.create_node(
                project=project,
                node_type=gap_spec.get('type', NodeType.CLAIM),
                content=gap_spec.get('content', ''),
                source_type=NodeSourceType.INTEGRATION,
                status=gap_spec.get('status'),
                properties={'gap_type': gap_spec.get('gap_type', 'missing_evidence')},
                source_document=source_document,
                created_by=created_by,
            )
            updated_nodes.append(gap_node.id)
        except Exception:
            logger.exception("Failed to create gap node from integration")

    logger.info(
        "integration_phase_b_complete",
        extra={
            'project_id': str(project_id),
            'new_nodes': len(new_node_ids),
            'edges_created': len(created_edges),
            'tensions_created': len(created_tensions),
            'nodes_updated': len(updated_nodes),
        },
    )

    return {
        'edges': created_edges,
        'tensions': created_tensions,
        'updated_nodes': updated_nodes,
    }


def _assemble_integration_context(
    project_id: uuid.UUID,
    new_nodes: List[Node],
    existing_nodes: List[Node],
    *,
    case_id=None,
) -> List[Node]:
    """
    For large graphs, find the most relevant existing nodes using
    embedding similarity (pgvector).

    Runs similarity searches in parallel across all new nodes using
    concurrent.futures for I/O-bound pgvector queries.

    When case_id is provided, similarity search is scoped to the
    pre-filtered existing_nodes (case-visible nodes only).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Build the base queryset — scoped to existing_nodes if case integration
    existing_ids = [n.id for n in existing_nodes]
    new_ids = [n.id for n in new_nodes]

    if case_id:
        base_qs = Node.objects.filter(id__in=existing_ids).exclude(id__in=new_ids)
    else:
        base_qs = Node.objects.filter(project_id=project_id).exclude(id__in=new_ids)

    # Filter to nodes with embeddings
    searchable_nodes = [n for n in new_nodes if n.embedding is not None]
    if not searchable_nodes:
        return []

    def _search_for_node(node):
        """Run a single similarity search (I/O-bound, safe to parallelize)."""
        results = list(similarity_search(
            queryset=base_qs,
            embedding_field='embedding',
            query_vector=list(node.embedding),
            threshold=SIMILARITY_THRESHOLD,
            top_k=10,
        ))
        return [n.id for n in results]

    relevant_ids: Set[uuid.UUID] = set()

    # Parallel similarity searches — one per new node
    with ThreadPoolExecutor(max_workers=min(len(searchable_nodes), 5)) as executor:
        futures = {
            executor.submit(_search_for_node, node): node
            for node in searchable_nodes
        }
        for future in as_completed(futures):
            try:
                ids = future.result()
                relevant_ids.update(ids)
            except Exception:
                logger.debug("Similarity search failed for node", exc_info=True)

            if len(relevant_ids) >= MAX_CONTEXT_NODES:
                # Cancel remaining futures — we have enough context
                for f in futures:
                    f.cancel()
                break

    # Fetch the relevant nodes
    return list(
        Node.objects.filter(id__in=list(relevant_ids)[:MAX_CONTEXT_NODES])
        .select_related('source_document')
    )


def _serialize_context_for_integration(
    context_nodes: List[Node],
    new_nodes: List[Node],
) -> str:
    """
    Serialize existing context and new nodes for the integration prompt.
    """
    lines = []

    if context_nodes:
        lines.append("=== EXISTING GRAPH NODES ===")
        for node in context_nodes:
            source = f" (from: {node.source_document.title[:40]})" if node.source_document else ""
            lines.append(f"[{node.id}] [{node.node_type}|{node.status}] {node.content}{source}")
        lines.append("")

    lines.append("=== NEW NODES (from this document) ===")
    for node in new_nodes:
        lines.append(f"[{node.id}] [{node.node_type}|{node.status}] {node.content}")

    return "\n".join(lines)


def _call_integration_llm(graph_context: str, new_nodes: List[Node]) -> Optional[Dict]:
    """Call LLM for integration analysis using structured tool_use."""
    from apps.common.llm_providers import get_llm_provider
    provider = get_llm_provider('extraction')

    prompt = _build_integration_prompt(graph_context)

    async def _call():
        return await provider.generate_with_tools(
            messages=[{"role": "user", "content": prompt}],
            tools=[INTEGRATION_TOOL],
            system_prompt=_INTEGRATION_SYSTEM_PROMPT,
            max_tokens=4096,
            temperature=0.3,
        )

    result = async_to_sync(_call)()

    if not isinstance(result, dict) or not result:
        logger.warning("Integration LLM returned non-dict: %s", type(result))
        return None

    return result


def _build_integration_prompt(graph_context: str) -> str:
    """Build the user prompt for integration."""
    return f"""Analyze the relationships between new and existing nodes in this knowledge graph.

{graph_context}

For each meaningful relationship you find, output:
1. **edges**: Relationships between any two nodes (new-to-new, new-to-existing, existing-to-existing if newly discovered).
2. **tensions**: Contradictions or conflicts between nodes that should be surfaced.
3. **status_updates**: If a new node changes the epistemic status of an existing node (e.g., new evidence makes a claim "supported" or an assumption "challenged").
4. **gaps**: Missing information that would strengthen the graph (unsubstantiated claims, untested assumptions).

Respond with a JSON object:
{{
    "edges": [
        {{"source_id": "uuid", "target_id": "uuid", "edge_type": "supports|contradicts|depends_on", "strength": 0.0-1.0, "provenance": "why this relationship exists"}}
    ],
    "tensions": [
        {{"content": "Description of the contradiction", "between_nodes": ["uuid1", "uuid2"], "severity": "high|medium|low"}}
    ],
    "status_updates": [
        {{"node_id": "uuid", "new_status": "status_value", "reason": "why status changed"}}
    ],
    "gaps": [
        {{"type": "claim|assumption", "content": "What's missing", "gap_type": "missing_evidence|untested_assumption"}}
    ],
    "delta_narrative": "2-3 sentence summary of what this document changes about the overall picture"
}}

Only include SUBSTANTIVE relationships. Do not create edges for trivial or obvious connections.
Be CONSERVATIVE with contradiction detection — only flag genuine conflicts where evidence clearly opposes."""


_INTEGRATION_SYSTEM_PROMPT = """You are an epistemic analyst integrating new knowledge into an existing graph.

Rules:
1. Only create edges for SUBSTANTIVE relationships — skip trivial or self-evident connections.
2. Be CONSERVATIVE with contradictions — a contradiction requires genuine evidence in opposition, not merely different perspectives on the same topic.
3. Status updates must be justified — explain why the new information changes the epistemic status.
4. Gaps should be actionable — "we don't know X" is only useful if knowing X would change the picture.
5. The delta_narrative should capture what changes for a DECISION-MAKER, not just catalog additions.
6. Respond ONLY with a valid JSON object."""


def _create_edge_from_spec(
    spec: Dict,
    nodes_map: Dict[str, Node],
    source_document=None,
    created_by=None,
) -> Optional[Edge]:
    """Create an edge from an integration spec."""
    source_id = _resolve_node_id(spec.get('source_id', ''), nodes_map)
    target_id = _resolve_node_id(spec.get('target_id', ''), nodes_map)

    if not source_id or not target_id:
        return None

    source_node = Node.objects.get(id=source_id)
    target_node = Node.objects.get(id=target_id)

    edge_type = spec.get('edge_type', '')
    if edge_type not in [et.value for et in EdgeType]:
        return None

    return GraphService.create_edge(
        source_node=source_node,
        target_node=target_node,
        edge_type=edge_type,
        source_type=NodeSourceType.INTEGRATION,
        strength=spec.get('strength'),
        provenance=spec.get('provenance', ''),
        source_document=source_document,
        created_by=created_by,
    )


def _create_tension_from_spec(
    spec: Dict,
    project,
    nodes_map: Dict[str, Node],
    source_document=None,
    created_by=None,
) -> Optional[Node]:
    """Create a tension node from an integration spec."""
    content = spec.get('content', '')
    if not content:
        return None

    between = spec.get('between_nodes', [])
    severity = spec.get('severity', 'medium')

    tension = GraphService.create_node(
        project=project,
        node_type=NodeType.TENSION,
        content=content,
        source_type=NodeSourceType.INTEGRATION,
        status=NodeStatus.SURFACED,
        properties={
            'tension_type': 'contradiction',
            'severity': severity,
            'between_nodes': between,
        },
        source_document=source_document,
        created_by=created_by,
    )

    # Create contradiction edges from tension to the conflicting nodes
    for node_id_str in between:
        node_id = _resolve_node_id(node_id_str, nodes_map)
        if node_id:
            try:
                target_node = Node.objects.get(id=node_id)
                GraphService.create_edge(
                    source_node=tension,
                    target_node=target_node,
                    edge_type=EdgeType.CONTRADICTS,
                    source_type=NodeSourceType.INTEGRATION,
                    provenance=f"Tension: {content[:100]}",
                    source_document=source_document,
                )
            except Exception:
                logger.exception("Failed to create tension edge")

    return tension


def _resolve_node_id(id_str: str, nodes_map: Dict[str, Node]) -> Optional[uuid.UUID]:
    """Resolve a node ID string to a UUID, checking it exists."""
    if not id_str:
        return None

    # Direct UUID lookup
    if id_str in nodes_map:
        return uuid.UUID(id_str)

    # Try parsing as UUID
    try:
        parsed = uuid.UUID(id_str)
        if str(parsed) in nodes_map:
            return parsed
    except ValueError:
        pass

    return None


def _parse_json_from_response(text: str) -> Any:
    """Multi-strategy JSON extraction from LLM response."""
    if not text:
        return None

    text = text.strip()

    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from code fence
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find first { to last }
    first = text.find('{')
    last = text.rfind('}')
    if first != -1 and last > first:
        try:
            return json.loads(text[first:last + 1])
        except json.JSONDecodeError:
            pass

    logger.warning("integration_json_parse_failed", extra={"text_preview": text[:200]})
    return None
