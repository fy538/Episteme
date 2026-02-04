"""
Graph analyzer - Find patterns in the knowledge graph
"""
import uuid
import logging
from typing import Dict, List
import numpy as np
from asgiref.sync import sync_to_async

from apps.chat.models import ChatThread
from apps.signals.models import Signal
from apps.projects.models import Evidence
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
            for signal in thread_signals.filter(type='Assumption'):
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
        for signal in thread_signals.filter(type='Assumption'):
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
        for signal in thread_signals.filter(type='Claim'):
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
            type='Question',
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
            type='Assumption',
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
