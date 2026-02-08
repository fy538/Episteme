"""
Event service - append events to the event store
"""
import uuid
from typing import Dict, Any, Optional
from django.utils import timezone
from django.db import transaction

from .models import Event, ActorType, EventType, EventCategory
from apps.common.exceptions import EventAppendError, InvalidEventPayload


# Event types classified as operational (not shown in timeline)
OPERATIONAL_EVENT_TYPES = {
    EventType.USER_MESSAGE_CREATED,
    EventType.ASSISTANT_MESSAGE_CREATED,
    EventType.CASE_PATCHED,
    EventType.CASE_LINKED_TO_THREAD,
    EventType.AGENT_WORKFLOW_STARTED,
    EventType.AGENT_PROGRESS,
    EventType.AGENT_COMPLETED,
    EventType.AGENT_FAILED,
    EventType.AGENT_CHECKPOINT,
    EventType.AGENT_TRAJECTORY,
    EventType.WORKFLOW_STARTED,
    EventType.WORKFLOW_COMPLETED,
    EventType.SIGNAL_EXTRACTED,
    EventType.SIGNAL_STATUS_CHANGED,
    EventType.SIGNAL_EDITED,
    EventType.WORKING_VIEW_MATERIALIZED,
    EventType.CONVERSATION_ANALYZED_FOR_CASE,
    EventType.CONVERSATION_ANALYZED_FOR_AGENT,
    EventType.STRUCTURE_SUGGESTED,
    EventType.PLAN_DIFF_PROPOSED,
    EventType.PLAN_DIFF_ACCEPTED,
    EventType.PLAN_DIFF_REJECTED,
    EventType.PLAN_RESTORED,
}


class EventService:
    """
    Service for appending events to the event store.

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
        Append a new event to the event store.

        Category is auto-assigned based on event_type — callers don't need
        to specify it.
        """
        try:
            # Validate payload is JSON-serializable
            if not isinstance(payload, dict):
                raise InvalidEventPayload("Payload must be a dictionary")

            # Auto-denormalize case_title into payload for timeline display.
            if case_id and 'case_title' not in payload:
                try:
                    from apps.cases.models import Case
                    case_obj = Case.objects.only('title').get(id=case_id)
                    payload = {**payload, 'case_title': case_obj.title}
                except Exception:
                    pass  # Non-fatal — skip if case not found

            # Auto-assign category from event type
            category = (
                EventCategory.OPERATIONAL
                if event_type in OPERATIONAL_EVENT_TYPES
                else EventCategory.PROVENANCE
            )

            # Create the event
            event = Event.objects.create(
                type=event_type,
                category=category,
                payload=payload,
                actor_type=actor_type,
                actor_id=actor_id,
                correlation_id=correlation_id,
                case_id=case_id,
                thread_id=thread_id,
            )

            return event

        except (InvalidEventPayload, EventAppendError):
            raise
        except Exception as e:
            raise EventAppendError(f"Failed to append event: {str(e)}")

    @staticmethod
    def get_case_timeline(case_id: uuid.UUID, limit: int = 100) -> list:
        """Get provenance events for a case, ordered by time."""
        return list(
            Event.objects
            .filter(case_id=case_id, category=EventCategory.PROVENANCE)
            .order_by('-timestamp')[:limit]
        )

    @staticmethod
    def get_thread_timeline(thread_id: uuid.UUID, limit: int = 100) -> list:
        """Get all events for a thread, ordered by time."""
        return list(
            Event.objects
            .filter(thread_id=thread_id)
            .order_by('timestamp')[:limit]
        )

    @staticmethod
    def get_workflow_events(correlation_id: uuid.UUID) -> list:
        """Get all events in a workflow (by correlation_id)."""
        return list(
            Event.objects
            .filter(correlation_id=correlation_id)
            .order_by('timestamp')
        )
