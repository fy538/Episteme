"""
Unified Analysis Engine

Core engine for single-call unified analysis:
- Chat response
- Meta-cognitive reflection

Uses sectioned streaming to route content to appropriate destinations.
"""

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
    PLAN_EDITS_COMPLETE = "plan_edits_complete"
    ORIENTATION_EDITS_COMPLETE = "orientation_edits_complete"
    TOOL_ACTIONS_COMPLETE = "tool_actions_complete"
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


# ---------------------------------------------------------------------------
# Section configuration — table-driven section handling.
#
# Adding a new section type requires:
#   1. Add to Section enum (parser.py)
#   2. Add marker pair to SectionedStreamParser.MARKERS (parser.py)
#   3. Add buffer + getter to SectionedStreamParser (parser.py)
#   4. Add entry to _SECTION_CONFIGS below
# That's it — no more copy-pasting 40 lines of handler code.
# ---------------------------------------------------------------------------

@dataclass
class _SectionConfig:
    """Configuration for how a section is handled in the streaming loop."""
    # Whether content chunks are streamed (response/reflection) vs buffered (JSON sections)
    streams: bool
    # Default value when JSON parse fails or section is empty
    default_value: Any
    # Key name in event data payloads
    data_key: str
    # StreamEventType for chunk events (only for streaming sections)
    chunk_event: Optional[StreamEventType] = None
    # StreamEventType for completion events
    complete_event: Optional[StreamEventType] = None
    # Buffer getter method name on the parser
    buffer_getter: Optional[str] = None


_SECTION_CONFIGS: Dict[Section, _SectionConfig] = {
    Section.RESPONSE: _SectionConfig(
        streams=True,
        default_value='',
        data_key='response',
        chunk_event=StreamEventType.RESPONSE_CHUNK,
        complete_event=StreamEventType.RESPONSE_COMPLETE,
    ),
    Section.REFLECTION: _SectionConfig(
        streams=True,
        default_value='',
        data_key='reflection',
        chunk_event=StreamEventType.REFLECTION_CHUNK,
        complete_event=StreamEventType.REFLECTION_COMPLETE,
    ),
    Section.ACTION_HINTS: _SectionConfig(
        streams=False,
        default_value=[],
        data_key='action_hints',
        complete_event=StreamEventType.ACTION_HINTS_COMPLETE,
        buffer_getter='get_action_hints_buffer',
    ),
    Section.GRAPH_EDITS: _SectionConfig(
        streams=False,
        default_value=[],
        data_key='graph_edits',
        complete_event=StreamEventType.GRAPH_EDITS_COMPLETE,
        buffer_getter='get_graph_edits_buffer',
    ),
    Section.PLAN_EDITS: _SectionConfig(
        streams=False,
        default_value={},
        data_key='plan_edits',
        complete_event=StreamEventType.PLAN_EDITS_COMPLETE,
        buffer_getter='get_plan_edits_buffer',
    ),
    Section.ORIENTATION_EDITS: _SectionConfig(
        streams=False,
        default_value={},
        data_key='orientation_edits',
        complete_event=StreamEventType.ORIENTATION_EDITS_COMPLETE,
        buffer_getter='get_orientation_edits_buffer',
    ),
    Section.TOOL_ACTIONS: _SectionConfig(
        streams=False,
        default_value=[],
        data_key='tool_actions',
        complete_event=StreamEventType.TOOL_ACTIONS_COMPLETE,
        buffer_getter='get_tool_actions_buffer',
    ),
}


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
        available_tools: Optional[List] = None,
    ) -> AsyncIterator[StreamEvent]:
        """
        Perform unified analysis with sectioned streaming.

        Args:
            context: Analysis context
            available_tools: Optional list of ToolDefinition objects

        Yields:
            StreamEvent objects for each section
        """
        # Build prompts
        prompt_config = UnifiedPromptConfig(
            topic=context.thread.title if context.thread.title != "New Chat" else "",
            patterns=context.patterns
        )

        system_prompt = build_unified_system_prompt(
            prompt_config,
            available_tools=available_tools,
        )
        user_prompt = build_unified_user_prompt(
            user_message=context.user_message,
            conversation_context=context.conversation_context,
            retrieval_context=context.retrieval_context,
        )

        async for event in self._stream_and_parse(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=2048,
        ):
            yield event

    async def analyze_simple(
        self,
        thread,
        user_message: str,
        conversation_context: str = "",
        system_prompt_override: str = None,
        retrieval_context: str = "",
        available_tools: Optional[List] = None,
    ) -> AsyncIterator[StreamEvent]:
        """
        Simplified analyze interface.

        Args:
            thread: ChatThread object
            user_message: User's message content
            conversation_context: Formatted conversation history
            system_prompt_override: Optional custom system prompt (e.g. for scaffolding mode)
            retrieval_context: RAG-retrieved document chunks for grounding
            available_tools: Optional list of ToolDefinition objects for tool actions

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
            user_prompt = build_unified_user_prompt(
                user_message=context.user_message,
                conversation_context=context.conversation_context,
                retrieval_context=context.retrieval_context,
            )
            # Use higher token limit for custom prompts (e.g. case-mode with plan_edits)
            async for event in self._stream_and_parse(
                system_prompt=system_prompt_override,
                user_prompt=user_prompt,
                max_tokens=4096,
            ):
                yield event
        else:
            async for event in self.analyze(
                context,
                available_tools=available_tools,
            ):
                yield event

    # ------------------------------------------------------------------
    # Shared streaming loop — the single source of truth for section
    # parsing, buffering, completion, flush, and done events.
    # ------------------------------------------------------------------

    async def _stream_and_parse(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2048,
    ) -> AsyncIterator[StreamEvent]:
        """
        Core streaming loop shared by all analysis paths.

        Streams from the LLM provider, parses sectioned output via
        SectionedStreamParser, and yields typed StreamEvents.
        """
        parser = SectionedStreamParser()

        # Accumulators for streaming sections (response, reflection)
        content_accum: Dict[Section, str] = {}
        for section, cfg in _SECTION_CONFIGS.items():
            if cfg.streams:
                content_accum[section] = ''

        # Track which sections have been completed
        completed: Dict[Section, bool] = {s: False for s in _SECTION_CONFIGS}

        try:
            async for chunk in self.provider.stream_chat(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
                max_tokens=max_tokens,
            ):
                parsed_chunks = parser.parse(chunk.content)

                for parsed in parsed_chunks:
                    cfg = _SECTION_CONFIGS.get(parsed.section)
                    if cfg is None:
                        continue

                    if cfg.streams:
                        # Streaming section (response, reflection)
                        if parsed.is_complete:
                            completed[parsed.section] = True
                            yield StreamEvent(
                                type=cfg.complete_event,
                                data=content_accum[parsed.section],
                                section=parsed.section,
                            )
                        elif parsed.content:
                            content_accum[parsed.section] += parsed.content
                            yield StreamEvent(
                                type=cfg.chunk_event,
                                data=parsed.content,
                                section=parsed.section,
                            )
                    else:
                        # Buffered JSON section (action_hints, graph_edits, plan_edits)
                        if parsed.is_complete:
                            completed[parsed.section] = True
                            buffer = getattr(parser, cfg.buffer_getter)()
                            try:
                                data = json.loads(buffer) if buffer.strip() else cfg.default_value
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse {cfg.data_key} JSON: {e}")
                                data = cfg.default_value
                            yield StreamEvent(
                                type=cfg.complete_event,
                                data={cfg.data_key: data, 'raw': buffer},
                                section=parsed.section,
                            )

            # Flush remaining content from the parser
            remaining = parser.flush()
            for parsed in remaining:
                cfg = _SECTION_CONFIGS.get(parsed.section)
                if cfg and cfg.streams and parsed.content:
                    content_accum[parsed.section] += parsed.content
                    yield StreamEvent(
                        type=cfg.chunk_event,
                        data=parsed.content,
                        section=parsed.section,
                    )

            # Emit completion events for any sections that didn't close cleanly
            for section, cfg in _SECTION_CONFIGS.items():
                if completed[section]:
                    continue

                if cfg.streams:
                    # Streaming section: emit complete if we have content
                    if content_accum.get(section):
                        yield StreamEvent(
                            type=cfg.complete_event,
                            data=content_accum[section],
                            section=section,
                        )
                else:
                    # Buffered section: parse whatever we have
                    buffer = getattr(parser, cfg.buffer_getter)()
                    try:
                        data = json.loads(buffer) if buffer.strip() else cfg.default_value
                    except json.JSONDecodeError:
                        data = cfg.default_value
                    yield StreamEvent(
                        type=cfg.complete_event,
                        data={cfg.data_key: data, 'raw': buffer},
                        section=section,
                    )

            # Final done event with all accumulated content
            done_data = {}
            for section, cfg in _SECTION_CONFIGS.items():
                if cfg.streams:
                    done_data[cfg.data_key] = content_accum.get(section, '')
                else:
                    done_data[f'{cfg.data_key}_raw'] = getattr(parser, cfg.buffer_getter)()

            yield StreamEvent(type=StreamEventType.DONE, data=done_data)

        except Exception as e:
            logger.exception(f"Error in unified analysis: {e}")
            yield StreamEvent(
                type=StreamEventType.ERROR,
                data={'error': 'An internal error occurred during analysis.'},
            )
            raise
