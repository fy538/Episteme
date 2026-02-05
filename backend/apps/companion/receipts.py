"""
Session Receipt Service - Records and retrieves session accomplishments
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from django.utils import timezone
from django.db.models import QuerySet

from apps.companion.models import SessionReceipt, SessionReceiptType
from apps.chat.models import ChatThread
from apps.cases.models import Case
from apps.inquiries.models import Inquiry

logger = logging.getLogger(__name__)

# Default session duration for grouping receipts
SESSION_DURATION_HOURS = 4


class SessionReceiptService:
    """
    Service for recording and retrieving session accomplishments.

    Tracks key events like case creation, inquiry resolution, etc.
    Groups receipts by session (default: 4 hour windows).
    """

    @staticmethod
    def get_session_start(reference_time: Optional[datetime] = None) -> datetime:
        """
        Get the session start time.

        Sessions are grouped by time windows. This returns the start
        of the current session window.

        Args:
            reference_time: Reference time (default: now)

        Returns:
            Session start datetime
        """
        if reference_time is None:
            reference_time = timezone.now()

        # Simple windowing: sessions start at the previous 4-hour boundary
        # e.g., 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
        hour = reference_time.hour
        session_hour = (hour // SESSION_DURATION_HOURS) * SESSION_DURATION_HOURS

        return reference_time.replace(
            hour=session_hour,
            minute=0,
            second=0,
            microsecond=0
        )

    @staticmethod
    def record(
        thread_id: uuid.UUID,
        receipt_type: str,
        title: str,
        detail: str = "",
        related_case: Optional[Case] = None,
        related_inquiry: Optional[Inquiry] = None
    ) -> SessionReceipt:
        """
        Record a session accomplishment.

        Args:
            thread_id: Thread where the accomplishment occurred
            receipt_type: Type of accomplishment (SessionReceiptType value)
            title: Brief title describing the accomplishment
            detail: Additional details (optional)
            related_case: Related case if applicable
            related_inquiry: Related inquiry if applicable

        Returns:
            Created SessionReceipt
        """
        try:
            thread = ChatThread.objects.get(id=thread_id)
        except ChatThread.DoesNotExist:
            logger.warning(f"[Receipts] Thread {thread_id} not found, skipping receipt")
            raise

        session_start = SessionReceiptService.get_session_start()

        receipt = SessionReceipt.objects.create(
            thread=thread,
            receipt_type=receipt_type,
            title=title,
            detail=detail,
            related_case=related_case,
            related_inquiry=related_inquiry,
            session_started_at=session_start
        )

        logger.info(f"[Receipts] Recorded {receipt_type}: {title} for thread {thread_id}")
        return receipt

    @staticmethod
    def record_case_created(
        thread_id: uuid.UUID,
        case: Case
    ) -> SessionReceipt:
        """
        Record a case creation receipt.

        Args:
            thread_id: Thread where case was created
            case: The created case

        Returns:
            Created SessionReceipt
        """
        return SessionReceiptService.record(
            thread_id=thread_id,
            receipt_type=SessionReceiptType.CASE_CREATED,
            title=f"Case created: {case.title[:50]}",
            related_case=case
        )

    @staticmethod
    def record_signals_extracted(
        thread_id: uuid.UUID,
        signal_count: int,
        related_case: Optional[Case] = None
    ) -> SessionReceipt:
        """
        Record signals extraction receipt.

        Args:
            thread_id: Thread where signals were extracted
            signal_count: Number of signals extracted
            related_case: Related case if applicable

        Returns:
            Created SessionReceipt
        """
        return SessionReceiptService.record(
            thread_id=thread_id,
            receipt_type=SessionReceiptType.SIGNALS_EXTRACTED,
            title=f"{signal_count} signal{'s' if signal_count != 1 else ''} extracted",
            detail=f"Extracted {signal_count} signals from conversation",
            related_case=related_case
        )

    @staticmethod
    def record_inquiry_resolved(
        thread_id: uuid.UUID,
        inquiry: Inquiry,
        conclusion: str = ""
    ) -> SessionReceipt:
        """
        Record inquiry resolution receipt.

        Args:
            thread_id: Thread where inquiry was resolved
            inquiry: The resolved inquiry
            conclusion: Resolution conclusion

        Returns:
            Created SessionReceipt
        """
        return SessionReceiptService.record(
            thread_id=thread_id,
            receipt_type=SessionReceiptType.INQUIRY_RESOLVED,
            title=f"Resolved: {inquiry.title[:50]}",
            detail=conclusion[:200] if conclusion else "",
            related_case=inquiry.case,
            related_inquiry=inquiry
        )

    @staticmethod
    def record_evidence_added(
        thread_id: uuid.UUID,
        inquiry: Inquiry,
        evidence_count: int = 1,
        direction: str = ""
    ) -> SessionReceipt:
        """
        Record evidence addition receipt.

        Args:
            thread_id: Thread where evidence was added
            inquiry: Inquiry evidence was added to
            evidence_count: Number of evidence items added
            direction: Evidence direction (supporting/contradicting)

        Returns:
            Created SessionReceipt
        """
        direction_text = f" ({direction})" if direction else ""
        return SessionReceiptService.record(
            thread_id=thread_id,
            receipt_type=SessionReceiptType.EVIDENCE_ADDED,
            title=f"Evidence added{direction_text}",
            detail=f"Added to: {inquiry.title[:60]}",
            related_case=inquiry.case,
            related_inquiry=inquiry
        )

    @staticmethod
    def record_research_completed(
        thread_id: uuid.UUID,
        research_title: str,
        source_count: int = 0,
        related_case: Optional[Case] = None
    ) -> SessionReceipt:
        """
        Record research completion receipt.

        Args:
            thread_id: Thread where research was conducted
            research_title: Title of the research
            source_count: Number of sources found
            related_case: Related case if applicable

        Returns:
            Created SessionReceipt
        """
        detail = f"{source_count} source{'s' if source_count != 1 else ''} found" if source_count > 0 else ""
        return SessionReceiptService.record(
            thread_id=thread_id,
            receipt_type=SessionReceiptType.RESEARCH_COMPLETED,
            title=f"Research: {research_title[:50]}",
            detail=detail,
            related_case=related_case
        )

    @staticmethod
    def get_session_receipts(
        thread_id: uuid.UUID,
        session_start: Optional[datetime] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Get receipts for the current session.

        Args:
            thread_id: Thread to get receipts for
            session_start: Session start time (default: current session)
            limit: Maximum receipts to return

        Returns:
            List of receipt dicts for API serialization
        """
        if session_start is None:
            session_start = SessionReceiptService.get_session_start()

        receipts = SessionReceipt.objects.filter(
            thread_id=thread_id,
            session_started_at=session_start
        ).select_related(
            'related_case',
            'related_inquiry'
        ).order_by('-created_at')[:limit]

        return [
            {
                'id': str(receipt.id),
                'type': receipt.receipt_type,
                'title': receipt.title,
                'detail': receipt.detail,
                'timestamp': receipt.created_at.isoformat(),
                'relatedCaseId': str(receipt.related_case_id) if receipt.related_case_id else None,
                'relatedInquiryId': str(receipt.related_inquiry_id) if receipt.related_inquiry_id else None,
            }
            for receipt in receipts
        ]

    @staticmethod
    def get_all_thread_receipts(
        thread_id: uuid.UUID,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get all receipts for a thread (across all sessions).

        Args:
            thread_id: Thread to get receipts for
            limit: Maximum receipts to return

        Returns:
            List of receipt dicts for API serialization
        """
        receipts = SessionReceipt.objects.filter(
            thread_id=thread_id
        ).select_related(
            'related_case',
            'related_inquiry'
        ).order_by('-created_at')[:limit]

        return [
            {
                'id': str(receipt.id),
                'type': receipt.receipt_type,
                'title': receipt.title,
                'detail': receipt.detail,
                'timestamp': receipt.created_at.isoformat(),
                'relatedCaseId': str(receipt.related_case_id) if receipt.related_case_id else None,
                'relatedInquiryId': str(receipt.related_inquiry_id) if receipt.related_inquiry_id else None,
            }
            for receipt in receipts
        ]

    @staticmethod
    def cleanup_old_receipts(days: int = 30) -> int:
        """
        Clean up old receipts.

        Args:
            days: Delete receipts older than this many days

        Returns:
            Number of receipts deleted
        """
        cutoff = timezone.now() - timedelta(days=days)
        deleted_count, _ = SessionReceipt.objects.filter(
            created_at__lt=cutoff
        ).delete()

        logger.info(f"[Receipts] Cleaned up {deleted_count} old receipts")
        return deleted_count
