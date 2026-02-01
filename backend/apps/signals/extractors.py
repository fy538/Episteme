"""
Signal extraction logic with LLM + embeddings

Refactored to use PydanticAI for structured extraction.
"""
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings
from pydantic_ai import Agent

from apps.chat.models import Message
from apps.signals.models import Signal, SignalType
from apps.signals.prompts import get_signal_extraction_prompt
from apps.signals.embedding_service import get_embedding_service
from apps.common.utils import normalize_text, generate_dedupe_key
from apps.common.ai_schemas import SignalExtractionResult
from apps.common.ai_models import get_model

logger = logging.getLogger(__name__)


class SignalExtractor:
    """
    Extract signals from user messages with semantic embeddings
    
    Key design:
    - Extract everything raw (no premature deduplication)
    - Embed with sentence-transformers (free, local)
    - Index with sequence_index for temporal ordering
    - Process/dedupe at read time
    - Uses PydanticAI for structured, validated extraction
    """
    
    # PydanticAI agent for signal extraction
    _extraction_agent = Agent(
        get_model(settings.AI_MODELS['extraction']),
        result_type=SignalExtractionResult,
        system_prompt=(
            "You are an epistemic analyst who extracts structured signals from technical conversations. "
            "Extract assumptions, questions, constraints, goals, decisions, claims, and evidence mentions. "
            "Be precise and extract only what is explicitly stated or clearly implied."
        )
    )
    
    def __init__(self):
        # Use shared embedding service (singleton)
        self.embedding_service = get_embedding_service()
        # 384 dimensions, fast, good quality
        # Alternative: 'all-mpnet-base-v2' (768 dim, slower, better quality)
    
    async def extract_from_messages_batch(
        self,
        messages: List[Message],
        thread = None
    ) -> Dict[str, List[Signal]]:
        """
        Extract signals from multiple messages in a single LLM call.
        
        More efficient than extracting one-by-one:
        - Single LLM call for batch
        - Better context window utilization
        - Amortize fixed prompt overhead
        
        Args:
            messages: List of user messages to extract from
            thread: ChatThread object for context
            
        Returns:
            Dict mapping message_id -> list of Signal objects
        """
        if not messages:
            return {}
        
        # Build batch extraction prompt
        batch_prompt = self._build_batch_extraction_prompt(messages, thread)
        
        # Call LLM once for all messages
        try:
            result = await self._extraction_agent.run(batch_prompt)
            extracted_signals = result.data.signals
        except Exception:
            logger.exception(
                "batch_signal_extraction_failed",
                extra={
                    "thread_id": str(thread.id) if thread else None,
                    "message_count": len(messages)
                }
            )
            return {}
        
        if not extracted_signals:
            return {}
        
        # Group signals by message (using span info)
        signals_by_message = {}
        for i, message in enumerate(messages):
            message_signals = []
            
            for extraction in extracted_signals:
                # Check if signal belongs to this message
                # (extraction should include message_index in span)
                if extraction.span and extraction.span.get('message_index') == i:
                    signal = self._create_signal_from_extraction(
                        extraction=extraction,
                        message=message,
                        sequence_index=i
                    )
                    if signal:
                        message_signals.append(signal)
            
            signals_by_message[str(message.id)] = message_signals
        
        return signals_by_message
    
    def _create_signal_from_extraction(
        self,
        extraction,
        message: Message,
        sequence_index: int
    ) -> Optional[Signal]:
        """
        Create a Signal object from an extraction result.
        
        Args:
            extraction: Extraction result from LLM
            message: Source message
            sequence_index: Position in conversation
            
        Returns:
            Signal object (not saved) or None if invalid
        """
        try:
            # Validate signal type
            if not self._is_valid_signal_type(extraction.type):
                logger.warning(
                    "invalid_signal_type",
                    extra={
                        "signal_type": extraction.type,
                        "message_id": str(message.id),
                        "thread_id": str(message.thread_id),
                    },
                )
                return None
            
            # Generate embedding
            embedding_vector = self.embedding_service.encode(
                extraction.text,
                convert_to_numpy=True
            )
            
            # Create signal (not yet saved)
            signal = Signal(
                # Core fields
                text=extraction.text,
                type=extraction.type,
                normalized_text=normalize_text(extraction.text),
                confidence=extraction.confidence,
                
                # Positioning
                sequence_index=sequence_index,
                
                # Embedding
                embedding=embedding_vector.tolist(),  # Convert numpy to list
                
                # Deduplication (exact-match fast path)
                dedupe_key=generate_dedupe_key(
                    extraction.type,
                    normalize_text(extraction.text),
                    scope_hint=str(message.thread_id)
                ),
                
                # Relationships
                thread=message.thread,
                # case linked later when case is opened
                # event linked in the workflow after event is created
                
                # Span tracking
                span={
                    'message_id': str(message.id),
                    'start': extraction.span.start if extraction.span else 0,
                    'end': extraction.span.end if extraction.span else len(message.content),
                },
            )
            return signal
            
        except Exception:
            # Log but don't fail the whole batch
            logger.exception(
                "signal_creation_failed",
                extra={
                    "message_id": str(message.id),
                    "thread_id": str(message.thread_id),
                    "signal_type": getattr(extraction, "type", None),
                },
            )
            return None
    
    def _build_batch_extraction_prompt(self, messages: List[Message], thread) -> str:
        """Build prompt for batch extraction from multiple messages"""
        from apps.signals.prompts import get_batch_signal_extraction_prompt
        
        # Format messages with indices
        formatted_messages = []
        for i, msg in enumerate(messages):
            formatted_messages.append({
                'index': i,
                'content': msg.content,
                'timestamp': msg.created_at.isoformat()
            })
        
        return get_batch_signal_extraction_prompt(
            messages=formatted_messages,
            thread_context=thread.title if thread else ""
        )
    
    async def extract_from_message(
        self,
        message: Message,
        context_messages: Optional[List[Message]] = None,
        sequence_index: int = 0,
    ) -> List[Signal]:
        """
        Extract signals from a user message using PydanticAI
        
        Args:
            message: The user message to extract from
            context_messages: Previous messages for context (last 3-5)
            sequence_index: Position in conversation (0, 1, 2...)
            
        Returns:
            List of Signal objects (not yet saved to DB)
        """
        
        # 1. Build extraction prompt
        conversation_context = self._format_conversation_context(context_messages)
        prompt = get_signal_extraction_prompt(
            user_message=message.content,
            conversation_context=conversation_context
        )
        
        # 2. Call LLM via PydanticAI (handles parsing, validation, retries)
        try:
            result = await self._extraction_agent.run(prompt)
            extracted_signals = result.data.signals
        except Exception:
            logger.exception(
                "signal_extraction_failed",
                extra={"message_id": str(message.id), "thread_id": str(message.thread_id)},
            )
            return []
        
        if not extracted_signals:
            return []
        
        # 3. Create Signal objects with embeddings
        signals = []
        for extraction in extracted_signals:
            try:
                # Validate signal type
                if not self._is_valid_signal_type(extraction.type):
                    logger.warning(
                        "invalid_signal_type",
                        extra={
                            "signal_type": extraction.type,
                            "message_id": str(message.id),
                            "thread_id": str(message.thread_id),
                        },
                    )
                    continue
                
                # Generate embedding
                embedding_vector = self.embedding_service.encode(
                    extraction.text,
                    convert_to_numpy=True
                )
                
                # Create signal (not yet saved)
                signal = Signal(
                    # Core fields
                    text=extraction.text,
                    type=extraction.type,
                    normalized_text=normalize_text(extraction.text),
                    confidence=extraction.confidence,
                    
                    # Positioning
                    sequence_index=sequence_index,
                    
                    # Embedding
                    embedding=embedding_vector.tolist(),  # Convert numpy to list
                    
                    # Deduplication (exact-match fast path)
                    dedupe_key=generate_dedupe_key(
                        extraction.type,
                        normalize_text(extraction.text),
                        scope_hint=str(message.thread_id)
                    ),
                    
                    # Relationships
                    thread=message.thread,
                    # case linked later when case is opened
                    # event linked in the workflow after event is created
                    
                    # Span tracking
                    span={
                        'message_id': str(message.id),
                        'start': extraction.span.start if extraction.span else 0,
                        'end': extraction.span.end if extraction.span else len(message.content),
                    },
                )
                signals.append(signal)
                
            except Exception:
                # Log but don't fail the whole batch
                logger.exception(
                    "signal_creation_failed",
                    extra={
                        "message_id": str(message.id),
                        "thread_id": str(message.thread_id),
                        "signal_type": getattr(extraction, "type", None),
                    },
                )
                continue
        
        return signals
    
    def _format_conversation_context(
        self,
        messages: Optional[List[Message]]
    ) -> str:
        """Format previous messages as context string"""
        
        if not messages:
            return ""
        
        # Last 3-5 messages
        recent = messages[-5:] if len(messages) > 5 else messages
        
        context_lines = []
        for msg in recent:
            role = msg.role.upper()
            content = msg.content[:200]  # Truncate long messages
            if len(msg.content) > 200:
                content += "..."
            context_lines.append(f"{role}: {content}")
        
        return "\n".join(context_lines)
    
    def _is_valid_signal_type(self, signal_type: str) -> bool:
        """
        Validate that the extracted signal type is valid
        
        PydanticAI handles most validation, but we still need to ensure
        the type matches our Django model choices.
        """
        valid_types = [choice[0] for choice in SignalType.choices]
        return signal_type in valid_types


        return signal_type in valid_types
    
    def should_extract(self, message: Message) -> bool:
        """
        Decide if we should extract from this message
        
        Heuristics:
        - Case is open (always extract substantive messages)
        - Contains decision/epistemic keywords
        - Message is substantive (>20 chars)
        - Skip trivial messages
        """
        
        # Always extract if case is linked (we're in "serious mode")
        if message.thread.primary_case:
            return len(message.content) > 10
        
        # Check for decision/epistemic keywords
        decision_keywords = [
            'should', 'choose', 'decide', 'deciding',
            'assume', 'assumption', 'assumptions',
            'constraint', 'constraints', 'deadline',
            'goal', 'goals', 'objective',
            'question', 'questions', 'concern', 'concerns',
            'worry', 'worried', 'risk', 'risks',
            'uncertain', 'not sure', 'wondering',
            'tradeoff', 'trade-off',
        ]
        
        content_lower = message.content.lower()
        if any(kw in content_lower for kw in decision_keywords):
            return True
        
        # Skip very short messages (likely acknowledgments)
        if len(message.content) < 20:
            return False
        
        # Skip social pleasantries
        pleasantries = ['thanks', 'thank you', 'ok', 'okay', 'got it', 'sounds good']
        if message.content.lower().strip() in pleasantries:
            return False
        
        # Default: extract if substantive
        return len(message.content) > 30


# Singleton instance (caches embedding model)
_extractor_instance = None


def get_extractor() -> SignalExtractor:
    """Get or create singleton extractor instance"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = SignalExtractor()
    return _extractor_instance


# Alias for consistency with other modules
get_signal_extractor = get_extractor
