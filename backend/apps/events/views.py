"""
Event views
"""
from django.db.models import Q

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Event
from .serializers import EventSerializer
from .services import EventService


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for events
    Events are append-only via EventService, not directly via API
    """
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def _user_owned_queryset(self):
        """
        Base queryset filtered to events the current user owns,
        via Case or ChatThread ownership.

        Event stores case_id/thread_id as UUIDs (not FK), so we
        resolve ownership through the Case and ChatThread models.
        """
        from apps.cases.models import Case
        from apps.chat.models import ChatThread

        user = self.request.user
        user_case_ids = Case.objects.filter(user=user).values_list('id', flat=True)
        user_thread_ids = ChatThread.objects.filter(user=user).values_list('id', flat=True)

        return Event.objects.filter(
            Q(case_id__in=user_case_ids) |
            Q(thread_id__in=user_thread_ids)
        )

    def get_queryset(self):
        """Filter events by query params, scoped to current user's data."""
        queryset = self._user_owned_queryset()
        
        # Filter by case_id
        case_id = self.request.query_params.get('case_id')
        if case_id:
            queryset = queryset.filter(case_id=case_id)
        
        # Filter by thread_id
        thread_id = self.request.query_params.get('thread_id')
        if thread_id:
            queryset = queryset.filter(thread_id=thread_id)
        
        # Filter by correlation_id
        correlation_id = self.request.query_params.get('correlation_id')
        if correlation_id:
            queryset = queryset.filter(correlation_id=correlation_id)
        
        # Filter by type (single)
        event_type = self.request.query_params.get('type')
        if event_type:
            queryset = queryset.filter(type=event_type)

        # Filter by types (comma-separated, e.g. ?types=CaseCreated,InquiryResolved)
        types = self.request.query_params.get('types')
        if types:
            queryset = queryset.filter(type__in=types.split(','))

        # Exclude types (comma-separated, e.g. ?exclude_types=AgentProgress,AgentCheckpoint)
        exclude_types = self.request.query_params.get('exclude_types')
        if exclude_types:
            queryset = queryset.exclude(type__in=exclude_types.split(','))

        # Filter by category (e.g. ?category=provenance)
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        # Limit results (default 50, max 200)
        limit = min(int(self.request.query_params.get('limit', 50)), 200)

        return queryset.order_by('-timestamp')[:limit]
    
    @action(detail=False, methods=['get'], url_path='case/(?P<case_id>[^/.]+)/timeline')
    def case_timeline(self, request, case_id=None):
        """Get timeline of events for a case, with optional filtering."""
        # Verify user owns this case
        from apps.cases.models import Case
        if not Case.objects.filter(id=case_id, user=request.user).exists():
            return Response(
                {'detail': 'Case not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        limit = min(int(request.query_params.get('limit', 100)), 200)
        exclude_types = request.query_params.get('exclude_types')
        category = request.query_params.get('category')

        queryset = Event.objects.filter(case_id=case_id)
        if exclude_types:
            queryset = queryset.exclude(type__in=exclude_types.split(','))
        if category:
            queryset = queryset.filter(category=category)
        events = list(queryset.order_by('-timestamp')[:limit])

        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='thread/(?P<thread_id>[^/.]+)/timeline')
    def thread_timeline(self, request, thread_id=None):
        """Get timeline of events for a thread."""
        # Verify user owns this thread
        from apps.chat.models import ChatThread
        if not ChatThread.objects.filter(id=thread_id, user=request.user).exists():
            return Response(
                {'detail': 'Thread not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        events = EventService.get_thread_timeline(thread_id)
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='workflow/(?P<correlation_id>[^/.]+)')
    def workflow_events(self, request, correlation_id=None):
        """
        Get all events for a workflow (agent execution, etc.)

        GET /api/events/workflow/{correlation_id}/

        Returns: Chronological list of events with same correlation_id,
        filtered to events the current user owns.
        """
        all_events = EventService.get_workflow_events(correlation_id)

        # Filter to user-owned events only
        from apps.cases.models import Case
        from apps.chat.models import ChatThread
        user_case_ids = set(
            Case.objects.filter(user=request.user).values_list('id', flat=True)
        )
        user_thread_ids = set(
            ChatThread.objects.filter(user=request.user).values_list('id', flat=True)
        )
        events = [
            e for e in all_events
            if (e.case_id in user_case_ids) or
               (e.thread_id in user_thread_ids) or
               (e.case_id is None and e.thread_id is None)
        ]

        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)