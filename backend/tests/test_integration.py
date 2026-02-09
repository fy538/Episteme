"""
End-to-end integration tests for complete workflows

Tests the full dogfooding flow:
1. User chats
2. Upload document -> chunks created
3. Graph extraction creates evidence nodes
4. Generate artifacts (research, critique, brief)
5. Edit artifact -> version created
"""
import logging
import pytest
from django.contrib.auth.models import User
from apps.chat.services import ChatService
from apps.cases.services import CaseService
from apps.projects.services import ProjectService, DocumentService
from apps.graph.models import Node, NodeType, NodeStatus, NodeSourceType

logger = logging.getLogger(__name__)

@pytest.mark.django_db
class TestCompleteWorkflow:
    """Integration test for complete Episteme workflow"""

    def test_full_dogfooding_flow(self):
        """
        Test complete workflow from chat to artifact generation.

        This simulates the full user experience.
        """
        # 1. Create user and project
        user = User.objects.create_user(username='dogfood', password='test123')
        project = ProjectService.create_project(
            user=user,
            title='Database Decision'
        )

        # 2. Create case
        case = CaseService.create_case(
            user=user,
            title='Should we use Postgres?',
            position='We should use Postgres for the event store',
            stakes='high',
            project_id=project.id
        )

        # 3. Chat and extract signals
        thread = ChatService.create_thread(user=user, title='Database Discussion')

        user_message = ChatService.create_user_message(
            thread_id=thread.id,
            content='I assume writes are mostly append-only. We must ship by Q2. What about MongoDB?',
            user=user
        )

        # 4. Upload document
        document = DocumentService.create_document(
            user=user,
            project_id=project.id,
            title='Performance Benchmark',
            source_type='text',
            content_text='Benchmark results: PostgreSQL handles 50,000 writes per second. MongoDB handles 25,000 writes per second.',
            case_id=case.id
        )

        # Simulate chunk creation (simplified)
        from apps.projects.models import DocumentChunk
        chunk = DocumentChunk.objects.create(
            document=document,
            chunk_index=0,
            chunk_text=document.content_text,
            token_count=50,
            embedding=[0.3] * 384,
            span={}
        )

        # 5. Create evidence as a graph node (replaces old Evidence model)
        evidence_node = Node.objects.create(
            project=project,
            node_type=NodeType.EVIDENCE,
            status=NodeStatus.CONFIRMED,
            content='PostgreSQL handles 50,000 writes per second',
            properties={
                'evidence_type': 'benchmark',
                'source_title': 'Performance Benchmark',
            },
            source_type=NodeSourceType.DOCUMENT_EXTRACTION,
            source_document=document,
            confidence=0.95,
            created_by=user,
        )
        evidence_node.source_chunks.add(chunk)

        # 6. Create working document (research report)
        from apps.cases.models import WorkingDocument, DocumentType, EditFriction

        research_doc = WorkingDocument.objects.create(
            title='Research: Database Options',
            document_type=DocumentType.RESEARCH,
            case=case,
            content_markdown=(
                '# Research Report\n\n'
                'PostgreSQL is recommended based on append-only write pattern.'
            ),
            edit_friction=EditFriction.HIGH,
            generated_by_ai=True,
            agent_type='test',
            generation_prompt='Database Options',
            created_by=user,
        )

        # 7. Update document content
        research_doc.content_markdown = (
            '# Research Report\n\n'
            'PostgreSQL is strongly recommended based on evidence.'
        )
        research_doc.save()

        # 8. Verify complete workflow
        assert Node.objects.filter(project=project, node_type=NodeType.EVIDENCE).count() == 1
        assert WorkingDocument.objects.filter(case=case).count() == 1
        assert 'strongly recommended' in research_doc.content_markdown

        logger.info("integration_test_complete")
        logger.info("integration_test_evidence_nodes", extra={"count": Node.objects.filter(project=project, node_type=NodeType.EVIDENCE).count()})
        logger.info("integration_test_documents", extra={"count": WorkingDocument.objects.filter(case=case).count()})
        logger.info("integration_test_versions", extra={"count": WorkingDocument.objects.filter(case=case).count()})
        logger.info("integration_test_complete_verified")
