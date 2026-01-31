"""
Knowledge graph traversal utilities

Utilities for navigating relationships between Signals and Evidence.
Enables reasoning queries like:
- "What does this assumption depend on?"
- "What evidence supports this claim?"
- "Are there any contradictions?"
"""
from typing import List, Set, Dict, Any
import uuid
from dataclasses import dataclass


@dataclass
class DependencyChain:
    """Represents a chain of signal dependencies"""
    root_signal: 'Signal'
    dependencies: List['Signal']
    depth: int


class GraphUtils:
    """Utilities for knowledge graph traversal"""
    
    @staticmethod
    def get_signal_dependencies(signal, max_depth: int = 5) -> DependencyChain:
        """
        Get all signals this signal depends on (recursively).
        
        Args:
            signal: Signal to get dependencies for
            max_depth: Maximum traversal depth (prevent infinite loops)
        
        Returns:
            DependencyChain with root and all dependencies
        """
        from apps.signals.models import Signal
        
        visited = set()
        dependencies = []
        
        def traverse(sig, depth=0):
            if depth >= max_depth or sig.id in visited:
                return
            
            visited.add(sig.id)
            
            for dep in sig.depends_on.all():
                if dep.id not in visited:
                    dependencies.append(dep)
                    traverse(dep, depth + 1)
        
        traverse(signal)
        
        return DependencyChain(
            root_signal=signal,
            dependencies=dependencies,
            depth=len(dependencies)
        )
    
    @staticmethod
    def get_signal_dependents(signal) -> List['Signal']:
        """
        Get all signals that depend on this signal.
        
        Args:
            signal: Signal to get dependents for
        
        Returns:
            List of signals that depend on this one
        """
        return list(signal.dependents.all())
    
    @staticmethod
    def find_contradictions(signal) -> Dict[str, List['Signal']]:
        """
        Find all contradictions for a signal.
        
        Args:
            signal: Signal to check
        
        Returns:
            Dict with 'direct' and 'transitive' contradictions
        """
        # Direct contradictions
        direct = list(signal.contradicts.all())
        
        # Signals that contradict this one
        contradicted_by = list(signal.contradicted_by.all())
        
        return {
            'this_contradicts': direct,
            'contradicted_by': contradicted_by,
        }
    
    @staticmethod
    def get_supporting_evidence(signal) -> List['Evidence']:
        """
        Get all evidence supporting this signal.
        
        Args:
            signal: Signal to get evidence for
        
        Returns:
            List of Evidence objects
        """
        return list(signal.supported_by_evidence.all())
    
    @staticmethod
    def get_contradicting_evidence(signal) -> List['Evidence']:
        """
        Get all evidence contradicting this signal.
        
        Args:
            signal: Signal to check
        
        Returns:
            List of Evidence objects that contradict this signal
        """
        return list(signal.contradicted_by_evidence.all())
    
    @staticmethod
    def detect_circular_dependencies(signal) -> bool:
        """
        Check if signal has circular dependencies.
        
        Args:
            signal: Signal to check
        
        Returns:
            True if circular dependency detected
        """
        visited = set()
        
        def has_cycle(sig, path):
            if sig.id in path:
                return True  # Cycle detected
            
            if sig.id in visited:
                return False  # Already checked this branch
            
            visited.add(sig.id)
            new_path = path | {sig.id}
            
            for dep in sig.depends_on.all():
                if has_cycle(dep, new_path):
                    return True
            
            return False
        
        return has_cycle(signal, set())
    
    @staticmethod
    def get_assumption_chain(signal) -> List[Dict[str, Any]]:
        """
        Get full assumption dependency tree.
        
        Args:
            signal: Signal to get chain for
        
        Returns:
            List of dicts representing the dependency tree
        """
        def build_tree(sig, visited=None):
            if visited is None:
                visited = set()
            
            if sig.id in visited:
                return {'signal': sig, 'dependencies': [], 'circular': True}
            
            visited.add(sig.id)
            
            deps = []
            for dep in sig.depends_on.all():
                deps.append(build_tree(dep, visited.copy()))
            
            return {
                'signal': {
                    'id': str(sig.id),
                    'text': sig.text,
                    'type': sig.type,
                    'status': sig.status,
                },
                'dependencies': deps,
                'circular': False,
            }
        
        return [build_tree(signal)]
    
    @staticmethod
    def get_evidence_strength(signal) -> Dict[str, Any]:
        """
        Calculate evidence strength for a signal.
        
        Args:
            signal: Signal to analyze
        
        Returns:
            Dict with support/contradict counts and confidence
        """
        supporting = signal.supported_by_evidence.all()
        contradicting = signal.contradicted_by_evidence.all()
        
        # Calculate average credibility
        support_credibility = []
        for evidence in supporting:
            if evidence.user_credibility_rating:
                support_credibility.append(evidence.user_credibility_rating / 5.0)
            else:
                support_credibility.append(evidence.extraction_confidence)
        
        avg_support = sum(support_credibility) / len(support_credibility) if support_credibility else 0
        
        return {
            'support_count': len(supporting),
            'contradict_count': len(contradicting),
            'avg_support_credibility': avg_support,
            'strength': 'strong' if avg_support > 0.8 and len(supporting) >= 2 else
                       'weak' if len(supporting) == 0 or len(contradicting) > 0 else
                       'moderate',
        }
