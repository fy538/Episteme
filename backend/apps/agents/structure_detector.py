"""
LLM-based structure readiness detection for progressive disclosure.

Detects when conversation has accumulated enough signals/context that
creating structure (case, inquiries) would be valuable.

Uses two-track approach:
1. Fast track: Signal-based threshold checks (no LLM)
2. Deep track: LLM semantic analysis (periodic)
"""
from typing import Dict
from django.utils import timezone
from datetime import timedelta

from apps.chat.models import ChatThread
from apps.events.services import EventService
from apps.events.models import EventType, ActorType


class StructureReadinessDetector:
    """
    Detects conversation inflection points where structure would help.
    
    Similar to InflectionDetector but focused on when to create
    cases/inquiries rather than which agent to invoke.
    """
    
    STRUCTURE_TYPES = {
        'decision_case': {
            'description': 'Decision with options, stakes, and constraints',
            'indicators': ['assumptions', 'alternatives', 'constraints', 'stakes']
        },
        'research_project': {
            'description': 'Open-ended research with multiple questions',
            'indicators': ['questions', 'unknowns', 'evidence_gathering']
        },
        'comparison': {
            'description': 'Comparing multiple options or approaches',
            'indicators': ['alternatives', 'trade_offs', 'criteria']
        },
        'none': {
            'description': 'Continue conversational flow',
            'indicators': []
        }
    }
    
    @staticmethod
    def get_sensitivity_thresholds(sensitivity: int) -> Dict[str, int]:
        """
        Convert sensitivity level (1-5) to concrete thresholds.
        
        Args:
            sensitivity: 1=conservative, 5=proactive
        
        Returns:
            Dict with thresholds for different signal types
        """
        # Base thresholds (for sensitivity=3, balanced)
        base = {
            'assumption_threshold': 3,
            'question_depth': 3,
            'evidence_pieces': 4,
            'min_turns': 4
        }
        
        # Adjust based on sensitivity
        # Higher sensitivity = lower thresholds (suggest sooner)
        multiplier = (6 - sensitivity) / 3.0  # 5->0.33, 3->1.0, 1->1.67
        
        return {
            'assumption_threshold': max(1, int(base['assumption_threshold'] * multiplier)),
            'question_depth': max(1, int(base['question_depth'] * multiplier)),
            'evidence_pieces': max(2, int(base['evidence_pieces'] * multiplier)),
            'min_turns': max(2, int(base['min_turns'] * multiplier))
        }
    
    @staticmethod
    def track_suggestion_feedback(thread: ChatThread, accepted: bool):
        """
        Track whether user accepted or dismissed structure suggestion.
        Use to tune sensitivity over time and emit events.
        
        Args:
            thread: Chat thread
            accepted: True if user created case, False if dismissed
        """
        if accepted:
            # User found suggestion helpful
            EventService.create_event(
                type=EventType.STRUCTURE_ACCEPTED,
                actor_type=ActorType.USER,
                user=thread.user,
                metadata={
                    'thread_id': str(thread.id),
                    'suggestion': thread.metadata.get('pending_structure_suggestion', {})
                }
            )
            
            # Clear pending suggestion
            if 'pending_structure_suggestion' in thread.metadata:
                del thread.metadata['pending_structure_suggestion']
                thread.save(update_fields=['metadata'])
        else:
            # User dismissed
            EventService.create_event(
                type=EventType.STRUCTURE_DISMISSED,
                actor_type=ActorType.USER,
                user=thread.user,
                metadata={
                    'thread_id': str(thread.id),
                    'suggestion': thread.metadata.get('pending_structure_suggestion', {})
                }
            )
            
            # Mark as dismissed
            if 'pending_structure_suggestion' in thread.metadata:
                thread.metadata['pending_structure_suggestion']['dismissed'] = True
                thread.metadata['pending_structure_suggestion']['dismissed_at'] = timezone.now().isoformat()
                thread.save(update_fields=['metadata'])
            
            # Check for auto-tuning
            from apps.events.models import Event
            recent_dismissals = Event.objects.filter(
                user=thread.user,
                type=EventType.STRUCTURE_DISMISSED,
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count()
            
            if recent_dismissals >= 3:
                # Suggest lowering sensitivity
                thread.metadata['sensitivity_suggestion'] = 'lower'
                thread.metadata['sensitivity_suggestion_reason'] = f'{recent_dismissals} dismissals in past week'
                thread.save(update_fields=['metadata'])
