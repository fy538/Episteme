"""
Unified Analysis Engine

Core engine for single-call unified analysis:
- Chat response
- Meta-cognitive reflection
- Signal extraction

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
from .extraction_rules import ExtractionRulesEngine

logger = logging.getLogger(__name__)


class StreamEventType(Enum):
    """Types of events emitted during streaming"""
    RESPONSE_CHUNK = "response_chunk"
    REFLECTION_CHUNK = "reflection_chunk"
    RESPONSE_COMPLETE = "response_complete"
    REFLECTION_COMPLETE = "reflection_complete"
    SIGNALS_COMPLETE = "signals_complete"
    ACTION_HINTS_COMPLETE = "action_hints_complete"
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
    existing_signals: List[Dict] = None
    patterns: Dict = None
    message_count: int = 0

    def __post_init__(self):
        if self.existing_signals is None:
            self.existing_signals = []
        if self.patterns is None:
            self.patterns = {}


class UnifiedAnalysisEngine:
    """
    Engine for unified LLM analysis.

    Combines chat response, reflection, and signal extraction
    into a single streaming LLM call with sectioned output.

    Usage:
        engine = UnifiedAnalysisEngine()
        async for event in engine.analyze(context):
            if event.type == StreamEventType.RESPONSE_CHUNK:
                yield_to_chat_ui(event.data)
            elif event.type == StreamEventType.REFLECTION_CHUNK:
                yield_to_companion_ui(event.data)
            elif event.type == StreamEventType.SIGNALS_COMPLETE:
                save_signals(event.data)
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
        force_extraction: bool = False
    ) -> AsyncIterator[StreamEvent]:
        """
        Perform unified analysis with sectioned streaming.

        Args:
            context: Analysis context
            force_extraction: Force signal extraction regardless of rules

        Yields:
            StreamEvent objects for each section
        """
        # Determine if we should extract signals
        extraction_rules = None
        should_extract = force_extraction

        if not force_extraction:
            extraction_state = ExtractionRulesEngine.get_thread_extraction_state(context.thread)
            extraction_rules = ExtractionRulesEngine.should_extract(
                thread=context.thread,
                message_content=context.user_message,
                message_count=context.message_count,
                **extraction_state
            )
            should_extract = extraction_rules.should_extract
            logger.info(f"Extraction decision: {should_extract} ({extraction_rules.reason})")

        # Build prompts
        prompt_config = UnifiedPromptConfig(
            include_signals=should_extract,
            signal_types=extraction_rules.include_types if extraction_rules else None,
            topic=context.thread.title if context.thread.title != "New Chat" else "",
            patterns=context.patterns
        )

        system_prompt = build_unified_system_prompt(prompt_config)
        user_prompt = build_unified_user_prompt(
            user_message=context.user_message,
            conversation_context=context.conversation_context,
            signals_context=context.existing_signals
        )

        # Initialize parser
        parser = SectionedStreamParser()

        # Accumulators for full content
        response_content = ""
        reflection_content = ""
        # Note: signals_content is accumulated by parser.signals_buffer

        # Track section completion
        response_complete = False
        reflection_complete = False
        signals_complete = False
        action_hints_complete = False

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

                    elif parsed.section == Section.SIGNALS:
                        if parsed.is_complete:
                            signals_complete = True
                            # Get full signals buffer (parser accumulates this)
                            signals_buffer = parser.get_signals_buffer()
                            # Parse and emit
                            try:
                                signals_data = json.loads(signals_buffer) if signals_buffer.strip() else []
                                yield StreamEvent(
                                    type=StreamEventType.SIGNALS_COMPLETE,
                                    data={
                                        'signals': signals_data,
                                        'raw': signals_buffer,
                                        'extraction_enabled': should_extract
                                    },
                                    section=Section.SIGNALS
                                )
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse signals JSON: {e}")
                                yield StreamEvent(
                                    type=StreamEventType.SIGNALS_COMPLETE,
                                    data={
                                        'signals': [],
                                        'raw': signals_buffer,
                                        'extraction_enabled': should_extract,
                                        'error': str(e)
                                    },
                                    section=Section.SIGNALS
                                )
                        # Note: parser._create_chunk() already accumulates signals content

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

            if not signals_complete:
                signals_buffer = parser.get_signals_buffer()
                try:
                    signals_data = json.loads(signals_buffer) if signals_buffer.strip() else []
                except json.JSONDecodeError:
                    signals_data = []

                yield StreamEvent(
                    type=StreamEventType.SIGNALS_COMPLETE,
                    data={
                        'signals': signals_data,
                        'raw': signals_buffer,
                        'extraction_enabled': should_extract
                    },
                    section=Section.SIGNALS
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

            # Final done event with all content
            yield StreamEvent(
                type=StreamEventType.DONE,
                data={
                    'response': response_content,
                    'reflection': reflection_content,
                    'signals_raw': parser.get_signals_buffer(),
                    'action_hints_raw': parser.get_action_hints_buffer(),
                    'extraction_enabled': should_extract,
                    'extraction_reason': extraction_rules.reason if extraction_rules else 'forced'
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
        conversation_context: str = ""
    ) -> AsyncIterator[StreamEvent]:
        """
        Simplified analyze interface.

        Args:
            thread: ChatThread object
            user_message: User's message content
            conversation_context: Formatted conversation history

        Yields:
            StreamEvent objects
        """
        from asgiref.sync import sync_to_async
        from apps.chat.models import Message
        from apps.signals.models import Signal

        # Get message count
        message_count = await sync_to_async(
            Message.objects.filter(thread=thread).count
        )()

        # Get existing signals for context
        existing_signals = await sync_to_async(list)(
            Signal.objects.filter(
                thread=thread,
                dismissed_at__isnull=True
            ).order_by('-created_at')[:10]
            .values('type', 'text', 'confidence')
        )

        # Get patterns if companion graph analyzer is available
        patterns = {}
        try:
            from apps.companion.graph_analyzer import GraphAnalyzer
            analyzer = GraphAnalyzer()
            patterns = await sync_to_async(analyzer.find_patterns)(thread.id)
        except Exception as e:
            logger.warning(f"Could not get patterns: {e}")

        context = UnifiedAnalysisContext(
            thread=thread,
            user_message=user_message,
            conversation_context=conversation_context,
            existing_signals=existing_signals,
            patterns=patterns,
            message_count=message_count
        )

        async for event in self.analyze(context):
            yield event
