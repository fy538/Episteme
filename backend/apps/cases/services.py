"""
Case service
"""
import uuid
from typing import Optional
from django.contrib.auth.models import User
from django.db import transaction

from .models import Case, CaseStatus, StakesLevel, WorkingView
from apps.events.services import EventService
from apps.events.models import EventType, ActorType, Event


class CaseService:
    """
    Service for case operations
    """
    
    @staticmethod
    @transaction.atomic
    def create_case(
        user: User,
        title: str,
        position: str = "",
        stakes: StakesLevel = StakesLevel.MEDIUM,
        thread_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,  # Phase 2
    ) -> tuple[Case, 'CaseDocument']:
        """
        Create a new case with auto-generated brief.
        
        Phase 2A: Now creates case brief automatically.
        
        Args:
            user: User creating the case
            title: Case title
            position: Initial position text
            stakes: Stakes level
            thread_id: Optional linked thread
            project_id: Optional project
        
        Returns:
            Tuple of (case, case_brief)
        """
        from apps.cases.document_service import CaseDocumentService
        
        # Generate correlation ID for this workflow
        correlation_id = uuid.uuid4()
        
        # 1. Append CaseCreated event
        event = EventService.append(
            event_type=EventType.CASE_CREATED,
            payload={
                'title': title,
                'position': position,
                'stakes': stakes,
                'thread_id': str(thread_id) if thread_id else None,
            },
            actor_type=ActorType.USER,
            actor_id=user.id,
            correlation_id=correlation_id,
            thread_id=thread_id,
        )
        
        # 2. Create case with brief (Phase 2A)
        case, case_brief = CaseDocumentService.create_case_with_brief(
            user=user,
            title=title,
            project_id=project_id,
            position=position,
            stakes=stakes,
            linked_thread_id=thread_id,
            created_from_event_id=event.id,
        )
        
        # 3. If linked to thread, emit linking event
        if thread_id:
            EventService.append(
                event_type=EventType.CASE_LINKED_TO_THREAD,
                payload={
                    'case_id': str(case.id),
                    'thread_id': str(thread_id),
                    'brief_id': str(case_brief.id),
                },
                actor_type=ActorType.SYSTEM,
                correlation_id=correlation_id,
                case_id=case.id,
                thread_id=thread_id,
            )
        
        return case, case_brief
    
    @staticmethod
    @transaction.atomic
    def update_case(
        case_id: uuid.UUID,
        user: User,
        **fields
    ) -> Case:
        """
        Update case fields
        
        Args:
            case_id: Case to update
            user: User making the update
            **fields: Fields to update (position, stakes, confidence, status)
        
        Returns:
            Updated Case
        """
        case = Case.objects.get(id=case_id)
        
        # Track what changed
        changes = {}
        for field, value in fields.items():
            if hasattr(case, field) and getattr(case, field) != value:
                changes[field] = {
                    'old': getattr(case, field),
                    'new': value
                }
                setattr(case, field, value)
        
        if changes:
            # 1. Append CasePatched event
            EventService.append(
                event_type=EventType.CASE_PATCHED,
                payload={
                    'case_id': str(case.id),
                    'changes': changes,
                },
                actor_type=ActorType.USER,
                actor_id=user.id,
                case_id=case.id,
            )
            
            # 2. Save case
            case.save()
        
        return case
    
    @staticmethod
    def refresh_working_view(case_id: uuid.UUID) -> WorkingView:
        """
        Create a new WorkingView snapshot for a case (Phase 1)
        
        Args:
            case_id: Case to snapshot
        
        Returns:
            Created WorkingView
        """
        case = Case.objects.get(id=case_id)
        
        # Get latest event affecting this case
        latest_event = Event.objects.filter(case_id=case_id).order_by('-timestamp').first()
        
        if not latest_event:
            # No events yet, use case creation event
            latest_event_id = case.created_from_event_id
        else:
            latest_event_id = latest_event.id
        
        # Check if we already have an up-to-date view
        last_view = case.working_views.first()
        if last_view and last_view.based_on_event_id == latest_event_id:
            return last_view
        
        # Build summary (Phase 1 will include signals)
        summary = {
            'title': case.title,
            'position': case.position,
            'stakes': case.stakes,
            'confidence': case.confidence,
            'status': case.status,
            # Phase 1: Add signals here
            'assumptions': [],
            'questions': [],
            'constraints': [],
        }
        
        # Create new snapshot
        working_view = WorkingView.objects.create(
            case=case,
            summary_json=summary,
            based_on_event_id=latest_event_id,
        )
        
        # Emit event
        EventService.append(
            event_type=EventType.WORKING_VIEW_MATERIALIZED,
            payload={
                'case_id': str(case.id),
                'working_view_id': str(working_view.id),
            },
            actor_type=ActorType.SYSTEM,
            case_id=case.id,
        )
        
        return working_view
