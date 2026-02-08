"""
Evidence views
"""
from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.projects.models import Evidence
from apps.projects.evidence_serializers import EvidenceSerializer, RateEvidenceSerializer


class EvidenceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for evidence extracted from documents.
    
    Evidence is read-only via API (created during document processing).
    Users can rate credibility of evidence items.
    """
    
    serializer_class = EvidenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter evidence by query params"""
        queryset = Evidence.objects.select_related('chunk', 'document')
        
        # Filter by document
        document_id = self.request.query_params.get('document_id')
        if document_id:
            queryset = queryset.filter(document_id=document_id)
        
        # Filter by case
        case_id = self.request.query_params.get('case_id')
        if case_id:
            queryset = queryset.filter(document__case_id=case_id)
        
        # Filter by project
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(document__project_id=project_id)
        
        # Filter by type
        evidence_type = self.request.query_params.get('type')
        if evidence_type:
            queryset = queryset.filter(type=evidence_type)
        
        # Filter by credibility rating
        min_rating = self.request.query_params.get('min_rating')
        if min_rating:
            queryset = queryset.filter(
                user_credibility_rating__gte=int(min_rating)
            )
        
        # Only show user's evidence
        queryset = queryset.filter(document__user=self.request.user)
        
        return queryset.order_by('-extracted_at')
    
    @action(detail=True, methods=['patch'])
    def rate(self, request, pk=None):
        """
        Rate the credibility of evidence.
        
        PATCH /api/evidence/{id}/rate/
        {
            "rating": 4
        }
        """
        evidence = self.get_object()
        serializer = RateEvidenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        evidence.user_credibility_rating = serializer.validated_data['rating']
        evidence.save(update_fields=['user_credibility_rating', 'updated_at'])
        
        return Response(self.get_serializer(evidence).data)
    
    @action(detail=False, methods=['get'])
    def high_confidence(self, request):
        """
        Get high-confidence evidence (confidence > 0.8 or user rating >= 4).
        
        GET /api/evidence/high_confidence/
        """
        queryset = self.get_queryset().filter(
            models.Q(extraction_confidence__gte=0.8) |
            models.Q(user_credibility_rating__gte=4)
        )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def link_signal(self, request, pk=None):
        """
        Link evidence to a signal (Phase 2.3)
        
        POST /api/evidence/{id}/link-signal/
        {
            "signal_id": "uuid",
            "relationship": "supports" | "contradicts"
        }
        """
        evidence = self.get_object()
        signal_id = request.data.get('signal_id')
        relationship = request.data.get('relationship')
        
        if not signal_id or not relationship:
            return Response(
                {'error': 'signal_id and relationship required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.signals.models import Signal
            signal = Signal.objects.get(id=signal_id, case__user=request.user)
            
            if relationship == 'supports':
                evidence.supports_signals.add(signal)
            elif relationship == 'contradicts':
                evidence.contradicts_signals.add(signal)
            else:
                return Response(
                    {'error': 'relationship must be supports or contradicts'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response(self.get_serializer(evidence).data)
            
        except Signal.DoesNotExist:
            return Response(
                {'error': 'signal_id not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def related_signals(self, request, pk=None):
        """
        Get signals related to this evidence (Phase 2.3)

        GET /api/evidence/{id}/related-signals/
        """
        from apps.signals.serializers import SignalSerializer

        evidence = self.get_object()

        supporting = evidence.supports_signals.all()
        contradicting = evidence.contradicts_signals.all()

        return Response({
            'supports': SignalSerializer(supporting, many=True).data,
            'contradicts': SignalSerializer(contradicting, many=True).data,
        })

    @action(detail=False, methods=['post'], url_path='ingest')
    def ingest_external(self, request):
        """
        Ingest external evidence (pasted text, URL content, etc.)
        through the universal ingestion pipeline.

        POST /api/evidence/ingest/
        {
            "case_id": "uuid",
            "items": [
                {
                    "text": "Market is growing 20% YoY...",
                    "source_url": "https://...",
                    "source_title": "Market Report 2025",
                    "evidence_type": "fact",
                    "source_published_date": "2025-03-15"
                }
            ],
            "source_label": "Perplexity Research"
        }
        """
        import dataclasses

        from apps.cases.models import Case
        from apps.projects.ingestion_service import EvidenceInput
        from tasks.ingestion_tasks import ingest_evidence_async

        case_id = request.data.get('case_id')
        items = request.data.get('items', [])

        if not case_id:
            return Response(
                {'error': 'case_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not items:
            return Response(
                {'error': 'items is required and must be non-empty'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            case = Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            return Response(
                {'error': 'Case not found or not owned by you'},
                status=status.HTTP_404_NOT_FOUND,
            )

        inputs = []
        for item in items:
            text = (item.get('text') or '').strip()
            if not text:
                continue
            inputs.append(dataclasses.asdict(EvidenceInput(
                text=text,
                evidence_type=item.get('evidence_type', 'fact'),
                extraction_confidence=float(item.get('confidence', 0.7)),
                source_url=item.get('source_url', ''),
                source_title=item.get('source_title', ''),
                source_published_date=item.get('source_published_date'),
                retrieval_method='external_paste',
            )))

        if not inputs:
            return Response(
                {'error': 'No valid evidence items (all empty text)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task = ingest_evidence_async.delay(
            inputs_data=inputs,
            case_id=str(case_id),
            user_id=request.user.id,
            source_label=request.data.get('source_label', 'External Research'),
        )

        return Response({
            'status': 'accepted',
            'task_id': task.id,
            'items_queued': len(inputs),
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['post'], url_path='fetch-url')
    def fetch_url(self, request):
        """
        Fetch a URL, extract its content, and ingest as evidence.

        Creates a Document from the fetched content and processes it
        through the full document pipeline (chunk → embed → extract → auto-reason).

        POST /api/evidence/fetch-url/
        {"url": "https://example.com/article", "case_id": "uuid"}
        """
        from apps.cases.models import Case
        from tasks.ingestion_tasks import fetch_url_and_ingest

        url = (request.data.get('url') or '').strip()
        case_id = request.data.get('case_id')

        if not url:
            return Response(
                {'error': 'url is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not case_id:
            return Response(
                {'error': 'case_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            return Response(
                {'error': 'Case not found or not owned by you'},
                status=status.HTTP_404_NOT_FOUND,
            )

        task = fetch_url_and_ingest.delay(
            url=url,
            case_id=str(case_id),
            user_id=request.user.id,
        )

        return Response({
            'status': 'accepted',
            'task_id': task.id,
        }, status=status.HTTP_202_ACCEPTED)
