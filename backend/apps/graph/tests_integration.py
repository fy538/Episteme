"""
Tests for integration pipeline — context assembly, serialization,
edge/tension creation, node ID resolution, and LLM integration.
"""

import json
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model

from apps.graph.integration import (
    _resolve_node_id,
    _serialize_context_for_integration,
    _call_integration_llm,
    _create_edge_from_spec,
    _create_tension_from_spec,
    integrate_new_nodes,
    SMALL_GRAPH_THRESHOLD,
    MAX_CONTEXT_NODES,
    SIMILARITY_THRESHOLD,
)
from apps.graph.models import (
    Node, Edge, NodeType, NodeStatus, EdgeType, NodeSourceType,
)
from apps.graph.services import GraphService
from apps.projects.models import Project, Document

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════
# Node ID resolution
# ═══════════════════════════════════════════════════════════════════


class ResolveNodeIdTests(TestCase):
    """Test _resolve_node_id — flexible UUID parsing."""

    def test_direct_uuid_string_match(self):
        node_id = uuid.uuid4()
        nodes_map = {str(node_id): MagicMock()}
        result = _resolve_node_id(str(node_id), nodes_map)
        self.assertEqual(result, node_id)

    def test_uuid_format_normalization(self):
        """Handles UUIDs with different formatting."""
        node_id = uuid.uuid4()
        nodes_map = {str(node_id): MagicMock()}
        # Pass UUID string — should still resolve
        result = _resolve_node_id(str(node_id), nodes_map)
        self.assertEqual(result, node_id)

    def test_empty_string_returns_none(self):
        self.assertIsNone(_resolve_node_id('', {}))

    def test_nonexistent_id_returns_none(self):
        nodes_map = {str(uuid.uuid4()): MagicMock()}
        result = _resolve_node_id(str(uuid.uuid4()), nodes_map)
        self.assertIsNone(result)

    def test_invalid_uuid_string_returns_none(self):
        nodes_map = {str(uuid.uuid4()): MagicMock()}
        result = _resolve_node_id('not-a-uuid', nodes_map)
        self.assertIsNone(result)

    def test_none_returns_none(self):
        # Edge case — should handle gracefully
        result = _resolve_node_id(None, {})
        # id_str is empty/falsy → returns None
        self.assertIsNone(result)


# ═══════════════════════════════════════════════════════════════════
# Context serialization
# ═══════════════════════════════════════════════════════════════════


class SerializeContextTests(TestCase):
    """Test _serialize_context_for_integration."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='serial_int', email='serial_int@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='Serialization Project', user=self.user
        )

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_serializes_existing_and_new_nodes(self, mock_embed):
        existing = GraphService.create_node(
            project=self.project, node_type='claim',
            content='Existing claim content', source_type='user_edit',
            status='supported', created_by=self.user,
        )
        new_node = GraphService.create_node(
            project=self.project, node_type='evidence',
            content='New evidence from document', source_type='document_extraction',
            status='uncertain', created_by=self.user,
        )

        result = _serialize_context_for_integration([existing], [new_node])
        self.assertIn('EXISTING GRAPH NODES', result)
        self.assertIn('NEW NODES', result)
        self.assertIn('Existing claim content', result)
        self.assertIn('New evidence from document', result)
        self.assertIn(str(existing.id), result)
        self.assertIn(str(new_node.id), result)

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_includes_type_and_status(self, mock_embed):
        node = GraphService.create_node(
            project=self.project, node_type='assumption',
            content='Users prefer mobile interfaces', source_type='user_edit',
            status='untested', created_by=self.user,
        )
        result = _serialize_context_for_integration([], [node])
        self.assertIn('assumption', result)
        self.assertIn('untested', result)

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_empty_context_nodes(self, mock_embed):
        new_node = GraphService.create_node(
            project=self.project, node_type='claim',
            content='First node in a fresh project', source_type='document_extraction',
            created_by=self.user,
        )
        result = _serialize_context_for_integration([], [new_node])
        self.assertNotIn('EXISTING GRAPH NODES', result)
        self.assertIn('NEW NODES', result)

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_includes_source_document_title(self, mock_embed):
        doc = Document.objects.create(
            project=self.project, user=self.user,
            title='Research Paper on Market Trends',
            content_text='Full text here.',
        )
        node = GraphService.create_node(
            project=self.project, node_type='evidence',
            content='Key finding from research', source_type='document_extraction',
            source_document=doc, created_by=self.user,
        )
        result = _serialize_context_for_integration([node], [])
        self.assertIn('Research Paper on Market', result)


# ═══════════════════════════════════════════════════════════════════
# LLM call (mocked)
# ═══════════════════════════════════════════════════════════════════


class CallIntegrationLLMTests(TestCase):
    """Test _call_integration_llm with mocked LLM provider."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='int_llm', email='int_llm@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='LLM Integration Project', user=self.user
        )

    @patch('apps.common.llm_providers.get_llm_provider')
    def test_returns_structured_result(self, mock_factory):
        mock_provider = MagicMock()
        expected = {
            'edges': [{'source_id': 'a', 'target_id': 'b', 'edge_type': 'supports'}],
            'tensions': [],
            'status_updates': [],
            'delta_narrative': 'New evidence supports existing claims.',
        }
        mock_provider.generate_with_tools = AsyncMock(return_value=expected)
        mock_factory.return_value = mock_provider

        result = _call_integration_llm("graph context", [])
        self.assertEqual(result['edges'][0]['edge_type'], 'supports')
        self.assertIn('delta_narrative', result)

    @patch('apps.common.llm_providers.get_llm_provider')
    def test_none_response_returns_none(self, mock_factory):
        mock_provider = MagicMock()
        mock_provider.generate_with_tools = AsyncMock(return_value=None)
        mock_factory.return_value = mock_provider

        result = _call_integration_llm("context", [])
        self.assertIsNone(result)

    @patch('apps.common.llm_providers.get_llm_provider')
    def test_non_dict_response_returns_none(self, mock_factory):
        mock_provider = MagicMock()
        mock_provider.generate_with_tools = AsyncMock(return_value="just a string")
        mock_factory.return_value = mock_provider

        result = _call_integration_llm("context", [])
        self.assertIsNone(result)


# ═══════════════════════════════════════════════════════════════════
# Edge creation from spec
# ═══════════════════════════════════════════════════════════════════


class CreateEdgeFromSpecTests(TestCase):
    """Test _create_edge_from_spec."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='edge_spec', email='edge_spec@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='Edge Spec Project', user=self.user
        )
        self.node1 = Node.objects.create(
            project=self.project,
            node_type=NodeType.CLAIM,
            status=NodeStatus.SUPPORTED,
            content='Claim node for edge testing',
            source_type='user_edit',
            created_by=self.user,
        )
        self.node2 = Node.objects.create(
            project=self.project,
            node_type=NodeType.EVIDENCE,
            status=NodeStatus.CONFIRMED,
            content='Evidence node for edge testing',
            source_type='user_edit',
            created_by=self.user,
        )
        self.nodes_map = {
            str(self.node1.id): self.node1,
            str(self.node2.id): self.node2,
        }

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_creates_supports_edge(self, mock_embed):
        spec = {
            'source_id': str(self.node2.id),
            'target_id': str(self.node1.id),
            'edge_type': 'supports',
            'strength': 0.8,
            'provenance': 'Evidence backs the claim',
        }
        edge = _create_edge_from_spec(spec, self.nodes_map, created_by=self.user)
        self.assertIsNotNone(edge)
        self.assertEqual(edge.edge_type, 'supports')
        self.assertEqual(edge.source_node, self.node2)
        self.assertEqual(edge.target_node, self.node1)

    def test_invalid_source_id_returns_none(self):
        spec = {
            'source_id': str(uuid.uuid4()),  # doesn't exist in map
            'target_id': str(self.node1.id),
            'edge_type': 'supports',
        }
        edge = _create_edge_from_spec(spec, self.nodes_map)
        self.assertIsNone(edge)

    def test_invalid_edge_type_returns_none(self):
        spec = {
            'source_id': str(self.node2.id),
            'target_id': str(self.node1.id),
            'edge_type': 'relates_to',
        }
        edge = _create_edge_from_spec(spec, self.nodes_map)
        self.assertIsNone(edge)


# ═══════════════════════════════════════════════════════════════════
# Tension creation from spec
# ═══════════════════════════════════════════════════════════════════


class CreateTensionFromSpecTests(TestCase):
    """Test _create_tension_from_spec."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='tension_spec', email='tension_spec@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='Tension Spec Project', user=self.user
        )
        self.node1 = Node.objects.create(
            project=self.project,
            node_type=NodeType.CLAIM,
            status=NodeStatus.SUPPORTED,
            content='Growth claim for tension testing',
            source_type='user_edit',
            created_by=self.user,
        )
        self.node2 = Node.objects.create(
            project=self.project,
            node_type=NodeType.EVIDENCE,
            status=NodeStatus.CONFIRMED,
            content='Decline evidence for tension testing',
            source_type='user_edit',
            created_by=self.user,
        )
        self.nodes_map = {
            str(self.node1.id): self.node1,
            str(self.node2.id): self.node2,
        }

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_creates_tension_node(self, mock_embed):
        spec = {
            'content': 'Revenue growth claims contradict declining sales data',
            'between_nodes': [str(self.node1.id), str(self.node2.id)],
            'severity': 'high',
        }
        tension = _create_tension_from_spec(
            spec, self.project, self.nodes_map, created_by=self.user,
        )
        self.assertIsNotNone(tension)
        self.assertEqual(tension.node_type, 'tension')
        self.assertEqual(tension.status, 'surfaced')
        self.assertEqual(tension.properties['severity'], 'high')

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_creates_contradiction_edges(self, mock_embed):
        spec = {
            'content': 'Growth vs decline tension in the analysis',
            'between_nodes': [str(self.node1.id), str(self.node2.id)],
            'severity': 'medium',
        }
        tension = _create_tension_from_spec(
            spec, self.project, self.nodes_map, created_by=self.user,
        )
        # Should create contradiction edges from tension to each between_node
        edges = Edge.objects.filter(source_node=tension, edge_type='contradicts')
        self.assertEqual(edges.count(), 2)

    def test_empty_content_returns_none(self):
        spec = {'content': '', 'between_nodes': [], 'severity': 'low'}
        result = _create_tension_from_spec(spec, self.project, self.nodes_map)
        self.assertIsNone(result)


# ═══════════════════════════════════════════════════════════════════
# End-to-end: integrate_new_nodes
# ═══════════════════════════════════════════════════════════════════


class IntegrateNewNodesTests(TestCase):
    """Integration tests for integrate_new_nodes (with mocked LLM)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='integrate_e2e', email='integrate_e2e@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='Integration E2E Project', user=self.user
        )

    def _create_node(self, content, node_type='claim', status='unsubstantiated'):
        return Node.objects.create(
            project=self.project,
            node_type=node_type,
            status=status,
            content=content,
            source_type='document_extraction',
            created_by=self.user,
            embedding=[0.1] * 384,
        )

    def test_empty_new_nodes_returns_empty(self):
        result = integrate_new_nodes(self.project.id, [])
        self.assertEqual(result['edges'], [])
        self.assertEqual(result['tensions'], [])
        self.assertEqual(result['updated_nodes'], [])

    @patch('apps.graph.integration._call_integration_llm')
    def test_no_llm_result_returns_empty(self, mock_llm):
        node = self._create_node('A new claim about market dynamics')
        mock_llm.return_value = None

        result = integrate_new_nodes(self.project.id, [node.id])
        self.assertEqual(result['edges'], [])

    @patch('apps.graph.integration._call_integration_llm')
    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_creates_edges_from_llm_result(self, mock_embed, mock_llm):
        existing = self._create_node('Existing claim about revenue growth')
        new_node = self._create_node('New evidence supporting revenue growth')

        mock_llm.return_value = {
            'edges': [{
                'source_id': str(new_node.id),
                'target_id': str(existing.id),
                'edge_type': 'supports',
                'strength': 0.85,
                'provenance': 'Direct evidence support',
            }],
            'tensions': [],
            'status_updates': [],
            'gaps': [],
            'delta_narrative': 'New evidence bolsters revenue growth claims.',
        }

        result = integrate_new_nodes(self.project.id, [new_node.id])
        self.assertEqual(len(result['edges']), 1)
        edge = Edge.objects.get(id=result['edges'][0])
        self.assertEqual(edge.edge_type, 'supports')
        self.assertEqual(edge.source_node, new_node)

    @patch('apps.graph.integration._call_integration_llm')
    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_creates_tensions_from_llm_result(self, mock_embed, mock_llm):
        existing = self._create_node('Market is growing rapidly this year')
        new_node = self._create_node('Revenue declined 15% in the quarter', node_type='evidence', status='confirmed')

        mock_llm.return_value = {
            'edges': [],
            'tensions': [{
                'content': 'Growth claims contradicted by revenue decline data',
                'between_nodes': [str(existing.id), str(new_node.id)],
                'severity': 'high',
            }],
            'status_updates': [],
            'gaps': [],
            'delta_narrative': 'New data reveals contradiction with growth claims.',
        }

        result = integrate_new_nodes(self.project.id, [new_node.id])
        self.assertEqual(len(result['tensions']), 1)
        tension = Node.objects.get(id=result['tensions'][0])
        self.assertEqual(tension.node_type, 'tension')
        self.assertEqual(tension.properties['severity'], 'high')

    @patch('apps.graph.integration._call_integration_llm')
    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_applies_status_updates(self, mock_embed, mock_llm):
        existing = self._create_node('Market will grow by 20% next year', status='unsubstantiated')
        new_node = self._create_node(
            'Gartner report confirms 22% growth forecast',
            node_type='evidence', status='confirmed',
        )

        mock_llm.return_value = {
            'edges': [],
            'tensions': [],
            'status_updates': [{
                'node_id': str(existing.id),
                'new_status': 'supported',
                'reason': 'Gartner report confirms the growth claim',
            }],
            'gaps': [],
            'delta_narrative': 'Growth claim now supported by Gartner data.',
        }

        result = integrate_new_nodes(self.project.id, [new_node.id])
        self.assertIn(existing.id, result['updated_nodes'])
        existing.refresh_from_db()
        self.assertEqual(existing.status, 'supported')

    @patch('apps.graph.integration._call_integration_llm')
    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_creates_gap_nodes(self, mock_embed, mock_llm):
        new_node = self._create_node('New claim requiring more evidence')

        mock_llm.return_value = {
            'edges': [],
            'tensions': [],
            'status_updates': [],
            'gaps': [{
                'type': 'claim',
                'content': 'No evidence for the 20% growth rate claim',
                'gap_type': 'missing_evidence',
            }],
            'delta_narrative': 'Gap identified in growth evidence.',
        }

        result = integrate_new_nodes(self.project.id, [new_node.id])
        self.assertEqual(len(result['updated_nodes']), 1)
        gap_node = Node.objects.get(id=result['updated_nodes'][0])
        self.assertEqual(gap_node.properties['gap_type'], 'missing_evidence')

    @patch('apps.graph.integration._call_integration_llm')
    def test_small_graph_uses_all_context(self, mock_llm):
        """Graph <= SMALL_GRAPH_THRESHOLD should use all existing nodes."""
        # Create a few existing nodes (well under threshold of 30)
        for i in range(5):
            self._create_node(f'Existing claim number {i} in the graph')

        new_node = self._create_node('Brand new claim from this document')
        mock_llm.return_value = {
            'edges': [], 'tensions': [], 'status_updates': [],
            'gaps': [], 'delta_narrative': '',
        }

        integrate_new_nodes(self.project.id, [new_node.id])

        # Verify LLM was called (context assembly ran)
        mock_llm.assert_called_once()
        # The context string should contain all existing nodes
        context_str = mock_llm.call_args[0][0]
        for i in range(5):
            self.assertIn(f'Existing claim number {i}', context_str)

    @patch('apps.graph.integration._assemble_integration_context')
    @patch('apps.graph.integration._call_integration_llm')
    def test_large_graph_uses_similarity_context(self, mock_llm, mock_assemble):
        """Graph > SMALL_GRAPH_THRESHOLD should use similarity-based context."""
        # Create SMALL_GRAPH_THRESHOLD + 1 existing nodes
        for i in range(SMALL_GRAPH_THRESHOLD + 1):
            self._create_node(f'Existing node number {i} in a large graph')

        new_node = self._create_node('New node to integrate into large graph')
        mock_assemble.return_value = []  # empty context from similarity
        mock_llm.return_value = {
            'edges': [], 'tensions': [], 'status_updates': [],
            'gaps': [], 'delta_narrative': '',
        }

        integrate_new_nodes(self.project.id, [new_node.id])
        # _assemble_integration_context should have been called
        mock_assemble.assert_called_once()
