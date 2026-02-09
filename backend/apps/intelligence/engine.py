"""
Unified Analysis Engine

Core engine for single-call unified analysis:
- Chat response
- Meta-cognitive reflection

Uses sectioned streaming to route content to appropriate destinations.
"""

import uuid
import json
import logging
from dataclasses import dataclass
from typing import AsyncIterator, Optional, Dict, List, Any
from enum import Enum

from .parser import SectionedStreamParser, Section, ParsedChunk
from .prompts import (
    build_unified_system_prompt,
    build_unified_user_prompt,
    UnifiedPromptConfig
)
logger = logging.getLogger(__name__)


class StreamEventType(Enum):
    """Types of events emitted during streaming"""
    RESPONSE_CHUNK = "response_chunk"
    REFLECTION_CHUNK = "reflection_chunk"
    RESPONSE_COMPLETE = "response_complete"
    REFLECTION_COMPLETE = "reflection_complete"
    ACTION_HINTS_COMPLETE = "action_hints_complete"
    GRAPH_EDITS_COMPLETE = "graph_edits_complete"
    ERROR = "error"
    DONE = "done"


@dataclass
class StreamEvent:
    """Event emitted during unified stream"""
    type: StreamEventType
    data: Any
    section: Optional[Section] = None


@dataclass
class UnifiedAnalysisContext:
    """Context for unified analysis"""
    thread: Any  # ChatThread
    user_message: str
    conversation_context: str = ""
    retrieval_context: str = ""
    patterns: Dict = None
    message_count: int = 0

    def __post_init__(self):
        if self.patterns is None:
            self.patterns = {}


class UnifiedAnalysisEngine:
    """
    Engine for unified LLM analysis.

    Combines chat response and reflection
    into a single streaming LLM call with sectioned output.

    Usage:
        engine = UnifiedAnalysisEngine()
        async for event in engine.analyze(context):
            if event.type == StreamEventType.RESPONSE_CHUNK:
                yield_to_chat_ui(event.data)
            elif event.type == StreamEventType.REFLECTION_CHUNK:
                yield_to_companion_ui(event.data)
    """

    def __init__(self, model_key: str = 'chat'):
        """
        Initialize the engine.

        Args:
            model_key: Key for model selection from settings.AI_MODELS
        """
        self.model_key = model_key
        self._provider = None

    @property
    def provider(self):
        """Lazy load LLM provider"""
        if self._provider is None:
            from apps.common.llm_providers import get_llm_provider
            self._provider = get_llm_provider(self.model_key)
        return self._provider

    async def analyze(
        self,
        context: UnifiedAnalysisContext,
    ) -> AsyncIterator[StreamEvent]:
        """
        Perform unified analysis with sectioned streaming.

        Args:
            context: Analysis context

        Yields:
            StreamEvent objects for each section
        """
        # Build prompts
        prompt_config = UnifiedPromptConfig(
            topic=context.thread.title if context.thread.title != "New Chat" else "",
            patterns=context.patterns
        )

        system_prompt = build_unified_system_prompt(prompt_config)
        user_prompt = build_unified_user_prompt(
            user_message=context.user_message,
            conversation_context=context.conversation_context,
            retrieval_context=context.retrieval_context,
        )

        # Initialize parser
        parser = SectionedStreamParser()

        # Accumulators for full content
        response_content = ""
        reflection_content = ""

        # Track section completion
        response_complete = False
        reflection_complete = False
        action_hints_complete = False
        graph_edits_complete = False

        try:
            # Stream from LLM
            async for chunk in self.provider.stream_chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
                max_tokens=2048
            ):
                # Parse the chunk
                parsed_chunks = parser.parse(chunk.content)

                for parsed in parsed_chunks:
                    if parsed.section == Section.RESPONSE:
                        if parsed.is_complete:
                            response_complete = True
                            yield StreamEvent(
                                type=StreamEventType.RESPONSE_COMPLETE,
                                data=response_content,
                                section=Section.RESPONSE
                            )
                        elif parsed.content:
                            response_content += parsed.content
                            yield StreamEvent(
                                type=StreamEventType.RESPONSE_CHUNK,
                                data=parsed.content,
                                section=Section.RESPONSE
                            )

                    elif parsed.section == Section.REFLECTION:
                        if parsed.is_complete:
                            reflection_complete = True
                            yield StreamEvent(
                                type=StreamEventType.REFLECTION_COMPLETE,
                                data=reflection_content,
                                section=Section.REFLECTION
                            )
                        elif parsed.content:
                            reflection_content += parsed.content
                            yield StreamEvent(
                                type=StreamEventType.REFLECTION_CHUNK,
                                data=parsed.content,
                                section=Section.REFLECTION
                            )

                    elif parsed.section == Section.ACTION_HINTS:
                        if parsed.is_complete:
                            action_hints_complete = True
                            # Get full action hints buffer
                            hints_buffer = parser.get_action_hints_buffer()
                            # Parse and emit
                            try:
                                hints_data = json.loads(hints_buffer) if hints_buffer.strip() else []
                                yield StreamEvent(
                                    type=StreamEventType.ACTION_HINTS_COMPLETE,
                                    data={
                                        'action_hints': hints_data,
                                        'raw': hints_buffer
                                    },
                                    section=Section.ACTION_HINTS
                                )
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse action hints JSON: {e}")
                                yield StreamEvent(
                                    type=StreamEventType.ACTION_HINTS_COMPLETE,
                                    data={
                                        'action_hints': [],
                                        'raw': hints_buffer,
                                        'error': str(e)
                                    },
                                    section=Section.ACTION_HINTS
                                )
                        # Note: parser._create_chunk() already accumulates action hints content

                    elif parsed.section == Section.GRAPH_EDITS:
                        if parsed.is_complete:
                            graph_edits_complete = True
                            edits_buffer = parser.get_graph_edits_buffer()
                            try:
                                edits_data = json.loads(edits_buffer) if edits_buffer.strip() else []
                                yield StreamEvent(
                                    type=StreamEventType.GRAPH_EDITS_COMPLETE,
                                    data={
                                        'graph_edits': edits_data,
                                        'raw': edits_buffer
                                    },
                                    section=Section.GRAPH_EDITS
                                )
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse graph edits JSON: {e}")
                                yield StreamEvent(
                                    type=StreamEventType.GRAPH_EDITS_COMPLETE,
                                    data={
                                        'graph_edits': [],
                                        'raw': edits_buffer,
                                        'error': str(e)
                                    },
                                    section=Section.GRAPH_EDITS
                                )

            # Flush any remaining content
            remaining = parser.flush()
            for parsed in remaining:
                if parsed.section == Section.RESPONSE and parsed.content:
                    response_content += parsed.content
                    yield StreamEvent(
                        type=StreamEventType.RESPONSE_CHUNK,
                        data=parsed.content,
                        section=Section.RESPONSE
                    )
                elif parsed.section == Section.REFLECTION and parsed.content:
                    reflection_content += parsed.content
                    yield StreamEvent(
                        type=StreamEventType.REFLECTION_CHUNK,
                        data=parsed.content,
                        section=Section.REFLECTION
                    )

            # Emit completion events if not already emitted
            if not response_complete and response_content:
                yield StreamEvent(
                    type=StreamEventType.RESPONSE_COMPLETE,
                    data=response_content,
                    section=Section.RESPONSE
                )

            if not reflection_complete and reflection_content:
                yield StreamEvent(
                    type=StreamEventType.REFLECTION_COMPLETE,
                    data=reflection_content,
                    section=Section.REFLECTION
                )

            if not action_hints_complete:
                hints_buffer = parser.get_action_hints_buffer()
                try:
                    hints_data = json.loads(hints_buffer) if hints_buffer.strip() else []
                except json.JSONDecodeError:
                    hints_data = []

                yield StreamEvent(
                    type=StreamEventType.ACTION_HINTS_COMPLETE,
                    data={
                        'action_hints': hints_data,
                        'raw': hints_buffer
                    },
                    section=Section.ACTION_HINTS
                )

            if not graph_edits_complete:
                edits_buffer = parser.get_graph_edits_buffer()
                try:
                    edits_data = json.loads(edits_buffer) if edits_buffer.strip() else []
                except json.JSONDecodeError:
                    edits_data = []

                yield StreamEvent(
                    type=StreamEventType.GRAPH_EDITS_COMPLETE,
                    data={
                        'graph_edits': edits_data,
                        'raw': edits_buffer
                    },
                    section=Section.GRAPH_EDITS
                )

            # Final done event with all content
            yield StreamEvent(
                type=StreamEventType.DONE,
                data={
                    'response': response_content,
                    'reflection': reflection_content,
                    'action_hints_raw': parser.get_action_hints_buffer(),
                    'graph_edits_raw': parser.get_graph_edits_buffer(),
                }
            )

        except Exception as e:
            logger.exception(f"Error in unified analysis: {e}")
            yield StreamEvent(
                type=StreamEventType.ERROR,
                data={'error': str(e)}
            )
            raise

    async def analyze_simple(
        self,
        thread,
        user_message: str,
        conversation_context: str = "",
        system_prompt_override: str = None,
        retrieval_context: str = "",
    ) -> AsyncIterator[StreamEvent]:
        """
        Simplified analyze interface.

        Args:
            thread: ChatThread object
            user_message: User's message content
            conversation_context: Formatted conversation history
            system_prompt_override: Optional custom system prompt (e.g. for scaffolding mode)
            retrieval_context: RAG-retrieved document chunks for grounding

        Yields:
            StreamEvent objects
        """
        from asgiref.sync import sync_to_async
        from apps.chat.models import Message

        # Get message count
        message_count = await sync_to_async(
            Message.objects.filter(thread=thread).count
        )()

        # Get patterns if companion graph analyzer is available
        patterns = {}
        try:
            from apps.graph.analyzer import GraphAnalyzer
            analyzer = GraphAnalyzer()
            patterns = await sync_to_async(analyzer.find_patterns)(thread.id)
        except Exception as e:
            logger.warning(f"Could not get patterns: {e}")

        context = UnifiedAnalysisContext(
            thread=thread,
            user_message=user_message,
            conversation_context=conversation_context,
            retrieval_context=retrieval_context,
            patterns=patterns,
            message_count=message_count,
        )

        if system_prompt_override:
            # Use the override directly instead of building from config
            async for event in self._analyze_with_custom_prompt(
                context, system_prompt_override
            ):
                yield event
        else:
            async for event in self.analyze(context):
                yield event

    async def _analyze_with_custom_prompt(
        self,
        context: UnifiedAnalysisContext,
        system_prompt: str,
    ) -> AsyncIterator[StreamEvent]:
        """
        Analyze with a custom system prompt (for scaffolding, etc.).

        Same streaming logic as analyze() but bypasses prompt building.
        """
        user_prompt = build_unified_user_prompt(
            user_message=context.user_message,
            conversation_context=context.conversation_context,
            retrieval_context=context.retrieval_context,
        )

        parser = SectionedStreamParser()
        response_content = ""
        reflection_content = ""
        response_complete = False
        reflection_complete = False
        action_hints_complete = False
        graph_edits_complete = False

        try:
            async for chunk in self.provider.stream_chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
                max_tokens=2048,
            ):
                parsed_chunks = parser.parse(chunk.content)

                for parsed in parsed_chunks:
                    if parsed.section == Section.RESPONSE:
                        if parsed.is_complete:
                            response_complete = True
                            yield StreamEvent(
                                type=StreamEventType.RESPONSE_COMPLETE,
                                data=response_content,
                                section=Section.RESPONSE,
                            )
                        else:
                            response_content += parsed.content
                            yield StreamEvent(
                                type=StreamEventType.RESPONSE_CHUNK,
                                data=parsed.content,
                                section=Section.RESPONSE,
                            )
                    elif parsed.section == Section.REFLECTION:
                        if parsed.is_complete:
                            reflection_complete = True
                            yield StreamEvent(
                                type=StreamEventType.REFLECTION_COMPLETE,
                                data=reflection_content,
                                section=Section.REFLECTION,
                            )
                        else:
                            reflection_content += parsed.content
                            yield StreamEvent(
                                type=StreamEventType.REFLECTION_CHUNK,
                                data=parsed.content,
                                section=Section.REFLECTION,
                            )
                    elif parsed.section == Section.ACTION_HINTS:
                        if parsed.is_complete:
                            action_hints_complete = True
                            try:
                                import json as json_mod
                                hints = json_mod.loads(parser.action_hints_buffer or '[]')
                            except Exception:
                                hints = []
                            yield StreamEvent(
                                type=StreamEventType.ACTION_HINTS_COMPLETE,
                                data={
                                    'action_hints': hints,
                                    'raw': parser.action_hints_buffer or '[]',
                                },
                                section=Section.ACTION_HINTS,
                            )
                    elif parsed.section == Section.GRAPH_EDITS:
                        if parsed.is_complete:
                            graph_edits_complete = True
                            try:
                                import json as json_mod
                                edits = json_mod.loads(parser.graph_edits_buffer or '[]')
                            except Exception:
                                edits = []
                            yield StreamEvent(
                                type=StreamEventType.GRAPH_EDITS_COMPLETE,
                                data={
                                    'graph_edits': edits,
                                    'raw': parser.graph_edits_buffer or '[]',
                                },
                                section=Section.GRAPH_EDITS,
                            )

            # Flush any remaining content from the parser
            remaining = parser.flush()
            for parsed in remaining:
                if parsed.section == Section.RESPONSE and parsed.content:
                    response_content += parsed.content
                    yield StreamEvent(
                        type=StreamEventType.RESPONSE_CHUNK,
                        data=parsed.content,
                        section=Section.RESPONSE,
                    )
                elif parsed.section == Section.REFLECTION and parsed.content:
                    reflection_content += parsed.content
                    yield StreamEvent(
                        type=StreamEventType.REFLECTION_CHUNK,
                        data=parsed.content,
                        section=Section.REFLECTION,
                    )

            # Emit completion events if not already emitted
            if not response_complete and response_content:
                yield StreamEvent(
                    type=StreamEventType.RESPONSE_COMPLETE,
                    data=response_content,
                    section=Section.RESPONSE,
                )

            if not reflection_complete and reflection_content:
                yield StreamEvent(
                    type=StreamEventType.REFLECTION_COMPLETE,
                    data=reflection_content,
                    section=Section.REFLECTION,
                )

            if not action_hints_complete:
                hints_buffer = parser.get_action_hints_buffer()
                try:
                    import json as json_mod
                    hints_data = json_mod.loads(hints_buffer) if hints_buffer.strip() else []
                except (json_mod.JSONDecodeError, Exception):
                    hints_data = []
                yield StreamEvent(
                    type=StreamEventType.ACTION_HINTS_COMPLETE,
                    data={
                        'action_hints': hints_data,
                        'raw': hints_buffer,
                    },
                    section=Section.ACTION_HINTS,
                )

            if not graph_edits_complete:
                edits_buffer = parser.get_graph_edits_buffer()
                try:
                    import json as json_mod
                    edits_data = json_mod.loads(edits_buffer) if edits_buffer.strip() else []
                except (json_mod.JSONDecodeError, Exception):
                    edits_data = []
                yield StreamEvent(
                    type=StreamEventType.GRAPH_EDITS_COMPLETE,
                    data={
                        'graph_edits': edits_data,
                        'raw': edits_buffer,
                    },
                    section=Section.GRAPH_EDITS,
                )

            # Final done event with all content
            yield StreamEvent(
                type=StreamEventType.DONE,
                data={
                    'response': response_content,
                    'reflection': reflection_content,
                    'action_hints_raw': parser.get_action_hints_buffer(),
                    'graph_edits_raw': parser.get_graph_edits_buffer(),
                },
            )

        except Exception as e:
            logger.exception("custom_prompt_analysis_error")
            yield StreamEvent(
                type=StreamEventType.ERROR,
                data={'error': str(e)},
            )
