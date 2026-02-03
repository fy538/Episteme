"""
Companion service - Meta-cognitive reflection and background work tracking
"""
import uuid
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Q

from apps.chat.models import ChatThread, Message
from apps.signals.models import Signal
from apps.projects.models import Evidence
from apps.inquiries.models import Inquiry
from apps.companion.models import Reflection, InquiryHistory, ReflectionTriggerType
from apps.common.llm_providers.factory import get_llm_provider

logger = logging.getLogger(__name__)


class CompanionService:
    """
    Service for generating meta-cognitive reflections and tracking background work.
    
    Provides two main functionalities:
    1. Meta-reflection: Socratic questioning and assumption challenges
    2. Background tracking: Activity monitoring (signal extraction, evidence linking, etc.)
    """
    
    def __init__(self):
        # Use cheaper model for meta-reflection (Haiku instead of Sonnet)
        self.meta_llm = get_llm_provider('fast')
    
    def extract_current_topic(self, messages: List[Dict]) -> Optional[str]:
        """
        Extract current topic/focus from recent messages.
        
        Uses simple keyword extraction from the last user message.
        Can be enhanced with NER or topic modeling in the future.
        
        Args:
            messages: Recent messages from thread
        
        Returns:
            Current topic string or None
        """
        if not messages:
            return None
        
        # Get last user message
        user_messages = [m for m in messages if m.get('role') == 'user']
        if not user_messages:
            return None
        
        last_user_msg = user_messages[-1]
        content = last_user_msg.get('content', '')
        
        # Simple extraction: key nouns/topics
        # For now, just use first 50 chars as topic context
        # TODO: Enhance with NER or topic modeling
        topic = content[:50].lower()
        
        # Extract question if present
        if '?' in content:
            sentences = content.split('?')
            if sentences[0]:
                topic = sentences[0][-100:].lower()  # Last 100 chars before ?
        
        return topic.strip() if topic else None
    
    async def generate_action_card_reflection(
        self,
        thread_id: uuid.UUID,
        card_type: str,
        card_heading: str,
        card_content: Dict
    ) -> str:
        """
        Generate reflection specifically for action cards.
        
        Provides meta-commentary on why the action matters, what's at stake,
        and what the user should consider.
        
        Args:
            thread_id: Thread where card appeared
            card_type: Type of action card
            card_heading: Card's heading text
            card_content: Card's content data
        
        Returns:
            Reflection text focused on the action card
        """
        from apps.companion.prompts import get_action_card_reflection_prompt
        
        # Build prompt
        system_prompt = get_action_card_reflection_prompt(
            card_type=card_type,
            card_heading=card_heading,
            card_content=card_content
        )
        
        # Call Meta-LLM
        full_response = ""
        async for chunk in self.meta_llm.stream_chat(
            messages=[{"role": "user", "content": "Provide reflection on this action card."}],
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=200  # Brief reflection
        ):
            full_response += chunk.content
        
        return full_response.strip()
    
    async def prepare_reflection_context(
        self,
        thread_id: uuid.UUID
    ) -> Dict:
        """
        Prepare context for reflection generation.
        
        Args:
            thread_id: Thread to analyze
        
        Returns:
            Dict with thread, messages, signals, and patterns
        """
        from asgiref.sync import sync_to_async
        
        thread = await sync_to_async(ChatThread.objects.get)(id=thread_id)
        
        # Get recent messages for context (last 10)
        recent_messages = await sync_to_async(list)(
            Message.objects.filter(thread=thread)
            .order_by('-created_at')[:10]
            .values('id', 'role', 'content')
        )
        recent_messages.reverse()  # Chronological order
        
        # Get current signals for analysis
        current_signals = await sync_to_async(list)(
            Signal.objects.filter(thread=thread, dismissed_at__isnull=True)
            .select_related('inquiry')
            .values('id', 'type', 'text', 'confidence')
        )
        
        # Analyze graph patterns using GraphAnalyzer
        from apps.companion.graph_analyzer import GraphAnalyzer
        analyzer = GraphAnalyzer()
        patterns = await analyzer.find_patterns(thread_id)
        
        return {
            'thread': thread,
            'recent_messages': recent_messages,
            'current_signals': current_signals,
            'patterns': patterns
        }
    
    async def stream_reflection(
        self,
        thread: ChatThread,
        recent_messages: List[Dict],
        current_signals: List[Dict],
        patterns: Dict
    ):
        """
        Stream Meta-LLM reflection token-by-token.
        
        Yields chunks as they're generated for true real-time streaming.
        
        Args:
            thread: Thread being analyzed
            recent_messages: Recent conversation messages
            current_signals: Current signals extracted
            patterns: Graph patterns identified
        
        Yields:
            String chunks (tokens) as they're generated
        """
        from apps.companion.prompts import get_socratic_reflection_prompt
        
        # Get topic/context from thread
        topic = thread.title if thread.title != "New Chat" else "this conversation"
        
        # Prepare data for prompt
        claims = [s for s in current_signals if s['type'] == 'Claim']
        assumptions = [s for s in current_signals if s['type'] == 'Assumption']
        questions = [s for s in current_signals if s['type'] == 'Question']
        
        # Build system prompt
        system_prompt = get_socratic_reflection_prompt(
            topic=topic,
            claims=claims,
            assumptions=assumptions,
            questions=questions,
            patterns=patterns
        )
        
        # Prepare conversation context
        messages = []
        for msg in recent_messages[-3:]:  # Last 3 messages for context
            messages.append({
                'role': msg['role'],
                'content': msg['content'][:500]  # Truncate long messages
            })
        
        # Stream LLM response token-by-token
        async for chunk in self.meta_llm.stream_chat(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.7,  # Some creativity for natural language
            max_tokens=500    # 2-3 paragraphs
        ):
            yield chunk.content
    
    async def track_background_work(
        self,
        thread_id: uuid.UUID,
        since: Optional[datetime] = None
    ) -> Dict:
        """
        Track background work happening in the system.
        
        Queries existing models for recent activity:
        - Signal extraction
        - Evidence linking
        - Graph connections
        - Confidence updates
        
        Args:
            thread_id: Thread to track activity for
            since: Track activity since this time (default: last 5 minutes)
        
        Returns:
            Dict with activity summary
        """
        from asgiref.sync import sync_to_async
        
        if since is None:
            since = timezone.now() - timedelta(minutes=5)
        
        thread = await sync_to_async(ChatThread.objects.get)(id=thread_id)
        
        # 1. Recent signal extraction
        recent_signals = await sync_to_async(list)(
            Signal.objects.filter(
                thread=thread,
                created_at__gte=since,
                dismissed_at__isnull=True
            ).values('id', 'type', 'text', 'status')
        )
        
        signals_by_type = {}
        for signal in recent_signals:
            sig_type = signal['type']
            if sig_type not in signals_by_type:
                signals_by_type[sig_type] = []
            signals_by_type[sig_type].append({
                'text': signal['text'][:60] + ('...' if len(signal['text']) > 60 else ''),
                'status': signal['status']
            })
        
        # 2. Recent evidence (if thread has a case)
        evidence_data = {'count': 0, 'sources': []}
        if thread.primary_case:
            recent_evidence = await sync_to_async(list)(
                Evidence.objects.filter(
                    document__case=thread.primary_case,
                    extracted_at__gte=since
                ).values('document__title').annotate(count=Count('id'))
            )
            
            evidence_data = {
                'count': sum(e['count'] for e in recent_evidence),
                'sources': [e['document__title'] for e in recent_evidence]
            }
        
        # 3. Graph connections (relationships between signals/evidence)
        # Count signals with depends_on or contradicts relationships created recently
        connections_count = await sync_to_async(
            Signal.objects.filter(
                Q(thread=thread, created_at__gte=since) &
                (Q(depends_on__isnull=False) | Q(contradicts__isnull=False))
            ).distinct().count
        )()
        
        # 4. Inquiry confidence updates
        confidence_updates = []
        if thread.primary_case:
            inquiries = await sync_to_async(list)(
                Inquiry.objects.filter(case=thread.primary_case)
            )
            
            for inquiry in inquiries:
                # Get last two history entries to show change
                history = await sync_to_async(list)(
                    InquiryHistory.objects.filter(
                        inquiry=inquiry,
                        timestamp__gte=since
                    ).order_by('-timestamp')[:2]
                )
                
                if len(history) >= 2:
                    confidence_updates.append({
                        'inquiry_id': str(inquiry.id),
                        'title': inquiry.title[:60],
                        'old': round(history[1].confidence, 2),
                        'new': round(history[0].confidence, 2)
                    })
                elif len(history) == 1:
                    # New confidence set
                    confidence_updates.append({
                        'inquiry_id': str(inquiry.id),
                        'title': inquiry.title[:60],
                        'old': None,
                        'new': round(history[0].confidence, 2)
                    })
        
        return {
            'signals_extracted': {
                'count': len(recent_signals),
                'by_type': signals_by_type,
                'items': [
                    {'text': s['text'][:60], 'type': s['type']}
                    for s in recent_signals[:3]  # Top 3 only
                ]
            },
            'evidence_linked': evidence_data,
            'connections_built': {
                'count': connections_count
            },
            'confidence_updates': confidence_updates
        }
