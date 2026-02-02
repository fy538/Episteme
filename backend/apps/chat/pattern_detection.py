"""
Detect patterns in conversations that trigger proactive intelligence
"""
from typing import List, Optional, Dict
from django.db.models import Count
from .models import ChatThread, Message
from apps.signals.models import Signal


class ConversationPattern:
    """Base class for conversation patterns"""
    
    def detect(self, thread: ChatThread, recent_messages: List[Message]) -> Optional[Dict]:
        """
        Detect if pattern is present
        
        Returns:
            Dict with detection details if pattern found, None otherwise
        """
        raise NotImplementedError


class MultipleQuestionsPattern(ConversationPattern):
    """Detects when user has asked multiple questions"""
    
    THRESHOLD = 3
    
    def detect(self, thread: ChatThread, recent_messages: List[Message]) -> Optional[Dict]:
        """Detect if user has asked 3+ questions"""
        # Get question signals from this thread
        questions = Signal.objects.filter(
            thread=thread,
            type='question',
            dismissed_at__isnull=True
        ).order_by('-created_at')[:10]
        
        if len(questions) >= self.THRESHOLD:
            return {
                'pattern_type': 'multiple_questions',
                'question_count': len(questions),
                'questions': [
                    {'id': str(q.id), 'text': q.text}
                    for q in questions
                ],
                'suggested_action': 'organize_questions',
                'confidence': min(len(questions) / 5.0, 1.0)  # Max at 5 questions
            }
        
        return None


class UnvalidatedAssumptionsPattern(ConversationPattern):
    """Detects when user has made assumptions that should be validated"""
    
    THRESHOLD = 3
    
    def detect(self, thread: ChatThread, recent_messages: List[Message]) -> Optional[Dict]:
        """Detect if user has 3+ unvalidated assumptions"""
        assumptions = Signal.objects.filter(
            thread=thread,
            type='assumption',
            dismissed_at__isnull=True
        )
        
        # Check if any have been validated (you'd need to track this)
        # For now, assume all are unvalidated
        unvalidated = assumptions
        
        if len(unvalidated) >= self.THRESHOLD:
            return {
                'pattern_type': 'unvalidated_assumptions',
                'assumption_count': len(unvalidated),
                'assumptions': [
                    {'id': str(a.id), 'text': a.text, 'confidence': a.confidence}
                    for a in unvalidated
                ],
                'suggested_action': 'validate_assumptions',
                'confidence': min(len(unvalidated) / 5.0, 1.0)
            }
        
        return None


class CaseStructurePattern(ConversationPattern):
    """Detects when conversation has enough structure to create a case"""
    
    def detect(self, thread: ChatThread, recent_messages: List[Message]) -> Optional[Dict]:
        """Detect if thread has case-like structure"""
        # Already has a case? Skip
        if thread.primary_case_id:
            return None
        
        # Count signals by type
        signal_counts = Signal.objects.filter(
            thread=thread,
            dismissed_at__isnull=True
        ).values('type').annotate(count=Count('id'))
        
        counts_dict = {item['type']: item['count'] for item in signal_counts}
        
        # Need at least 2 assumptions, 2 questions, and some evidence/claims
        has_structure = (
            counts_dict.get('assumption', 0) >= 2 and
            counts_dict.get('question', 0) >= 2 and
            (counts_dict.get('evidence', 0) + counts_dict.get('claim', 0)) >= 3
        )
        
        if has_structure:
            total_signals = sum(counts_dict.values())
            return {
                'pattern_type': 'case_structure',
                'signal_distribution': counts_dict,
                'total_signals': total_signals,
                'suggested_action': 'create_case',
                'confidence': min(total_signals / 15.0, 0.95)  # Max 95% confidence
            }
        
        return None


class RepeatedTopicPattern(ConversationPattern):
    """Detects when user keeps asking about the same topic"""
    
    def detect(self, thread: ChatThread, recent_messages: List[Message]) -> Optional[Dict]:
        """Detect repeated topics (could trigger research agent)"""
        # This would use semantic similarity or keyword extraction
        # Simplified for now - checking if recent messages have similar terms
        
        if len(recent_messages) < 5:
            return None
        
        # Get last 5 user messages
        user_messages = [msg for msg in recent_messages if msg.role == 'user'][-5:]
        
        if len(user_messages) < 3:
            return None
        
        # Basic keyword overlap check (in production, use embeddings)
        # For now, just detect if same words appear multiple times
        all_words = set()
        word_counts = {}
        
        for msg in user_messages:
            words = set(msg.content.lower().split())
            for word in words:
                if len(word) > 5:  # Only meaningful words
                    word_counts[word] = word_counts.get(word, 0) + 1
        
        # Find words that appear in multiple messages
        repeated_words = [word for word, count in word_counts.items() if count >= 3]
        
        if repeated_words:
            return {
                'pattern_type': 'repeated_topic',
                'repeated_terms': repeated_words[:5],  # Top 5
                'suggested_action': 'research_topic',
                'confidence': min(len(repeated_words) / 5.0, 0.8)  # Max 80%
            }
        
        return None


class HighSignalDensityPattern(ConversationPattern):
    """Detects when there are many signals that should be organized"""
    
    THRESHOLD = 8
    
    def detect(self, thread: ChatThread, recent_messages: List[Message]) -> Optional[Dict]:
        """Detect if thread has high signal density"""
        # Count total signals
        total_signals = Signal.objects.filter(
            thread=thread,
            dismissed_at__isnull=True
        ).count()
        
        if total_signals >= self.THRESHOLD:
            # Get distribution
            signal_counts = Signal.objects.filter(
                thread=thread,
                dismissed_at__isnull=True
            ).values('type').annotate(count=Count('id'))
            
            counts_dict = {item['type']: item['count'] for item in signal_counts}
            
            return {
                'pattern_type': 'high_signal_density',
                'signal_count': total_signals,
                'signal_distribution': counts_dict,
                'suggested_action': 'organize_signals',
                'confidence': min(total_signals / 15.0, 0.95)
            }
        
        return None


class PatternDetectionEngine:
    """Orchestrates pattern detection"""
    
    PATTERNS = [
        UnvalidatedAssumptionsPattern(),  # High priority
        MultipleQuestionsPattern(),
        CaseStructurePattern(),
        HighSignalDensityPattern(),
        RepeatedTopicPattern(),
    ]
    
    @classmethod
    def analyze_thread(
        cls,
        thread: ChatThread,
        message_window: int = 10
    ) -> List[Dict]:
        """
        Analyze thread for patterns
        
        Args:
            thread: ChatThread to analyze
            message_window: Number of recent messages to consider
            
        Returns:
            List of detected patterns with details
        """
        recent_messages = list(
            Message.objects.filter(thread=thread)
            .order_by('-created_at')[:message_window]
        )
        
        detected_patterns = []
        for pattern_detector in cls.PATTERNS:
            result = pattern_detector.detect(thread, recent_messages)
            if result:
                detected_patterns.append(result)
        
        # Sort by confidence
        detected_patterns.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        return detected_patterns
