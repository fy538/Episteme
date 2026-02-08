"""
Graph analyzer - Find patterns in the knowledge graph
"""
import uuid
import logging
from typing import Dict, List
import numpy as np
from asgiref.sync import sync_to_async

from apps.chat.models import ChatThread
from apps.signals.models import Signal, SignalType
from apps.projects.models import Evidence
from apps.inquiries.models import Inquiry
from apps.common.graph_utils import GraphUtils

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
    
    def __init__(self):
        self.similarity_threshold = 0.80  # For semantic similarity
    
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
            # No case yet, limited analysis
            thread_signals = Signal.objects.filter(thread=thread, dismissed_at__isnull=True)
            
            # Just find assumptions
            for signal in thread_signals.filter(type=SignalType.ASSUMPTION):
                patterns['ungrounded_assumptions'].append({
                    'id': str(signal.id),
                    'text': signal.text,
                    'mentioned_times': 1
                })
            
            return patterns
        
        # Get signals from this thread and broader case
        thread_signals = Signal.objects.filter(
            thread=thread,
            dismissed_at__isnull=True
        ).prefetch_related('supported_by_evidence', 'contradicted_by_evidence')
        
        case_signals = Signal.objects.filter(
            case=case,
            dismissed_at__isnull=True
        ).prefetch_related('supported_by_evidence', 'contradicted_by_evidence')
        
        # 1. Find ungrounded assumptions
        for signal in thread_signals.filter(type=SignalType.ASSUMPTION):
            evidence_count = signal.supported_by_evidence.count()
            
            if evidence_count == 0:
                # Count how many times this assumption appears in case
                similar_count = self._count_similar_signals(signal, case_signals)
                
                patterns['ungrounded_assumptions'].append({
                    'id': str(signal.id),
                    'text': signal.text,
                    'mentioned_times': similar_count,
                    'confidence': signal.confidence
                })
        
        # 2. Find contradictions
        for signal in thread_signals:
            contradictions = GraphUtils.find_contradictions(signal)
            
            if contradictions['this_contradicts'] or contradictions['contradicted_by']:
                all_contradictions = (
                    list(contradictions['this_contradicts']) +
                    list(contradictions['contradicted_by'])
                )
                
                for contradicting_signal in all_contradictions:
                    patterns['contradictions'].append({
                        'signal_id': str(signal.id),
                        'signal_text': signal.text,
                        'contradicts_id': str(contradicting_signal.id),
                        'contradicts_text': contradicting_signal.text
                    })
        
        # 3. Find strongly supported claims
        for signal in thread_signals.filter(type=SignalType.CLAIM):
            supporting_evidence = list(signal.supported_by_evidence.all())
            
            if len(supporting_evidence) >= 2:
                # Calculate average confidence
                avg_confidence = sum(
                    e.extraction_confidence for e in supporting_evidence
                ) / len(supporting_evidence)
                
                if avg_confidence > 0.75:
                    patterns['strong_claims'].append({
                        'id': str(signal.id),
                        'text': signal.text,
                        'evidence_count': len(supporting_evidence),
                        'avg_confidence': round(avg_confidence, 2)
                    })
        
        # 4. Find recurring themes (signals mentioned multiple times)
        # Group signals by semantic similarity
        theme_groups = self._find_recurring_themes(case_signals)
        
        for theme in theme_groups:
            if len(theme['signals']) >= 2:  # Mentioned at least twice
                patterns['recurring_themes'].append({
                    'theme': theme['representative_text'],
                    'count': len(theme['signals']),
                    'signal_ids': [str(s.id) for s in theme['signals']]
                })
        
        # 5. Identify missing considerations
        # Check for questions without answers
        unanswered_questions = thread_signals.filter(
            type=SignalType.QUESTION,
            inquiry__isnull=True  # Not elevated to inquiry
        )
        
        for question in unanswered_questions[:3]:  # Top 3 only
            patterns['missing_considerations'].append({
                'id': str(question.id),
                'text': question.text
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
    
    def _count_similar_signals(self, signal: Signal, signals_to_search) -> int:
        """
        Count how many similar signals exist.
        
        Uses simple text matching for now (can be enhanced with embeddings).
        """
        # Simple approach: check if signal text appears in other signals
        count = 0
        normalized_text = signal.normalized_text.lower()
        
        for other_signal in signals_to_search:
            if other_signal.id != signal.id:
                if normalized_text in other_signal.normalized_text.lower():
                    count += 1
                elif other_signal.normalized_text.lower() in normalized_text:
                    count += 1
        
        return max(1, count)  # At least 1 (itself)
    
    def _find_recurring_themes(self, signals) -> List[Dict]:
        """
        Find signals that represent recurring themes.
        
        Groups semantically similar signals together.
        Currently uses embedding similarity (if available).
        """
        themes = []
        processed_ids = set()
        
        # Get signals with embeddings
        signals_with_embeddings = [
            s for s in signals
            if s.embedding is not None
        ]
        
        if not signals_with_embeddings:
            return themes
        
        for signal in signals_with_embeddings:
            if signal.id in processed_ids:
                continue
            
            # Find similar signals
            similar_signals = [signal]  # Start with this signal
            processed_ids.add(signal.id)
            
            signal_embedding = np.array(signal.embedding)
            
            for other_signal in signals_with_embeddings:
                if other_signal.id in processed_ids:
                    continue
                
                if other_signal.embedding is None:
                    continue
                
                # Calculate cosine similarity
                other_embedding = np.array(other_signal.embedding)
                similarity = self._cosine_similarity(signal_embedding, other_embedding)
                
                if similarity >= self.similarity_threshold:
                    similar_signals.append(other_signal)
                    processed_ids.add(other_signal.id)
            
            # Only create theme if multiple similar signals found
            if len(similar_signals) >= 2:
                themes.append({
                    'representative_text': signal.text,
                    'signals': similar_signals
                })
        
        return themes
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    async def detect_circular_reasoning(self, thread_id: uuid.UUID) -> List[Dict]:
        """
        Detect circular dependencies in signal reasoning.
        
        Example: Signal A depends on B, B depends on C, C depends on A
        
        Args:
            thread_id: Thread to analyze
        
        Returns:
            List of circular dependency chains
        """
        thread = ChatThread.objects.get(id=thread_id)
        
        if not thread.primary_case:
            return []
        
        circular_chains = []
        signals = Signal.objects.filter(
            case=thread.primary_case,
            dismissed_at__isnull=True
        ).prefetch_related('depends_on')
        
        for signal in signals:
            # Use existing GraphUtils to detect circular dependencies
            has_cycle = GraphUtils.detect_circular_dependencies(signal)
            
            if has_cycle:
                # Get the dependency chain to show the cycle
                chain = GraphUtils.get_signal_dependencies(signal)
                
                circular_chains.append({
                    'root_signal_id': str(signal.id),
                    'root_signal_text': signal.text,
                    'dependency_count': chain.depth,
                    'circular': True
                })
        
        return circular_chains
    
    async def find_orphaned_assumptions(self, thread_id: uuid.UUID) -> List[Dict]:
        """
        Find assumptions that have no path to evidence.
        
        These are assumptions that:
        - Have no supporting evidence directly
        - Don't depend on signals that have evidence
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
        assumptions = Signal.objects.filter(
            case=thread.primary_case,
            type=SignalType.ASSUMPTION,
            dismissed_at__isnull=True
        ).prefetch_related('supported_by_evidence', 'depends_on')
        
        for assumption in assumptions:
            # Check if has direct evidence
            if assumption.supported_by_evidence.exists():
                continue
            
            # Check if depends on signals that have evidence
            has_grounded_dependency = False
            for dep in assumption.depends_on.all():
                if dep.supported_by_evidence.exists():
                    has_grounded_dependency = True
                    break
            
            if not has_grounded_dependency:
                orphaned.append({
                    'id': str(assumption.id),
                    'text': assumption.text,
                    'mentioned_in_thread': assumption.thread_id == thread.id
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
        ).prefetch_related('evidence_items', 'related_signals')
        
        for inquiry in inquiries:
            # Count evidence
            evidence_count = inquiry.evidence_items.count()
            
            # Count signals with evidence
            signals_with_evidence = 0
            for signal in inquiry.related_signals.all():
                if signal.supported_by_evidence.exists():
                    signals_with_evidence += 1
            
            total_evidence = evidence_count + signals_with_evidence
            
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
        
        # Get signals with contradictions
        signals = Signal.objects.filter(
            case_id=case_id,
            dismissed_at__isnull=True,
            confidence__gte=0.75  # High confidence
        ).prefetch_related('contradicts', 'contradicted_by_evidence')
        
        for signal in signals:
            # Check signal contradictions
            for contra in signal.contradicts.all():
                if contra.confidence >= 0.75:
                    conflicts.append({
                        'type': 'signal_vs_signal',
                        'signal1_id': str(signal.id),
                        'signal1_text': signal.text,
                        'signal1_confidence': signal.confidence,
                        'signal2_id': str(contra.id),
                        'signal2_text': contra.text,
                        'signal2_confidence': contra.confidence
                    })
            
            # Check evidence contradictions
            for evidence in signal.contradicted_by_evidence.all():
                if evidence.extraction_confidence >= 0.75:
                    conflicts.append({
                        'type': 'signal_vs_evidence',
                        'signal_id': str(signal.id),
                        'signal_text': signal.text,
                        'signal_confidence': signal.confidence,
                        'evidence_id': str(evidence.id),
                        'evidence_text': evidence.text,
                        'evidence_confidence': evidence.extraction_confidence
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

        # Get signals for this inquiry
        inquiry_signals = inquiry.related_signals.filter(
            dismissed_at__isnull=True
        ).prefetch_related('supported_by_evidence', 'contradicted_by_evidence')

        if not inquiry_signals.exists():
            return patterns

        # 1. Ungrounded assumptions
        for signal in inquiry_signals.filter(type=SignalType.ASSUMPTION):
            if not signal.supported_by_evidence.exists():
                patterns['ungrounded_assumptions'].append({
                    'id': str(signal.id),
                    'text': signal.text,
                    'confidence': signal.confidence,
                })

        # 2. Contradictions (deduplicated)
        seen_pairs = set()
        for signal in inquiry_signals:
            for contra in signal.contradicts.filter(dismissed_at__isnull=True):
                pair = tuple(sorted([str(signal.id), str(contra.id)]))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    patterns['contradictions'].append({
                        'signal_id': str(signal.id),
                        'signal_text': signal.text,
                        'contradicts_id': str(contra.id),
                        'contradicts_text': contra.text,
                        'both_high_confidence': (
                            signal.confidence >= 0.75 and contra.confidence >= 0.75
                        ),
                    })

        # 3. Strong claims
        for signal in inquiry_signals.filter(type=SignalType.CLAIM):
            supporting = list(signal.supported_by_evidence.all())
            if len(supporting) >= 2:
                avg_conf = sum(
                    e.extraction_confidence for e in supporting
                ) / len(supporting)
                if avg_conf > 0.7:
                    patterns['strong_claims'].append({
                        'id': str(signal.id),
                        'text': signal.text,
                        'evidence_count': len(supporting),
                        'avg_confidence': round(avg_conf, 2),
                    })

        # 4. Recurring themes via semantic similarity
        themes = self._find_recurring_themes(inquiry_signals)
        for theme in themes:
            if len(theme['signals']) >= 2:
                patterns['recurring_themes'].append({
                    'theme': theme['representative_text'],
                    'count': len(theme['signals']),
                    'signal_ids': [str(s.id) for s in theme['signals']],
                })

        # 5. Evidence quality breakdown
        evidence_items = inquiry.evidence_items.all()
        for ev in evidence_items:
            patterns['evidence_quality']['total'] += 1
            if hasattr(ev, 'strength') and ev.strength and ev.strength >= 0.75:
                patterns['evidence_quality']['high_confidence'] += 1
            elif hasattr(ev, 'strength') and ev.strength and ev.strength < 0.5:
                patterns['evidence_quality']['low_confidence'] += 1
            if hasattr(ev, 'direction'):
                if ev.direction == 'supports':
                    patterns['evidence_quality']['supporting'] += 1
                elif ev.direction == 'contradicts':
                    patterns['evidence_quality']['contradicting'] += 1
                else:
                    patterns['evidence_quality']['neutral'] += 1

        logger.info(
            f"Inquiry pattern analysis complete for {inquiry_id}: "
            f"{len(patterns['ungrounded_assumptions'])} ungrounded, "
            f"{len(patterns['contradictions'])} contradictions, "
            f"{len(patterns['strong_claims'])} strong claims"
        )

        return patterns

    def find_orphaned_assumptions_for_inquiry(self, inquiry_id: uuid.UUID) -> List[Dict]:
        """
        Find assumptions within an inquiry that have no path to evidence.

        Unlike the thread-scoped version, this checks both:
        - Direct evidence on the assumption
        - Evidence on signals the assumption depends on

        Args:
            inquiry_id: Inquiry to analyze

        Returns:
            List of orphaned assumption dicts
        """
        orphaned = []
        assumptions = Signal.objects.filter(
            inquiry_id=inquiry_id,
            type=SignalType.ASSUMPTION,
            dismissed_at__isnull=True,
        ).prefetch_related('supported_by_evidence', 'depends_on')

        for assumption in assumptions:
            # Has direct evidence?
            if assumption.supported_by_evidence.exists():
                continue

            # Has grounded dependency?
            has_grounded_dep = False
            for dep in assumption.depends_on.all():
                if dep.supported_by_evidence.exists():
                    has_grounded_dep = True
                    break

            if not has_grounded_dep:
                orphaned.append({
                    'id': str(assumption.id),
                    'text': assumption.text,
                    'confidence': assumption.confidence,
                    'dependency_count': assumption.depends_on.count(),
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
