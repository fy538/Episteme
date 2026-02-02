"""
Service for triggering proactive interventions based on detected patterns
"""
import logging
from typing import List, Optional
from .models import ChatThread, Message
from .pattern_detection import PatternDetectionEngine
from .card_builders import CardBuilder
from .services import ChatService

logger = logging.getLogger(__name__)


class InterventionService:
    """Handles proactive interventions in conversations"""
    
    # Intervention cooldown (don't spam user with suggestions)
    INTERVENTION_COOLDOWN_TURNS = 3
    
    @classmethod
    def should_intervene(cls, thread: ChatThread) -> bool:
        """
        Check if enough turns have passed since last intervention
        
        Returns:
            True if we should check for interventions
        """
        # Check metadata for last intervention turn
        last_intervention_turn = thread.metadata.get('last_intervention_turn', 0)
        current_turn = thread.messages.count()
        
        return (current_turn - last_intervention_turn) >= cls.INTERVENTION_COOLDOWN_TURNS
    
    @classmethod
    def check_and_intervene(cls, thread: ChatThread) -> Optional[Message]:
        """
        Check for patterns and create intervention card if appropriate
        
        Args:
            thread: ChatThread to check
            
        Returns:
            Created intervention message or None
        """
        # Don't intervene too frequently
        if not cls.should_intervene(thread):
            logger.debug(f"Skipping intervention for thread {thread.id} - cooldown active")
            return None
        
        # Detect patterns
        patterns = PatternDetectionEngine.analyze_thread(thread)
        
        if not patterns:
            logger.debug(f"No patterns detected for thread {thread.id}")
            return None
        
        # Get highest confidence pattern
        top_pattern = patterns[0]
        
        logger.info(
            "pattern_detected",
            extra={
                "thread_id": str(thread.id),
                "pattern_type": top_pattern['pattern_type'],
                "confidence": top_pattern['confidence']
            }
        )
        
        # Check if we've already suggested this
        dismissed_suggestions = thread.metadata.get('dismissed_suggestions', [])
        if top_pattern['pattern_type'] in dismissed_suggestions:
            logger.debug(f"Pattern {top_pattern['pattern_type']} was previously dismissed")
            return None
        
        # Create appropriate intervention card
        intervention_message = None
        
        if top_pattern['pattern_type'] == 'multiple_questions':
            intervention_message = cls._create_organize_questions_card(thread, top_pattern)
        
        elif top_pattern['pattern_type'] == 'unvalidated_assumptions':
            intervention_message = cls._create_validate_assumptions_card(thread, top_pattern)
        
        elif top_pattern['pattern_type'] == 'case_structure':
            intervention_message = cls._create_case_suggestion_card(thread, top_pattern)
        
        elif top_pattern['pattern_type'] == 'high_signal_density':
            intervention_message = cls._create_organize_signals_card(thread, top_pattern)
        
        # Update thread metadata
        if intervention_message:
            current_turn = thread.messages.count()
            thread.metadata['last_intervention_turn'] = current_turn
            thread.metadata['last_intervention_type'] = top_pattern['pattern_type']
            thread.save(update_fields=['metadata'])
            
            logger.info(
                "intervention_created",
                extra={
                    "thread_id": str(thread.id),
                    "message_id": str(intervention_message.id),
                    "pattern_type": top_pattern['pattern_type']
                }
            )
        
        return intervention_message
    
    @classmethod
    def _create_organize_questions_card(
        cls,
        thread: ChatThread,
        pattern: dict
    ) -> Message:
        """Create action prompt card for organizing questions"""
        card_data = CardBuilder.build_action_prompt_card(
            prompt_type='organize_questions',
            detected_context=pattern
        )
        
        return ChatService.create_rich_message(
            thread_id=thread.id,
            content_type='card_action_prompt',
            structured_content=card_data,
            fallback_text=f"You've asked {pattern['question_count']} questions - would you like to organize them into an inquiry?",
            metadata={'pattern_detection': pattern}
        )
    
    @classmethod
    def _create_validate_assumptions_card(
        cls,
        thread: ChatThread,
        pattern: dict
    ) -> Message:
        """Create action prompt card for validating assumptions"""
        card_data = CardBuilder.build_action_prompt_card(
            prompt_type='validate_assumptions',
            detected_context=pattern
        )
        
        return ChatService.create_rich_message(
            thread_id=thread.id,
            content_type='card_action_prompt',
            structured_content=card_data,
            fallback_text=f"I noticed {pattern['assumption_count']} assumptions - would you like me to help validate them?",
            metadata={'pattern_detection': pattern}
        )
    
    @classmethod
    def _create_case_suggestion_card(
        cls,
        thread: ChatThread,
        pattern: dict
    ) -> Message:
        """Create action prompt card for case creation"""
        card_data = CardBuilder.build_action_prompt_card(
            prompt_type='create_case',
            detected_context=pattern
        )
        
        return ChatService.create_rich_message(
            thread_id=thread.id,
            content_type='card_action_prompt',
            structured_content=card_data,
            fallback_text="Your conversation has enough structure to create a case - would you like to?",
            metadata={'pattern_detection': pattern}
        )
    
    @classmethod
    def _create_organize_signals_card(
        cls,
        thread: ChatThread,
        pattern: dict
    ) -> Message:
        """Create action prompt card for organizing high signal density"""
        card_data = CardBuilder.build_action_prompt_card(
            prompt_type='organize_questions',  # Reuse this for now
            detected_context=pattern
        )
        
        return ChatService.create_rich_message(
            thread_id=thread.id,
            content_type='card_action_prompt',
            structured_content=card_data,
            fallback_text=f"I've detected {pattern['signal_count']} signals in this conversation - let's organize them!",
            metadata={'pattern_detection': pattern}
        )
    
    @classmethod
    def dismiss_suggestion(cls, thread: ChatThread, suggestion_type: str) -> None:
        """
        Mark a suggestion type as dismissed for this thread
        
        Args:
            thread: ChatThread
            suggestion_type: Type of suggestion to dismiss
        """
        dismissed = thread.metadata.get('dismissed_suggestions', [])
        if suggestion_type not in dismissed:
            dismissed.append(suggestion_type)
            thread.metadata['dismissed_suggestions'] = dismissed
            thread.save(update_fields=['metadata'])
            
            logger.info(
                "suggestion_dismissed",
                extra={
                    "thread_id": str(thread.id),
                    "suggestion_type": suggestion_type
                }
            )
