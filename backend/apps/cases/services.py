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
            'user_confidence': case.user_confidence,
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
    
    @classmethod
    @transaction.atomic
    def create_case_from_analysis(
        cls,
        user: User,
        analysis: dict,
        thread_id: uuid.UUID,
        correlation_id: uuid.UUID,
        user_edits: Optional[dict] = None
    ) -> tuple[Case, 'CaseDocument', list]:
        """
        Create case with pre-populated content from conversation analysis.
        Auto-creates inquiries from questions.
        Emits events for full provenance chain.
        
        Args:
            user: User creating the case
            analysis: AI analysis from analyze_for_case
            thread_id: Thread where conversation happened
            correlation_id: Links to CONVERSATION_ANALYZED event
            user_edits: Optional user overrides (title, etc.)
        
        Returns:
            Tuple of (case, brief, inquiries)
        """
        from apps.cases.document_service import CaseDocumentService
        from apps.inquiries.services import InquiryService
        from apps.inquiries.models import ElevationReason
        
        # Apply user edits
        title = user_edits.get('title') if user_edits else analysis['suggested_title']
        position = analysis['position_draft']
        
        # Create case (emits CASE_CREATED event internally)
        case, _ = cls.create_case(
            user=user,
            title=title,
            position=position,
            thread_id=thread_id
        )
        
        # Emit analysis-based creation event
        EventService.append(
            event_type=EventType.CASE_CREATED_FROM_ANALYSIS,
            payload={
                'analysis': analysis,
                'user_edits': user_edits or {},
                'acceptance_metrics': {
                    'title_accepted': title == analysis['suggested_title'],
                    'questions_count': len(analysis.get('key_questions', [])),
                    'assumptions_count': len(analysis.get('assumptions', []))
                }
            },
            actor_type=ActorType.USER,
            actor_id=user.id,
            case_id=case.id,
            thread_id=thread_id,
            correlation_id=correlation_id
        )
        
        # Pre-populate brief with analysis content
        brief_content = f"""# {title}

## Background
{analysis.get('background_summary', '')}

## Current Position
{position}

## Key Assumptions
{chr(10).join(f"- {a}" for a in analysis.get('assumptions', []))}

## Open Questions
{chr(10).join(f"- {q}" for q in analysis.get('key_questions', []))}

---
*Auto-generated from conversation. Edit freely.*
"""
        
        # Update the brief that was auto-created
        brief = case.main_brief
        if brief:
            brief.content_markdown = brief_content
            
            # Store assumptions as metadata for highlighting
            if analysis.get('assumptions'):
                brief.ai_structure = {
                    'assumptions': [
                        {
                            'text': a,
                            'status': 'untested',
                            'risk_level': 'medium',
                            'source': 'conversation_analysis'
                        }
                        for a in analysis['assumptions']
                    ]
                }
            brief.save()
        
        # Auto-create inquiries from questions
        inquiries = []
        for question in analysis.get('key_questions', []):
            inquiry = InquiryService.create_inquiry(
                case=case,
                title=question,
                elevation_reason=ElevationReason.USER_CREATED,
                description="Auto-created from conversation analysis"
            )
            inquiries.append(inquiry)
        
        # Emit inquiry auto-creation event
        if inquiries:
            EventService.append(
                event_type=EventType.INQUIRIES_AUTO_CREATED,
                payload={
                    'inquiry_ids': [str(i.id) for i in inquiries],
                    'source': 'conversation_analysis',
                    'questions': analysis.get('key_questions', [])
                },
                actor_type=ActorType.ASSISTANT,
                case_id=case.id,
                correlation_id=correlation_id
            )
        
        return case, brief, inquiries
