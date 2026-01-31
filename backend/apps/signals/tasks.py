"""
Celery tasks for signal processing

Phase 1: Signal extraction, deduplication, consolidation
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task
def consolidate_thread_signals(thread_id: str):
    """
    Periodic signal consolidation with adaptive decay (ARM-style).
    
    Run periodically per thread to:
    1. Deduplicate signals by embedding similarity
    2. Apply confidence decay to old/contradicted signals
    3. Archive cold signals (very low confidence)
    
    Args:
        thread_id: ChatThread ID to consolidate
    
    Returns:
        Consolidation result with counts
    """
    from apps.signals.models import Signal
    from apps.signals.similarity import dedupe_signals_by_embedding
    
    try:
        signals = list(Signal.objects.filter(
            thread_id=thread_id,
            dismissed_at__isnull=True
        ))
        
        if not signals:
            return {
                'status': 'skipped',
                'reason': 'no_signals',
                'thread_id': thread_id
            }
        
        initial_count = len(signals)
        
        # 1. Deduplicate by embedding similarity
        deduplicated = dedupe_signals_by_embedding(signals, threshold=0.90)
        duplicates = set(signals) - set(deduplicated)
        
        # Mark duplicates as dismissed
        duplicates_count = 0
        for dup in duplicates:
            dup.dismissed_at = timezone.now()
            dup.save(update_fields=['dismissed_at'])
            duplicates_count += 1
        
        # 2. Apply confidence decay to remaining signals
        decayed_count = 0
        for signal in deduplicated:
            age_days = (timezone.now() - signal.created_at).days
            original_confidence = signal.confidence
            
            # Decay old signals (30-day half-life)
            if age_days > 30:
                decay_factor = 0.95 ** (age_days / 30)
                signal.confidence *= decay_factor
                decayed_count += 1
            
            # Heavy decay for contradicted signals
            if signal.contradicted_by.exists():
                signal.confidence *= 0.5
                decayed_count += 1
            
            # Only save if confidence changed significantly
            if abs(original_confidence - signal.confidence) > 0.01:
                signal.save(update_fields=['confidence'])
        
        # 3. Archive very low confidence signals
        archived_count = Signal.objects.filter(
            thread_id=thread_id,
            confidence__lt=0.3,
            dismissed_at__isnull=True
        ).update(dismissed_at=timezone.now())
        
        logger.info(
            "thread_signals_consolidated",
            extra={
                "thread_id": thread_id,
                "initial_count": initial_count,
                "duplicates_removed": duplicates_count,
                "signals_decayed": decayed_count,
                "signals_archived": archived_count,
                "final_count": initial_count - duplicates_count - archived_count
            }
        )
        
        return {
            'status': 'completed',
            'thread_id': thread_id,
            'initial_count': initial_count,
            'duplicates_removed': duplicates_count,
            'signals_decayed': decayed_count,
            'signals_archived': archived_count,
            'final_count': initial_count - duplicates_count - archived_count
        }
        
    except Exception:
        logger.exception(
            "consolidate_thread_signals_failed",
            extra={"thread_id": thread_id}
        )
        return {
            'status': 'failed',
            'thread_id': thread_id,
            'error': 'exception'
        }


@shared_task
def schedule_signal_consolidation():
    """
    Periodic task to consolidate signals across all active threads.
    
    Run daily via Celery Beat. Only consolidates threads with:
    - Recent activity (updated in last 7 days)
    - At least 10 signals
    
    Returns:
        Summary of consolidation tasks scheduled
    """
    from apps.chat.models import ChatThread
    from django.db.models import Count
    
    try:
        # Find active threads with signals
        active_threads = ChatThread.objects.filter(
            updated_at__gte=timezone.now() - timedelta(days=7),
            archived=False
        ).annotate(
            signal_count=Count('signals')
        ).filter(
            signal_count__gte=10  # Only consolidate if enough signals
        )
        
        scheduled_count = 0
        for thread in active_threads:
            consolidate_thread_signals.delay(str(thread.id))
            scheduled_count += 1
        
        logger.info(
            "signal_consolidation_scheduled",
            extra={
                "threads_scheduled": scheduled_count
            }
        )
        
        return {
            'status': 'completed',
            'threads_scheduled': scheduled_count
        }
        
    except Exception:
        logger.exception("schedule_signal_consolidation_failed")
        return {
            'status': 'failed',
            'error': 'exception'
        }


@shared_task
def update_signal_temperatures():
    """
    Update signal temperature tiers based on access patterns.
    
    Runs daily to recalculate hot/warm/cold tiers adaptively.
    
    Returns:
        Count of signals updated per tier
    """
    from apps.signals.models import Signal, SignalTemperature
    
    try:
        # Get all active signals
        signals = Signal.objects.filter(dismissed_at__isnull=True)
        
        updates = {
            'hot': 0,
            'warm': 0,
            'cold': 0
        }
        
        for signal in signals:
            old_temp = signal.temperature
            new_temp = signal.calculate_temperature()
            
            if old_temp != new_temp:
                signal.temperature = new_temp
                signal.save(update_fields=['temperature'])
                updates[new_temp] += 1
        
        logger.info(
            "signal_temperatures_updated",
            extra=updates
        )
        
        return {
            'status': 'completed',
            'updates': updates
        }
        
    except Exception:
        logger.exception("update_signal_temperatures_failed")
        return {
            'status': 'failed',
            'error': 'exception'
        }
