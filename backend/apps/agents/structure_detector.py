"""
LLM-based structure readiness detection for progressive disclosure.

Detects when conversation has accumulated enough signals/context that
creating structure (case, inquiries) would be valuable.

Uses two-track approach:
1. Fast track: Signal-based threshold checks (no LLM)
2. Deep track: LLM semantic analysis (periodic)
"""
from typing import Dict, List, Optional
import json
from django.utils import timezone
from datetime import timedelta

from apps.chat.models import ChatThread
from apps.signals.models import Signal
from apps.common.llm_providers import get_llm_provider
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
    def check_fast_thresholds(
        thread: ChatThread,
        recent_signals: List[Signal],
        sensitivity: int = 3
    ) -> bool:
        """
        Fast path: count-based threshold checks (no LLM).
        
        Args:
            thread: Chat thread
            recent_signals: Recent signals from thread
            sensitivity: 1-5 scale (1=conservative, 5=proactive)
        
        Returns:
            True if thresholds met and should proceed to deep analysis
        """
        thresholds = StructureReadinessDetector.get_sensitivity_thresholds(sensitivity)
        
        # Count signals by type
        signal_counts = {
            'assumption': 0,
            'question': 0,
            'evidence': 0,
            'claim': 0
        }
        
        for signal in recent_signals:
            signal_type = signal.type.lower()
            if signal_type in signal_counts:
                signal_counts[signal_type] += 1
        
        # Check if any threshold is met
        return (
            signal_counts['assumption'] >= thresholds['assumption_threshold'] or
            signal_counts['question'] >= thresholds['question_depth'] or
            signal_counts['evidence'] >= thresholds['evidence_pieces']
        )
    
    @staticmethod
    async def analyze_structure_readiness(
        thread: ChatThread,
        recent_signals: List[Signal],
        sensitivity: int = 3,
        context_window: int = 10
    ) -> Dict:
        """
        Deep path: LLM semantic analysis of conversation.
        
        Args:
            thread: Chat thread
            recent_signals: Recent signals from thread
            sensitivity: 1-5 scale
            context_window: Number of recent messages to analyze
        
        Returns:
            {
                'ready': bool,
                'confidence': float,
                'structure_type': 'decision_case' | 'research_project' | 'comparison' | 'none',
                'suggested_inquiries': [str],
                'detected_assumptions': [str],
                'reasoning': str,
                'context_summary': str
            }
        """
        from asgiref.sync import sync_to_async
        from apps.chat.models import Message
        
        # Get recent messages
        messages = await sync_to_async(lambda: list(
            Message.objects.filter(thread=thread)
                .order_by('created_at')
                .values('role', 'content')
        ))()
        
        recent_messages = messages[max(0, len(messages) - context_window):]
        
        if len(recent_messages) < 3:
            return {
                'ready': False,
                'confidence': 0.0,
                'structure_type': 'none',
                'suggested_inquiries': [],
                'detected_assumptions': [],
                'reasoning': 'Insufficient conversation history (need at least 3 messages)',
                'context_summary': 'Conversation just started'
            }
        
        # Build conversation context
        conversation_text = "\n\n".join([
            f"{m['role'].upper()}: {m['content']}"
            for m in recent_messages
        ])
        
        # Build signal summary
        signal_summary = {}
        for signal in recent_signals[:15]:  # Top 15 recent signals
            signal_type = signal.type.lower()
            if signal_type not in signal_summary:
                signal_summary[signal_type] = []
            signal_summary[signal_type].append(signal.text)
        
        signal_context = "\n".join([
            f"{stype.title()}s ({len(items)}):\n" + "\n".join([f"  - {item}" for item in items[:5]])
            for stype, items in signal_summary.items()
        ])
        
        # LLM analysis
        provider = get_llm_provider('fast')
        
        system_prompt = """You are an expert at detecting when unstructured conversations need structure.

You identify when a conversation has accumulated enough complexity that creating
a structured case (with inquiries, assumptions tracking, evidence) would help the user.

Key indicators:
- **Decision case**: Multiple options, stakes mentioned, constraints, assumptions to validate
- **Research project**: Multiple open questions, evidence gathering, exploration
- **Comparison**: Evaluating alternatives, trade-offs, criteria

You should suggest structure when:
1. Conversation has depth (not just simple Q&A)
2. Multiple assumptions or questions are accumulating
3. User is working toward a decision or deep understanding
4. Structure would reduce cognitive load

DO NOT suggest structure for:
- Simple informational questions
- Single-topic clarifications
- Casual conversation
- When user explicitly wants to just chat

Respond ONLY with valid JSON."""

        user_prompt = f"""Analyze this conversation for structure readiness:

CONVERSATION:
{conversation_text}

EXTRACTED SIGNALS:
{signal_context if signal_context else 'No signals extracted yet'}

CONTEXT:
- Message count: {len(recent_messages)}
- Thread has case: {thread.primary_case is not None}
- Signal types detected: {list(signal_summary.keys())}

Questions to answer:
1. Is this conversation ready for structure (case + inquiries)?
2. What type of structure would help? (decision_case, research_project, comparison, none)
3. What would be the 2-4 core inquiries/questions to investigate?
4. What assumptions have been stated or implied?
5. How confident are you (0.0-1.0)?

Extract:
- ready: true/false (should we suggest creating structure?)
- confidence: 0.0-1.0 (how certain?)
- structure_type: "decision_case" | "research_project" | "comparison" | "none"
- suggested_inquiries: [2-4 question strings] (or empty if not ready)
- detected_assumptions: [assumption strings] (or empty)
- reasoning: Why you made this determination (2-3 sentences)
- context_summary: Current conversation state (1 sentence)

Return ONLY valid JSON:
{{"ready": true, "confidence": 0.85, "structure_type": "decision_case", "suggested_inquiries": ["...", "..."], "detected_assumptions": ["...", "..."], "reasoning": "...", "context_summary": "..."}}"""
        
        # Stream from LLM
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt
        ):
            full_response += chunk.content
        
        try:
            analysis = json.loads(full_response.strip())
        except json.JSONDecodeError as e:
            # Fallback if parsing fails
            return {
                'ready': False,
                'confidence': 0.0,
                'structure_type': 'none',
                'suggested_inquiries': [],
                'detected_assumptions': [],
                'reasoning': f'Failed to parse LLM response: {str(e)}',
                'context_summary': 'Analysis error'
            }
        
        # Validate response
        required_fields = ['ready', 'confidence', 'structure_type', 'suggested_inquiries', 
                          'detected_assumptions', 'reasoning', 'context_summary']
        for field in required_fields:
            if field not in analysis:
                analysis[field] = [] if field in ['suggested_inquiries', 'detected_assumptions'] else ''
        
        return analysis
    
    @staticmethod
    def should_check_structure_readiness(thread: ChatThread, sensitivity: int = 3) -> bool:
        """
        Determine if we should check for structure readiness.
        
        Uses turn-based threshold and cooldown period.
        
        Args:
            thread: Chat thread
            sensitivity: 1-5 scale (affects check frequency)
        
        Returns:
            True if should check
        """
        # Get threshold based on sensitivity
        thresholds = StructureReadinessDetector.get_sensitivity_thresholds(sensitivity)
        
        # Check if thread already has a case
        if thread.primary_case is not None:
            return False
        
        # Check if we recently suggested structure
        last_suggestion = thread.metadata.get('last_structure_suggestion_at')
        if last_suggestion:
            from django.utils.dateparse import parse_datetime
            last_time = parse_datetime(last_suggestion)
            if last_time and (timezone.now() - last_time) < timedelta(minutes=10):
                # Cooldown: don't re-suggest within 10 minutes
                return False
        
        # Check turn count
        from apps.chat.models import Message
        message_count = Message.objects.filter(thread=thread).count()
        
        return message_count >= thresholds['min_turns']
    
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
