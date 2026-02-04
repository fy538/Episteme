"""
Post-processing handlers for unified analysis

Handles saving messages, reflections, and signals after stream completes.
"""

import json
import uuid
import logging
import hashlib
from typing import Dict, List, Optional, Any, Set
from django.utils import timezone
from django.db import transaction

from apps.events.services import EventService
from apps.events.models import EventType, ActorType

logger = logging.getLogger(__name__)

# Valid signal types - used for validation
VALID_SIGNAL_TYPES = {
    'assumption', 'claim', 'question', 'evidence', 'constraint',
    'goal', 'decisionintent', 'decision', 'risk', 'opportunity',
    'stakeholder', 'resource', 'dependency', 'milestone', 'metric'
}


class UnifiedAnalysisHandler:
    """
    Handles post-processing after unified analysis stream completes.

    Responsibilities:
    1. Save assistant message to DB
    2. Save reflection to DB
    3. Parse and save signals to DB
    4. Emit completion events
    5. Trigger async tasks (embeddings, etc.)
    """

    @staticmethod
    async def handle_completion(
        thread,
        user,
        response_content: str,
        reflection_content: str,
        signals_json: str,
        model_key: str,
        extraction_was_enabled: bool = True,
        correlation_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Handle completion of unified analysis.

        Args:
            thread: ChatThread object
            user: User object
            response_content: Full assistant response text
            reflection_content: Full reflection text
            signals_json: JSON string of extracted signals
            model_key: Model used for generation
            extraction_was_enabled: Whether signal extraction was enabled
            correlation_id: Optional correlation ID for event tracking

        Returns:
            Dict with created object IDs
        """
        from asgiref.sync import sync_to_async
        from apps.chat.services import ChatService
        from apps.companion.models import Reflection, ReflectionTriggerType

        result = {
            'message_id': None,
            'reflection_id': None,
            'signals_count': 0,
            'signal_ids': []
        }

        correlation_id = correlation_id or uuid.uuid4()

        # 1. Save assistant message
        try:
            assistant_message = await sync_to_async(ChatService.create_assistant_message)(
                thread_id=thread.id,
                content=response_content,
                metadata={
                    'model': model_key,
                    'unified_stream': True,
                    'streamed': True
                }
            )
            result['message_id'] = str(assistant_message.id)
            logger.info(f"Saved assistant message: {assistant_message.id}")
        except Exception as e:
            logger.exception(f"Failed to save assistant message: {e}")
            raise

        # 2. Save reflection
        if reflection_content.strip():
            try:
                # Get recent message IDs for tracking
                from apps.chat.models import Message
                recent_messages = await sync_to_async(list)(
                    Message.objects.filter(thread=thread)
                    .order_by('-created_at')[:5]
                    .values_list('id', flat=True)
                )

                reflection = await sync_to_async(Reflection.objects.create)(
                    thread=thread,
                    reflection_text=reflection_content.strip(),
                    trigger_type=ReflectionTriggerType.USER_MESSAGE,
                    analyzed_messages=[str(mid) for mid in recent_messages],
                    analyzed_signals=[],
                    patterns={}
                )
                result['reflection_id'] = str(reflection.id)
                logger.info(f"Saved reflection: {reflection.id}")
            except Exception as e:
                logger.exception(f"Failed to save reflection: {e}")
                # Non-fatal - continue

        # 3. Parse and save signals
        if extraction_was_enabled and signals_json.strip():
            try:
                signals = json.loads(signals_json.strip())
                if isinstance(signals, list) and signals:
                    saved_signals = await UnifiedAnalysisHandler._save_signals(
                        thread=thread,
                        message=assistant_message,
                        signals=signals,
                        correlation_id=correlation_id
                    )
                    result['signals_count'] = len(saved_signals)
                    result['signal_ids'] = [str(s.id) for s in saved_signals]
                    logger.info(f"Saved {len(saved_signals)} signals")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse signals JSON: {e}")
            except Exception as e:
                logger.exception(f"Failed to save signals: {e}")
                # Non-fatal - continue

        # 4. Emit completion event
        try:
            await sync_to_async(EventService.append)(
                event_type=EventType.WORKFLOW_COMPLETED,
                payload={
                    'workflow_type': 'unified_analysis',
                    'thread_id': str(thread.id),
                    'message_id': result['message_id'],
                    'reflection_id': result['reflection_id'],
                    'signals_count': result['signals_count'],
                    'model': model_key
                },
                actor_type=ActorType.ASSISTANT,
                correlation_id=correlation_id,
                thread_id=thread.id
            )
        except Exception as e:
            logger.warning(f"Failed to emit completion event: {e}")

        # 5. Trigger async tasks for signal embeddings
        if result['signal_ids']:
            try:
                # Import here to avoid circular imports
                from tasks.workflows import generate_signal_embeddings
                generate_signal_embeddings.delay(result['signal_ids'])
                logger.info(f"Triggered embedding generation for {len(result['signal_ids'])} signals")
            except Exception as e:
                logger.warning(f"Failed to trigger embedding task: {e}")

        # 6. Update thread extraction state for future extraction decisions
        if extraction_was_enabled:
            try:
                from apps.chat.models import Message
                from .extraction_rules import ExtractionRulesEngine

                message_count = await sync_to_async(
                    Message.objects.filter(thread=thread).count
                )()
                total_chars = len(response_content) + len(reflection_content)

                await sync_to_async(ExtractionRulesEngine.update_thread_extraction_state)(
                    thread=thread,
                    current_turn=message_count,
                    current_chars=total_chars,
                    extracted=result['signals_count'] > 0
                )
            except Exception as e:
                logger.warning(f"Failed to update extraction state: {e}")

        return result

    @staticmethod
    async def _save_signals(
        thread,
        message,
        signals: List[Dict],
        correlation_id: uuid.UUID
    ) -> List:
        """
        Save extracted signals to database.

        Args:
            thread: ChatThread object
            message: Message object the signals came from
            signals: List of signal dicts from LLM
            correlation_id: Correlation ID for events

        Returns:
            List of created Signal objects
        """
        from asgiref.sync import sync_to_async
        from apps.signals.models import Signal, SignalSourceType

        if not signals:
            return []

        # Get current message count for sequence_index base
        from apps.chat.models import Message
        message_count = await sync_to_async(
            Message.objects.filter(thread=thread).count
        )()

        # Pre-compute dedupe keys for all signals (batch approach)
        signal_dedupe_data = []
        for signal_data in signals:
            signal_type = signal_data.get('type', 'Claim')
            signal_text = signal_data.get('text', '').strip()

            if not signal_text:
                continue

            # Validate and normalize signal type
            signal_type_lower = signal_type.lower()
            if signal_type_lower not in VALID_SIGNAL_TYPES:
                logger.warning(f"Unknown signal type '{signal_type}', defaulting to 'Claim'")
                signal_type = 'Claim'

            dedupe_key = hashlib.sha256(
                f"{signal_type}:{signal_text.lower()}".encode()
            ).hexdigest()[:64]

            signal_dedupe_data.append({
                'data': signal_data,
                'type': signal_type,
                'text': signal_text,
                'dedupe_key': dedupe_key,
                'confidence': float(signal_data.get('confidence', 0.7))
            })

        if not signal_dedupe_data:
            return []

        # Batch query to find existing signals (avoid N+1)
        all_dedupe_keys = [s['dedupe_key'] for s in signal_dedupe_data]
        existing_keys: Set[str] = set(
            await sync_to_async(list)(
                Signal.objects.filter(
                    thread=thread,
                    dedupe_key__in=all_dedupe_keys,
                    dismissed_at__isnull=True
                ).values_list('dedupe_key', flat=True)
            )
        )

        # Get case ID safely (ForeignKey always exists, check if set)
        case_id = thread.primary_case_id if thread.primary_case_id else None

        # Save signals in a transaction
        @sync_to_async
        @transaction.atomic
        def save_signals_batch():
            saved = []
            for idx, signal_info in enumerate(signal_dedupe_data):
                if signal_info['dedupe_key'] in existing_keys:
                    logger.debug(f"Skipping duplicate signal: {signal_info['text'][:50]}")
                    continue

                try:
                    # Create event for signal
                    event = EventService.append(
                        event_type=EventType.SIGNAL_EXTRACTED,
                        payload={
                            'type': signal_info['type'],
                            'text': signal_info['text'],
                            'confidence': signal_info['confidence'],
                            'source': 'unified_analysis',
                            'message_id': str(message.id) if message else None
                        },
                        actor_type=ActorType.ASSISTANT,
                        correlation_id=correlation_id,
                        thread_id=thread.id,
                        case_id=case_id
                    )

                    # Create signal with unique sequence_index
                    signal = Signal.objects.create(
                        event=event,
                        source_type=SignalSourceType.CHAT_MESSAGE,
                        type=signal_info['type'],
                        text=signal_info['text'],
                        normalized_text=signal_info['text'].lower().strip(),
                        span={'message_id': str(message.id) if message else None},
                        confidence=signal_info['confidence'],
                        sequence_index=message_count * 100 + idx,  # Unique per signal
                        dedupe_key=signal_info['dedupe_key'],
                        thread=thread,
                        case_id=case_id
                    )

                    saved.append(signal)

                except Exception as e:
                    logger.warning(f"Failed to save signal '{signal_info['text'][:50]}': {e}")
                    continue

            return saved

        saved_signals = await save_signals_batch()
        return saved_signals
