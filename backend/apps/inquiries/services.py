"""
Business logic for inquiry management
"""
from django.utils import timezone
from django.db.models import Count
from django.contrib.auth.models import User

from apps.inquiries.models import Inquiry, ElevationReason, InquiryStatus
from apps.signals.models import Signal, SignalType
from apps.cases.models import Case


class InquiryService:
    """Service for managing inquiries and auto-promotion logic"""
    
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
            # Auto-generate title based on signal type
            if signal.type == SignalType.QUESTION:
                title = signal.text
            elif signal.type == SignalType.CLAIM:
                title = f"Validate: {signal.text}"
            elif signal.type == SignalType.ASSUMPTION:
                title = f"Test assumption: {signal.text}"
            elif signal.type == SignalType.DECISION_INTENT:
                title = signal.text
            else:
                title = f"Examine: {signal.text}"
        
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
        signal.save()
        
        # Find and link similar signals
        similar_signals = Signal.objects.filter(
            case=case,
            dedupe_key=signal.dedupe_key,
            dismissed_at__isnull=True,
            inquiry__isnull=True
        ).exclude(id=signal.id)
        
        for similar_signal in similar_signals:
            similar_signal.inquiry = inquiry
            similar_signal.save()
        
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
    
    @staticmethod
    def resolve_inquiry(inquiry, conclusion, conclusion_confidence=None):
        """
        Resolve an inquiry with a conclusion.
        
        Args:
            inquiry: The inquiry to resolve
            conclusion: The conclusion text
            conclusion_confidence: Optional confidence score (0.0-1.0)
        
        Returns:
            Inquiry: The updated inquiry
        """
        inquiry.conclusion = conclusion
        inquiry.conclusion_confidence = conclusion_confidence
        inquiry.status = InquiryStatus.RESOLVED
        inquiry.resolved_at = timezone.now()
        inquiry.save()
        
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
