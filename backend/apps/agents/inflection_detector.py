"""
LLM-based inflection point detection for agent routing.

Mirrors the case suggestion pattern but detects when specialized agents should engage.
Uses semantic understanding rather than regex patterns.
"""
from typing import Dict, List, Optional
import json
from django.utils import timezone

from apps.chat.models import Message, ChatThread
from apps.common.llm_providers import get_llm_provider
from apps.events.services import EventService
from apps.events.models import EventType, ActorType


class InflectionDetector:
    """
    Detects conversation inflection points where agents would be valuable.
    
    Uses LLM analysis (like case suggestions) rather than regex routing.
    """
    
    INFLECTION_TYPES = {
        'research_depth': {
            'agent': 'research',
            'description': 'Shift from simple Q&A to needing comprehensive analysis'
        },
        'critique_assumptions': {
            'agent': 'critique',
            'description': 'Shift from forming ideas to needing validation'
        },
        'synthesis_decision': {
            'agent': 'brief',
            'description': 'Shift from gathering info to needing decision framework'
        },
        'none': {
            'agent': None,
            'description': 'Continue conversational flow'
        }
    }
    
    @staticmethod
    async def analyze_for_agent_need(
        thread: ChatThread,
        recent_messages: Optional[List[Message]] = None,
        context_window: int = 6
    ) -> Dict:
        """
        Analyze conversation to detect if an agent would be helpful.
        
        Similar to analyze_for_case but focused on agent routing.
        
        Args:
            thread: Chat thread
            recent_messages: Optional specific messages (defaults to last N)
            context_window: Number of recent messages to analyze
        
        Returns:
            {
                'needs_agent': bool,
                'suggested_agent': str,  # 'research' | 'critique' | 'brief' | None
                'confidence': float,
                'inflection_type': str,
                'reasoning': str,
                'suggested_topic': str,
                'suggested_target': str,
                'context_summary': str,
                'active_skills': list,
                'message_count': int
            }
        """
        # Get recent messages if not provided
        if recent_messages is None:
            from asgiref.sync import sync_to_async
            messages = await sync_to_async(lambda: list(
                Message.objects.filter(thread=thread).order_by('created_at')
            ))()
            recent_messages = messages[max(0, len(messages) - context_window):]
        
        if len(recent_messages) < 2:
            return {
                'needs_agent': False,
                'suggested_agent': None,
                'confidence': 0.0,
                'inflection_type': 'none',
                'reasoning': 'Insufficient conversation history (need at least 2 messages)',
                'suggested_topic': '',
                'suggested_target': '',
                'context_summary': 'Conversation just started',
                'active_skills': [],
                'message_count': len(recent_messages)
            }
        
        # Build conversation context
        conversation_text = "\n\n".join([
            f"{m.role.upper()}: {m.content}"
            for m in recent_messages
        ])
        
        # Get case and skill context
        has_case = thread.primary_case is not None
        skill_names = []
        
        if has_case:
            from asgiref.sync import sync_to_async
            skills = await sync_to_async(lambda: list(
                thread.primary_case.active_skills.filter(status='active')
            ))()
            skill_names = [s.name for s in skills]
        
        # Build context info for LLM
        context_info = f"""- Thread has case: {has_case}
- Active skills: {', '.join(skill_names) if skill_names else 'None'}
- Message count: {len(recent_messages)}"""
        
        # LLM analysis
        provider = get_llm_provider('fast')
        
        system_prompt = """You are an expert at detecting conversation inflection points.

An inflection point is when conversation shifts from casual discussion to needing specialized analysis.

You identify THREE types of inflection points:
1. **research_depth**: Shift from simple Q&A to needing comprehensive analysis
   - Multiple complex questions
   - Unfamiliar territory exploration
   - Need for evidence from various sources
   - Exploring options systematically

2. **critique_assumptions**: Shift from forming ideas to needing validation
   - User has stated a position
   - Mentions assumptions or uncertainties
   - Asks about risks or what they're missing
   - Needs external challenge

3. **synthesis_decision**: Shift from gathering info to needing decision framework
   - Information has been collected
   - Multiple perspectives discussed
   - User asking for recommendation
   - Ready to decide but needs structure

4. **none**: Continue conversational flow
   - Simple questions
   - Clarifications
   - Social chat
   - Single-turn needs

Respond ONLY with valid JSON."""

        user_prompt = f"""Analyze this conversation for inflection points:

CONVERSATION:
{conversation_text}

CONTEXT:
{context_info}

Detect if a specialized agent would help at this point. Consider:
- Has conversation shifted from casual to analytical?
- Is user asking for depth beyond simple Q&A?
- Are they exploring a complex decision space?
- Do they need synthesis or critique?

Extract:
1. needs_agent: true/false (is this an inflection point?)
2. suggested_agent: "research" | "critique" | "brief" | null
3. confidence: 0.0-1.0 (how certain?)
4. inflection_type: "research_depth" | "critique_assumptions" | "synthesis_decision" | "none"
5. reasoning: Why you detected this (2-3 sentences)
6. suggested_topic: If research agent, what topic? (or "")
7. suggested_target: If critique agent, what to critique? (or "")
8. context_summary: Current conversation state (1 sentence)

Return ONLY valid JSON:
{{"needs_agent": true, "suggested_agent": "research", "confidence": 0.85, "inflection_type": "research_depth", "reasoning": "...", "suggested_topic": "...", "suggested_target": "", "context_summary": "..."}}"""
        
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
                'needs_agent': False,
                'suggested_agent': None,
                'confidence': 0.0,
                'inflection_type': 'none',
                'reasoning': f'Failed to parse LLM response: {str(e)}',
                'suggested_topic': '',
                'suggested_target': '',
                'context_summary': 'Analysis error',
                'active_skills': skill_names,
                'message_count': len(recent_messages)
            }
        
        # Add metadata
        analysis['active_skills'] = skill_names
        analysis['message_count'] = len(recent_messages)
        
        return analysis
    
    @staticmethod
    def get_agent_check_threshold() -> int:
        """
        Get the turn threshold for checking agent needs.
        
        Similar to signal extraction threshold but for agent routing.
        Defaults to 3 turns.
        """
        from django.conf import settings
        return getattr(settings, 'AGENT_CHECK_INTERVAL', 3)
    
    @staticmethod
    def should_check_for_agents(thread: ChatThread) -> bool:
        """
        Determine if we should check for agent inflection points.
        
        Uses turn-based threshold like signal extraction.
        """
        threshold = InflectionDetector.get_agent_check_threshold()
        
        turns_since_check = getattr(thread, 'turns_since_agent_check', 0)
        
        return (
            turns_since_check >= threshold or
            thread.last_agent_check_at is None
        )
