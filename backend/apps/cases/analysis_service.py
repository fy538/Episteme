"""
CaseAnalysisService — analyze a case's graph after extraction.

Runs blind spot detection, assumption quality assessment, tension
identification, evidence coverage analysis, and decision readiness
computation.

Blind spot detection uses an LLM call; the rest are structural
analyses of the graph topology.
"""
import logging
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, FrozenSet, List, Optional, Set

from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# Text helpers for theme matching
# ═══════════════════════════════════════════════════════════════════

# Common English stop words to filter out of theme/node comparisons
_STOP_WORDS: FrozenSet[str] = frozenset({
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'has',
    'have', 'had', 'do', 'does', 'did', 'not', 'no', 'from', 'as', 'it',
    'its', 'this', 'that', 'which', 'who', 'whom', 'what', 'how', 'when',
    'where', 'why', 'all', 'each', 'some', 'any', 'more', 'most', 'also',
})

_WORD_RE = re.compile(r'[a-z0-9]+')


def _tokenize(text: str) -> List[str]:
    """Lowercase, split on non-alphanumeric, drop stop words and short tokens."""
    return [
        w for w in _WORD_RE.findall(text.lower())
        if len(w) > 2 and w not in _STOP_WORDS
    ]


def _jaccard(a: Set[str], b: Set[str]) -> float:
    """Jaccard similarity between two word sets. Returns 0.0 if both empty."""
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


# ═══════════════════════════════════════════════════════════════════
# Dataclasses
# ═══════════════════════════════════════════════════════════════════

@dataclass
class BlindSpot:
    description: str
    severity: str  # 'high' | 'medium' | 'low'
    suggested_action: str
    relevant_theme_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AssumptionAssessment:
    node_id: str
    content: str
    load_bearing: bool
    supporting_evidence: int
    contradicting_evidence: int
    testable: bool
    implicit: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TensionSummary:
    node_id: str
    content: str
    status: str
    involved_nodes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvidenceCoverage:
    total_claims: int
    supported_claims: int
    unsupported_claims: List[Dict[str, str]] = field(default_factory=list)
    total_evidence: int = 0
    evidence_per_claim: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DecisionReadiness:
    ready: bool
    confidence: float
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CaseAnalysis:
    blind_spots: List[BlindSpot] = field(default_factory=list)
    assumption_assessment: List[AssumptionAssessment] = field(default_factory=list)
    key_tensions: List[TensionSummary] = field(default_factory=list)
    evidence_coverage: Optional[EvidenceCoverage] = None
    readiness: Optional[DecisionReadiness] = None

    def to_dict(self) -> dict:
        return {
            'blind_spots': [b.to_dict() for b in self.blind_spots],
            'assumption_assessment': [a.to_dict() for a in self.assumption_assessment],
            'key_tensions': [t.to_dict() for t in self.key_tensions],
            'evidence_coverage': self.evidence_coverage.to_dict() if self.evidence_coverage else {},
            'readiness': self.readiness.to_dict() if self.readiness else {},
            'assumption_count': len(self.assumption_assessment),
            'tension_count': len(self.key_tensions),
        }


# ═══════════════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════════════

class CaseAnalysisService:
    """Run analysis on a case's graph after extraction."""

    def analyze_case(self, case) -> CaseAnalysis:
        """Run full analysis on a case's graph.

        Steps:
        1. Get the case graph (nodes + edges)
        2. Detect blind spots (LLM + hierarchy cross-reference)
        3. Assess assumptions (structural)
        4. Identify key tensions (structural)
        5. Assess evidence coverage (structural)
        6. Compute decision readiness (aggregation)

        Returns CaseAnalysis with all results.
        """
        from apps.graph.services import GraphService

        graph = GraphService.get_case_graph(case.id)
        analysis = CaseAnalysis()

        # 1. Structural analyses (no LLM needed)
        analysis.assumption_assessment = self._assess_assumptions(case, graph)
        analysis.key_tensions = self._identify_key_tensions(case, graph)
        analysis.evidence_coverage = self._assess_evidence_coverage(graph)

        # 2. LLM-based blind spot detection (best-effort)
        try:
            analysis.blind_spots = self._detect_blind_spots(case, graph)
        except Exception:
            logger.warning("Blind spot detection failed", exc_info=True)
            analysis.blind_spots = []

        # 3. Compute readiness (aggregation of above)
        analysis.readiness = self._compute_readiness(analysis)

        return analysis

    def _detect_blind_spots(self, case, graph: dict) -> List[BlindSpot]:
        """Detect what's missing from the case's analysis.

        Uses an LLM call with the decision question and extracted nodes
        to identify uncovered aspects. Cross-references with project
        hierarchy themes that weren't pulled into the case.
        """
        nodes = graph.get('nodes', [])
        if not nodes:
            return [BlindSpot(
                description="No evidence has been extracted yet for this decision.",
                severity='high',
                suggested_action="Add relevant documents to the project and re-extract.",
            )]

        # Format nodes for the prompt
        node_summaries = []
        for node in nodes[:40]:  # Cap at 40 to fit context
            node_summaries.append(
                f"- [{node.node_type}] {node.content[:150]}"
            )
        nodes_text = "\n".join(node_summaries)

        # Find uncovered themes from project hierarchy
        uncovered_themes = self._find_uncovered_themes(case, nodes)
        uncovered_text = ""
        if uncovered_themes:
            uncovered_text = "\n\nThese project themes were NOT included in the case analysis:\n"
            uncovered_text += "\n".join(f"- {t}" for t in uncovered_themes)

        prompt = f"""Given this decision: "{case.decision_question}"

And these extracted nodes:
{nodes_text}
{uncovered_text}

What important aspects of this decision are NOT covered by the evidence?

Consider:
- Stakeholder impacts not addressed
- Implementation risks not identified
- Alternative approaches not explored
- Second-order effects not considered
- Timing considerations missing
- Reversibility not assessed

Return a JSON array of blind spots, each with:
- "description": what's missing (1-2 sentences)
- "severity": "high", "medium", or "low"
- "suggested_action": what to do about it (1 sentence)

Return ONLY the JSON array. Maximum 5 blind spots, focused on the most critical gaps."""

        from apps.common.llm_providers import get_llm_provider
        from apps.common.utils import parse_json_from_response
        provider = get_llm_provider('fast')

        async def _call():
            return await provider.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an analytical assistant identifying blind spots in decision analysis. Return only valid JSON.",
                max_tokens=1500,
                temperature=0.3,
            )

        try:
            result = async_to_sync(_call)()
            parsed = parse_json_from_response(result)

            if isinstance(parsed, list):
                return [
                    BlindSpot(
                        description=item.get('description', ''),
                        severity=item.get('severity', 'medium'),
                        suggested_action=item.get('suggested_action', ''),
                    )
                    for item in parsed[:5]
                    if item.get('description')
                ]
        except Exception:
            logger.warning("Failed to parse blind spot LLM response", exc_info=True)

        return []

    def _find_uncovered_themes(self, case, nodes) -> List[str]:
        """Find project hierarchy themes that weren't represented in the case.

        Uses word-overlap scoring (Jaccard similarity) between theme labels/
        summaries and extracted node content. A theme is considered "covered"
        if any node has sufficient keyword overlap with it. This is more
        robust than exact substring matching — e.g. a theme labeled
        "Multi-Tenancy Architecture" will partially match a node about
        "schema isolation for tenant separation."

        If theme quality is still insufficient, a future improvement would
        be to pre-compute theme embeddings on ClusterHierarchy and use
        cosine similarity against existing node embeddings.
        """
        try:
            from apps.graph.models import ClusterHierarchy
            hierarchy = ClusterHierarchy.objects.filter(
                project_id=case.project_id,
                is_current=True,
            ).first()

            if not hierarchy:
                return []

            tree = hierarchy.tree or {}

            # Tokenize each node's content into word sets for overlap scoring
            node_word_sets = []
            for n in nodes:
                if hasattr(n, 'content') and n.content:
                    node_word_sets.append(
                        set(_tokenize(n.content))
                    )

            if not node_word_sets:
                return []

            uncovered = []
            for theme in tree.get('children', []):
                label = theme.get('label', '')
                summary = theme.get('summary', '')
                # Combine label + summary for richer matching
                theme_text = f"{label} {summary}".strip()
                if not theme_text:
                    continue

                theme_words = set(_tokenize(theme_text))
                if len(theme_words) < 2:
                    continue

                # A theme is "covered" if any node has ≥30% word overlap
                covered = any(
                    _jaccard(theme_words, node_words) >= 0.3
                    for node_words in node_word_sets
                )
                # Also check: do ≥50% of theme keywords appear anywhere
                # across all nodes? (handles spread across multiple nodes)
                if not covered:
                    all_node_words = set()
                    for ws in node_word_sets:
                        all_node_words.update(ws)
                    overlap = len(theme_words & all_node_words)
                    covered = overlap >= len(theme_words) * 0.5

                if not covered:
                    uncovered.append((label or summary)[:100])

            return uncovered[:10]
        except Exception as e:
            logger.warning("Heuristic blind spot detection failed: %s", e)
            return []

    def _assess_assumptions(self, case, graph: dict) -> List[AssumptionAssessment]:
        """Assess each assumption node's quality and risk.

        For each assumption:
        - Count supporting/contradicting edges → tested or untested
        - Check if load_bearing (has depends_on edges from important claims)
        - Determine if testable (from properties)
        """
        nodes = graph.get('nodes', [])
        edges = graph.get('edges', [])

        assumptions = [n for n in nodes if n.node_type == 'assumption']
        if not assumptions:
            return []

        # Build edge index for fast lookup
        incoming = {}  # node_id -> list of edges
        outgoing = {}  # node_id -> list of edges
        for edge in edges:
            src = str(edge.source_node_id)
            tgt = str(edge.target_node_id)
            outgoing.setdefault(src, []).append(edge)
            incoming.setdefault(tgt, []).append(edge)

        assessments = []
        for assumption in assumptions:
            node_id = str(assumption.id)

            # Count evidence edges
            in_edges = incoming.get(node_id, [])
            out_edges = outgoing.get(node_id, [])
            all_edges = in_edges + out_edges

            supporting = sum(1 for e in all_edges if e.edge_type == 'supports')
            contradicting = sum(1 for e in all_edges if e.edge_type == 'contradicts')

            # Check if load-bearing: are there depends_on edges FROM important nodes?
            depends_on_me = [
                e for e in incoming.get(node_id, [])
                if e.edge_type == 'depends_on'
            ]
            load_bearing = len(depends_on_me) > 0

            # Properties may contain testable/implicit flags from extraction
            props = assumption.properties or {}

            assessments.append(AssumptionAssessment(
                node_id=node_id,
                content=assumption.content,
                load_bearing=load_bearing,
                supporting_evidence=supporting,
                contradicting_evidence=contradicting,
                testable=props.get('testable', True),
                implicit=props.get('implicit', False),
            ))

        return assessments

    def _identify_key_tensions(self, case, graph: dict) -> List[TensionSummary]:
        """Identify the most decision-critical tensions.

        Tensions are nodes of type 'tension' plus any 'contradicts' edges.
        Ranked by importance and connection to high-importance claims.
        """
        nodes = graph.get('nodes', [])
        edges = graph.get('edges', [])

        tensions = [n for n in nodes if n.node_type == 'tension']

        # Build edge index
        node_edges = {}  # node_id -> list of (edge, other_node_id)
        for edge in edges:
            src = str(edge.source_node_id)
            tgt = str(edge.target_node_id)
            node_edges.setdefault(src, []).append((edge, tgt))
            node_edges.setdefault(tgt, []).append((edge, src))

        summaries = []
        for tension in tensions:
            node_id = str(tension.id)
            connected = node_edges.get(node_id, [])
            involved_ids = list(set(other_id for _, other_id in connected))

            summaries.append(TensionSummary(
                node_id=node_id,
                content=tension.content,
                status=tension.status,
                involved_nodes=involved_ids,
            ))

        # Sort by importance (from properties) using a pre-built lookup
        importance_by_id = {
            str(n.id): (n.properties or {}).get('importance', 1)
            for n in tensions
        }
        summaries.sort(
            key=lambda t: -importance_by_id.get(t.node_id, 1)
        )

        return summaries

    def _assess_evidence_coverage(self, graph: dict) -> EvidenceCoverage:
        """How well-supported are the claims?

        Pure structural analysis — counts direct 'supports' edges and
        identifies unsupported claims.

        NOTE: This intentionally checks only DIRECT evidence support
        (Evidence → supports → Claim), not transitive chains like
        Evidence → supports → Claim A → supports → Claim B. A claim
        supported only through other claims (not directly by evidence)
        should still surface as a gap — that's the kind of thing the
        readiness assessment needs to flag.
        """
        nodes = graph.get('nodes', [])
        edges = graph.get('edges', [])

        claims = [n for n in nodes if n.node_type == 'claim']
        evidence = [n for n in nodes if n.node_type == 'evidence']

        if not claims:
            return EvidenceCoverage(
                total_claims=0,
                supported_claims=0,
                total_evidence=len(evidence),
                evidence_per_claim=0.0,
            )

        # Find unsupported claims using a pre-built set (O(C+E) instead of O(C*E))
        supported_claim_ids = {
            str(e.target_node_id) for e in edges if e.edge_type == 'supports'
        }
        unsupported = []
        for claim in claims:
            claim_id = str(claim.id)
            if claim_id not in supported_claim_ids:
                unsupported.append({
                    'node_id': claim_id,
                    'content': claim.content[:200],
                })

        supported_count = len(claims) - len(unsupported)
        return EvidenceCoverage(
            total_claims=len(claims),
            supported_claims=supported_count,
            unsupported_claims=unsupported,
            total_evidence=len(evidence),
            evidence_per_claim=len(evidence) / max(len(claims), 1),
        )

    def _compute_readiness(self, analysis: CaseAnalysis) -> DecisionReadiness:
        """Overall assessment: is this decision ready to be made?

        Aggregates issues from all analysis dimensions.
        """
        issues = []

        # Blind spots
        high_severity_spots = [b for b in analysis.blind_spots if b.severity == 'high']
        if high_severity_spots:
            issues.append(f"{len(high_severity_spots)} high-severity blind spot(s)")

        # Untested load-bearing assumptions
        risky_assumptions = [
            a for a in analysis.assumption_assessment
            if a.load_bearing and a.supporting_evidence == 0
        ]
        if risky_assumptions:
            issues.append(f"{len(risky_assumptions)} load-bearing untested assumption(s)")

        # Unresolved tensions
        unresolved = [t for t in analysis.key_tensions if t.status != 'resolved']
        if unresolved:
            issues.append(f"{len(unresolved)} unresolved tension(s)")

        # Unsupported claims
        if analysis.evidence_coverage and analysis.evidence_coverage.unsupported_claims:
            count = len(analysis.evidence_coverage.unsupported_claims)
            issues.append(f"{count} unsupported claim(s)")

        confidence = max(0.0, 1.0 - (len(issues) * 0.15))

        return DecisionReadiness(
            ready=len(issues) == 0,
            confidence=round(confidence, 2),
            issues=issues,
        )
