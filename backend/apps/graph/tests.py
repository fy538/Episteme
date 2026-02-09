"""
Graph app tests — Models, services, serialization, extraction, integration,
edit handler, and API endpoints.
"""

import json
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.graph.models import Node, Edge, GraphDelta, NodeType, NodeStatus, EdgeType
from apps.graph.services import GraphService
from apps.graph.serialization import GraphSerializationService
from apps.graph.delta_service import GraphDeltaService
from apps.graph.edit_handler import GraphEditHandler
from apps.projects.models import Project, Document

User = get_user_model()


class NodeModelTests(TestCase):
    """Test Node model creation, validation, and status constraints."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='Test Project', user=self.user
        )

    def test_create_claim_node(self):
        node = Node.objects.create(
            project=self.project,
            node_type=NodeType.CLAIM,
            status=NodeStatus.SUPPORTED,
            content='Test claim content',
            source_type='user_edit',
            created_by=self.user,
        )
        self.assertEqual(node.node_type, 'claim')
        self.assertEqual(node.status, 'supported')
        self.assertIsNotNone(node.id)
        self.assertEqual(node.scope, 'project')

    def test_create_evidence_node(self):
        node = Node.objects.create(
            project=self.project,
            node_type=NodeType.EVIDENCE,
            status=NodeStatus.CONFIRMED,
            content='Test evidence content',
            source_type='document_extraction',
            created_by=self.user,
        )
        self.assertEqual(node.node_type, 'evidence')
        self.assertEqual(node.status, 'confirmed')

    def test_create_assumption_node(self):
        node = Node.objects.create(
            project=self.project,
            node_type=NodeType.ASSUMPTION,
            status=NodeStatus.UNTESTED,
            content='We assume X is true',
            source_type='agent_analysis',
            created_by=self.user,
        )
        self.assertEqual(node.node_type, 'assumption')
        self.assertEqual(node.status, 'untested')

    def test_create_tension_node(self):
        node = Node.objects.create(
            project=self.project,
            node_type=NodeType.TENSION,
            status=NodeStatus.SURFACED,
            content='A contradicts B',
            source_type='agent_analysis',
            created_by=self.user,
        )
        self.assertEqual(node.node_type, 'tension')
        self.assertEqual(node.status, 'surfaced')

    def test_node_default_confidence(self):
        node = Node.objects.create(
            project=self.project,
            node_type=NodeType.CLAIM,
            status=NodeStatus.SUPPORTED,
            content='Default confidence',
            source_type='user_edit',
        )
        self.assertEqual(node.confidence, 0.8)

    def test_node_custom_properties(self):
        props = {'source_passage': 'Some text', 'load_bearing': True}
        node = Node.objects.create(
            project=self.project,
            node_type=NodeType.ASSUMPTION,
            status=NodeStatus.UNTESTED,
            content='Custom properties',
            source_type='user_edit',
            properties=props,
        )
        self.assertEqual(node.properties['source_passage'], 'Some text')
        self.assertTrue(node.properties['load_bearing'])

    def test_invalid_status_for_type_auto_fixed(self):
        """Status auto-fix in save() sets invalid statuses to default."""
        node = Node(
            project=self.project,
            node_type=NodeType.CLAIM,
            status='surfaced',  # Not valid for claim
            content='Bad status',
            source_type='user_edit',
        )
        node.save()
        node.refresh_from_db()
        # Should be auto-fixed to a valid claim status
        self.assertIn(node.status, ['supported', 'contested', 'unsubstantiated'])


class EdgeModelTests(TestCase):
    """Test Edge model creation and uniqueness."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='edge@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='Edge Project', user=self.user
        )
        self.node1 = Node.objects.create(
            project=self.project,
            node_type=NodeType.CLAIM,
            status=NodeStatus.SUPPORTED,
            content='Claim 1',
            source_type='user_edit',
        )
        self.node2 = Node.objects.create(
            project=self.project,
            node_type=NodeType.EVIDENCE,
            status=NodeStatus.CONFIRMED,
            content='Evidence 1',
            source_type='user_edit',
        )

    def test_create_supports_edge(self):
        edge = Edge.objects.create(
            source_node=self.node2,
            target_node=self.node1,
            edge_type=EdgeType.SUPPORTS,
            strength=0.9,
            provenance='Evidence supports claim',
            source_type='user_edit',
        )
        self.assertEqual(edge.edge_type, 'supports')
        self.assertEqual(edge.source_node, self.node2)
        self.assertEqual(edge.target_node, self.node1)

    def test_unique_edge_constraint(self):
        """Same source, target, and type should not be duplicated."""
        Edge.objects.create(
            source_node=self.node1,
            target_node=self.node2,
            edge_type=EdgeType.SUPPORTS,
            source_type='user_edit',
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Edge.objects.create(
                source_node=self.node1,
                target_node=self.node2,
                edge_type=EdgeType.SUPPORTS,
                source_type='user_edit',
            )

    def test_different_edge_types_allowed(self):
        """Different edge types between same nodes are allowed."""
        Edge.objects.create(
            source_node=self.node1,
            target_node=self.node2,
            edge_type=EdgeType.SUPPORTS,
            source_type='user_edit',
        )
        edge2 = Edge.objects.create(
            source_node=self.node1,
            target_node=self.node2,
            edge_type=EdgeType.DEPENDS_ON,
            source_type='user_edit',
        )
        self.assertIsNotNone(edge2.id)


class GraphDeltaModelTests(TestCase):
    """Test GraphDelta model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='delta@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='Delta Project', user=self.user
        )

    def test_create_delta(self):
        delta = GraphDelta.objects.create(
            project=self.project,
            trigger='document_upload',
            patch={'nodes_added': [str(uuid.uuid4())]},
            narrative='Added 2 claims from uploaded document.',
            nodes_created=2,
            edges_created=1,
        )
        self.assertEqual(delta.trigger, 'document_upload')
        self.assertEqual(delta.nodes_created, 2)


class GraphServiceTests(TestCase):
    """Test GraphService CRUD, orientation, and health methods."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='service@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='Service Project', user=self.user
        )

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_create_node(self, mock_embed):
        node = GraphService.create_node(
            project=self.project,
            node_type='claim',
            content='The market is growing at 15% annually',
            source_type='user_edit',
            status='supported',
            user=self.user,
        )
        self.assertIsNotNone(node.id)
        self.assertEqual(node.content, 'The market is growing at 15% annually')
        mock_embed.assert_called_once()

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_create_edge(self, mock_embed):
        node1 = GraphService.create_node(
            project=self.project,
            node_type='claim',
            content='Claim 1',
            source_type='user_edit',
            user=self.user,
        )
        node2 = GraphService.create_node(
            project=self.project,
            node_type='evidence',
            content='Evidence 1',
            source_type='user_edit',
            user=self.user,
        )
        edge = GraphService.create_edge(
            source_node=node2,
            target_node=node1,
            edge_type='supports',
            strength=0.8,
            provenance='Study shows growth',
            source_type='user_edit',
        )
        self.assertIsNotNone(edge.id)
        self.assertEqual(edge.edge_type, 'supports')

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_get_orientation_view(self, mock_embed):
        # Create various node types
        GraphService.create_node(
            project=self.project, node_type='tension',
            content='A vs B', source_type='agent_analysis',
            status='surfaced', user=self.user,
        )
        GraphService.create_node(
            project=self.project, node_type='assumption',
            content='We assume X', source_type='agent_analysis',
            status='untested', user=self.user,
        )
        GraphService.create_node(
            project=self.project, node_type='claim',
            content='Market growing', source_type='document_extraction',
            status='supported', user=self.user,
        )
        GraphService.create_node(
            project=self.project, node_type='claim',
            content='Revenue unclear', source_type='document_extraction',
            status='unsubstantiated', user=self.user,
        )

        view = GraphService.get_orientation_view(self.project.id)
        self.assertEqual(len(view['contradictions']), 1)
        self.assertEqual(len(view['hidden_assumptions']), 1)
        self.assertEqual(len(view['agreements']), 1)
        self.assertEqual(len(view['gaps']), 1)

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_compute_graph_health(self, mock_embed):
        GraphService.create_node(
            project=self.project, node_type='claim',
            content='Claim', source_type='user_edit',
            status='supported', user=self.user,
        )
        GraphService.create_node(
            project=self.project, node_type='assumption',
            content='Assumption', source_type='user_edit',
            status='untested', user=self.user,
        )

        health = GraphService.compute_graph_health(self.project.id)
        self.assertEqual(health['total_nodes'], 2)
        self.assertEqual(health['untested_assumptions'], 1)
        self.assertIn('claim', health['nodes_by_type'])

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_update_node(self, mock_embed):
        node = GraphService.create_node(
            project=self.project, node_type='claim',
            content='Original', source_type='user_edit',
            status='supported', user=self.user,
        )
        updated = GraphService.update_node(
            node_id=node.id, content='Updated content'
        )
        self.assertEqual(updated.content, 'Updated content')
        # Embedding should have been regenerated
        self.assertEqual(mock_embed.call_count, 2)

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_remove_node(self, mock_embed):
        node = GraphService.create_node(
            project=self.project, node_type='claim',
            content='To remove', source_type='user_edit',
            user=self.user,
        )
        node_id = node.id
        GraphService.remove_node(node_id)
        self.assertFalse(Node.objects.filter(id=node_id).exists())


class GraphSerializationTests(TestCase):
    """Test compact serialization for LLM context."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='serial@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='Serial Project', user=self.user
        )

    def test_serialize_empty_graph(self):
        text, ref_map = GraphSerializationService.serialize_for_llm(self.project.id)
        self.assertIn('empty', text.lower())
        self.assertEqual(len(ref_map), 0)

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_serialize_with_nodes(self, mock_embed):
        GraphService.create_node(
            project=self.project, node_type='claim',
            content='Market growing', source_type='user_edit',
            status='supported', user=self.user,
        )
        GraphService.create_node(
            project=self.project, node_type='evidence',
            content='Study shows 15%', source_type='user_edit',
            status='confirmed', user=self.user,
        )

        text, ref_map = GraphSerializationService.serialize_for_llm(self.project.id)
        self.assertIn('[C1]', text)
        self.assertIn('[E1]', text)
        self.assertEqual(len(ref_map), 2)

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_resolve_ref(self, mock_embed):
        node = GraphService.create_node(
            project=self.project, node_type='claim',
            content='Test claim', source_type='user_edit',
            status='supported', user=self.user,
        )

        _, ref_map = GraphSerializationService.serialize_for_llm(self.project.id)
        resolved_id = GraphSerializationService.resolve_ref(self.project.id, 'C1')
        self.assertEqual(resolved_id, node.id)


class GraphEditHandlerTests(TestCase):
    """Test the chat → graph edit handler."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='edit@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='Edit Project', user=self.user
        )

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_apply_create_node_edit(self, mock_embed):
        edits = [
            {
                'action': 'create_node',
                'type': 'claim',
                'content': 'New claim from chat',
                'status': 'supported',
            }
        ]
        result = GraphEditHandler.apply_edits(
            project_id=str(self.project.id),
            edits=edits,
            user=self.user,
        )
        self.assertEqual(result['nodes_created'], 1)
        self.assertEqual(Node.objects.filter(project=self.project).count(), 1)

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_apply_create_edge_edit(self, mock_embed):
        node1 = GraphService.create_node(
            project=self.project, node_type='claim',
            content='Claim A', source_type='user_edit',
            status='supported', user=self.user,
        )
        node2 = GraphService.create_node(
            project=self.project, node_type='evidence',
            content='Evidence B', source_type='user_edit',
            status='confirmed', user=self.user,
        )

        # First serialize to build the ref map
        _, ref_map = GraphSerializationService.serialize_for_llm(self.project.id)

        edits = [
            {
                'action': 'create_edge',
                'source_ref': 'E1',
                'target_ref': 'C1',
                'edge_type': 'supports',
                'provenance': 'Created via chat',
            }
        ]
        result = GraphEditHandler.apply_edits(
            project_id=str(self.project.id),
            edits=edits,
            user=self.user,
        )
        self.assertEqual(result['edges_created'], 1)

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_apply_update_node_edit(self, mock_embed):
        node = GraphService.create_node(
            project=self.project, node_type='claim',
            content='Old content', source_type='user_edit',
            status='supported', user=self.user,
        )

        edits = [
            {
                'action': 'update_node',
                'ref': str(node.id),
                'content': 'Updated content',
                'status': 'contested',
            }
        ]
        result = GraphEditHandler.apply_edits(
            project_id=str(self.project.id),
            edits=edits,
            user=self.user,
        )
        self.assertEqual(result['nodes_updated'], 1)
        node.refresh_from_db()
        self.assertEqual(node.content, 'Updated content')
        self.assertEqual(node.status, 'contested')

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_apply_remove_node_edit(self, mock_embed):
        node = GraphService.create_node(
            project=self.project, node_type='claim',
            content='To delete', source_type='user_edit',
            status='supported', user=self.user,
        )
        node_id = node.id

        edits = [
            {
                'action': 'remove_node',
                'ref': str(node_id),
            }
        ]
        result = GraphEditHandler.apply_edits(
            project_id=str(self.project.id),
            edits=edits,
            user=self.user,
        )
        self.assertEqual(result['nodes_removed'], 1)
        self.assertFalse(Node.objects.filter(id=node_id).exists())

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_new_ref_in_same_batch(self, mock_embed):
        """Test that new-0, new-1 references work within the same batch."""
        edits = [
            {
                'action': 'create_node',
                'type': 'claim',
                'content': 'Claim A',
                'status': 'supported',
            },
            {
                'action': 'create_node',
                'type': 'evidence',
                'content': 'Evidence B',
                'status': 'confirmed',
            },
            {
                'action': 'create_edge',
                'source_ref': 'new-1',
                'target_ref': 'new-0',
                'edge_type': 'supports',
            },
        ]
        result = GraphEditHandler.apply_edits(
            project_id=str(self.project.id),
            edits=edits,
            user=self.user,
        )
        self.assertEqual(result['nodes_created'], 2)
        self.assertEqual(result['edges_created'], 1)


class GraphAPITests(TestCase):
    """Test graph API endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='api@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='API Project', user=self.user
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_orientation_view_endpoint(self, mock_embed):
        GraphService.create_node(
            project=self.project, node_type='claim',
            content='Test claim', source_type='user_edit',
            status='supported', user=self.user,
        )

        response = self.client.get(
            f'/api/v2/projects/{self.project.id}/graph/orientation/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('agreements', response.data)
        self.assertIn('contradictions', response.data)
        self.assertIn('hidden_assumptions', response.data)
        self.assertIn('gaps', response.data)

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_health_endpoint(self, mock_embed):
        GraphService.create_node(
            project=self.project, node_type='claim',
            content='Test claim', source_type='user_edit',
            status='supported', user=self.user,
        )

        response = self.client.get(
            f'/api/v2/projects/{self.project.id}/graph/health/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_nodes'], 1)

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_node_detail_endpoint(self, mock_embed):
        node = GraphService.create_node(
            project=self.project, node_type='claim',
            content='Detailed claim', source_type='user_edit',
            status='supported', user=self.user,
        )

        response = self.client.get(
            f'/api/v2/projects/{self.project.id}/nodes/{node.id}/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['content'], 'Detailed claim')
        self.assertIn('edges', response.data)
        self.assertIn('neighbors', response.data)

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_node_update_endpoint(self, mock_embed):
        node = GraphService.create_node(
            project=self.project, node_type='claim',
            content='Original', source_type='user_edit',
            status='supported', user=self.user,
        )

        response = self.client.patch(
            f'/api/v2/projects/{self.project.id}/nodes/{node.id}/',
            {'status': 'contested'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        node.refresh_from_db()
        self.assertEqual(node.status, 'contested')

    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_project_graph_endpoint(self, mock_embed):
        node1 = GraphService.create_node(
            project=self.project, node_type='claim',
            content='Claim 1', source_type='user_edit',
            status='supported', user=self.user,
        )
        node2 = GraphService.create_node(
            project=self.project, node_type='evidence',
            content='Evidence 1', source_type='user_edit',
            status='confirmed', user=self.user,
        )
        GraphService.create_edge(
            source_node=node2, target_node=node1,
            edge_type='supports', source_type='user_edit',
        )

        response = self.client.get(
            f'/api/v2/projects/{self.project.id}/graph/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['nodes']), 2)
        self.assertEqual(len(response.data['edges']), 1)

    def test_orientation_requires_auth(self):
        unauth_client = APIClient()
        response = unauth_client.get(
            f'/api/v2/projects/{self.project.id}/graph/orientation/'
        )
        self.assertEqual(response.status_code, 401)

    def test_orientation_filters_by_owner(self):
        other_user = User.objects.create_user(
            email='other@example.com', password='testpass'
        )
        other_project = Project.objects.create(
            title='Other Project', user=other_user
        )
        response = self.client.get(
            f'/api/v2/projects/{other_project.id}/graph/orientation/'
        )
        self.assertEqual(response.status_code, 404)


class SectionedStreamParserGraphEditsTests(TestCase):
    """Test that the parser handles <graph_edits> sections correctly."""

    def test_parse_graph_edits_section(self):
        from apps.intelligence.parser import SectionedStreamParser, Section

        parser = SectionedStreamParser()

        chunks = parser.parse('<response>Hello</response>')
        chunks += parser.parse('<graph_edits>[{"action":"create_node","type":"claim","content":"Test"}]</graph_edits>')
        chunks += parser.flush()

        sections_seen = {c.section for c in chunks}
        self.assertIn(Section.RESPONSE, sections_seen)
        self.assertIn(Section.GRAPH_EDITS, sections_seen)

        # Check graph_edits buffer accumulated
        buffer = parser.get_graph_edits_buffer()
        self.assertIn('create_node', buffer)

    def test_graph_edits_split_across_chunks(self):
        from apps.intelligence.parser import SectionedStreamParser, Section

        parser = SectionedStreamParser()
        chunks = parser.parse('<graph_ed')
        chunks += parser.parse('its>[{"action":"create')
        chunks += parser.parse('_node"}]</graph_edits>')
        chunks += parser.flush()

        buffer = parser.get_graph_edits_buffer()
        self.assertIn('create_node', buffer)

        # Verify completion marker was emitted
        complete_chunks = [c for c in chunks if c.is_complete and c.section == Section.GRAPH_EDITS]
        self.assertEqual(len(complete_chunks), 1)
