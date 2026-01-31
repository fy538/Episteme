"""
Event service - append events to the event store
"""
import uuid
from typing import Dict, Any, Optional
from django.utils import timezone
from django.db import transaction

from .models import Event, ActorType, EventType
from apps.common.exceptions import EventAppendError, InvalidEventPayload


class EventService:
    """
    Service for appending events to the event store
    
    This is the ONLY way to create events in the system.
    Never create Event objects directly.
    """
    
    @staticmethod
    def append(
        event_type: EventType,
        payload: Dict[str, Any],
        actor_type: ActorType = ActorType.SYSTEM,
        actor_id: Optional[uuid.UUID] = None,
        correlation_id: Optional[uuid.UUID] = None,
        case_id: Optional[uuid.UUID] = None,
        thread_id: Optional[uuid.UUID] = None,
    ) -> Event:
        """
        Append a new event to the event store
        
        Args:
            event_type: Type of event
            payload: Event-specific data (must be JSON-serializable)
            actor_type: Who/what caused this event
            actor_id: ID of the actor (user ID, etc.)
            correlation_id: Groups related events in a workflow
            case_id: Associated case (if any)
            thread_id: Associated thread (if any)
        
        Returns:
            The created Event
        
        Raises:
            InvalidEventPayload: If payload is invalid
            EventAppendError: If append fails
        """
        try:
            # Validate payload is JSON-serializable
            if not isinstance(payload, dict):
                raise InvalidEventPayload("Payload must be a dictionary")
            
            # Create the event
            event = Event.objects.create(
                type=event_type,
                payload=payload,
                actor_type=actor_type,
                actor_id=actor_id,
                correlation_id=correlation_id,
                case_id=case_id,
                thread_id=thread_id,
            )
            
            return event
            
        except Exception as e:
            raise EventAppendError(f"Failed to append event: {str(e)}")
    
    @staticmethod
    def get_case_timeline(case_id: uuid.UUID, limit: int = 100) -> list:
        """
        Get all events for a case, ordered by time
        
        Args:
            case_id: Case ID
            limit: Maximum number of events to return
        
        Returns:
            List of Event objects
        """
        return list(
            Event.objects
            .filter(case_id=case_id)
            .order_by('timestamp')[:limit]
        )
    
    @staticmethod
    def get_thread_timeline(thread_id: uuid.UUID, limit: int = 100) -> list:
        """
        Get all events for a thread, ordered by time
        
        Args:
            thread_id: Thread ID
            limit: Maximum number of events to return
        
        Returns:
            List of Event objects
        """
        return list(
            Event.objects
            .filter(thread_id=thread_id)
            .order_by('timestamp')[:limit]
        )
    
    @staticmethod
    def get_workflow_events(correlation_id: uuid.UUID) -> list:
        """
        Get all events in a workflow (by correlation_id)
        
        Args:
            correlation_id: Correlation ID
        
        Returns:
            List of Event objects
        """
        return list(
            Event.objects
            .filter(correlation_id=correlation_id)
            .order_by('timestamp')
        )
