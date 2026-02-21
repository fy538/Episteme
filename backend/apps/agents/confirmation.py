"""
Natural language confirmation detection

Detects when user is confirming or declining agent suggestions using LLM.
"""
import json
from typing import Optional, Dict
from asgiref.sync import sync_to_async

from apps.chat.models import ChatThread, Message
from apps.common.llm_providers import get_llm_provider


async def check_for_agent_confirmation(
    thread: ChatThread,
    user_message: Message
) -> Optional[Dict]:
    """
    Check if user message is confirming a pending agent suggestion.
    
    Uses LLM to detect confirmation (more flexible than keyword matching).
    
    Args:
        thread: Chat thread
        user_message: Latest user message
    
    Returns:
        {
            'confirmed': bool,
            'agent_type': str,
            'params': dict
        } or None if no pending suggestion
    """
    # Check if there's a pending agent suggestion
    pending = thread.metadata.get('pending_agent_suggestion')
    if not pending:
        return None
    
    # Get the suggestion message for context
    last_assistant = await sync_to_async(lambda: 
        Message.objects.filter(
            thread=thread,
            role='ASSISTANT',
            metadata__type='agent_suggestion',
            metadata__awaiting_confirmation=True
        ).order_by('-created_at').first()
    )()
    
    if not last_assistant:
        return None
    
    # Use LLM to detect intent
    provider = get_llm_provider('fast')
    
    system_prompt = """You detect user intent from responses to agent suggestions.

You categorize responses into:
- CONFIRM: User wants to run the agent (yes, sure, do it, go ahead, please, etc.)
- DECLINE: User doesn't want the agent (no, skip, not now, maybe later, etc.)
- CLARIFY: User has questions (what would that do?, how long?, will it..., etc.)
- IGNORE: User continues on different topic

Respond ONLY with valid JSON."""
    
    user_prompt = f"""The assistant suggested running an agent. The user responded:

USER RESPONSE: "{user_message.content}"

AGENT SUGGESTION CONTEXT: {pending.get('suggested_agent', '')} agent for {pending.get('inflection_type', '')}

Is the user:
A) CONFIRM - Agreeing to run the agent
B) DECLINE - Not interested right now
C) CLARIFY - Asking questions about what it would do
D) IGNORE - Continuing conversation on different topic

Extract:
1. intent: "confirm" | "decline" | "clarify" | "ignore"
2. confidence: 0.0-1.0 (how certain is this classification?)

Return ONLY valid JSON:
{{"intent": "confirm", "confidence": 0.95}}"""
    
    # Get intent from LLM
    full_response = ""
    async for chunk in provider.stream_chat(
        messages=[{"role": "user", "content": user_prompt}],
        system_prompt=system_prompt
    ):
        full_response += chunk.content
    
    try:
        result = json.loads(full_response.strip())
        intent = result.get('intent', 'ignore')
        confidence = result.get('confidence', 0.0)
    except json.JSONDecodeError:
        # Failed to parse, assume ignore
        return None
    
    # Handle different intents
    if intent == 'confirm' and confidence > 0.7:
        # User confirmed!
        agent_type = pending['suggested_agent']
        
        # Build params for agent
        params = {}
        if agent_type == 'research':
            params['topic'] = pending.get('suggested_topic', thread.primary_case.position)
        elif agent_type == 'critique':
            params['suggested_target'] = pending.get('suggested_target', '')
        
        # Mark suggestion as handled
        last_assistant.metadata['awaiting_confirmation'] = False
        last_assistant.metadata['user_confirmed'] = True
        await last_assistant.asave()
        
        return {
            'confirmed': True,
            'agent_type': agent_type,
            'params': params,
            'inflection': pending
        }
    
    elif intent == 'decline' and confidence > 0.7:
        # User declined
        last_assistant.metadata['awaiting_confirmation'] = False
        last_assistant.metadata['user_confirmed'] = False
        await last_assistant.asave()
        
        # Clear pending
        thread.metadata['pending_agent_suggestion'] = None
        await thread.asave()
        
        return None
    
    elif intent == 'clarify':
        # User asking questions - keep suggestion active
        # The assistant's next response should answer their clarifying question
        return None
    
    else:
        # Ignore - user moved on to different topic
        # After 2 ignored messages, clear the suggestion
        ignored_count = last_assistant.metadata.get('ignored_count', 0) + 1
        last_assistant.metadata['ignored_count'] = ignored_count
        
        if ignored_count >= 2:
            last_assistant.metadata['awaiting_confirmation'] = False
            thread.metadata['pending_agent_suggestion'] = None
            await thread.asave()
        
        await last_assistant.asave()
        return None


