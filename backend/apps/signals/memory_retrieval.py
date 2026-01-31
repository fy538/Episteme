"""
Memory retrieval service for scope-aware signal retrieval.

Implements hot/warm/cold memory tiers across thread/case/project scopes.
"""
import uuid
from typing import List, Optional
from dataclasses import dataclass
from django.utils import timezone
from datetime import timedelta

from apps.signals.models import Signal, SignalType, SignalTemperature
from apps.signals.query_engine import get_query_engine, QueryScope


@dataclass
class MemoryRetrievalStrategy:
    """
    Defines how to retrieve signals across scope × temperature dimensions.
    
    Examples:
    - Narrow scope, all temps: Thread-only, hot+warm+cold
    - Wide scope, hot only: All cases in project, hot tier only
    - Medium scope, warm only: Case-level, semantic search
    """
    # Scope settings
    thread_id: Optional[uuid.UUID] = None
    case_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    
    # Temperature settings
    include_hot: bool = True
    include_warm: bool = True
    include_cold: bool = False  # Default: exclude archival
    
    # Retrieval limits per tier
    max_hot: int = 10   # Always include all hot signals up to limit
    max_warm: int = 20  # Semantic search up to limit
    max_cold: int = 0   # Archival rarely needed


class MemoryRetrievalService:
    """
    Service for retrieving signals across scope and temperature dimensions.
    
    Implements:
    - Hot tier: Always-on signals (recent, pinned, high-access)
    - Warm tier: Retrieved on-demand via semantic search
    - Cold tier: Archival signals (only when explicitly requested)
    """
    
    @staticmethod
    def retrieve_signals(
        user_message: str,
        strategy: MemoryRetrievalStrategy
    ) -> List[Signal]:
        """
        Retrieve signals across scope × temperature dimensions.
        
        Strategy:
        1. Get hot signals from specified scopes (always include)
        2. Semantic search for warm signals (on-demand)
        3. Optionally include cold signals (rarely)
        
        Args:
            user_message: User's message (for semantic search)
            strategy: Retrieval strategy defining scope and temperature
            
        Returns:
            List of signals sorted by: temperature (hot first) → relevance
        """
        all_signals = []
        
        # === HOT TIER: Always include (no semantic search) ===
        if strategy.include_hot:
            hot_signals = MemoryRetrievalService._get_hot_signals(strategy)
            all_signals.extend(hot_signals[:strategy.max_hot])
        
        # === WARM TIER: Semantic search within scope ===
        if strategy.include_warm:
            warm_signals = MemoryRetrievalService._get_warm_signals(
                user_message,
                strategy,
                exclude_ids=[s.id for s in all_signals]
            )
            all_signals.extend(warm_signals[:strategy.max_warm])
        
        # === COLD TIER: Archival (optional) ===
        if strategy.include_cold and strategy.max_cold > 0:
            cold_signals = MemoryRetrievalService._get_cold_signals(
                strategy,
                exclude_ids=[s.id for s in all_signals]
            )
            all_signals.extend(cold_signals[:strategy.max_cold])
        
        return all_signals
    
    @staticmethod
    def _get_hot_signals(strategy: MemoryRetrievalStrategy) -> List[Signal]:
        """
        Get hot tier signals (always in context).
        
        Hot signals are:
        - User-pinned signals
        - Recent signals (last 5 messages in thread)
        - Frequently accessed signals (access_count >= 10)
        """
        from apps.chat.models import Message
        
        # Build scope filters
        filters = {'dismissed_at__isnull': True}
        
        if strategy.thread_id:
            filters['thread_id'] = strategy.thread_id
        elif strategy.case_id:
            filters['case_id'] = strategy.case_id
        elif strategy.project_id:
            filters['case__project_id'] = strategy.project_id
        
        queryset = Signal.objects.filter(**filters)
        
        # Get hot signals based on multiple criteria
        hot_signals = []
        
        # 1. Pinned signals
        pinned = list(queryset.filter(pinned_at__isnull=False))
        hot_signals.extend(pinned)
        
        # 2. Recent signals (last 5 messages in thread)
        if strategy.thread_id:
            # Get total message count in thread
            from apps.chat.models import ChatThread
            try:
                thread = ChatThread.objects.get(id=strategy.thread_id)
                message_count = Message.objects.filter(thread=thread).count()
                
                # Get signals from last 5 messages
                recent = list(queryset.filter(
                    thread_id=strategy.thread_id,
                    sequence_index__gte=max(0, message_count - 5)
                ).exclude(id__in=[s.id for s in hot_signals]))
                hot_signals.extend(recent)
            except ChatThread.DoesNotExist:
                pass
        
        # 3. Frequently accessed signals
        frequent = list(queryset.filter(
            access_count__gte=10
        ).exclude(id__in=[s.id for s in hot_signals]))
        hot_signals.extend(frequent)
        
        # Sort by confidence and recency
        hot_signals.sort(key=lambda s: (s.confidence, s.created_at), reverse=True)
        
        return hot_signals
    
    @staticmethod
    def _get_warm_signals(
        user_message: str,
        strategy: MemoryRetrievalStrategy,
        exclude_ids: List[uuid.UUID]
    ) -> List[Signal]:
        """
        Get warm tier signals via semantic search.
        
        Uses query engine for similarity-based retrieval.
        """
        engine = get_query_engine()
        scope = QueryScope(
            thread_id=strategy.thread_id,
            case_id=strategy.case_id,
            project_id=strategy.project_id
        )
        
        # Execute semantic search
        result = engine.query(
            query_text=user_message,
            scope=scope,
            top_k=strategy.max_warm * 2,  # Get extra to filter
            threshold=0.6
        )
        
        # Filter out signals already in hot tier
        warm_signals = [
            r.signal for r in result.signals
            if r.signal.id not in exclude_ids and not r.signal.dismissed_at
        ]
        
        # Track access for adaptive temperature
        for signal in warm_signals:
            signal.mark_accessed()
        
        return warm_signals
    
    @staticmethod
    def _get_cold_signals(
        strategy: MemoryRetrievalStrategy,
        exclude_ids: List[uuid.UUID]
    ) -> List[Signal]:
        """
        Get cold tier signals (archival).
        
        Only retrieved when explicitly requested (e.g., "what did I say 3 months ago?")
        """
        filters = {
            'dismissed_at__isnull': True,
            'created_at__lt': timezone.now() - timedelta(days=30)
        }
        
        if strategy.thread_id:
            filters['thread_id'] = strategy.thread_id
        elif strategy.case_id:
            filters['case_id'] = strategy.case_id
        elif strategy.project_id:
            filters['case__project_id'] = strategy.project_id
        
        cold_signals = list(
            Signal.objects.filter(**filters)
            .exclude(id__in=exclude_ids)
            .order_by('-created_at')
        )
        
        return cold_signals
    
    @staticmethod
    def detect_retrieval_strategy(
        thread,
        user_message: str
    ) -> MemoryRetrievalStrategy:
        """
        Detect appropriate retrieval strategy based on message content.
        
        Heuristics:
        - "in this thread/conversation" → thread scope
        - "in this case/investigation" → case scope
        - "across my projects" → project scope
        - "what did I say before/earlier/previously" → include cold
        - "recently" → hot only
        """
        message_lower = user_message.lower()
        
        # Scope detection
        if any(keyword in message_lower for keyword in ['this thread', 'this conversation', 'earlier here']):
            scope_level = 'thread'
        elif any(keyword in message_lower for keyword in ['this case', 'this investigation', 'in general']):
            scope_level = 'case'
        elif any(keyword in message_lower for keyword in ['across', 'all my', 'in other']):
            scope_level = 'project'
        else:
            scope_level = 'case'  # Default: case-wide
        
        # Temperature detection
        include_cold = any(keyword in message_lower for keyword in [
            'before', 'previously', 'earlier', 'ago', 'past', 'history'
        ])
        
        hot_only = any(keyword in message_lower for keyword in [
            'recently', 'just said', 'just mentioned', 'current'
        ])
        
        # Build strategy based on scope and temperature
        if scope_level == 'thread':
            return MemoryRetrievalStrategy(
                thread_id=thread.id,
                include_hot=True,
                include_warm=not hot_only,
                include_cold=include_cold,
                max_hot=5,
                max_warm=10 if not hot_only else 0,
                max_cold=10 if include_cold else 0
            )
        elif scope_level == 'case':
            case_id = thread.case_id if thread.case else None
            return MemoryRetrievalStrategy(
                case_id=case_id,
                include_hot=True,
                include_warm=True,
                include_cold=include_cold,
                max_hot=10,
                max_warm=20,
                max_cold=10 if include_cold else 0
            )
        else:  # project
            project_id = thread.case.project_id if thread.case else thread.project_id
            return MemoryRetrievalStrategy(
                project_id=project_id,
                include_hot=True,
                include_warm=True,
                include_cold=include_cold,
                max_hot=5,
                max_warm=30,
                max_cold=15 if include_cold else 0
            )
