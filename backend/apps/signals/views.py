"""
Signal views (Phase 1 + Phase 2)
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction, models
from django.utils import timezone

from .models import Signal
from .serializers import (
    SignalSerializer,
    EditSignalSerializer,
)
from .query_engine import get_query_engine, QueryScope
from apps.events.services import EventService
from apps.events.models import EventType, ActorType


class SignalViewSet(viewsets.ModelViewSet):
    """ViewSet for signals (Phase 1)"""
    
    serializer_class = SignalSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Optimize with select_related to avoid N+1 queries
        queryset = Signal.objects.select_related(
            'case',
            'thread',
            'event',
            'inquiry',
            'document'
        ).prefetch_related(
            'depends_on',
            'contradicts'
        ).all()
        
        # Filter by case
        case_id = self.request.query_params.get('case_id')
        if case_id:
            queryset = queryset.filter(case_id=case_id)
        
        # Filter by thread
        thread_id = self.request.query_params.get('thread_id')
        if thread_id:
            queryset = queryset.filter(thread_id=thread_id)
        
        # Filter by message_id (new - for frontend optimization)
        message_id = self.request.query_params.get('message_id')
        if message_id:
            queryset = queryset.filter(span__message_id=message_id)
        
        # Filter by type
        signal_type = self.request.query_params.get('type')
        if signal_type:
            queryset = queryset.filter(type=signal_type)
        
        # Filter dismissed signals
        include_dismissed = self.request.query_params.get('include_dismissed', 'false')
        if include_dismissed.lower() != 'true':
            queryset = queryset.filter(dismissed_at__isnull=True)
        
        # Filter by inquiry
        inquiry_id = self.request.query_params.get('inquiry_id')
        if inquiry_id:
            queryset = queryset.filter(inquiry_id=inquiry_id)
        
        # Only show signals from user's cases/threads
        queryset = queryset.filter(
            models.Q(case__user=self.request.user) |
            models.Q(thread__user=self.request.user)
        )
        
        return queryset
    
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def dismiss(self, request, pk=None):
        """
        Dismiss a signal as not relevant.
        
        POST /api/signals/{id}/dismiss/
        """
        signal = self.get_object()
        
        if signal.dismissed_at:
            return Response(
                {'error': 'Signal already dismissed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        signal.dismissed_at = timezone.now()
        signal.save()
        
        # Emit event
        EventService.append(
            event_type=EventType.SIGNAL_EDITED,
            payload={
                'signal_id': str(signal.id),
                'action': 'dismissed',
            },
            actor_type=ActorType.USER,
            actor_id=request.user.id,
            case_id=signal.case_id,
            thread_id=signal.thread_id,
        )
        
        return Response(self.get_serializer(signal).data)
    
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def undismiss(self, request, pk=None):
        """
        Un-dismiss a signal.
        
        POST /api/signals/{id}/undismiss/
        """
        signal = self.get_object()
        
        if not signal.dismissed_at:
            return Response(
                {'error': 'Signal is not dismissed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        signal.dismissed_at = None
        signal.save()
        
        # Emit event
        EventService.append(
            event_type=EventType.SIGNAL_EDITED,
            payload={
                'signal_id': str(signal.id),
                'action': 'undismissed',
            },
            actor_type=ActorType.USER,
            actor_id=request.user.id,
            case_id=signal.case_id,
            thread_id=signal.thread_id,
        )
        
        return Response(self.get_serializer(signal).data)
    
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def promote_to_inquiry(self, request, pk=None):
        """
        Promote a signal to an inquiry.
        
        POST /api/signals/{id}/promote_to_inquiry/
        {
            "title": "Optional custom title",
            "elevation_reason": "user_created"
        }
        """
        from apps.inquiries.services import InquiryService
        from apps.inquiries.models import ElevationReason
        
        signal = self.get_object()
        
        if signal.inquiry_id:
            return Response(
                {'error': 'Signal already promoted to an inquiry'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not signal.case:
            return Response(
                {'error': 'Signal must belong to a case to be promoted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        title = request.data.get('title')
        elevation_reason = request.data.get('elevation_reason', ElevationReason.USER_CREATED)
        
        # Create inquiry from signal
        inquiry = InquiryService.create_inquiry_from_signal(
            signal=signal,
            case=signal.case,
            elevation_reason=elevation_reason,
            title=title
        )
        
        # Emit event
        EventService.append(
            event_type=EventType.SIGNAL_EDITED,
            payload={
                'signal_id': str(signal.id),
                'action': 'promoted_to_inquiry',
                'inquiry_id': str(inquiry.id),
            },
            actor_type=ActorType.USER,
            actor_id=request.user.id,
            case_id=signal.case_id,
            thread_id=signal.thread_id,
        )
        
        return Response({
            'signal': self.get_serializer(signal).data,
            'inquiry_id': str(inquiry.id),
        })
    
    @action(detail=True, methods=['patch'])
    @transaction.atomic
    def edit(self, request, pk=None):
        """
        Edit signal text
        
        PATCH /api/signals/{id}/edit/
        {
            "text": "Updated assumption text"
        }
        """
        signal = self.get_object()
        serializer = EditSignalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        old_text = signal.text
        new_text = serializer.validated_data['text']
        
        signal.text = new_text
        signal.save()
        
        # Emit event
        EventService.append(
            event_type=EventType.SIGNAL_EDITED,
            payload={
                'signal_id': str(signal.id),
                'old_text': old_text,
                'new_text': new_text,
            },
            actor_type=ActorType.USER,
            actor_id=request.user.id,
            case_id=signal.case_id,
            thread_id=signal.thread_id,
        )
        
        return Response(self.get_serializer(signal).data)
    
    @action(detail=False, methods=['get'])
    def promotion_suggestions(self, request):
        """
        Get signals that should be promoted to inquiries.
        
        GET /api/signals/promotion_suggestions/?case_id=uuid
        """
        from apps.inquiries.services import InquiryService
        
        case_id = request.query_params.get('case_id')
        if not case_id:
            return Response(
                {'error': 'case_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get case
        from apps.cases.models import Case
        try:
            case = Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            return Response(
                {'error': 'Case not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        suggestions = InquiryService.get_promotion_suggestions(case)
        
        # Serialize suggestions
        result = []
        for suggestion in suggestions:
            result.append({
                'signal': self.get_serializer(suggestion['signal']).data,
                'reason': suggestion['reason'],
                'suggested_title': suggestion['suggested_title'],
                'similar_count': suggestion['similar_count'],
            })
        
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def query(self, request):
        """
        Semantic query across signals (Phase 2)
        
        POST /api/signals/query/
        {
            "query_text": "What are my assumptions about performance?",
            "scope": {
                "case_id": "uuid",  // optional
                "project_id": "uuid",  // optional
                "thread_id": "uuid",  // optional
            },
            "signal_types": ["Assumption", "Question"],  // optional
            "top_k": 10,  // optional, default 10
            "threshold": 0.5  // optional, default 0.5
        }
        """
        query_text = request.data.get('query_text')
        if not query_text:
            return Response(
                {'error': 'query_text is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Build scope
        scope_data = request.data.get('scope', {})
        scope = QueryScope(
            case_id=scope_data.get('case_id'),
            project_id=scope_data.get('project_id'),
            thread_id=scope_data.get('thread_id'),
            document_id=scope_data.get('document_id'),
        )
        
        # Get query engine
        engine = get_query_engine()
        
        # Execute query
        result = engine.query(
            query_text=query_text,
            scope=scope,
            signal_types=request.data.get('signal_types'),
            top_k=request.data.get('top_k', 10),
            threshold=request.data.get('threshold', 0.5),
            status_filter=request.data.get('status_filter'),
        )
        
        return Response(result.to_dict())
    
    @action(detail=True, methods=['get'])
    def dependencies(self, request, pk=None):
        """
        Get dependency chain for a signal (Phase 2.3)
        
        GET /api/signals/{id}/dependencies/
        """
        from apps.common.graph_utils import GraphUtils
        
        signal = self.get_object()
        chain = GraphUtils.get_signal_dependencies(signal)
        
        return Response({
            'root': self.get_serializer(chain.root_signal).data,
            'dependencies': self.get_serializer(chain.dependencies, many=True).data,
            'depth': chain.depth,
        })
    
    @action(detail=True, methods=['get'])
    def evidence(self, request, pk=None):
        """
        Get supporting and contradicting evidence (Phase 2.3)
        
        GET /api/signals/{id}/evidence/
        """
        from apps.common.graph_utils import GraphUtils
        from apps.projects.evidence_serializers import EvidenceSerializer
        
        signal = self.get_object()
        
        supporting = GraphUtils.get_supporting_evidence(signal)
        contradicting = GraphUtils.get_contradicting_evidence(signal)
        strength = GraphUtils.get_evidence_strength(signal)
        
        return Response({
            'supporting': EvidenceSerializer(supporting, many=True).data,
            'contradicting': EvidenceSerializer(contradicting, many=True).data,
            'strength': strength,
        })
    
    @action(detail=True, methods=['get'])
    def contradictions(self, request, pk=None):
        """
        Find contradicting signals (Phase 2.3)
        
        GET /api/signals/{id}/contradictions/
        """
        from apps.common.graph_utils import GraphUtils
        
        signal = self.get_object()
        contradictions = GraphUtils.find_contradictions(signal)
        
        return Response({
            'this_contradicts': self.get_serializer(contradictions['this_contradicts'], many=True).data,
            'contradicted_by': self.get_serializer(contradictions['contradicted_by'], many=True).data,
        })
    
    @action(detail=True, methods=['post'])
    def link(self, request, pk=None):
        """
        Create relationship between signals (Phase 2.3)
        
        POST /api/signals/{id}/link/
        {
            "target_signal_id": "uuid",
            "relationship": "depends_on" | "contradicts"
        }
        """
        signal = self.get_object()
        target_id = request.data.get('target_signal_id')
        relationship = request.data.get('relationship')
        
        if not target_id or not relationship:
            return Response(
                {'error': 'target_signal_id and relationship required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            target_signal = Signal.objects.get(id=target_id)
            
            if relationship == 'depends_on':
                signal.depends_on.add(target_signal)
            elif relationship == 'contradicts':
                signal.contradicts.add(target_signal)
            else:
                return Response(
                    {'error': 'relationship must be depends_on or contradicts'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Emit event
            EventService.append(
                event_type=EventType.SIGNAL_STATUS_CHANGED,  # Or create new type
                payload={
                    'signal_id': str(signal.id),
                    'action': 'link_created',
                    'relationship': relationship,
                    'target_signal_id': str(target_id),
                },
                actor_type=ActorType.USER,
                actor_id=request.user.id,
                case_id=signal.case_id,
            )
            
            return Response(self.get_serializer(signal).data)
            
        except Signal.DoesNotExist:
            return Response(
                {'error': 'target_signal_id not found'},
                status=status.HTTP_404_NOT_FOUND
            )
