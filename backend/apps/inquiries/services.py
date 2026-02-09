"""
Business logic for inquiry management
"""
import uuid
from typing import Optional
from django.utils import timezone
from django.db.models import Count
from django.contrib.auth.models import User
from django.db import transaction

from apps.inquiries.models import Inquiry, ElevationReason, InquiryStatus
from apps.cases.models import Case
from apps.events.services import EventService
from apps.events.models import EventType, ActorType


MAX_INQUIRY_TITLE_LEN = 100


class InquiryService:
    """Service for managing inquiries and auto-promotion logic"""
    
    @classmethod
    @transaction.atomic
    def create_inquiry(
        cls,
        case: Case,
        title: str,
        elevation_reason: ElevationReason = ElevationReason.USER_CREATED,
        description: str = "",
        source: str = "manual",
        user: Optional[User] = None,
        origin_signal_id: Optional[uuid.UUID] = None,
        origin_text: Optional[str] = None,
        origin_document_id: Optional[uuid.UUID] = None
    ) -> Inquiry:
        """
        Create inquiry with event tracking.
        
        Args:
            case: Case this inquiry belongs to
            title: Inquiry title/question
            elevation_reason: Why created
            description: Additional context
            source: How created (manual, signal_promotion, conversation_analysis, etc.)
            user: User who created (if applicable)
            origin_signal_id: Source signal if promoted
            origin_text: Selected text if from inline creation
            origin_document_id: Source document if from inline creation
        
        Returns:
            Created Inquiry
        """
        # Get next sequence index
        last_inquiry = Inquiry.objects.filter(case=case).order_by('-sequence_index').first()
        sequence_index = (last_inquiry.sequence_index + 1) if last_inquiry else 0
        
        # Create inquiry
        inquiry = Inquiry.objects.create(
            case=case,
            title=title,
            elevation_reason=elevation_reason,
            description=description,
            origin_text=origin_text,
            origin_document_id=origin_document_id,
            sequence_index=sequence_index,
            status=InquiryStatus.OPEN
        )
        
        # Emit event (store event_id if field exists)
        event = EventService.append(
            event_type=EventType.INQUIRY_CREATED,
            payload={
                'inquiry_id': str(inquiry.id),
                'case_id': str(case.id),
                'title': title,
                'elevation_reason': elevation_reason,
                'source': source,
                'origin_signal_id': str(origin_signal_id) if origin_signal_id else None,
                'origin_text': origin_text,
                'sequence_index': sequence_index
            },
            actor_type=ActorType.USER if user else ActorType.SYSTEM,
            actor_id=user.id if user else None,
            case_id=case.id,
            thread_id=None  # Case no longer has linked_thread
        )
        
        # Link event to inquiry if field exists (graceful handling for pre-migration)
        if hasattr(inquiry, 'created_from_event_id'):
            inquiry.created_from_event_id = event.id
            inquiry.save(update_fields=['created_from_event_id'])
        
        return inquiry
    
    @staticmethod
    def create_inquiry_with_brief(case: Case, title: str, user: User, elevation_reason: str = 'user_created'):
        """
        Create inquiry with auto-generated brief (Phase 2A).
        
        Args:
            case: Case this inquiry belongs to
            title: Inquiry title
            user: User creating inquiry
            elevation_reason: Why inquiry was created
        
        Returns:
            Tuple of (inquiry, inquiry_brief)
        """
        from apps.cases.document_service import WorkingDocumentService
        
        return WorkingDocumentService.create_inquiry_with_brief(
            case=case,
            title=title,
            user=user,
            elevation_reason=elevation_reason
        )
    
    @classmethod
    @transaction.atomic
    def resolve_inquiry(
        cls,
        inquiry: Inquiry,
        conclusion: str,
        conclusion_confidence: Optional[float] = None,
        user: Optional[User] = None
    ) -> Inquiry:
        """
        Resolve an inquiry with a conclusion. Emits event for provenance.
        
        Args:
            inquiry: The inquiry to resolve
            conclusion: The conclusion text
            conclusion_confidence: Optional confidence score (0.0-1.0)
            user: User resolving the inquiry
        
        Returns:
            Inquiry: The updated inquiry
        """
        # Calculate resolution time
        resolution_time = (timezone.now() - inquiry.created_at).total_seconds()

        # Update inquiry
        inquiry.conclusion = conclusion
        inquiry.conclusion_confidence = conclusion_confidence
        inquiry.status = InquiryStatus.RESOLVED
        inquiry.resolved_at = timezone.now()
        inquiry.save(update_fields=[
            'conclusion', 'conclusion_confidence', 'status',
            'resolved_at', 'updated_at',
        ])
        
        # Emit event
        EventService.append(
            event_type=EventType.INQUIRY_RESOLVED,
            payload={
                'inquiry_id': str(inquiry.id),
                'case_id': str(inquiry.case_id),
                'title': inquiry.title,
                'conclusion': conclusion,
                'conclusion_confidence': conclusion_confidence,
                'resolution_time_seconds': int(resolution_time),
                'triggered_brief_update': False  # Will be set by auto-synthesis
            },
            actor_type=ActorType.USER if user else ActorType.SYSTEM,
            actor_id=user.id if user else None,
            case_id=inquiry.case_id
        )
        
        return inquiry
    
    @staticmethod
    def get_case_inquiry_stats(case):
        """
        Get statistics about inquiries in a case.
        
        Returns:
            dict: Statistics about inquiries
        """
        inquiries = Inquiry.objects.filter(case=case)
        
        return {
            'total': inquiries.count(),
            'open': inquiries.filter(status=InquiryStatus.OPEN).count(),
            'investigating': inquiries.filter(status=InquiryStatus.INVESTIGATING).count(),
            'resolved': inquiries.filter(status=InquiryStatus.RESOLVED).count(),
            'archived': inquiries.filter(status=InquiryStatus.ARCHIVED).count(),
            'high_priority': inquiries.filter(priority__gt=0).count(),
        }
