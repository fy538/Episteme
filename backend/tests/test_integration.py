"""
End-to-end integration tests for complete workflows

Tests the full dogfooding flow:
1. User chats → signals extracted
2. Upload document → evidence extracted
3. Link evidence to signals (graph)
4. Generate artifacts (research, critique, brief)
5. Edit artifact → version created
"""
import pytest
from django.contrib.auth.models import User
from apps.chat.services import ChatService
from apps.cases.services import CaseService
from apps.projects.services import ProjectService, DocumentService
from apps.signals.models import Signal
from apps.projects.models import Evidence
from apps.common.graph_utils import GraphUtils


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
        
        # Simulate signal extraction (would happen via Celery in real system)
        # For test, create signals manually
        assumption = Signal.objects.create(
            text='Writes are mostly append-only',
            type='Assumption',
            thread=thread,
            case=case,
            status='suggested',
            sequence_index=0,
            confidence=0.85,
            embedding=[0.1] * 384,  # Stub embedding
            event_id=user_message.event_id,
            source_type='chat_message',
            normalized_text='writes are mostly append only',
            dedupe_key='test_dedupe_1',
            span={}
        )
        
        constraint = Signal.objects.create(
            text='Must ship by Q2',
            type='Constraint',
            thread=thread,
            case=case,
            status='suggested',
            sequence_index=0,
            confidence=0.95,
            embedding=[0.2] * 384,
            event_id=user_message.event_id,
            source_type='chat_message',
            normalized_text='must ship by q2',
            dedupe_key='test_dedupe_2',
            span={}
        )
        
        # 4. Upload document and extract evidence
        document = DocumentService.create_document(
            user=user,
            project_id=project.id,
            title='Performance Benchmark',
            source_type='text',
            content_text='Benchmark results: PostgreSQL handles 50,000 writes per second. MongoDB handles 25,000 writes per second.',
            case_id=case.id
        )
        
        # Process document (creates chunks and evidence)
        # In real system, this happens via Celery
        # For test, create evidence manually
        
        # Simulate chunk creation (simplified)
        from apps.projects.models import DocumentChunk
        chunk = DocumentChunk.objects.create(
            document=document,
            chunk_index=0,
            chunk_text=document.content_text,
            token_count=50,
            embedding=[0.3] * 384,
            chunking_strategy='recursive_token',
            span={}
        )
        
        # Create evidence
        evidence = Evidence.objects.create(
            text='PostgreSQL handles 50,000 writes per second',
            type='benchmark',
            chunk=chunk,
            document=document,
            extraction_confidence=0.95,
            embedding=[0.3] * 384,
        )
        
        # 5. Link evidence to signal (knowledge graph)
        evidence.supports_signals.add(assumption)
        
        # 6. Verify graph queries work
        supporting_evidence = GraphUtils.get_supporting_evidence(assumption)
        assert len(supporting_evidence) == 1
        assert supporting_evidence[0].text == evidence.text
        
        strength = GraphUtils.get_evidence_strength(assumption)
        assert strength['support_count'] == 1
        assert strength['contradict_count'] == 0
        
        # 7. Create artifact (simplified - not using ADK in test)
        from apps.artifacts.models import Artifact, ArtifactVersion
        
        artifact = Artifact.objects.create(
            title='Research: Database Options',
            type='research',
            case=case,
            user=user,
            generated_by='test',
            version_count=1
        )
        
        version = ArtifactVersion.objects.create(
            artifact=artifact,
            version=1,
            blocks=[
                {
                    'id': 'block1',
                    'type': 'heading',
                    'content': 'Research Report',
                    'cites': []
                },
                {
                    'id': 'block2',
                    'type': 'paragraph',
                    'content': 'PostgreSQL is recommended based on append-only write pattern.',
                    'cites': [str(assumption.id), str(evidence.id)]
                }
            ],
            created_by=user
        )
        
        artifact.current_version = version
        artifact.save()
        
        # Link inputs
        artifact.input_signals.add(assumption)
        artifact.input_evidence.add(evidence)
        
        # 8. Edit artifact (creates new version)
        new_blocks = version.blocks.copy()
        new_blocks[1]['content'] = 'PostgreSQL is strongly recommended based on evidence.'
        
        version_2 = ArtifactVersion.objects.create(
            artifact=artifact,
            version=2,
            blocks=new_blocks,
            parent_version=version,
            diff={
                'modified_blocks': [{
                    'block_id': 'block2',
                    'old_content': version.blocks[1]['content'],
                    'new_content': new_blocks[1]['content']
                }]
            },
            created_by=user
        )
        
        artifact.current_version = version_2
        artifact.version_count = 2
        artifact.save()
        
        # 9. Verify complete workflow
        assert Signal.objects.filter(case=case).count() == 2
        assert Evidence.objects.filter(document__case=case).count() == 1
        assert Artifact.objects.filter(case=case).count() == 1
        assert artifact.version_count == 2
        assert len(artifact.current_version.blocks) == 2
        assert artifact.input_signals.count() == 1
        assert artifact.input_evidence.count() == 1
        
        print("✅ Complete integration test passed!")
        print(f"   - Signals: {Signal.objects.filter(case=case).count()}")
        print(f"   - Evidence: {Evidence.objects.filter(document__case=case).count()}")
        print(f"   - Artifacts: {Artifact.objects.filter(case=case).count()}")
        print(f"   - Artifact versions: {artifact.version_count}")
        print(f"   - Graph links: {assumption.supported_by_evidence.count()} evidence supports")
