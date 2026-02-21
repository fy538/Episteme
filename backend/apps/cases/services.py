"""
Case service
"""
import logging
import uuid
from typing import Optional
from django.contrib.auth.models import User
from django.db import transaction

logger = logging.getLogger(__name__)

from .models import Case, CaseStatus, StakesLevel
from apps.events.services import EventService
from apps.events.models import EventType, ActorType


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
        decision_question: str = "",
    ) -> tuple[Case, 'WorkingDocument']:
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
            decision_question: Core question being decided

        Returns:
            Tuple of (case, case_brief)
        """
        from apps.cases.document_service import WorkingDocumentService
        
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
        case, case_brief = WorkingDocumentService.create_case_with_brief(
            user=user,
            title=title,
            project_id=project_id,
            position=position,
            stakes=stakes,
            created_from_event_id=event.id,
        )
        
        # 2b. Set decision_question if provided
        if decision_question:
            case.decision_question = decision_question
            case.save(update_fields=['decision_question'])

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
        
        # Auto-pull or extract graph nodes for the case
        from django.conf import settings
        extraction_settings = getattr(settings, 'CASE_EXTRACTION_SETTINGS', {})

        if extraction_settings.get('enabled', False) and case.decision_question:
            # NEW: Dispatch async case extraction pipeline
            # Use transaction.on_commit to avoid race where Celery picks up
            # the task before the transaction creating the case has committed.
            try:
                from django.db import transaction as db_transaction
                from apps.cases.tasks import run_case_extraction_pipeline
                case.metadata = case.metadata or {}
                case.metadata['extraction_status'] = 'pending'
                case.save(update_fields=['metadata'])
                case_id_str = str(case.id)
                db_transaction.on_commit(
                    lambda: run_case_extraction_pipeline.delay(case_id_str)
                )
            except Exception:
                logger.warning(
                    "Failed to dispatch case extraction for %s, falling back to auto_pull",
                    case.id, exc_info=True,
                )
                try:
                    from apps.graph.services import GraphService
                    GraphService.auto_pull_project_nodes(case)
                except Exception:
                    logger.warning("Auto-pull fallback also failed for case %s", case.id, exc_info=True)
        else:
            # LEGACY: Pull pre-extracted project nodes by similarity
            try:
                from apps.graph.services import GraphService
                GraphService.auto_pull_project_nodes(case)
            except Exception:
                logger.warning("Auto-pull failed for case %s", case.id, exc_info=True)

        return case, case_brief

    # Fields that callers are allowed to update via update_case
    ALLOWED_UPDATE_FIELDS = frozenset({
        'title', 'position', 'stakes', 'status',
        'user_confidence', 'decision_question',
        'constraints', 'success_criteria', 'stakeholders',
        'premortem_text', 'what_would_change_mind',
    })

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

        Raises:
            Case.DoesNotExist: If case not found or not owned by user
            ValueError: If disallowed field is passed
        """
        case = Case.objects.select_for_update().get(id=case_id, user=user)

        # Reject disallowed fields
        disallowed = set(fields.keys()) - CaseService.ALLOWED_UPDATE_FIELDS
        if disallowed:
            raise ValueError(f"Cannot update fields: {', '.join(sorted(disallowed))}")

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
            # 1. Append operational CasePatched event
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

            # 2. Emit specific provenance events for key field changes
            if 'user_confidence' in changes:
                old_val = changes['user_confidence']['old']
                new_val = changes['user_confidence']['new']
                direction = 'increased' if (new_val or 0) > (old_val or 0) else 'decreased'
                EventService.append(
                    event_type=EventType.CONFIDENCE_CHANGED,
                    payload={
                        'old_value': old_val,
                        'new_value': new_val,
                        'direction': direction,
                    },
                    actor_type=ActorType.USER,
                    actor_id=user.id,
                    case_id=case.id,
                )

            if 'position' in changes and changes['position']['old']:
                EventService.append(
                    event_type=EventType.POSITION_REVISED,
                    payload={
                        'old_length': len(changes['position']['old'] or ''),
                        'new_length': len(changes['position']['new'] or ''),
                    },
                    actor_type=ActorType.USER,
                    actor_id=user.id,
                    case_id=case.id,
                )

            # 3. Save case — only write changed fields
            case.save(update_fields=list(changes.keys()) + ['updated_at'])
        
        return case

    @classmethod
    @transaction.atomic
    def create_case_from_analysis(
        cls,
        user: User,
        analysis: dict,
        thread_id: uuid.UUID,
        correlation_id: uuid.UUID,
        user_edits: Optional[dict] = None
    ) -> tuple[Case, 'WorkingDocument', list]:
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
        from apps.cases.document_service import WorkingDocumentService
        from apps.inquiries.services import InquiryService
        from apps.inquiries.models import ElevationReason
        
        # Apply user edits
        title = (user_edits.get('title') if user_edits else None) or analysis['suggested_title']
        position = analysis['position_draft']

        # Determine decision question from user_edits or analysis
        decision_question = ''
        if user_edits and 'decision_question' in user_edits:
            decision_question = user_edits['decision_question']
        elif analysis.get('suggested_question'):
            decision_question = analysis['suggested_question']

        # Resolve user-edited questions/assumptions/criteria (or fallback to analysis)
        key_questions = analysis.get('key_questions', [])
        if user_edits and 'key_questions' in user_edits:
            key_questions = user_edits['key_questions']

        assumptions = analysis.get('assumptions', [])
        if user_edits and 'assumptions' in user_edits:
            assumptions = user_edits['assumptions']

        # Create case (emits CASE_CREATED event internally)
        case, _ = cls.create_case(
            user=user,
            title=title,
            position=position,
            thread_id=thread_id,
            decision_question=decision_question,
        )

        # Transfer companion state for case extraction context
        companion_state = analysis.get('companion_state', {})
        if companion_state:
            case.metadata = case.metadata or {}
            case.metadata['companion_origin'] = companion_state
            case.save(update_fields=['metadata'])

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
        
        # Pre-populate brief with analysis content (uses resolved questions/assumptions)
        brief_content = f"""# {title}

## Background
{analysis.get('background_summary', '')}

## Current Position
{position}

## Key Assumptions
{chr(10).join(f"- {a}" for a in assumptions)}

## Open Questions
{chr(10).join(f"- {q}" for q in key_questions)}

---
*Auto-generated from conversation. Edit freely.*
"""

        # Update the brief that was auto-created
        brief = case.main_brief
        if brief:
            brief.content_markdown = brief_content

            # Store assumptions as metadata for highlighting
            if assumptions:
                brief.ai_structure = {
                    'assumptions': [
                        {
                            'text': a,
                            'status': 'untested',
                            'risk_level': 'medium',
                            'source': 'conversation_analysis'
                        }
                        for a in assumptions
                    ]
                }
            brief.save(update_fields=['content_markdown', 'ai_structure', 'updated_at'])

        # Auto-create inquiries from questions (uses resolved key_questions)
        inquiries = []
        for question in key_questions:
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

        # Create initial investigation plan
        # Override criteria in analysis if user edited them
        from apps.cases.plan_service import PlanService
        if user_edits and 'decision_criteria' in user_edits:
            analysis_for_plan = {**analysis, 'decision_criteria': user_edits['decision_criteria']}
        else:
            analysis_for_plan = analysis

        plan, _plan_version = PlanService.create_initial_plan(
            case=case,
            analysis=analysis_for_plan,
            inquiries=inquiries,
            correlation_id=correlation_id,
        )

        # Transfer companion state if available
        companion_state = analysis.get('companion_state')
        if companion_state:
            case.metadata = case.metadata or {}
            case.metadata['companion_origin'] = {
                'established': companion_state.get('established', []),
                'open_questions': companion_state.get('open_questions', []),
                'eliminated': companion_state.get('eliminated', []),
                'structure_type': companion_state.get('structure_type', ''),
                'structure_snapshot': companion_state.get('structure_snapshot', {}),
            }
            case.save(update_fields=['metadata'])

            # Transfer completed research results as working documents
            try:
                from apps.chat.models import ResearchResult
                research_results = ResearchResult.objects.filter(
                    thread_id=thread_id,
                    status='complete',
                )
                for rr in research_results:
                    research_md = f"""# Research: {rr.question}

{rr.answer}

## Sources
{chr(10).join(f"- {s.get('title', 'Source')}: {s.get('snippet', '')[:200]}" for s in rr.sources) if rr.sources else "No external sources."}

---
*Auto-researched by companion during conversation.*
"""
                    WorkingDocumentService.create_working_document(
                        case=case,
                        title=f"Research: {rr.question[:80]}",
                        content_markdown=research_md,
                    )
            except Exception:
                logger.debug("Could not transfer research results to case", exc_info=True)

        return case, brief, inquiries, plan
