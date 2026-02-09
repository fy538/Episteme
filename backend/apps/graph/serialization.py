"""
GraphSerializationService — compact graph context for LLM system prompts.

Produces token-efficient text with node references like [C1], [E2], [A3], [T4].
These references are used by the graph-aware agent and the edit handler to
address specific nodes in conversation.
"""
import logging
import uuid
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from .models import Node, Edge, NodeType

logger = logging.getLogger(__name__)

# Reference prefixes by node type
_TYPE_PREFIX = {
    NodeType.CLAIM: 'C',
    NodeType.EVIDENCE: 'E',
    NodeType.ASSUMPTION: 'A',
    NodeType.TENSION: 'T',
}


class GraphSerializationService:
    """
    Serializes the knowledge graph for injection into LLM system prompts.

    The output format is designed for minimal token usage while preserving
    enough structure for the LLM to reason about and reference specific nodes.
    """

    @staticmethod
    def serialize_for_llm(
        project_id: uuid.UUID,
        max_nodes: int = 50,
        case_id: uuid.UUID = None,
    ) -> Tuple[str, Dict[str, uuid.UUID]]:
        """
        Serialize the project graph into compact LLM-friendly text.

        When case_id is provided, serializes the case-composed graph
        (case-scoped nodes + referenced project nodes) instead of the
        full project graph.

        Returns:
            (serialized_text, ref_map)
            - serialized_text: compact text with [C1], [E2] etc. references
            - ref_map: dict mapping ref strings to node UUIDs, e.g. {'C1': uuid}
        """
        if case_id:
            from .services import GraphService
            case_graph = GraphService.get_case_graph(case_id)
            candidates = list(case_graph['nodes'])
            case_edges = list(case_graph['edges'])
            # Track which nodes are case-local for tagging
            case_node_ids = {
                n.id for n in candidates if n.scope == 'case'
            }
        else:
            # Fetch more than max_nodes to allow importance-based filtering
            candidates = list(
                Node.objects.filter(project_id=project_id)
                .select_related('source_document')
                .order_by('node_type', '-created_at')
            )
            case_node_ids = set()
            case_edges = None

        # Sort by importance descending within each type, then trim to max_nodes
        # This ensures importance=3 nodes are always included
        candidates.sort(
            key=lambda n: (
                -n.properties.get('importance', 2),
                n.node_type,
                ),
        )
        nodes = candidates[:max_nodes]

        if not nodes:
            return "No knowledge graph nodes yet.", {}

        # Build edges lookup
        node_ids = [n.id for n in nodes]
        if case_edges is not None:
            # Use pre-fetched case edges (already filtered for visibility)
            edges = [e for e in case_edges if e.source_node_id in set(node_ids) and e.target_node_id in set(node_ids)]
        else:
            edges = Edge.objects.filter(
                source_node_id__in=node_ids,
                target_node_id__in=node_ids,
            )

        # Assign references and build ref_map
        ref_map: Dict[str, uuid.UUID] = {}
        node_ref: Dict[uuid.UUID, str] = {}
        type_counters: Dict[str, int] = defaultdict(int)

        for node in nodes:
            prefix = _TYPE_PREFIX.get(node.node_type, 'N')
            type_counters[prefix] += 1
            ref = f"{prefix}{type_counters[prefix]}"
            ref_map[ref] = node.id
            node_ref[node.id] = ref

        # Group nodes by type
        grouped: Dict[str, List[Tuple[str, Node]]] = defaultdict(list)
        for node in nodes:
            ref = node_ref[node.id]
            grouped[node.node_type].append((ref, node))

        # Build output
        lines: List[str] = []
        lines.append("=== KNOWLEDGE GRAPH ===")

        # Print each type section
        type_order = [
            (NodeType.CLAIM, "CLAIMS"),
            (NodeType.EVIDENCE, "EVIDENCE"),
            (NodeType.ASSUMPTION, "ASSUMPTIONS"),
            (NodeType.TENSION, "TENSIONS"),
        ]

        for ntype, label in type_order:
            items = grouped.get(ntype, [])
            if not items:
                continue
            lines.append(f"\n--- {label} ({len(items)}) ---")
            for ref, node in items:
                status_tag = f"[{node.status}]"
                role = node.properties.get('document_role', '')
                role_tag = f" [{role}]" if role and role != 'detail' else ""
                scope_tag = " [case-local]" if node.id in case_node_ids else ""
                source = ""
                if node.source_document:
                    source = f" (from: {node.source_document.title[:40]})"
                lines.append(f"[{ref}] {status_tag}{role_tag}{scope_tag} {node.content}{source}")

        # Print edges
        edge_lines: List[str] = []
        for edge in edges:
            src_ref = node_ref.get(edge.source_node_id)
            tgt_ref = node_ref.get(edge.target_node_id)
            if src_ref and tgt_ref:
                edge_lines.append(f"  [{src_ref}] --{edge.edge_type}--> [{tgt_ref}]")

        if edge_lines:
            lines.append(f"\n--- RELATIONSHIPS ({len(edge_lines)}) ---")
            lines.extend(edge_lines)

        lines.append("\n=== END GRAPH ===")

        return "\n".join(lines), ref_map

    @staticmethod
    def resolve_ref(project_id: uuid.UUID, ref: str, case_id: uuid.UUID = None) -> Optional[uuid.UUID]:
        """
        Resolve a reference like 'C1' back to a node UUID.

        This re-serializes to rebuild the ref_map, which is fine for
        single-shot resolution. For batch resolution, use serialize_for_llm()
        and use the returned ref_map directly.
        """
        _, ref_map = GraphSerializationService.serialize_for_llm(project_id, case_id=case_id)
        return ref_map.get(ref.upper())

    @staticmethod
    def serialize_node_neighborhood(node_id: uuid.UUID) -> str:
        """
        Serialize a single node + its 1-hop neighborhood.

        Used for detailed node inspection in conversation.
        """
        from .services import GraphService

        data = GraphService.get_node_neighborhood(node_id)
        node = data['node']
        edges = data['edges']
        neighbors = data['neighbors']

        neighbor_map = {n.id: n for n in neighbors}

        lines = [
            f"=== NODE DETAIL ===",
            f"Type: {node.node_type} | Status: {node.status}",
            f"Content: {node.content}",
        ]

        if node.source_document:
            lines.append(f"Source: {node.source_document.title}")

        if node.properties:
            props_str = ", ".join(f"{k}={v}" for k, v in node.properties.items())
            lines.append(f"Properties: {props_str}")

        if edges:
            lines.append(f"\n--- CONNECTIONS ({len(edges)}) ---")
            for edge in edges:
                if edge.source_node_id == node.id:
                    other = neighbor_map.get(edge.target_node_id)
                    direction = "-->"
                else:
                    other = neighbor_map.get(edge.source_node_id)
                    direction = "<--"

                other_text = other.content[:60] if other else "?"
                lines.append(
                    f"  {direction} [{edge.edge_type}] [{other.node_type if other else '?'}] {other_text}"
                )

        lines.append("=== END DETAIL ===")
        return "\n".join(lines)
