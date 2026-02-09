"""
Graph analyzer - Find patterns in the knowledge graph
"""
import uuid
import logging
from typing import Dict, List
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
        case_assumptions = Node.objects.filter(
            case=case,
            node_type='assumption',
        )
        for assumption in case_assumptions:
            # Check if any 'supports' edges point to this assumption
            support_count = Edge.objects.filter(
                target_node=assumption,
                edge_type=EdgeType.SUPPORTS,
            ).count()

            if support_count == 0:
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
        case_claims = Node.objects.filter(
            case=case,
            node_type='claim',
        )
        for claim_node in case_claims:
            support_edges = Edge.objects.filter(
                target_node=claim_node,
                edge_type=EdgeType.SUPPORTS,
            )
            support_count = support_edges.count()

            if support_count >= 2:
                # Use average edge strength as confidence proxy
                strengths = [
                    e.strength for e in support_edges
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

        for assumption in assumptions:
            # Check if any 'supports' edge targets this assumption
            has_direct_support = Edge.objects.filter(
                target_node=assumption,
                edge_type=EdgeType.SUPPORTS,
            ).exists()

            if has_direct_support:
                continue

            # Check if any node this assumption depends_on has support
            has_grounded_dependency = False
            dep_target_ids = Edge.objects.filter(
                source_node=assumption,
                edge_type=EdgeType.DEPENDS_ON,
            ).values_list('target_node_id', flat=True)

            if dep_target_ids:
                has_grounded_dependency = Edge.objects.filter(
                    target_node_id__in=dep_target_ids,
                    edge_type=EdgeType.SUPPORTS,
                ).exists()

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

        for inquiry in inquiries:
            # Count evidence from graph nodes
            try:
                total_evidence = Node.objects.filter(
                    project=inquiry.case.project,
                    node_type='evidence',
                ).count() if inquiry.case and inquiry.case.project else 0
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
        if case:
            case_assumptions = Node.objects.filter(
                case=case,
                node_type='assumption',
            )
            for assumption in case_assumptions:
                has_support = Edge.objects.filter(
                    target_node=assumption,
                    edge_type=EdgeType.SUPPORTS,
                ).exists()
                if not has_support:
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
        if case:
            case_claims = Node.objects.filter(
                case=case,
                node_type='claim',
            )
            for claim_node in case_claims:
                support_edges = Edge.objects.filter(
                    target_node=claim_node,
                    edge_type=EdgeType.SUPPORTS,
                )
                support_count = support_edges.count()
                if support_count >= 2:
                    strengths = [
                        e.strength for e in support_edges
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

        for assumption in assumptions:
            # Has direct support edge?
            has_direct_support = Edge.objects.filter(
                target_node=assumption,
                edge_type=EdgeType.SUPPORTS,
            ).exists()

            if has_direct_support:
                continue

            # Has grounded dependency? (depends_on edge -> node with support)
            dep_target_ids = Edge.objects.filter(
                source_node=assumption,
                edge_type=EdgeType.DEPENDS_ON,
            ).values_list('target_node_id', flat=True)

            has_grounded_dep = False
            dep_count = len(dep_target_ids)
            if dep_target_ids:
                has_grounded_dep = Edge.objects.filter(
                    target_node_id__in=dep_target_ids,
                    edge_type=EdgeType.SUPPORTS,
                ).exists()

            if not has_grounded_dep:
                orphaned.append({
                    'id': str(assumption.id),
                    'text': assumption.content,
                    'confidence': assumption.confidence,
                    'dependency_count': dep_count,
                })

        return orphaned

    def compute_inquiry_health(self, inquiry_id: uuid.UUID) -> Dict:
        """
        Compute an overall health assessment for an inquiry.

        Combines pattern analysis into a single health summary
        suitable for driving brief annotations and readiness items.

        Args:
            inquiry_id: Inquiry to assess

        Returns:
            Dict with:
            - health_score: 0-100 overall health
            - blocking_issues: List of critical issues
            - warnings: List of non-critical concerns
            - strengths: List of well-grounded areas
        """
        patterns = self.find_patterns_for_inquiry(inquiry_id)

        health = {
            'health_score': 50,  # Start neutral
            'blocking_issues': [],
            'warnings': [],
            'strengths': [],
        }

        # High-confidence contradictions are blocking
        for contradiction in patterns['contradictions']:
            if contradiction.get('both_high_confidence'):
                health['blocking_issues'].append({
                    'type': 'high_confidence_contradiction',
                    'description': (
                        f'High-confidence conflict: "{contradiction["signal_text"][:50]}..." '
                        f'vs "{contradiction["contradicts_text"][:50]}..."'
                    ),
                })
                health['health_score'] -= 15
            else:
                health['warnings'].append({
                    'type': 'contradiction',
                    'description': (
                        f'Conflict: "{contradiction["signal_text"][:50]}..." '
                        f'vs "{contradiction["contradicts_text"][:50]}..."'
                    ),
                })
                health['health_score'] -= 5

        # Ungrounded assumptions are warnings
        for assumption in patterns['ungrounded_assumptions']:
            health['warnings'].append({
                'type': 'ungrounded_assumption',
                'description': f'Unvalidated: "{assumption["text"][:60]}..."',
            })
            health['health_score'] -= 5

        # Strong claims are strengths
        for claim in patterns['strong_claims']:
            health['strengths'].append({
                'type': 'well_grounded_claim',
                'description': (
                    f'Well-supported ({claim["evidence_count"]} evidence): '
                    f'"{claim["text"][:60]}..."'
                ),
            })
            health['health_score'] += 10

        # Evidence quality adjustments
        eq = patterns['evidence_quality']
        if eq['total'] == 0:
            health['warnings'].append({
                'type': 'no_evidence',
                'description': 'No evidence gathered yet.',
            })
            health['health_score'] -= 20
        elif eq['total'] < 2:
            health['warnings'].append({
                'type': 'insufficient_evidence',
                'description': f'Only {eq["total"]} piece(s) of evidence. Consider gathering more.',
            })
            health['health_score'] -= 10

        # Clamp to 0-100
        health['health_score'] = max(0, min(100, health['health_score']))

        return health
