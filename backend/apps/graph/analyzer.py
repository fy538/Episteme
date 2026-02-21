"""
Graph analyzer - Find patterns in the knowledge graph
"""
import uuid
import logging
from collections import defaultdict
from typing import Dict, List

from django.db.models import Count, Q

from apps.chat.models import ChatThread
from apps.graph.models import Node, Edge, EdgeType
from apps.inquiries.models import Inquiry

logger = logging.getLogger(__name__)


class GraphAnalyzer:
    """
    Analyze knowledge graph for patterns.

    Finds:
    - Ungrounded assumptions (signals without evidence)
    - Contradictions (conflicting signals)
    - Strong claims (well-supported signals)
    - Recurring themes (semantically similar signals)
    """

    def find_patterns(self, thread_id: uuid.UUID) -> Dict:
        """
        Find interesting patterns in the graph for a thread.

        Args:
            thread_id: Thread to analyze

        Returns:
            Dict with pattern categories:
            - ungrounded_assumptions: Assumptions without evidence
            - contradictions: Conflicting signals
            - strong_claims: Well-supported claims
            - recurring_themes: Similar signals mentioned multiple times
        """
        thread = ChatThread.objects.get(id=thread_id)
        case = thread.primary_case

        patterns = {
            'ungrounded_assumptions': [],
            'contradictions': [],
            'strong_claims': [],
            'recurring_themes': [],
            'missing_considerations': []
        }

        if not case:
            # No case yet, limited analysis.
            # Assumptions are now graph nodes, not signals. Without a case we
            # cannot scope to a project, so return empty patterns.
            return patterns

        # 1. Find ungrounded assumptions
        # Assumptions are now graph Nodes, not Signals. Query the graph layer.
        # Annotate with support count to avoid N+1 queries.
        case_assumptions = Node.objects.filter(
            case=case,
            node_type='assumption',
        ).annotate(
            support_count=Count(
                'incoming_edges',
                filter=Q(incoming_edges__edge_type=EdgeType.SUPPORTS),
            )
        )
        for assumption in case_assumptions:
            if assumption.support_count == 0:
                patterns['ungrounded_assumptions'].append({
                    'id': str(assumption.id),
                    'text': assumption.content,
                    'mentioned_times': 1,
                    'confidence': assumption.confidence,
                })

        # 2. Find contradictions
        # Contradiction relationships are now graph Edges, not Signal M2Ms.
        contradiction_edges = Edge.objects.filter(
            edge_type=EdgeType.CONTRADICTS,
            source_node__case=case,
        ).select_related('source_node', 'target_node')

        for edge in contradiction_edges:
            patterns['contradictions'].append({
                'signal_id': str(edge.source_node.id),
                'signal_text': edge.source_node.content,
                'contradicts_id': str(edge.target_node.id),
                'contradicts_text': edge.target_node.content,
            })

        # 3. Find strongly supported claims
        # Claims are now graph Nodes. Check supporting edges + evidence links.
        # Bulk-fetch all support edges for claims in this case, then group by target.
        case_claims = Node.objects.filter(
            case=case,
            node_type='claim',
        )
        claim_ids = set(case_claims.values_list('id', flat=True))
        all_support_edges = Edge.objects.filter(
            target_node_id__in=claim_ids,
            edge_type=EdgeType.SUPPORTS,
        )
        support_edges_by_target = defaultdict(list)
        for edge in all_support_edges:
            support_edges_by_target[edge.target_node_id].append(edge)

        for claim_node in case_claims:
            edges_for_claim = support_edges_by_target.get(claim_node.id, [])
            support_count = len(edges_for_claim)

            if support_count >= 2:
                # Use average edge strength as confidence proxy
                strengths = [
                    e.strength for e in edges_for_claim
                    if e.strength is not None
                ]
                avg_confidence = (
                    sum(strengths) / len(strengths)
                    if strengths else 0.8
                )

                if avg_confidence > 0.75:
                    patterns['strong_claims'].append({
                        'id': str(claim_node.id),
                        'text': claim_node.content,
                        'evidence_count': support_count,
                        'avg_confidence': round(avg_confidence, 2),
                    })

        logger.info(
            f"Graph analysis complete for thread {thread_id}",
            extra={
                'thread_id': str(thread_id),
                'ungrounded_count': len(patterns['ungrounded_assumptions']),
                'contradiction_count': len(patterns['contradictions']),
                'strong_claim_count': len(patterns['strong_claims'])
            }
        )

        return patterns

    async def detect_circular_reasoning(self, thread_id: uuid.UUID) -> List[Dict]:
        """
        Detect circular dependencies in the knowledge graph.

        Example: Node A depends on B, B depends on C, C depends on A

        Args:
            thread_id: Thread to analyze

        Returns:
            List of circular dependency chains
        """
        thread = ChatThread.objects.get(id=thread_id)

        if not thread.primary_case:
            return []

        circular_chains = []

        # Dependencies are now graph Edges (edge_type='depends_on').
        # Build an adjacency list from depends_on edges scoped to the case.
        depends_edges = Edge.objects.filter(
            edge_type=EdgeType.DEPENDS_ON,
            source_node__case=thread.primary_case,
        ).values_list('source_node_id', 'target_node_id')

        adjacency: Dict[uuid.UUID, List[uuid.UUID]] = {}
        for src, tgt in depends_edges:
            adjacency.setdefault(src, []).append(tgt)

        # Simple cycle detection via DFS
        visited: set = set()
        for start_id in adjacency:
            if start_id in visited:
                continue

            path: set = set()
            stack = [(start_id, False)]
            while stack:
                node_id, leaving = stack.pop()
                if leaving:
                    path.discard(node_id)
                    continue
                if node_id in path:
                    # Cycle found — look up the node for reporting
                    try:
                        node = Node.objects.get(id=start_id)
                        circular_chains.append({
                            'root_signal_id': str(node.id),
                            'root_signal_text': node.content,
                            'dependency_count': len(path),
                            'circular': True,
                        })
                    except Node.DoesNotExist:
                        pass
                    break
                if node_id in visited:
                    continue
                visited.add(node_id)
                path.add(node_id)
                stack.append((node_id, True))
                for neighbour in adjacency.get(node_id, []):
                    stack.append((neighbour, False))

        return circular_chains

    async def find_orphaned_assumptions(self, thread_id: uuid.UUID) -> List[Dict]:
        """
        Find assumptions that have no path to evidence.

        These are assumption *graph nodes* that:
        - Have no incoming 'supports' edge
        - Don't depend on nodes that have support edges
        - Are "floating" without grounding

        Args:
            thread_id: Thread to analyze

        Returns:
            List of orphaned assumptions
        """
        thread = ChatThread.objects.get(id=thread_id)

        if not thread.primary_case:
            return []

        orphaned = []
        assumptions = Node.objects.filter(
            case=thread.primary_case,
            node_type='assumption',
        )
        assumption_ids = set(assumptions.values_list('id', flat=True))
        if not assumption_ids:
            return orphaned

        # Bulk: which assumptions have direct support edges?
        directly_supported_ids = set(
            Edge.objects.filter(
                target_node_id__in=assumption_ids,
                edge_type=EdgeType.SUPPORTS,
            ).values_list('target_node_id', flat=True)
        )

        unsupported_ids = assumption_ids - directly_supported_ids
        if not unsupported_ids:
            return orphaned

        # Bulk: depends_on edges from unsupported assumptions
        dep_edges = Edge.objects.filter(
            source_node_id__in=unsupported_ids,
            edge_type=EdgeType.DEPENDS_ON,
        ).values_list('source_node_id', 'target_node_id')

        deps_by_assumption = defaultdict(set)
        all_dep_target_ids = set()
        for src_id, tgt_id in dep_edges:
            deps_by_assumption[src_id].add(tgt_id)
            all_dep_target_ids.add(tgt_id)

        # Bulk: which dependency targets have support edges?
        grounded_dep_ids = set()
        if all_dep_target_ids:
            grounded_dep_ids = set(
                Edge.objects.filter(
                    target_node_id__in=all_dep_target_ids,
                    edge_type=EdgeType.SUPPORTS,
                ).values_list('target_node_id', flat=True)
            )

        for assumption in assumptions:
            if assumption.id in directly_supported_ids:
                continue
            dep_targets = deps_by_assumption.get(assumption.id, set())
            has_grounded_dependency = bool(dep_targets & grounded_dep_ids)
            if not has_grounded_dependency:
                orphaned.append({
                    'id': str(assumption.id),
                    'text': assumption.content,
                    'mentioned_in_thread': False,  # Graph nodes are not thread-scoped
                })

        return orphaned

    async def find_evidence_deserts(self, case_id: uuid.UUID) -> List[Dict]:
        """
        Find inquiries with insufficient evidence (<2 pieces).

        Args:
            case_id: Case to analyze

        Returns:
            List of inquiries needing more evidence
        """
        deserts = []

        inquiries = Inquiry.objects.filter(
            case_id=case_id,
            status__in=['open', 'investigating']
        ).select_related('case__project')

        # Bulk: collect distinct project IDs and count evidence nodes per project
        project_ids = set()
        for inquiry in inquiries:
            if inquiry.case and inquiry.case.project_id:
                project_ids.add(inquiry.case.project_id)

        evidence_counts_by_project = {}
        if project_ids:
            evidence_qs = (
                Node.objects.filter(
                    project_id__in=project_ids,
                    node_type='evidence',
                )
                .values('project_id')
                .annotate(cnt=Count('id'))
            )
            evidence_counts_by_project = {
                row['project_id']: row['cnt'] for row in evidence_qs
            }

        for inquiry in inquiries:
            try:
                project_id = (
                    inquiry.case.project_id
                    if inquiry.case and inquiry.case.project_id
                    else None
                )
                total_evidence = evidence_counts_by_project.get(project_id, 0)
            except Exception:
                total_evidence = 0

            if total_evidence < 2:
                deserts.append({
                    'id': str(inquiry.id),
                    'title': inquiry.title,
                    'evidence_count': total_evidence,
                    'status': inquiry.status
                })

        return deserts

    async def find_confidence_conflicts(self, case_id: uuid.UUID) -> List[Dict]:
        """
        Find high-confidence items that contradict each other.

        These are particularly problematic - both sides are confident
        they're right, but they contradict.

        Args:
            case_id: Case to analyze

        Returns:
            List of high-confidence conflicts
        """
        conflicts = []

        # Node-vs-node contradictions via graph edges
        contradiction_edges = Edge.objects.filter(
            edge_type=EdgeType.CONTRADICTS,
            source_node__case_id=case_id,
            source_node__confidence__gte=0.75,
            target_node__confidence__gte=0.75,
        ).select_related('source_node', 'target_node')

        for edge in contradiction_edges:
            conflicts.append({
                'type': 'signal_vs_signal',
                'signal1_id': str(edge.source_node.id),
                'signal1_text': edge.source_node.content,
                'signal1_confidence': edge.source_node.confidence,
                'signal2_id': str(edge.target_node.id),
                'signal2_text': edge.target_node.content,
                'signal2_confidence': edge.target_node.confidence,
            })

        return conflicts

    # ── Inquiry-Scoped Analysis Methods ──────────────────────────

    def find_patterns_for_inquiry(self, inquiry_id: uuid.UUID) -> Dict:
        """
        Find patterns within a single inquiry's signal network.

        Same pattern detection as find_patterns() but scoped to signals
        related to one inquiry. Used by BriefGroundingEngine for
        per-section intelligence.

        Args:
            inquiry_id: Inquiry to analyze

        Returns:
            Dict with pattern categories:
            - ungrounded_assumptions: Assumptions without evidence
            - contradictions: Conflicting signals
            - strong_claims: Well-supported claims
            - recurring_themes: Similar signals mentioned multiple times
            - evidence_quality: Evidence strength breakdown
        """
        inquiry = Inquiry.objects.get(id=inquiry_id)

        patterns = {
            'ungrounded_assumptions': [],
            'contradictions': [],
            'strong_claims': [],
            'recurring_themes': [],
            'evidence_quality': {
                'total': 0,
                'high_confidence': 0,
                'low_confidence': 0,
                'supporting': 0,
                'contradicting': 0,
                'neutral': 0,
            },
        }

        # Scope graph nodes to the inquiry's case for assumption/claim queries
        case = inquiry.case if hasattr(inquiry, 'case') else None

        # 1. Ungrounded assumptions (now graph Nodes, not Signals)
        # Annotate with support count to avoid N+1 queries.
        if case:
            case_assumptions = Node.objects.filter(
                case=case,
                node_type='assumption',
            ).annotate(
                support_count=Count(
                    'incoming_edges',
                    filter=Q(incoming_edges__edge_type=EdgeType.SUPPORTS),
                )
            )
            for assumption in case_assumptions:
                if assumption.support_count == 0:
                    patterns['ungrounded_assumptions'].append({
                        'id': str(assumption.id),
                        'text': assumption.content,
                        'confidence': assumption.confidence,
                    })

        # 2. Contradictions (now graph Edges, deduplicated)
        seen_pairs: set = set()
        if case:
            contradiction_edges = Edge.objects.filter(
                edge_type=EdgeType.CONTRADICTS,
                source_node__case=case,
            ).select_related('source_node', 'target_node')

            for edge in contradiction_edges:
                pair = tuple(sorted([str(edge.source_node.id), str(edge.target_node.id)]))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    patterns['contradictions'].append({
                        'signal_id': str(edge.source_node.id),
                        'signal_text': edge.source_node.content,
                        'contradicts_id': str(edge.target_node.id),
                        'contradicts_text': edge.target_node.content,
                        'both_high_confidence': (
                            edge.source_node.confidence >= 0.75
                            and edge.target_node.confidence >= 0.75
                        ),
                    })

        # 3. Strong claims (now graph Nodes)
        # Bulk-fetch all support edges for claims in this case, then group by target.
        if case:
            case_claims = Node.objects.filter(
                case=case,
                node_type='claim',
            )
            claim_ids = set(case_claims.values_list('id', flat=True))
            all_claim_support_edges = Edge.objects.filter(
                target_node_id__in=claim_ids,
                edge_type=EdgeType.SUPPORTS,
            )
            claim_support_by_target = defaultdict(list)
            for edge in all_claim_support_edges:
                claim_support_by_target[edge.target_node_id].append(edge)

            for claim_node in case_claims:
                edges_for_claim = claim_support_by_target.get(claim_node.id, [])
                support_count = len(edges_for_claim)
                if support_count >= 2:
                    strengths = [
                        e.strength for e in edges_for_claim
                        if e.strength is not None
                    ]
                    avg_conf = (
                        sum(strengths) / len(strengths)
                        if strengths else 0.8
                    )
                    if avg_conf > 0.7:
                        patterns['strong_claims'].append({
                            'id': str(claim_node.id),
                            'text': claim_node.content,
                            'evidence_count': support_count,
                            'avg_confidence': round(avg_conf, 2),
                        })

        # 4. Evidence quality breakdown — from graph evidence nodes
        evidence_nodes = Node.objects.filter(
            project=inquiry.case.project,
            node_type='evidence',
        ) if inquiry.case and inquiry.case.project else Node.objects.none()
        for ev_node in evidence_nodes:
            patterns['evidence_quality']['total'] += 1
            conf = ev_node.confidence or 0
            if conf >= 0.75:
                patterns['evidence_quality']['high_confidence'] += 1
            elif conf < 0.5:
                patterns['evidence_quality']['low_confidence'] += 1
        # Count supporting/contradicting from edges
        patterns['evidence_quality']['supporting'] = Edge.objects.filter(
            source_node__in=evidence_nodes,
            edge_type=EdgeType.SUPPORTS,
        ).count()
        patterns['evidence_quality']['contradicting'] = Edge.objects.filter(
            source_node__in=evidence_nodes,
            edge_type=EdgeType.CONTRADICTS,
        ).count()
        patterns['evidence_quality']['neutral'] = max(
            0,
            patterns['evidence_quality']['total']
            - patterns['evidence_quality']['supporting']
            - patterns['evidence_quality']['contradicting'],
        )

        logger.info(
            f"Inquiry pattern analysis complete for {inquiry_id}: "
            f"{len(patterns['ungrounded_assumptions'])} ungrounded, "
            f"{len(patterns['contradictions'])} contradictions, "
            f"{len(patterns['strong_claims'])} strong claims"
        )

        return patterns

    def find_orphaned_assumptions_for_inquiry(self, inquiry_id: uuid.UUID) -> List[Dict]:
        """
        Find assumptions within an inquiry's case that have no path to evidence.

        Unlike the thread-scoped version, this checks both:
        - Direct support edges on the assumption node
        - Support edges on nodes the assumption depends on

        Args:
            inquiry_id: Inquiry to analyze

        Returns:
            List of orphaned assumption dicts
        """
        inquiry = Inquiry.objects.get(id=inquiry_id)
        case = inquiry.case if hasattr(inquiry, 'case') else None

        if not case:
            return []

        orphaned = []
        # Assumptions are now graph Nodes, scoped to the inquiry's case.
        assumptions = Node.objects.filter(
            case=case,
            node_type='assumption',
        )
        assumption_ids = set(assumptions.values_list('id', flat=True))
        if not assumption_ids:
            return orphaned

        # Bulk: which assumptions have direct support edges?
        directly_supported_ids = set(
            Edge.objects.filter(
                target_node_id__in=assumption_ids,
                edge_type=EdgeType.SUPPORTS,
            ).values_list('target_node_id', flat=True)
        )

        unsupported_ids = assumption_ids - directly_supported_ids
        if not unsupported_ids:
            return orphaned

        # Bulk: depends_on edges from unsupported assumptions
        dep_edges = Edge.objects.filter(
            source_node_id__in=unsupported_ids,
            edge_type=EdgeType.DEPENDS_ON,
        ).values_list('source_node_id', 'target_node_id')

        deps_by_assumption = defaultdict(set)
        all_dep_target_ids = set()
        for src_id, tgt_id in dep_edges:
            deps_by_assumption[src_id].add(tgt_id)
            all_dep_target_ids.add(tgt_id)

        # Bulk: which dependency targets have support edges?
        grounded_dep_ids = set()
        if all_dep_target_ids:
            grounded_dep_ids = set(
                Edge.objects.filter(
                    target_node_id__in=all_dep_target_ids,
                    edge_type=EdgeType.SUPPORTS,
                ).values_list('target_node_id', flat=True)
            )

        for assumption in assumptions:
            if assumption.id in directly_supported_ids:
                continue
            dep_targets = deps_by_assumption.get(assumption.id, set())
            has_grounded_dep = bool(dep_targets & grounded_dep_ids)
            dep_count = len(dep_targets)
            if not has_grounded_dep:
                orphaned.append({
                    'id': str(assumption.id),
                    'text': assumption.content,
                    'confidence': assumption.confidence,
                    'dependency_count': dep_count,
                })

        return orphaned

