"""
Event views
"""
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
    
    def get_queryset(self):
        """Filter events by query params"""
        queryset = Event.objects.all()
        
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
        
        # Filter by type
        event_type = self.request.query_params.get('type')
        if event_type:
            queryset = queryset.filter(type=event_type)
        
        return queryset.order_by('timestamp')
    
    @action(detail=False, methods=['get'], url_path='case/(?P<case_id>[^/.]+)/timeline')
    def case_timeline(self, request, case_id=None):
        """Get timeline of events for a case"""
        events = EventService.get_case_timeline(case_id)
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='thread/(?P<thread_id>[^/.]+)/timeline')
    def thread_timeline(self, request, thread_id=None):
        """Get timeline of events for a thread"""
        events = EventService.get_thread_timeline(thread_id)
        serializer = self.get_serializer(events, many=True)
        return Response(serializer.data)
