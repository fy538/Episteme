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
from apps.signals.models import Signal, SignalType
from apps.cases.models import Case
from apps.events.services import EventService
from apps.events.models import EventType, ActorType


MAX_INQUIRY_TITLE_LEN = 100


def _build_inquiry_title_from_signal(signal) -> str:
    """
    Build a clean inquiry title from a signal.

    Uses type-based prefixes and truncates long text at a word boundary.
    """
    text = signal.text.strip()

    if signal.type == SignalType.QUESTION:
        title = text
    elif signal.type == SignalType.CLAIM:
        title = f"Validate: {text}"
    elif signal.type == SignalType.ASSUMPTION:
        title = f"Test assumption: {text}"
    elif signal.type == SignalType.DECISION_INTENT:
        title = text
    else:
        title = f"Examine: {text}"

    # Truncate at word boundary if too long
    if len(title) > MAX_INQUIRY_TITLE_LEN:
        truncated = title[:MAX_INQUIRY_TITLE_LEN]
        # Find last space to avoid cutting mid-word
        last_space = truncated.rfind(' ')
        if last_space > MAX_INQUIRY_TITLE_LEN // 2:
            truncated = truncated[:last_space]
        title = truncated.rstrip('.,;:') + '...'

    return title


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
        from apps.cases.document_service import CaseDocumentService
        
        return CaseDocumentService.create_inquiry_with_brief(
            case=case,
            title=title,
            user=user,
            elevation_reason=elevation_reason
        )
    
    @staticmethod
    def should_promote_to_inquiry(signal, case):
        """
        Determine if a signal should be promoted to an inquiry.
        
        Returns:
            tuple: (should_promote: bool, reason: str or None, suggested_title: str or None)
        """
        # 1. Check for repetition - similar signals mentioned multiple times
        similar_count = Signal.objects.filter(
            case=case,
            dedupe_key=signal.dedupe_key,
            dismissed_at__isnull=True
        ).count()
        
        if similar_count >= 3:
            return True, ElevationReason.REPETITION, f"Examine: {signal.text}"
        
        # 2. Check for conflicts - contradicting signals
        # TODO: Implement semantic similarity check for conflicts
        # For now, check if there are signals with same type but different dedupe_key
        
        # 3. Check for blocking questions
        if signal.type == SignalType.QUESTION:
            # Check if this question is mentioned multiple times or has high confidence
            if signal.confidence > 0.8 or similar_count >= 2:
                return True, ElevationReason.BLOCKING, signal.text
        
        # 4. Check for critical assumptions
        if signal.type == SignalType.ASSUMPTION:
            # High confidence assumptions should be examined
            if signal.confidence > 0.85:
                return True, ElevationReason.HIGH_STRENGTH, f"Validate assumption: {signal.text}"
        
        # 5. Check for high-confidence claims without evidence
        if signal.type == SignalType.CLAIM:
            if signal.confidence > 0.8:
                # TODO: Check if claim has supporting evidence
                # For now, promote high-confidence claims for validation
                return True, ElevationReason.HIGH_STRENGTH, f"Validate claim: {signal.text}"
        
        return False, None, None
    
    @staticmethod
    @transaction.atomic
    def create_inquiry_from_signal(signal, case, elevation_reason=None, title=None):
        """
        Create an inquiry from a signal.

        Args:
            signal: The signal to promote
            case: The case this inquiry belongs to
            elevation_reason: Why this signal is being elevated
            title: Optional custom title (defaults to signal text)

        Returns:
            Inquiry: The created inquiry
        """
        # Get next sequence index
        last_inquiry = Inquiry.objects.filter(case=case).order_by('-sequence_index').first()
        sequence_index = (last_inquiry.sequence_index + 1) if last_inquiry else 0

        # Determine title
        if not title:
            title = _build_inquiry_title_from_signal(signal)

        # Create inquiry
        inquiry = Inquiry.objects.create(
            case=case,
            title=title,
            description=f"Auto-promoted from {signal.type} signal (confidence: {signal.confidence})",
            elevation_reason=elevation_reason or ElevationReason.USER_CREATED,
            sequence_index=sequence_index,
            status=InquiryStatus.OPEN,
        )

        # Link signal to inquiry
        signal.inquiry = inquiry
        signal.save(update_fields=['inquiry'])

        # Find and link similar signals (bulk update instead of per-object save)
        Signal.objects.filter(
            case=case,
            dedupe_key=signal.dedupe_key,
            dismissed_at__isnull=True,
            inquiry__isnull=True,
        ).exclude(id=signal.id).update(inquiry=inquiry)

        return inquiry
    
    @staticmethod
    def get_promotion_suggestions(case):
        """
        Get signals that should be suggested for promotion to inquiries.
        
        Returns:
            list: List of dicts with signal and promotion info
        """
        suggestions = []
        
        # Get signals not already promoted or dismissed
        signals = Signal.objects.filter(
            case=case,
            inquiry__isnull=True,
            dismissed_at__isnull=True
        ).order_by('-created_at')
        
        # Group by dedupe_key to find repeated signals
        signal_groups = {}
        for signal in signals:
            if signal.dedupe_key not in signal_groups:
                signal_groups[signal.dedupe_key] = []
            signal_groups[signal.dedupe_key].append(signal)
        
        # Check each unique signal for promotion criteria
        checked_signals = set()
        for signal in signals:
            if signal.id in checked_signals:
                continue
            
            should_promote, reason, title = InquiryService.should_promote_to_inquiry(signal, case)
            
            if should_promote:
                suggestions.append({
                    'signal': signal,
                    'reason': reason,
                    'suggested_title': title,
                    'similar_count': len(signal_groups.get(signal.dedupe_key, [])),
                })
                
                # Mark all similar signals as checked
                for similar_signal in signal_groups.get(signal.dedupe_key, []):
                    checked_signals.add(similar_signal.id)
        
        return suggestions
    
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
        from apps.inquiries.models import Evidence
        
        # Calculate resolution time
        resolution_time = (timezone.now() - inquiry.created_at).total_seconds()
        
        # Count evidence
        evidence = Evidence.objects.filter(inquiry=inquiry)
        supporting_count = evidence.filter(direction='supporting').count()
        contradicting_count = evidence.filter(direction='contradicting').count()
        
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
                'evidence_count_supporting': supporting_count,
                'evidence_count_contradicting': contradicting_count,
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
