"""
Agent suggestion message creation helpers

Creates inline agent suggestion messages in chat.
"""
import logging
from typing import Dict
from django.utils import timezone
from apps.chat.models import ChatThread
from apps.chat.services import ChatService

logger = logging.getLogger(__name__)


async def create_agent_suggestion_message(
    thread: ChatThread,
    inflection: Dict
) -> 'Message':
    """
    Create an inline agent suggestion message.

    Similar to case suggestion card but for agents.

    Args:
        thread: Chat thread
        inflection: Inflection analysis from InflectionDetector

    Returns:
        Created Message instance
    """
    agent_type = inflection['suggested_agent']
    confidence = inflection['confidence']
    reasoning = inflection['reasoning']

    # Build suggestion text
    suggestion_text = _build_suggestion_text(
        agent_type=agent_type,
        inflection=inflection,
        thread=thread
    )

    # Create message with special metadata
    suggestion_msg = await ChatService.create_assistant_message(
        thread_id=thread.id,
        content=suggestion_text,
        metadata={
            'type': 'agent_suggestion',
            'agent_type': agent_type,
            'inflection': inflection,
            'awaiting_confirmation': True,
            'confidence': confidence,
            'suggested_at': timezone.now().isoformat()
        }
    )

    return suggestion_msg


def _build_suggestion_text(
    agent_type: str,
    inflection: Dict,
    thread: ChatThread
) -> str:
    """Build formatted suggestion message text"""

    agent_emoji = {
        'research': '🔬',
        'critique': '🎯',
        'brief': '📋'
    }

    agent_display = {
        'research': 'Research Agent',
        'critique': 'Critique Agent',
        'brief': 'Brief Agent'
    }

    suggestion = f"{agent_emoji.get(agent_type, '🤖')} **Agent Suggestion**\n\n"

    suggestion += f"I've detected an inflection point: **{inflection['inflection_type'].replace('_', ' ').title()}**\n\n"

    suggestion += f"**Suggested**: {agent_display.get(agent_type, agent_type.title())}\n\n"

    # What it would do
    suggestion += "**What it would do**:\n"

    if agent_type == 'research':
        topic = inflection.get('suggested_topic', 'this topic')
        suggestion += f"- Research: {topic}\n"
        suggestion += "- Gather comprehensive information from multiple sources\n"
        suggestion += "- Synthesize findings into structured report\n"

    elif agent_type == 'critique':
        target = inflection.get('suggested_target', 'your position')
        suggestion += f"- Critique: {target}\n"
        suggestion += "- Challenge assumptions rigorously\n"
        suggestion += "- Identify risks and counterarguments\n"
        suggestion += "- Explore what might go wrong\n"

    elif agent_type == 'brief':
        suggestion += "- Synthesize discussion into decision framework\n"
        suggestion += "- Generate structured recommendation\n"
        suggestion += "- Organize for stakeholder consumption\n"

    # Add skill info if available
    if thread.primary_case:
        from asgiref.sync import sync_to_async

        # Get active skills (sync wrapper)
        def get_skill_names():
            return list(
                thread.primary_case.active_skills.filter(status='active').values_list('name', flat=True)
            )

        try:
            skill_names = sync_to_async(get_skill_names)()

            if skill_names:
                suggestion += f"\n**Using skills**: {', '.join(skill_names)}\n"
        except Exception as e:
            # Skill names are optional enhancement, continue without them
            logger.warning("Could not fetch skill names: %s", e)

    # Add confidence and reasoning
    confidence_pct = int(inflection['confidence'] * 100)
    suggestion += f"\n**Confidence**: {confidence_pct}%\n"
    suggestion += f"\n_Why_: {reasoning}\n"

    # Add call to action
    suggestion += "\n---\n"
    suggestion += "\nReply with \"**yes**\" to run the agent, or \"**no thanks**\" to continue chatting normally."

    return suggestion
