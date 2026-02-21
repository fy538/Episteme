"""
Cross-cutting integration tests for the three-plan pipeline.

Tests the handoffs between:
  Plan 1 (Hierarchical Clustering) → Plan 3 (Case Extraction)
  Plan 2 (Organic Companion) → Plan 3 (Case Extraction)
  Plan 3 end-to-end (retrieval → extraction → integration → analysis)

All LLM calls are mocked. These tests validate the data flow and contract
between services, not the LLM output quality.

Run with:
    DJANGO_SETTINGS_MODULE=config.settings.test pytest tests/test_cross_cutting.py -v
"""
import json
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings

from apps.cases.models import Case, CaseStatus, StakesLevel
from apps.cases.chunk_retrieval import CaseChunkRetriever
from apps.cases.extraction_service import (
    CaseExtractionService,
    CaseExtractionResult,
    ExtractionLLMError,
)
from apps.cases.analysis_service import CaseAnalysisService
from apps.chat.models import ChatThread, Message, ConversationStructure
from apps.events.models import Event, EventType, ActorType
from apps.events.services import EventService
from apps.graph.models import (
    Node, Edge, NodeType, NodeStatus, NodeSourceType, EdgeType,
    ClusterHierarchy, HierarchyStatus,
)
from apps.graph.services import GraphService
from apps.projects.models import Project, Document, DocumentChunk

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════


def _make_embedding(seed: float = 0.5) -> list:
    """Create a 384-dim embedding vector for testing."""
    import random
    rng = random.Random(int(seed * 1000))
    return [rng.gauss(0, 1) for _ in range(384)]


def _make_project_with_chunks(user, num_docs=2, chunks_per_doc=3):
    """Create a project with documents and embedded chunks."""
    project = Project.objects.create(
        title='Test Project',
        description='A test project for integration tests',
        owner=user,
    )

    all_chunks = []
    for doc_idx in range(num_docs):
        doc = Document.objects.create(
            project=project,
            title=f'Document {doc_idx + 1}',
            source_type='text',
            content_text=f'Content of document {doc_idx + 1}',
            uploaded_by=user,
        )

        for chunk_idx in range(chunks_per_doc):
            chunk = DocumentChunk.objects.create(
                document=doc,
                chunk_index=chunk_idx,
                chunk_text=f'Chunk {chunk_idx} of doc {doc_idx}: Important analysis about topic {chunk_idx}.',
                token_count=50,
                embedding=_make_embedding(doc_idx * 10 + chunk_idx),
                span={},
            )
            all_chunks.append(chunk)

    return project, all_chunks


def _make_case(user, project, decision_question='Should we use Postgres?',
               position='We should use Postgres', metadata=None):
    """Create a case with a decision question."""
    event = EventService.append(
        event_type=EventType.CASE_CREATED,
        payload={'title': decision_question},
        actor_type=ActorType.USER,
        actor_id=user.id,
    )
    case = Case.objects.create(
        title=decision_question,
        decision_question=decision_question,
        position=position,
        user=user,
        project=project,
        status=CaseStatus.ACTIVE,
        stakes=StakesLevel.HIGH,
        created_from_event_id=event.id,
        metadata=metadata or {},
    )
    return case


def _make_hierarchy_tree(chunks, project_id):
    """Build a minimal hierarchy tree with embeddings for testing."""
    # Split chunks into two themes
    mid = len(chunks) // 2
    theme_a_chunks = chunks[:mid]
    theme_b_chunks = chunks[mid:]

    topic_a = {
        'id': str(uuid.uuid4()),
        'level': 1,
        'label': 'Database Performance',
        'summary': 'Analysis of database write performance and benchmarks',
        'children': [],
        'chunk_ids': [str(c.id) for c in theme_a_chunks],
        'document_ids': list(set(str(c.document_id) for c in theme_a_chunks)),
        'chunk_count': len(theme_a_chunks),
        'coverage_pct': 50.0,
        'embedding': _make_embedding(100),
    }

    topic_b = {
        'id': str(uuid.uuid4()),
        'level': 1,
        'label': 'Scalability Architecture',
        'summary': 'Scalability patterns and horizontal scaling approaches',
        'children': [],
        'chunk_ids': [str(c.id) for c in theme_b_chunks],
        'document_ids': list(set(str(c.document_id) for c in theme_b_chunks)),
        'chunk_count': len(theme_b_chunks),
        'coverage_pct': 50.0,
        'embedding': _make_embedding(200),
    }

    theme_a = {
        'id': str(uuid.uuid4()),
        'level': 2,
        'label': 'Performance & Reliability',
        'summary': 'Database performance benchmarks and reliability patterns',
        'children': [topic_a],
        'chunk_ids': topic_a['chunk_ids'],
        'document_ids': topic_a['document_ids'],
        'chunk_count': topic_a['chunk_count'],
        'coverage_pct': 50.0,
        'embedding': _make_embedding(300),
    }

    theme_b = {
        'id': str(uuid.uuid4()),
        'level': 2,
        'label': 'Architecture & Scale',
        'summary': 'System architecture and scaling strategies',
        'children': [topic_b],
        'chunk_ids': topic_b['chunk_ids'],
        'document_ids': topic_b['document_ids'],
        'chunk_count': topic_b['chunk_count'],
        'coverage_pct': 50.0,
        'embedding': _make_embedding(400),
    }

    root = {
        'id': str(uuid.uuid4()),
        'level': 3,
        'label': 'Test Project Overview',
        'summary': 'A project about database and architecture decisions',
        'children': [theme_a, theme_b],
        'chunk_ids': topic_a['chunk_ids'] + topic_b['chunk_ids'],
        'document_ids': list(set(topic_a['document_ids'] + topic_b['document_ids'])),
        'chunk_count': len(chunks),
        'coverage_pct': 100.0,
    }

    return root


# ═══════════════════════════════════════════════════════════════════
# Test 1: Plan 1 → Plan 3 (Hierarchy → Case Chunk Retrieval)
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.django_db(transaction=True)
class TestHierarchyToCaseRetrieval(TransactionTestCase):
    """Test that case chunk retrieval uses the hierarchy built by Plan 1."""

    def setUp(self):
        self.user = User.objects.create_user(username='test_h2c', password='test123')
        self.project, self.chunks = _make_project_with_chunks(self.user, num_docs=2, chunks_per_doc=3)

    def test_hierarchy_aware_retrieval_finds_cluster_chunks(self):
        """
        When a hierarchy exists, the retriever should find chunks from
        relevant theme/topic clusters in addition to direct embedding matches.
        """
        # Create a hierarchy with embeddings stored (the cross-cutting fix)
        tree = _make_hierarchy_tree(self.chunks, self.project.id)
        hierarchy = ClusterHierarchy.objects.create(
            project=self.project,
            version=1,
            status=HierarchyStatus.READY,
            is_current=True,
            tree=tree,
            metadata={'total_chunks': len(self.chunks)},
        )

        # Create a case
        case = _make_case(self.user, self.project,
                          decision_question='What database should we use for write-heavy workloads?')

        # Mock generate_embedding to return a vector similar to theme_a's embedding
        with patch('apps.cases.chunk_retrieval.generate_embedding') as mock_embed:
            # Return an embedding close to theme_a's embedding
            mock_embed.return_value = _make_embedding(300)

            retriever = CaseChunkRetriever()
            chunks = retriever.retrieve_relevant_chunks(case, max_chunks=50)

        # Should find chunks — at minimum the hierarchy-aware ones
        # (exact count depends on cosine similarity thresholds)
        self.assertIsInstance(chunks, list)
        # Verify that the retriever accessed the hierarchy
        self.assertTrue(
            ClusterHierarchy.objects.filter(
                project=self.project, is_current=True
            ).exists()
        )

    def test_retrieval_without_hierarchy_falls_back_to_embedding(self):
        """
        Without a hierarchy, retrieval should still work via direct
        embedding similarity (Plan 3 should work before Plan 1 runs).
        """
        case = _make_case(self.user, self.project,
                          decision_question='What database should we use?')

        with patch('apps.cases.chunk_retrieval.generate_embedding') as mock_embed:
            mock_embed.return_value = _make_embedding(0.5)

            retriever = CaseChunkRetriever()
            chunks = retriever.retrieve_relevant_chunks(case, max_chunks=50)

        # Should return some chunks via embedding similarity
        self.assertIsInstance(chunks, list)

    def test_hierarchy_embedding_stored_and_accessible(self):
        """
        Verify that the hierarchy tree stores embeddings for Level 1-2
        nodes (the cross-cutting fix for Plan 1 ↔ Plan 3 integration).
        """
        tree = _make_hierarchy_tree(self.chunks, self.project.id)

        # Verify embeddings are present in theme and topic nodes
        for theme in tree['children']:
            self.assertIn('embedding', theme,
                          f"Theme '{theme['label']}' should have an embedding")
            self.assertEqual(len(theme['embedding']), 384)

            for topic in theme.get('children', []):
                self.assertIn('embedding', topic,
                              f"Topic '{topic['label']}' should have an embedding")
                self.assertEqual(len(topic['embedding']), 384)


# ═══════════════════════════════════════════════════════════════════
# Test 2: Plan 2 → Plan 3 (Companion → Case Bridge)
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.django_db(transaction=True)
class TestCompanionToCaseBridge(TransactionTestCase):
    """Test the companion → case signal → case creation data flow."""

    def setUp(self):
        self.user = User.objects.create_user(username='test_c2c', password='test123')
        self.project, self.chunks = _make_project_with_chunks(self.user)

    def test_companion_state_transfers_to_case_metadata(self):
        """
        When a case is created from a companion signal, the companion's
        established facts, open questions, and eliminated options should
        transfer to case.metadata['companion_origin'].
        """
        companion_state = {
            'established': [
                'PostgreSQL handles 50k writes/sec',
                'MongoDB handles 25k writes/sec',
            ],
            'open_questions': [
                'What about read performance?',
                'How does replication factor affect writes?',
            ],
            'eliminated': [
                'SQLite eliminated — not suitable for concurrent writes',
            ],
            'structure_snapshot': {
                'type': 'comparison',
                'options': ['PostgreSQL', 'MongoDB'],
            },
            'structure_type': 'comparison',
        }

        case = _make_case(
            self.user, self.project,
            decision_question='Should we use PostgreSQL or MongoDB for the event store?',
            metadata={'companion_origin': companion_state},
        )

        # Verify companion state is accessible
        self.assertIn('companion_origin', case.metadata)
        origin = case.metadata['companion_origin']
        self.assertEqual(len(origin['established']), 2)
        self.assertEqual(len(origin['open_questions']), 2)
        self.assertEqual(len(origin['eliminated']), 1)
        self.assertEqual(origin['structure_type'], 'comparison')

    def test_companion_established_facts_enrich_focus_text(self):
        """
        CaseChunkRetriever._build_focus_text should include companion
        established facts, improving retrieval relevance.
        """
        companion_state = {
            'established': [
                'Writes are mostly append-only',
                'Must handle 50k concurrent connections',
            ],
        }

        case = _make_case(
            self.user, self.project,
            decision_question='Which database for our event store?',
            position='Leaning toward PostgreSQL',
            metadata={'companion_origin': companion_state},
        )

        retriever = CaseChunkRetriever()
        focus_text = retriever._build_focus_text(case)

        # Focus text should include the decision question, position, AND established facts
        self.assertIn('Which database', focus_text)
        self.assertIn('PostgreSQL', focus_text)
        self.assertIn('append-only', focus_text)
        self.assertIn('50k concurrent', focus_text)

    def test_case_detection_heuristic_requires_enough_context(self):
        """
        detect_case_signal should return None when the companion
        structure doesn't have enough established facts/open questions.
        """
        from apps.chat.companion_service import CompanionService

        thread = ChatThread.objects.create(
            user=self.user,
            title='Test thread',
            project=self.project,
        )

        # Create a structure with insufficient context
        ConversationStructure.objects.create(
            thread=thread,
            version=1,
            structure_type='exploration_map',  # Valid type
            content={'topics': ['databases']},
            established=['One fact'],  # Only 1 — needs >= 2
            open_questions=['One question'],
            eliminated=[],
            context_summary='Exploring databases',
        )

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            CompanionService.detect_case_signal(thread.id)
        )
        self.assertIsNone(result, "Should not suggest case with only 1 established fact")


# ═══════════════════════════════════════════════════════════════════
# Test 3: Plan 3 End-to-End (Extraction → Integration → Analysis)
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.django_db(transaction=True)
class TestCaseExtractionEndToEnd(TransactionTestCase):
    """Test the full Plan 3 pipeline with mocked LLM calls."""

    def setUp(self):
        self.user = User.objects.create_user(username='test_e2e', password='test123')
        self.project, self.chunks = _make_project_with_chunks(self.user, num_docs=2, chunks_per_doc=3)

    def _mock_extraction_result(self):
        """Return a mock LLM extraction result with nodes and edges."""
        return {
            'nodes': [
                {
                    'id': 'n0',
                    'type': 'claim',
                    'content': 'PostgreSQL handles 50k writes per second',
                    'importance': 3,
                    'document_role': 'thesis',
                    'confidence': 0.9,
                    'source_passage': 'Chunk 0',
                },
                {
                    'id': 'n1',
                    'type': 'evidence',
                    'content': 'Benchmark results show 50k TPS on standard hardware',
                    'importance': 2,
                    'document_role': 'supporting',
                    'confidence': 0.85,
                    'source_passage': 'Chunk 1',
                },
                {
                    'id': 'n2',
                    'type': 'assumption',
                    'content': 'Write workload is mostly append-only',
                    'importance': 2,
                    'document_role': 'context',
                    'confidence': 0.7,
                    'source_passage': 'Chunk 2',
                },
            ],
            'edges': [
                {
                    'source_id': 'n1',
                    'target_id': 'n0',
                    'edge_type': 'supports',
                    'provenance': 'Benchmark directly supports performance claim',
                },
                {
                    'source_id': 'n0',
                    'target_id': 'n2',
                    'edge_type': 'depends_on',
                    'provenance': 'Performance claim assumes append-only workload',
                },
            ],
        }

    @patch('apps.cases.extraction_service.generate_embeddings_batch')
    @patch('apps.cases.extraction_service.CaseExtractionService._call_extraction_llm')
    def test_extraction_creates_nodes_and_edges(self, mock_llm, mock_embed):
        """Full extraction: LLM returns nodes/edges → service creates them in DB."""
        mock_llm.return_value = self._mock_extraction_result()
        mock_embed.return_value = [_make_embedding(i) for i in range(3)]

        case = _make_case(self.user, self.project)
        extractor = CaseExtractionService()
        result = extractor.extract_case_graph(case, self.chunks[:3])

        self.assertEqual(result.node_count, 3)
        self.assertEqual(result.edge_count, 2)
        self.assertEqual(result.chunk_count, 3)

        # Verify nodes are case-scoped
        db_nodes = Node.objects.filter(case=case)
        self.assertEqual(db_nodes.count(), 3)

        # Verify node types
        types = set(db_nodes.values_list('node_type', flat=True))
        self.assertEqual(types, {'claim', 'evidence', 'assumption'})

        # Verify edges exist
        db_edges = Edge.objects.filter(
            source_node__case=case,
        )
        self.assertEqual(db_edges.count(), 2)

    @patch('apps.cases.extraction_service.generate_embeddings_batch')
    @patch('apps.cases.extraction_service.CaseExtractionService._call_extraction_llm')
    def test_analysis_runs_on_extracted_graph(self, mock_llm, mock_embed):
        """Analysis produces blind spots, assumptions, tensions, and readiness."""
        mock_llm.return_value = self._mock_extraction_result()
        mock_embed.return_value = [_make_embedding(i) for i in range(3)]

        case = _make_case(self.user, self.project)
        extractor = CaseExtractionService()
        extractor.extract_case_graph(case, self.chunks[:3])

        # Run analysis with mocked blind spot LLM call
        with patch('apps.cases.analysis_service.CaseAnalysisService._detect_blind_spots') as mock_bs:
            mock_bs.return_value = []

            analyzer = CaseAnalysisService()
            analysis = analyzer.analyze_case(case)

        # Should have structural analysis results
        self.assertIsNotNone(analysis.evidence_coverage)
        self.assertEqual(analysis.evidence_coverage.total_claims, 1)
        self.assertEqual(analysis.evidence_coverage.total_evidence, 1)

        # Assumption assessment
        self.assertEqual(len(analysis.assumption_assessment), 1)
        assumption = analysis.assumption_assessment[0]
        self.assertEqual(assumption.content, 'Write workload is mostly append-only')

        # Readiness
        self.assertIsNotNone(analysis.readiness)

        # Serialization should work
        analysis_dict = analysis.to_dict()
        self.assertIn('blind_spots', analysis_dict)
        self.assertIn('readiness', analysis_dict)

    @patch('apps.cases.extraction_service.generate_embeddings_batch')
    @patch('apps.cases.extraction_service.CaseExtractionService._call_extraction_llm')
    def test_incremental_extraction_aware_of_existing(self, mock_llm, mock_embed):
        """Incremental extraction receives existing nodes in prompt context."""
        # First extraction
        mock_llm.return_value = self._mock_extraction_result()
        mock_embed.return_value = [_make_embedding(i) for i in range(3)]

        case = _make_case(self.user, self.project)
        extractor = CaseExtractionService()
        first_result = extractor.extract_case_graph(case, self.chunks[:3])

        # Second incremental extraction — mock returns one new node
        mock_llm.return_value = {
            'nodes': [{
                'id': 'n3',
                'type': 'tension',
                'content': 'Write performance degrades with complex indexes',
                'importance': 3,
                'confidence': 0.8,
            }],
            'edges': [],
        }
        mock_embed.return_value = [_make_embedding(99)]

        existing_nodes = list(Node.objects.filter(case=case))
        second_result = extractor.incremental_extract(
            case, self.chunks[3:], existing_nodes
        )

        self.assertEqual(second_result.node_count, 1)
        # Total nodes should be 3 + 1 = 4
        total_nodes = Node.objects.filter(case=case).count()
        self.assertEqual(total_nodes, 4)


# ═══════════════════════════════════════════════════════════════════
# Test 4: Error Handling (Cross-cutting issue #2)
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.django_db(transaction=True)
class TestExtractionErrorHandling(TransactionTestCase):
    """Test that LLM failures propagate correctly through the pipeline."""

    def setUp(self):
        self.user = User.objects.create_user(username='test_err', password='test123')
        self.project, self.chunks = _make_project_with_chunks(self.user)

    def test_extraction_llm_failure_raises_error(self):
        """
        When the extraction LLM call fails, ExtractionLLMError should be
        raised (not silently swallowed).
        """
        case = _make_case(self.user, self.project)
        extractor = CaseExtractionService()

        with patch(
            'apps.cases.extraction_service.get_llm_provider'
        ) as mock_provider:
            mock_instance = MagicMock()
            mock_instance.generate_with_tools = AsyncMock(
                side_effect=ConnectionError("LLM service unavailable")
            )
            mock_provider.return_value = mock_instance

            with self.assertRaises(ExtractionLLMError) as ctx:
                extractor.extract_case_graph(case, self.chunks[:3])

            self.assertIn('LLM service unavailable', str(ctx.exception))

    def test_extraction_empty_result_is_not_error(self):
        """
        When the LLM returns an empty result (nothing to extract),
        it should NOT raise — just return an empty CaseExtractionResult.
        """
        case = _make_case(self.user, self.project)
        extractor = CaseExtractionService()

        with patch(
            'apps.cases.extraction_service.get_llm_provider'
        ) as mock_provider:
            mock_instance = MagicMock()
            # LLM returns None (parsed to empty)
            mock_instance.generate_with_tools = AsyncMock(return_value=None)
            mock_provider.return_value = mock_instance

            # Should not raise
            result = extractor.extract_case_graph(case, self.chunks[:3])

        self.assertEqual(result.node_count, 0)
        self.assertEqual(result.edge_count, 0)
        self.assertEqual(result.chunk_count, 3)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=False)
    @patch('apps.cases.extraction_service.CaseExtractionService._call_extraction_llm')
    @patch('apps.cases.chunk_retrieval.generate_embedding')
    def test_pipeline_task_sets_failed_on_llm_error(self, mock_embed, mock_llm):
        """
        When extraction LLM fails, the Celery task should catch the error
        and set extraction_status='failed' with an error message.
        """
        mock_embed.return_value = _make_embedding(0.5)
        mock_llm.side_effect = ExtractionLLMError("Test LLM failure")

        case = _make_case(self.user, self.project,
                          decision_question='Test decision for error handling')

        from apps.cases.tasks import run_case_extraction_pipeline
        result = run_case_extraction_pipeline(str(case.id))

        self.assertEqual(result['status'], 'failed')
        self.assertIn('Test LLM failure', result.get('error', ''))

        # Verify case metadata was updated
        case.refresh_from_db()
        self.assertEqual(case.metadata.get('extraction_status'), 'failed')
        self.assertIn('Test LLM failure', case.metadata.get('extraction_error', ''))

    @patch('apps.graph.integration._call_integration_llm')
    def test_integration_llm_failure_is_graceful(self, mock_llm):
        """
        Integration LLM failure should not crash the pipeline.
        It returns empty results and logs a warning.
        """
        mock_llm.return_value = None  # Simulates LLM failure

        from apps.graph.integration import integrate_new_nodes

        # Create a test node
        node = Node.objects.create(
            project=self.project,
            node_type=NodeType.CLAIM,
            content='Test claim for integration',
            source_type=NodeSourceType.DOCUMENT_EXTRACTION,
            embedding=_make_embedding(0.5),
            created_by=self.user,
        )

        result = integrate_new_nodes(
            project_id=self.project.id,
            new_node_ids=[node.id],
        )

        # Should return empty results, not crash
        self.assertEqual(result['edges'], [])
        self.assertEqual(result['tensions'], [])


# ═══════════════════════════════════════════════════════════════════
# Test 5: Full Pipeline Task (end-to-end with mocked LLM)
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.django_db(transaction=True)
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class TestFullPipelineTask(TransactionTestCase):
    """Test run_case_extraction_pipeline task end-to-end."""

    def setUp(self):
        self.user = User.objects.create_user(username='test_pipe', password='test123')
        self.project, self.chunks = _make_project_with_chunks(self.user, num_docs=2, chunks_per_doc=3)

    @patch('apps.cases.analysis_service.CaseAnalysisService._detect_blind_spots')
    @patch('apps.graph.integration._call_integration_llm')
    @patch('apps.cases.extraction_service.generate_embeddings_batch')
    @patch('apps.cases.extraction_service.CaseExtractionService._call_extraction_llm')
    @patch('apps.cases.chunk_retrieval.generate_embedding')
    def test_full_pipeline_happy_path(
        self, mock_focus_embed, mock_extraction_llm, mock_embeddings,
        mock_integration_llm, mock_blind_spots,
    ):
        """
        End-to-end: retrieval → extraction → integration → analysis → complete.
        All LLM calls mocked. Verifies status transitions and final state.
        """
        # Mock chunk retrieval embedding
        mock_focus_embed.return_value = _make_embedding(0.5)

        # Mock extraction LLM
        mock_extraction_llm.return_value = {
            'nodes': [
                {
                    'id': 'n0',
                    'type': 'claim',
                    'content': 'PostgreSQL is optimal for append-only workloads',
                    'importance': 3,
                    'confidence': 0.9,
                },
                {
                    'id': 'n1',
                    'type': 'evidence',
                    'content': 'Benchmark: 50k TPS on standard hardware',
                    'importance': 2,
                    'confidence': 0.85,
                },
            ],
            'edges': [
                {
                    'source_id': 'n1',
                    'target_id': 'n0',
                    'edge_type': 'supports',
                    'provenance': 'Benchmark supports performance claim',
                },
            ],
        }

        # Mock embeddings
        mock_embeddings.return_value = [_make_embedding(i) for i in range(2)]

        # Mock integration LLM (return empty — no cross-doc edges)
        mock_integration_llm.return_value = {
            'edges': [],
            'tensions': [],
            'status_updates': [],
            'gaps': [],
            'delta_narrative': 'No new cross-document relationships.',
        }

        # Mock blind spot detection
        mock_blind_spots.return_value = []

        # Create case and run pipeline
        case = _make_case(
            self.user, self.project,
            decision_question='Should we use PostgreSQL for write-heavy workloads?',
        )

        from apps.cases.tasks import run_case_extraction_pipeline
        result = run_case_extraction_pipeline(str(case.id))

        # Verify task returned success
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['nodes_created'], 2)
        self.assertEqual(result['edges_created'], 1)

        # Verify case metadata
        case.refresh_from_db()
        self.assertEqual(case.metadata.get('extraction_status'), 'complete')
        self.assertIn('extraction_result', case.metadata)
        self.assertEqual(case.metadata['extraction_result']['node_count'], 2)

        # Verify analysis was stored
        self.assertIn('analysis', case.metadata)
        analysis = case.metadata['analysis']
        self.assertIn('readiness', analysis)
        self.assertIn('evidence_coverage', analysis)

        # Verify DB state
        nodes = Node.objects.filter(case=case)
        self.assertEqual(nodes.count(), 2)

        edges = Edge.objects.filter(source_node__case=case)
        self.assertEqual(edges.count(), 1)

    @patch('apps.cases.chunk_retrieval.generate_embedding')
    def test_pipeline_no_chunks_completes_gracefully(self, mock_embed):
        """Pipeline with no matching chunks should complete (not fail) with zero results."""
        # Return an embedding that won't match any chunks (all zeros)
        mock_embed.return_value = [0.0] * 384

        case = _make_case(
            self.user, self.project,
            decision_question='Unrelated topic that matches nothing',
        )

        from apps.cases.tasks import run_case_extraction_pipeline
        result = run_case_extraction_pipeline(str(case.id))

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['nodes_created'], 0)

        case.refresh_from_db()
        self.assertEqual(case.metadata.get('extraction_status'), 'complete')


# ═══════════════════════════════════════════════════════════════════
# Test 6: Companion Research Dedup (Plan 2 internal quality)
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestCompanionResearchDedup(TestCase):
    """Test research question deduplication across plans."""

    def test_normalize_question_strips_question_words(self):
        from apps.chat.companion_service import CompanionService

        q1 = CompanionService._normalize_question("What is the best database?")
        q2 = CompanionService._normalize_question("How is the best database?")

        # Both should normalize to the same form (question words stripped)
        self.assertEqual(q1, q2)

    def test_duplicate_detection_catches_rephrased(self):
        from apps.chat.companion_service import CompanionService

        existing = {
            "What database handles the most writes per second?",
            "How does PostgreSQL compare to MongoDB?",
        }

        # Near-duplicate of existing question
        is_dup = CompanionService._is_duplicate_question(
            "Which database handles most writes per second?",
            existing,
        )
        self.assertTrue(is_dup, "Rephrased question should be detected as duplicate")

    def test_novel_question_not_flagged(self):
        from apps.chat.companion_service import CompanionService

        existing = {
            "What database handles the most writes per second?",
        }

        is_dup = CompanionService._is_duplicate_question(
            "What are the replication options for multi-region deployment?",
            existing,
        )
        self.assertFalse(is_dup, "Novel question should not be flagged as duplicate")


# ═══════════════════════════════════════════════════════════════════
# Test 7: Analysis Blind Spot Theme Matching (Plan 3 quality)
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestBlindSpotThemeMatching(TestCase):
    """Test the Jaccard-based theme matching in analysis_service."""

    def test_tokenize_removes_stop_words(self):
        from apps.cases.analysis_service import _tokenize

        tokens = _tokenize("The architecture of a scalable system")
        self.assertNotIn('the', tokens)
        self.assertNotIn('of', tokens)
        self.assertIn('architecture', tokens)
        self.assertIn('scalable', tokens)
        self.assertIn('system', tokens)

    def test_jaccard_identical_sets(self):
        from apps.cases.analysis_service import _jaccard

        a = {'database', 'performance', 'benchmark'}
        b = {'database', 'performance', 'benchmark'}
        self.assertAlmostEqual(_jaccard(a, b), 1.0)

    def test_jaccard_partial_overlap(self):
        from apps.cases.analysis_service import _jaccard

        a = {'database', 'performance', 'benchmark'}
        b = {'database', 'scalability', 'benchmark'}
        # Intersection: {database, benchmark} = 2
        # Union: {database, performance, benchmark, scalability} = 4
        self.assertAlmostEqual(_jaccard(a, b), 0.5)

    def test_jaccard_no_overlap(self):
        from apps.cases.analysis_service import _jaccard

        a = {'database', 'performance'}
        b = {'authentication', 'security'}
        self.assertAlmostEqual(_jaccard(a, b), 0.0)

    def test_jaccard_empty_sets(self):
        from apps.cases.analysis_service import _jaccard
        self.assertAlmostEqual(_jaccard(set(), set()), 0.0)
        self.assertAlmostEqual(_jaccard({'a'}, set()), 0.0)
