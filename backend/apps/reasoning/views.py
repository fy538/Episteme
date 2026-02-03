"""
API views for knowledge graph
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.cases.models import Case
from apps.signals.models import Signal
from apps.projects.models import Evidence
from apps.inquiries.models import Inquiry


class KnowledgeGraphViewSet(viewsets.ViewSet):
    """
    ViewSet for knowledge graph visualization.
    
    Provides endpoints to retrieve graph structure for a case.
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'], url_path='case/(?P<case_id>[^/.]+)')
    def case_graph(self, request, case_id=None):
        """
        Get knowledge graph for a case.
        
        GET /api/knowledge-graph/case/{case_id}/
        
        Returns nodes (signals, evidence, inquiries) and edges (relationships).
        """
        try:
            case = Case.objects.get(id=case_id, user=request.user)
        except Case.DoesNotExist:
            return Response(
                {'error': 'Case not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Build nodes and edges
        nodes = []
        edges = []
        
        # 1. Add inquiry nodes (largest)
        inquiries = Inquiry.objects.filter(case=case)
        for inquiry in inquiries:
            nodes.append({
                'id': f'inquiry-{inquiry.id}',
                'type': 'inquiry',
                'label': inquiry.title[:50],
                'confidence': inquiry.conclusion_confidence,
                'status': inquiry.status,
                'data': {
                    'full_title': inquiry.title,
                    'description': inquiry.description,
                    'conclusion': inquiry.conclusion
                }
            })
        
        # 2. Add signal nodes (medium)
        signals = Signal.objects.filter(
            case=case,
            dismissed_at__isnull=True
        ).prefetch_related('supported_by_evidence', 'contradicted_by_evidence', 'depends_on', 'contradicts')
        
        for signal in signals:
            nodes.append({
                'id': f'signal-{signal.id}',
                'type': 'signal',
                'label': signal.text[:40],
                'signalType': signal.type,
                'confidence': signal.confidence,
                'data': {
                    'full_text': signal.text,
                    'type': signal.type,
                    'status': signal.status
                }
            })
            
            # Add edges: signal → inquiry
            if signal.inquiry:
                edges.append({
                    'id': f'signal-{signal.id}-inquiry-{signal.inquiry.id}',
                    'source': f'signal-{signal.id}',
                    'target': f'inquiry-{signal.inquiry.id}',
                    'type': 'related_to',
                    'label': 'related to'
                })
            
            # Add edges: signal depends_on signal
            for dep in signal.depends_on.all():
                edges.append({
                    'id': f'signal-{signal.id}-depends-{dep.id}',
                    'source': f'signal-{signal.id}',
                    'target': f'signal-{dep.id}',
                    'type': 'depends_on',
                    'label': 'depends on'
                })
            
            # Add edges: signal contradicts signal
            for contra in signal.contradicts.all():
                edges.append({
                    'id': f'signal-{signal.id}-contradicts-{contra.id}',
                    'source': f'signal-{signal.id}',
                    'target': f'signal-{contra.id}',
                    'type': 'contradicts',
                    'label': 'contradicts'
                })
        
        # 3. Add evidence nodes (small - limit to most relevant)
        evidence_items = Evidence.objects.filter(
            document__case=case
        ).prefetch_related('supports_signals', 'contradicts_signals')[:50]  # Limit to 50
        
        for evidence in evidence_items:
            # Only include evidence that has relationships
            if evidence.supports_signals.exists() or evidence.contradicts_signals.exists():
                nodes.append({
                    'id': f'evidence-{evidence.id}',
                    'type': 'evidence',
                    'label': evidence.text[:30],
                    'evidenceType': evidence.type,
                    'strength': evidence.extraction_confidence,
                    'data': {
                        'full_text': evidence.text,
                        'type': evidence.type,
                        'document': evidence.document.title,
                        'credibility': evidence.user_credibility_rating
                    }
                })
                
                # Add edges: evidence → signal (supports)
                for signal in evidence.supports_signals.all():
                    edges.append({
                        'id': f'evidence-{evidence.id}-supports-{signal.id}',
                        'source': f'evidence-{evidence.id}',
                        'target': f'signal-{signal.id}',
                        'type': 'supports',
                        'label': 'supports',
                        'strength': evidence.extraction_confidence
                    })
                
                # Add edges: evidence → signal (contradicts)
                for signal in evidence.contradicts_signals.all():
                    edges.append({
                        'id': f'evidence-{evidence.id}-contradicts-{signal.id}',
                        'source': f'evidence-{evidence.id}',
                        'target': f'signal-{signal.id}',
                        'type': 'contradicts',
                        'label': 'contradicts',
                        'strength': evidence.extraction_confidence
                    })
        
        return Response({
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'inquiries': len([n for n in nodes if n['type'] == 'inquiry']),
                'signals': len([n for n in nodes if n['type'] == 'signal']),
                'evidence': len([n for n in nodes if n['type'] == 'evidence'])
            }
        })
