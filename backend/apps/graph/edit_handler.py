"""
GraphEditHandler — applies structural edits from chat conversation.

Parses the <graph_edits> JSON from the LLM response and translates each
edit action into GraphService calls. Handles "new-N" references for
nodes created within the same batch.
"""
import logging
import uuid
from typing import Any, Dict, List, Optional

from .models import Node, NodeType, NodeSourceType
from .services import GraphService
from .serialization import GraphSerializationService
from .delta_service import GraphDeltaService

logger = logging.getLogger(__name__)


class GraphEditHandler:
    """
    Parse and apply graph edits emitted by the graph-aware agent.

    Handles:
    - create_node: Create a new node
    - create_edge: Create an edge between nodes (supports refs and new-N)
    - update_node: Update an existing node's fields
    - remove_node: Delete a node
    """

    @staticmethod
    def apply_edits(
        project_id: uuid.UUID,
        edits: List[Dict[str, Any]],
        source_message_id: Optional[uuid.UUID] = None,
        user=None,
        case_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Apply a batch of graph edits from a chat message.

        Args:
            project_id: Project to edit
            edits: List of edit action dicts from LLM
            source_message_id: Message that triggered these edits
            user: User who initiated the edit
            case_id: When provided, new nodes inherit case scope

        Returns:
            Summary dict with counts and created IDs
        """
        from apps.projects.models import Project
        from apps.chat.models import Message

        project = Project.objects.get(id=project_id)
        source_message = None
        if source_message_id:
            try:
                source_message = Message.objects.get(id=source_message_id)
            except Message.DoesNotExist:
                pass

        # Resolve case for scope inheritance
        case = None
        if case_id:
            from apps.cases.models import Case
            try:
                case = Case.objects.get(id=case_id)
            except Case.DoesNotExist:
                pass

        # Build ref_map from current graph state (case-scoped if applicable)
        _, ref_map = GraphSerializationService.serialize_for_llm(project_id, case_id=case_id)

        # Track new nodes created in this batch (for "new-N" references)
        new_nodes_map: Dict[str, Node] = {}

        # Accumulators
        nodes_added: List[Node] = []
        nodes_updated: List[Node] = []
        edges_added = []
        nodes_removed = 0

        for i, edit in enumerate(edits):
            action = edit.get('action', '')

            try:
                if action == 'create_node':
                    node = _handle_create_node(
                        edit, project, source_message, user, case=case
                    )
                    if node:
                        new_nodes_map[f"new-{len(nodes_added)}"] = node
                        nodes_added.append(node)

                elif action == 'create_edge':
                    edge = _handle_create_edge(
                        edit, project_id, ref_map, new_nodes_map, user
                    )
                    if edge:
                        edges_added.append(edge)

                elif action == 'update_node':
                    node = _handle_update_node(
                        edit, project_id, ref_map
                    )
                    if node:
                        nodes_updated.append(node)

                elif action == 'remove_node':
                    removed = _handle_remove_node(
                        edit, project_id, ref_map
                    )
                    if removed:
                        nodes_removed += 1

                else:
                    logger.warning(
                        "Unknown graph edit action: %s", action,
                        extra={'edit_index': i},
                    )

            except Exception:
                logger.exception(
                    "Failed to apply graph edit",
                    extra={'action': action, 'edit_index': i},
                )

        # Create delta record
        if nodes_added or nodes_updated or edges_added or nodes_removed:
            tensions = [n for n in nodes_added if n.node_type == NodeType.TENSION]
            challenged = [
                n for n in nodes_updated
                if n.node_type == 'assumption' and n.status in ('challenged', 'refuted')
            ]

            GraphDeltaService.create_delta(
                project_id=project_id,
                trigger='chat_edit',
                case_id=case_id,
                source_message=source_message,
                nodes_added=nodes_added,
                nodes_updated=nodes_updated,
                edges_added=edges_added,
                tensions_surfaced=len(tensions),
                assumptions_challenged=len(challenged),
            )

        summary = {
            'nodes_created': len(nodes_added),
            'nodes_updated': len(nodes_updated),
            'edges_created': len(edges_added),
            'nodes_removed': nodes_removed,
            'created_node_ids': [str(n.id) for n in nodes_added],
        }

        logger.info(
            "graph_edits_applied",
            extra={
                'project_id': str(project_id),
                **summary,
            },
        )

        return summary


def _resolve_ref(
    ref: str,
    project_id: uuid.UUID,
    ref_map: Dict[str, uuid.UUID],
    new_nodes_map: Dict[str, Node],
) -> Optional[Node]:
    """
    Resolve a node reference to a Node object.

    Handles:
    - Bracket refs like "C1", "A2" (from ref_map)
    - "new-N" refs (from nodes created in this batch)
    - Direct UUIDs
    """
    # Strip brackets if present
    ref = ref.strip('[]').upper()

    # Check new-N references
    ref_lower = ref.lower()
    if ref_lower in new_nodes_map:
        return new_nodes_map[ref_lower]

    # Check ref_map
    node_id = ref_map.get(ref)
    if node_id:
        try:
            return Node.objects.get(id=node_id, project_id=project_id)
        except Node.DoesNotExist:
            return None

    # Try direct UUID
    try:
        uid = uuid.UUID(ref)
        return Node.objects.get(id=uid, project_id=project_id)
    except (ValueError, Node.DoesNotExist):
        return None


def _handle_create_node(edit, project, source_message, user, case=None) -> Optional[Node]:
    """Handle a create_node action."""
    node_type = edit.get('type', '')
    content = edit.get('content', '').strip()

    if not node_type or not content:
        return None

    # Validate node type
    valid_types = [nt.value for nt in NodeType]
    if node_type not in valid_types:
        logger.warning("Invalid node type in edit: %s", node_type)
        return None

    return GraphService.create_node(
        project=project,
        node_type=node_type,
        content=content,
        source_type=NodeSourceType.CHAT_EDIT,
        status=edit.get('status'),
        properties=edit.get('properties', {}),
        source_message=source_message,
        created_by=user,
        case=case,
    )


def _handle_create_edge(edit, project_id, ref_map, new_nodes_map, user):
    """Handle a create_edge action."""
    from .models import EdgeType

    source_ref = edit.get('source_ref', '')
    target_ref = edit.get('target_ref', '')
    edge_type = edit.get('edge_type', '')

    if not source_ref or not target_ref or not edge_type:
        return None

    # Validate edge type
    if edge_type not in [et.value for et in EdgeType]:
        logger.warning("Invalid edge type in edit: %s", edge_type)
        return None

    source_node = _resolve_ref(source_ref, project_id, ref_map, new_nodes_map)
    target_node = _resolve_ref(target_ref, project_id, ref_map, new_nodes_map)

    if not source_node or not target_node:
        logger.warning(
            "Could not resolve edge refs: %s -> %s",
            source_ref, target_ref,
        )
        return None

    return GraphService.create_edge(
        source_node=source_node,
        target_node=target_node,
        edge_type=edge_type,
        source_type=NodeSourceType.CHAT_EDIT,
        strength=edit.get('strength'),
        provenance=edit.get('provenance', ''),
        created_by=user,
    )


def _handle_update_node(edit, project_id, ref_map) -> Optional[Node]:
    """Handle an update_node action."""
    ref = edit.get('ref', '')
    if not ref:
        return None

    node = _resolve_ref(ref, project_id, ref_map, {})
    if not node:
        logger.warning("Could not resolve update ref: %s", ref)
        return None

    updates = {}
    if 'content' in edit:
        updates['content'] = edit['content']
    if 'status' in edit:
        updates['status'] = edit['status']
    if 'properties' in edit:
        updates['properties'] = edit['properties']
    if 'confidence' in edit:
        updates['confidence'] = edit['confidence']

    if not updates:
        return None

    return GraphService.update_node(node.id, **updates)


def _handle_remove_node(edit, project_id, ref_map) -> bool:
    """Handle a remove_node action."""
    ref = edit.get('ref', '')
    if not ref:
        return False

    node = _resolve_ref(ref, project_id, ref_map, {})
    if not node:
        logger.warning("Could not resolve remove ref: %s", ref)
        return False

    GraphService.remove_node(node.id)
    return True
