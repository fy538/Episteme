"""
Companion memory - Persist and recall past reflections.

Enables the companion to "remember" previous observations and build
on them for continuity across reflections.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from django.utils import timezone

from apps.chat.models import ChatThread
from apps.companion.models import Reflection

logger = logging.getLogger(__name__)


# Memory window configuration
MAX_RECENT_REFLECTIONS = 5
MAX_KEY_OBSERVATIONS = 3
MAX_SUMMARY_LENGTH = 200


class CompanionMemory:
    """
    Manages companion's memory of past reflections.

    Memory is stored in ChatThread.metadata['companion_memory'] and includes:
    - recent_reflections: Last 5 reflection summaries
    - key_observations: Persistent patterns noticed
    - conversation_arc: Phase and progress tracking
    """

    @staticmethod
    def get_memory_context(thread: ChatThread) -> Dict:
        """
        Get memory context for reflection generation.

        Returns context suitable for including in the reflection prompt.
        Token budget: ~500 tokens max.

        Args:
            thread: ChatThread to get memory for

        Returns:
            Dict with recent_reflections, key_observations, conversation_arc
        """
        memory = thread.metadata.get('companion_memory', {})

        return {
            'recent_reflections': memory.get('recent_reflections', [])[-MAX_RECENT_REFLECTIONS:],
            'key_observations': memory.get('key_observations', [])[:MAX_KEY_OBSERVATIONS],
            'conversation_arc': memory.get('conversation_arc', {
                'phase': 'exploration',
                'turns': 0,
                'topics_covered': []
            })
        }

    @staticmethod
    def update_memory(thread: ChatThread, reflection: Reflection) -> None:
        """
        Update memory after a new reflection is generated.

        Extracts summary, updates recent_reflections, and checks for
        key observations to persist.

        Args:
            thread: ChatThread to update
            reflection: New reflection to add to memory
        """
        # Initialize memory structure if needed
        if 'companion_memory' not in thread.metadata:
            thread.metadata['companion_memory'] = {
                'recent_reflections': [],
                'key_observations': [],
                'conversation_arc': {
                    'phase': 'exploration',
                    'turns': 0,
                    'topics_covered': []
                }
            }

        memory = thread.metadata['companion_memory']

        # 1. Add reflection summary to recent_reflections
        summary = CompanionMemory._extract_summary(reflection.reflection_text)

        reflection_entry = {
            'id': str(reflection.id),
            'summary': summary,
            'trigger_type': reflection.trigger_type,
            'created_at': reflection.created_at.isoformat()
        }

        memory['recent_reflections'].append(reflection_entry)

        # Keep only last N reflections
        if len(memory['recent_reflections']) > MAX_RECENT_REFLECTIONS:
            memory['recent_reflections'] = memory['recent_reflections'][-MAX_RECENT_REFLECTIONS:]

        # 2. Check for key observations to extract
        new_observations = CompanionMemory._extract_key_observations(
            reflection.reflection_text,
            reflection.patterns
        )

        for obs in new_observations:
            if obs not in memory['key_observations']:
                memory['key_observations'].append(obs)

        # Keep only top N observations
        if len(memory['key_observations']) > MAX_KEY_OBSERVATIONS:
            memory['key_observations'] = memory['key_observations'][:MAX_KEY_OBSERVATIONS]

        # 3. Update conversation arc
        memory['conversation_arc']['turns'] += 1
        arc_phase = CompanionMemory._determine_conversation_phase(
            turns=memory['conversation_arc']['turns'],
            patterns=reflection.patterns
        )
        memory['conversation_arc']['phase'] = arc_phase

        # Save to thread
        thread.metadata['companion_memory'] = memory
        thread.save(update_fields=['metadata'])

        logger.debug(
            "companion_memory_updated",
            extra={
                "thread_id": str(thread.id),
                "reflection_id": str(reflection.id),
                "recent_count": len(memory['recent_reflections']),
                "observations_count": len(memory['key_observations'])
            }
        )

    @staticmethod
    def _extract_summary(reflection_text: str) -> str:
        """
        Extract key insight from reflection text for memory storage.

        Strategy: First sentence or first MAX_SUMMARY_LENGTH chars.

        Args:
            reflection_text: Full reflection text

        Returns:
            Summary string
        """
        if not reflection_text:
            return ""

        # Try to get first sentence
        sentences = reflection_text.replace('\n', ' ').split('. ')
        if sentences and sentences[0]:
            first_sentence = sentences[0].strip()
            if len(first_sentence) <= MAX_SUMMARY_LENGTH:
                return first_sentence + ('.' if not first_sentence.endswith('.') else '')

        # Fall back to truncation
        return reflection_text[:MAX_SUMMARY_LENGTH].strip() + '...'

    @staticmethod
    def _extract_key_observations(reflection_text: str, patterns: Dict) -> List[str]:
        """
        Extract key observations worth persisting.

        Looks for patterns that indicate recurring themes or important insights.

        Args:
            reflection_text: Full reflection text
            patterns: Graph patterns from reflection

        Returns:
            List of observation strings
        """
        observations = []

        # Extract from patterns
        if patterns:
            # Ungrounded assumptions are worth noting
            ungrounded = patterns.get('ungrounded_assumptions', [])
            if len(ungrounded) >= 2:
                observations.append(
                    f"Multiple ungrounded assumptions detected ({len(ungrounded)} total)"
                )

            # Recurring themes indicate important topics
            themes = patterns.get('recurring_themes', [])
            for theme in themes[:1]:  # Just first theme
                if theme.get('count', 0) >= 3:
                    observations.append(
                        f"Recurring theme: {theme.get('theme', 'unknown')[:50]}"
                    )

            # Contradictions are always notable
            contradictions = patterns.get('contradictions', [])
            if contradictions:
                observations.append(
                    f"Contradiction detected in reasoning"
                )

        return observations

    @staticmethod
    def _determine_conversation_phase(turns: int, patterns: Dict) -> str:
        """
        Determine current phase of the conversation.

        Phases:
        - exploration: Early stage, gathering information
        - deepening: Building structure, connecting ideas
        - resolution: Reaching conclusions, high confidence

        Args:
            turns: Number of companion turns (reflections)
            patterns: Current graph patterns

        Returns:
            Phase string
        """
        # Simple heuristic based on turns and patterns
        if turns < 3:
            return 'exploration'

        # Check for strong claims (indicates progress)
        strong_claims = patterns.get('strong_claims', []) if patterns else []

        if len(strong_claims) >= 2:
            return 'resolution'

        if turns >= 3:
            return 'deepening'

        return 'exploration'

    @staticmethod
    def format_memory_for_prompt(memory_context: Dict) -> str:
        """
        Format memory context as text for inclusion in prompts.

        Args:
            memory_context: Dict from get_memory_context()

        Returns:
            Formatted string for prompt
        """
        sections = []

        # Recent reflections
        recent = memory_context.get('recent_reflections', [])
        if recent:
            sections.append("Your previous observations:")
            for i, r in enumerate(recent[-3:], 1):  # Last 3 only
                sections.append(f"  {i}. {r['summary']}")

        # Key observations
        observations = memory_context.get('key_observations', [])
        if observations:
            sections.append("\nPatterns you've noticed:")
            for obs in observations:
                sections.append(f"  - {obs}")

        # Conversation arc
        arc = memory_context.get('conversation_arc', {})
        phase = arc.get('phase', 'exploration')
        turns = arc.get('turns', 0)

        if turns > 0:
            sections.append(f"\nConversation phase: {phase} (reflection #{turns})")

        return '\n'.join(sections) if sections else ""
