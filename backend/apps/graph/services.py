"""
GraphService — CRUD, queries, and health computation for the knowledge graph.

All DB writes are wrapped in @transaction.atomic and emit events.
Pattern follows apps/projects/services.py (static methods on a service class).
"""
import logging
import uuid
from typing import Dict, Any, List, Optional

from django.db import transaction
from django.db.models import Count, Q

from apps.common.vector_utils import generate_embedding
from apps.events.models import EventType, ActorType
from apps.events.services import EventService

from .embedding_state import clear_embedding_failure, mark_embedding_failed
from .models import (
    Node, Edge, GraphDelta,
    NodeType, NodeStatus, EdgeType, NodeSourceType, DeltaTrigger,
    VALID_STATUSES_BY_TYPE, DEFAULT_STATUS_BY_TYPE,
)

logger = logging.getLogger(__name__)


def _sort_by_importance(nodes: list) -> list:
    """Sort nodes by properties.importance descending (3 first, then 2, then 1)."""
    return sorted(
        nodes,
        key=lambda n: n.properties.get('importance', 2),
        reverse=True,
    )


def _embedding_failure_reason(error: Optional[Exception] = None) -> str:
    """Normalize embedding failure reason for node properties."""
    if error is None:
        return "embedding_generation_returned_none"
    return f"{type(error).__name__}: {error}"


class GraphService:
    """
    Service for graph operations — create, update, query, orient.

    Every write method:
    1. Validates inputs
    2. Wraps in @transaction.atomic
    3. Generates embedding when content is set/changed
    4. Emits an event
    """

    # ───────────────────────────────────────────────────────────
    # Node CRUD
    # ───────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def create_node(
        project,
        node_type: str,
        content: str,
        source_type: str,
        *,
        status: Optional[str] = None,
        properties: Optional[dict] = None,
        case=None,
        source_document=None,
        source_message=None,
        confidence: float = 0.8,
        created_by=None,
        generate_embed: bool = True,
    ) -> Node:
        """
        Create a graph node, generate its embedding, and emit an event.

        Returns the created Node.
        """
        # Default status for the type if not provided
        if status is None:
            status = DEFAULT_STATUS_BY_TYPE.get(node_type, NodeStatus.UNSUBSTANTIATED)

        scope = 'case' if case else 'project'

        node = Node(
            project=project,
            node_type=node_type,
            status=status,
            content=content,
            properties=properties or {},
            case=case,
            scope=scope,
            source_type=source_type,
            source_document=source_document,
            source_message=source_message,
            confidence=confidence,
            created_by=created_by,
        )

        # Generate embedding
        if generate_embed:
            try:
                embedding = generate_embedding(content)
                if embedding is None:
                    node.embedding = None
                    node.properties = mark_embedding_failed(
                        node.properties, _embedding_failure_reason(),
                    )
                    logger.warning(
                        "Embedding generation returned no vector for new node",
                        extra={'project_id': str(project.id), 'node_type': node_type},
                    )
                else:
                    node.embedding = embedding
                    node.properties = clear_embedding_failure(node.properties)
            except Exception as exc:
                node.embedding = None
                node.properties = mark_embedding_failed(
                    node.properties, _embedding_failure_reason(exc),
                )
                logger.warning("Failed to generate embedding for node", exc_info=True)

        node.save()

        # Emit event
        EventService.append(
            event_type=EventType.GRAPH_NODE_CREATED,
            payload={
                'node_id': str(node.id),
                'node_type': node_type,
                'content_preview': content[:120],
                'project_id': str(project.id),
            },
            actor_type=ActorType.SYSTEM if not created_by else ActorType.USER,
            actor_id=created_by.id if created_by else None,
        )

        return node

    @staticmethod
    @transaction.atomic
    def update_node(node_id: uuid.UUID, **updates) -> Node:
        """
        Partial update on a node. Re-generates embedding if content changed.

        Allowed updates: content, status, properties, confidence, node_type.
        Returns the updated Node.
        """
        node = Node.objects.get(id=node_id)

        content_changed = False
        for field, value in updates.items():
            if field == 'content' and value != node.content:
                content_changed = True
            if hasattr(node, field):
                setattr(node, field, value)

        # Re-embed on content change
        if content_changed:
            try:
                embedding = generate_embedding(node.content)
                if embedding is None:
                    node.embedding = None
                    node.properties = mark_embedding_failed(
                        node.properties, _embedding_failure_reason(),
                    )
                    logger.warning(
                        "Embedding regeneration returned no vector",
                        extra={'node_id': str(node_id)},
                    )
                else:
                    node.embedding = embedding
                    node.properties = clear_embedding_failure(node.properties)
            except Exception as exc:
                node.embedding = None
                node.properties = mark_embedding_failed(
                    node.properties, _embedding_failure_reason(exc),
                )
                logger.warning("Failed to re-embed node %s", node_id, exc_info=True)

        node.save()
        return node

    @staticmethod
    @transaction.atomic
    def remove_node(node_id: uuid.UUID):
        """
        Delete a node and its connected edges (cascade).
        """
        Node.objects.filter(id=node_id).delete()

    # ───────────────────────────────────────────────────────────
    # Edge CRUD
    # ───────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def create_edge(
        source_node: Node,
        target_node: Node,
        edge_type: str,
        source_type: str,
        *,
        strength: Optional[float] = None,
        provenance: str = '',
        source_document=None,
        created_by=None,
    ) -> Edge:
        """
        Create an edge between two nodes. Enforces uniqueness constraint.

        Returns the created Edge (or existing if already present).
        """
        edge, created = Edge.objects.get_or_create(
            source_node=source_node,
            target_node=target_node,
            edge_type=edge_type,
            defaults={
                'strength': strength,
                'provenance': provenance,
                'source_type': source_type,
                'source_document': source_document,
                'created_by': created_by,
            }
        )

        if created:
            EventService.append(
                event_type=EventType.GRAPH_EDGE_CREATED,
                payload={
                    'edge_id': str(edge.id),
                    'edge_type': edge_type,
                    'source_node_id': str(source_node.id),
                    'target_node_id': str(target_node.id),
                    'project_id': str(source_node.project_id),
                },
                actor_type=ActorType.SYSTEM if not created_by else ActorType.USER,
                actor_id=created_by.id if created_by else None,
            )
        else:
            # Update strength/provenance if edge already existed
            if strength is not None:
                edge.strength = strength
            if provenance:
                edge.provenance = provenance
            edge.save()

        return edge

    # ───────────────────────────────────────────────────────────
    # Graph queries
    # ───────────────────────────────────────────────────────────

    GRAPH_DEFAULT_LIMIT = 2000
    GRAPH_MAX_LIMIT = 5000

    @staticmethod
    def get_project_graph(
        project_id: uuid.UUID,
        *,
        limit: Optional[int] = None,
        node_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Graph for a project — nodes and edges with optional limit and filtering.

        Args:
            project_id: Project UUID.
            limit: Max nodes to return. Defaults to GRAPH_DEFAULT_LIMIT.
            node_type: Filter to a specific node type (claim, evidence, etc.).

        Returns:
            {
                'nodes': [Node, ...],
                'edges': [Edge, ...],
                'total_node_count': int,
                'truncated': bool,
            }
        """
        if limit is None:
            limit = GraphService.GRAPH_DEFAULT_LIMIT
        limit = min(limit, GraphService.GRAPH_MAX_LIMIT)

        qs = Node.objects.filter(project_id=project_id)
        if node_type:
            qs = qs.filter(node_type=node_type)

        total_node_count = qs.count()
        nodes = list(
            qs.select_related('source_document', 'case', 'created_by')[:limit]
        )
        node_ids = {n.id for n in nodes}
        edges = list(
            Edge.objects.filter(
                source_node_id__in=node_ids,
                target_node_id__in=node_ids,
            ).select_related('source_node', 'target_node')
        )
        return {
            'nodes': nodes,
            'edges': edges,
            'total_node_count': total_node_count,
            'truncated': total_node_count > len(nodes),
        }

    @staticmethod
    def get_document_subgraph(document_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get nodes and edges for a single document, sorted by importance.

        Returns the document's argument structure: core thesis first,
        then supporting nodes, then peripheral details.

        Returns:
            {'nodes': [Node, ...], 'edges': [Edge, ...]}
        """
        nodes = _sort_by_importance(list(
            Node.objects.filter(source_document_id=document_id)
            .select_related('source_document', 'case', 'created_by')
        ))
        node_ids = {n.id for n in nodes}
        edges = list(
            Edge.objects.filter(
                source_node_id__in=node_ids,
                target_node_id__in=node_ids,
            ).select_related('source_node', 'target_node')
        )
        return {'nodes': nodes, 'edges': edges}

    @staticmethod
    def compute_graph_health(project_id: uuid.UUID) -> Dict[str, Any]:
        """
        Quick health stats for the knowledge graph.

        Uses conditional aggregation so node totals, type/status breakdowns,
        and key health indicators come from one node query.

        Returns:
            {
                'total_nodes': int,
                'total_edges': int,
                'nodes_by_type': {claim: N, evidence: N, ...},
                'nodes_by_status': {supported: N, ...},
                'untested_assumptions': int,
                'unresolved_tensions': int,
                'unsubstantiated_claims': int,
                'total_documents': int,
                'total_deltas': int,
            }
        """
        nodes_qs = Node.objects.filter(project_id=project_id)

        agg_spec = {
            'total_nodes': Count('id'),
            'untested_assumptions': Count(
                'id', filter=Q(node_type=NodeType.ASSUMPTION, status=NodeStatus.UNTESTED)
            ),
            'unresolved_tensions': Count(
                'id', filter=Q(
                    node_type=NodeType.TENSION,
                    status__in=[NodeStatus.SURFACED, NodeStatus.ACKNOWLEDGED],
                )
            ),
            'unsubstantiated_claims': Count(
                'id', filter=Q(node_type=NodeType.CLAIM, status=NodeStatus.UNSUBSTANTIATED)
            ),
        }
        for node_type, _label in NodeType.choices:
            agg_spec[f"type__{node_type}"] = Count(
                'id', filter=Q(node_type=node_type),
            )
        for status, _label in NodeStatus.choices:
            agg_spec[f"status__{status}"] = Count(
                'id', filter=Q(status=status),
            )

        agg = nodes_qs.aggregate(**agg_spec)

        type_counts = {
            node_type: agg[f"type__{node_type}"]
            for node_type, _label in NodeType.choices
            if agg.get(f"type__{node_type}", 0)
        }
        status_counts = {
            status: agg[f"status__{status}"]
            for status, _label in NodeStatus.choices
            if agg.get(f"status__{status}", 0)
        }

        # Edge count using FK join instead of subquery
        total_edges = Edge.objects.filter(
            source_node__project_id=project_id
        ).count()

        total_docs = nodes_qs.filter(
            source_document__isnull=False
        ).values('source_document').distinct().count()

        total_deltas = GraphDelta.objects.filter(project_id=project_id).count()

        return {
            'total_nodes': agg['total_nodes'],
            'total_edges': total_edges,
            'nodes_by_type': type_counts,
            'nodes_by_status': status_counts,
            'untested_assumptions': agg['untested_assumptions'],
            'unresolved_tensions': agg['unresolved_tensions'],
            'unsubstantiated_claims': agg['unsubstantiated_claims'],
            'total_documents': total_docs,
            'total_deltas': total_deltas,
        }

    # ───────────────────────────────────────────────────────────
    # Case-scoped queries
    # ───────────────────────────────────────────────────────────

    @staticmethod
    def _get_case_visible_nodes(case_id: uuid.UUID):
        """
        Return the set of node IDs visible to a case:
        - Case's own nodes (scope='case', case=case_id)
        - Referenced project nodes (CaseNodeReference, not excluded)

        Uses a single combined query for efficiency.
        """
        from django.db.models import Q
        from .models import CaseNodeReference

        return set(
            Node.objects.filter(
                Q(case_id=case_id, scope='case') |
                Q(id__in=CaseNodeReference.objects.filter(
                    case_id=case_id, excluded=False
                ).values_list('node_id', flat=True))
            ).values_list('id', flat=True)
        )

    @staticmethod
    def get_case_graph(
        case_id: uuid.UUID,
        *,
        limit: Optional[int] = None,
        node_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Composed graph for a case: case-scoped nodes + referenced project
        nodes + edges where BOTH endpoints are visible.

        Args:
            case_id: Case UUID.
            limit: Max nodes to return. Defaults to GRAPH_DEFAULT_LIMIT.
            node_type: Filter to a specific node type (claim, evidence, etc.).

        Returns:
            {
                'nodes': [Node, ...],
                'edges': [Edge, ...],
                'total_node_count': int,
                'truncated': bool,
            }
        """
        from .models import CaseNodeReference

        if limit is None:
            limit = GraphService.GRAPH_DEFAULT_LIMIT
        limit = min(limit, GraphService.GRAPH_MAX_LIMIT)

        # Case's own nodes
        case_qs = Node.objects.filter(case_id=case_id, scope='case')
        if node_type:
            case_qs = case_qs.filter(node_type=node_type)

        # Referenced project nodes
        ref_node_ids = list(
            CaseNodeReference.objects.filter(
                case_id=case_id, excluded=False
            ).values_list('node_id', flat=True)
        )
        ref_qs = Node.objects.filter(id__in=ref_node_ids)
        if node_type:
            ref_qs = ref_qs.filter(node_type=node_type)

        total_node_count = case_qs.count() + ref_qs.count()

        case_nodes = list(
            case_qs.select_related('source_document', 'case', 'created_by')[:limit]
        )
        remaining = limit - len(case_nodes)
        referenced_nodes = list(
            ref_qs.select_related('source_document', 'case', 'created_by')[:remaining]
        ) if remaining > 0 else []

        all_nodes = case_nodes + referenced_nodes
        visible_ids = {n.id for n in all_nodes}

        # Edges where BOTH endpoints are visible
        edges = list(
            Edge.objects.filter(
                source_node_id__in=visible_ids,
                target_node_id__in=visible_ids,
            ).select_related('source_node', 'target_node')
        )

        return {
            'nodes': all_nodes,
            'edges': edges,
            'total_node_count': total_node_count,
            'truncated': total_node_count > len(all_nodes),
        }

    @staticmethod
    def compute_case_graph_health(case_id: uuid.UUID) -> Dict[str, Any]:
        """Health stats scoped to a case's visible graph."""
        visible_ids = GraphService._get_case_visible_nodes(case_id)

        nodes_qs = Node.objects.filter(id__in=visible_ids)

        type_counts = dict(
            nodes_qs.values_list('node_type')
            .annotate(count=Count('id'))
            .values_list('node_type', 'count')
        )

        status_counts = dict(
            nodes_qs.values_list('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        )

        untested = nodes_qs.filter(
            node_type=NodeType.ASSUMPTION, status=NodeStatus.UNTESTED
        ).count()
        unresolved = nodes_qs.filter(
            node_type=NodeType.TENSION,
            status__in=[NodeStatus.SURFACED, NodeStatus.ACKNOWLEDGED],
        ).count()
        unsubstantiated = nodes_qs.filter(
            node_type=NodeType.CLAIM, status=NodeStatus.UNSUBSTANTIATED
        ).count()

        total_nodes = nodes_qs.count()
        total_edges = Edge.objects.filter(
            source_node_id__in=visible_ids,
            target_node_id__in=visible_ids,
        ).count()

        total_docs = nodes_qs.filter(
            source_document__isnull=False
        ).values('source_document').distinct().count()

        return {
            'total_nodes': total_nodes,
            'total_edges': total_edges,
            'nodes_by_type': type_counts,
            'nodes_by_status': status_counts,
            'untested_assumptions': untested,
            'unresolved_tensions': unresolved,
            'unsubstantiated_claims': unsubstantiated,
            'total_documents': total_docs,
            'total_deltas': 0,  # Deltas are project-level
        }

    # ───────────────────────────────────────────────────────────
    # Auto-pull and scope transitions
    # ───────────────────────────────────────────────────────────

    @staticmethod
    def auto_pull_project_nodes(case) -> list:
        """
        Embed case focus text (position + decision_question), find similar
        project-scoped nodes via pgvector, create CaseNodeReference rows.

        Called on case creation. Best-effort — failure should not block
        case creation.

        Returns list of created CaseNodeReference objects.
        """
        from .models import CaseNodeReference

        focus_text = f"{case.decision_question} {case.position}".strip()
        if not focus_text:
            return []

        try:
            query_vector = generate_embedding(focus_text)
        except Exception:
            logger.warning("Failed to generate embedding for case focus", exc_info=True)
            return []

        # Find similar project-scoped nodes
        project_nodes = Node.objects.filter(
            project_id=case.project_id,
            scope='project',
        ).exclude(embedding__isnull=True)

        from apps.common.vector_utils import similarity_search as sim_search
        similar_nodes = list(sim_search(
            queryset=project_nodes,
            embedding_field='embedding',
            query_vector=query_vector,
            threshold=0.5,
            top_k=20,
        ))

        # Batch-create references (ignore_conflicts handles existing refs)
        refs_to_create = [
            CaseNodeReference(
                case=case,
                node=node,
                inclusion_type='auto',
                relevance=round(1.0 - getattr(node, 'distance', 0.5), 3),
            )
            for node in similar_nodes
        ]
        created_refs = CaseNodeReference.objects.bulk_create(
            refs_to_create, ignore_conflicts=True,
        )
        # bulk_create with ignore_conflicts may return objs without IDs on some DBs,
        # so re-fetch to get actual created count
        created_count = CaseNodeReference.objects.filter(
            case=case, inclusion_type='auto',
        ).count() if refs_to_create else 0

        pulled_node_ids = [str(n.id) for n in similar_nodes]
        if pulled_node_ids:
            logger.info(
                "auto_pull_complete",
                extra={
                    'case_id': str(case.id),
                    'refs_created': created_count,
                    'candidates': len(pulled_node_ids),
                },
            )

            # Emit audit event
            try:
                from apps.events.services import EventService
                from apps.events.models import EventType, ActorType
                EventService.append(
                    event_type=EventType.CASE_NODES_AUTO_PULLED,
                    payload={
                        'count': created_count,
                        'node_ids': pulled_node_ids,
                    },
                    actor_type=ActorType.SYSTEM,
                    case_id=case.id,
                )
            except Exception:
                logger.warning("Failed to emit auto-pull event", exc_info=True)

        return created_refs

    @staticmethod
    @transaction.atomic
    def promote_document_to_project(document):
        """
        Promote a case-scoped document to project scope.

        1. Update document scope/case fields
        2. Update all extracted nodes to project scope
        3. Remove CaseNodeReferences to those nodes (now project-level)

        Returns dict with node_ids for re-integration.
        """
        from .models import CaseNodeReference

        old_case_id = document.case_id

        # Update document
        document.scope = 'project'
        document.case = None
        document.save(update_fields=['scope', 'case'])

        # Update nodes
        affected_nodes = Node.objects.filter(source_document=document)
        node_ids = list(affected_nodes.values_list('id', flat=True))
        affected_nodes.update(scope='project', case=None)

        # Remove CaseNodeReferences (these nodes are now project-level)
        CaseNodeReference.objects.filter(node_id__in=node_ids).delete()

        logger.info(
            "document_promoted",
            extra={
                'document_id': str(document.id),
                'old_case_id': str(old_case_id),
                'nodes_promoted': len(node_ids),
            },
        )

        return {
            'node_ids': node_ids,
            'old_case_id': old_case_id,
        }

    @staticmethod
    @transaction.atomic
    def demote_document_to_case(document, case):
        """
        Demote a project-scoped document to case scope.

        1. Update document scope/case fields
        2. Update all extracted nodes to case scope
        3. Auto-create CaseNodeReferences for project neighbors
           connected via edges (so those edges remain visible in case)

        Returns dict with node_ids and references created count.
        """
        from .models import CaseNodeReference

        # Update document
        document.scope = 'case'
        document.case = case
        document.save(update_fields=['scope', 'case'])

        # Update nodes
        affected_nodes = Node.objects.filter(source_document=document)
        node_ids = list(affected_nodes.values_list('id', flat=True))
        affected_nodes.update(scope='case', case=case)

        # Find project-scoped neighbors connected via edges
        connected_edges = Edge.objects.filter(
            Q(source_node_id__in=node_ids) | Q(target_node_id__in=node_ids)
        )

        neighbor_project_ids = set()
        node_id_set = set(node_ids)
        for edge in connected_edges:
            if edge.source_node_id not in node_id_set:
                neighbor_project_ids.add(edge.source_node_id)
            if edge.target_node_id not in node_id_set:
                neighbor_project_ids.add(edge.target_node_id)

        # Create CaseNodeReferences for project neighbors
        refs_created = 0
        project_neighbors = Node.objects.filter(
            id__in=neighbor_project_ids, scope='project'
        )
        for neighbor in project_neighbors:
            _, created = CaseNodeReference.objects.get_or_create(
                case=case,
                node=neighbor,
                defaults={
                    'inclusion_type': 'document',
                    'relevance': 0.9,
                },
            )
            if created:
                refs_created += 1

        logger.info(
            "document_demoted",
            extra={
                'document_id': str(document.id),
                'case_id': str(case.id),
                'nodes_demoted': len(node_ids),
                'refs_created': refs_created,
            },
        )

        return {
            'node_ids': node_ids,
            'references_created': refs_created,
        }

    # ───────────────────────────────────────────────────────────
    # Node neighborhood
    # ───────────────────────────────────────────────────────────

    @staticmethod
    def get_node_neighborhood(node_id: uuid.UUID) -> Dict[str, Any]:
        """
        A single node with its 1-hop neighborhood (connected edges + neighbors).

        Returns:
            {'node': Node, 'edges': [Edge, ...], 'neighbors': [Node, ...]}
        """
        node = Node.objects.select_related(
            'source_document', 'case', 'created_by'
        ).get(id=node_id)

        edges = list(
            Edge.objects.filter(
                Q(source_node=node) | Q(target_node=node)
            ).select_related('source_node', 'target_node')
        )

        neighbor_ids = set()
        for e in edges:
            if e.source_node_id != node.id:
                neighbor_ids.add(e.source_node_id)
            if e.target_node_id != node.id:
                neighbor_ids.add(e.target_node_id)

        neighbors = list(
            Node.objects.filter(id__in=neighbor_ids)
            .select_related('source_document')
        )

        return {'node': node, 'edges': edges, 'neighbors': neighbors}
