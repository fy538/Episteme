"""
Tests for the progressive two-tier thematic summary system.

Covers:
- ChunkClusteringService (direct + fallback + sampled) — no DB required
- Thematic XML parsing (_parse_thematic_summary_xml) — no DB required
- should_generate logic (thematic_upgrade, thematic_insufficient_nodes) — requires DB
- cleanup_stuck_generating_summaries task — requires DB

Run the no-DB tests locally (always works):
    DJANGO_SETTINGS_MODULE=config.settings.test pytest apps/graph/tests_thematic_summary.py -k "Clustering or XML" -v --no-cov

Run all tests (requires DB with pgvector):
    DJANGO_SETTINGS_MODULE=config.settings.test pytest apps/graph/tests_thematic_summary.py -v --no-cov
"""

import unittest
import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

# ── Django setup for imports (needed even for non-DB tests) ──────
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
django.setup()

from apps.graph.chunk_clustering import ChunkClusteringService
from apps.graph.summary_service import ProjectSummaryService


# ═══════════════════════════════════════════════════════════════
# ChunkClusteringService Tests (no DB — plain unittest)
# ═══════════════════════════════════════════════════════════════


class ChunkClusteringDirectTests(unittest.TestCase):
    """Test _cluster_direct with sklearn."""

    def test_identical_vectors_form_one_cluster(self):
        """Identical embeddings should all land in the same cluster."""
        vecs = np.array([[1, 0, 0]] * 5, dtype=float)
        labels = ChunkClusteringService._cluster_direct(vecs, distance_threshold=0.65)
        unique = set(int(l) for l in labels)
        self.assertEqual(len(unique), 1)

    def test_orthogonal_vectors_form_separate_clusters(self):
        """Orthogonal vectors should form separate clusters."""
        vecs = np.array([
            [1, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [0, 0, 1],
        ], dtype=float)
        labels = ChunkClusteringService._cluster_direct(vecs, distance_threshold=0.5)
        unique = set(int(l) for l in labels)
        self.assertEqual(len(unique), 3)

    def test_single_vector_returns_single_label(self):
        """Single vector should return one label."""
        vecs = np.array([[1, 0, 0]], dtype=float)
        labels = ChunkClusteringService._cluster_direct(vecs, distance_threshold=0.65)
        self.assertEqual(len(labels), 1)

    def test_high_threshold_merges_more(self):
        """Higher distance_threshold should merge more aggressively."""
        vecs = np.array([
            [1.0, 0.1, 0],
            [1.0, -0.1, 0],
            [0.1, 1.0, 0],
            [-0.1, 1.0, 0],
        ], dtype=float)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        vecs = vecs / norms

        labels_tight = ChunkClusteringService._cluster_direct(vecs, distance_threshold=0.3)
        labels_loose = ChunkClusteringService._cluster_direct(vecs, distance_threshold=0.9)

        unique_tight = set(int(l) for l in labels_tight)
        unique_loose = set(int(l) for l in labels_loose)
        self.assertGreaterEqual(len(unique_tight), len(unique_loose))


class ChunkClusteringFallbackTests(unittest.TestCase):
    """Test _fallback_cluster (greedy algorithm)."""

    def test_identical_vectors_single_cluster(self):
        vecs = np.array([[1, 0, 0]] * 5, dtype=float)
        labels = ChunkClusteringService._fallback_cluster(vecs, distance_threshold=0.65)
        unique = set(int(l) for l in labels)
        self.assertEqual(len(unique), 1)

    def test_distant_vectors_separate_clusters(self):
        vecs = np.array([
            [1, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 1, 0],
        ], dtype=float)
        labels = ChunkClusteringService._fallback_cluster(vecs, distance_threshold=0.5)
        # Vectors 0,1 should be in one cluster; 2,3 in another
        self.assertEqual(labels[0], labels[1])
        self.assertEqual(labels[2], labels[3])
        self.assertNotEqual(labels[0], labels[2])

    def test_zero_norm_vectors_handled(self):
        """Zero vectors shouldn't crash."""
        vecs = np.array([[0, 0, 0], [1, 0, 0], [1, 0, 0]], dtype=float)
        labels = ChunkClusteringService._fallback_cluster(vecs, distance_threshold=0.65)
        self.assertEqual(len(labels), 3)

    def test_consistent_with_direct_for_clear_clusters(self):
        """Fallback should separate clearly distinct groups, similar to sklearn."""
        vecs = np.array([
            [1, 0, 0], [1, 0, 0], [1, 0, 0],
            [0, 1, 0], [0, 1, 0], [0, 1, 0],
        ], dtype=float)
        labels = ChunkClusteringService._fallback_cluster(vecs, distance_threshold=0.5)
        # First 3 in one cluster, last 3 in another
        self.assertEqual(labels[0], labels[1])
        self.assertEqual(labels[1], labels[2])
        self.assertEqual(labels[3], labels[4])
        self.assertEqual(labels[4], labels[5])
        self.assertNotEqual(labels[0], labels[3])


class ChunkClusteringSampledTests(unittest.TestCase):
    """Test _cluster_sampled (two-phase approach)."""

    def test_sampled_produces_labels_for_all_vectors(self):
        """Sampled clustering should return labels for every input vector."""
        n = 100
        rng = np.random.default_rng(0)
        vecs = rng.standard_normal((n, 10))
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        vecs = vecs / norms

        labels = ChunkClusteringService._cluster_sampled(
            vecs, distance_threshold=0.65, sample_size=30,
        )
        self.assertEqual(len(labels), n)

    def test_sampled_deterministic(self):
        """Same input should produce same output (seeded RNG)."""
        n = 50
        rng = np.random.default_rng(7)
        vecs = rng.standard_normal((n, 10))
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        vecs = vecs / norms

        labels1 = ChunkClusteringService._cluster_sampled(vecs, 0.65, 20)
        labels2 = ChunkClusteringService._cluster_sampled(vecs, 0.65, 20)
        np.testing.assert_array_equal(labels1, labels2)

    def test_sampled_clusters_similar_vectors(self):
        """Similar vectors should still cluster together even when sampled."""
        # 3 tight clusters of 20 each
        rng = np.random.default_rng(42)
        cluster_a = rng.normal(loc=[1, 0, 0], scale=0.05, size=(20, 3))
        cluster_b = rng.normal(loc=[0, 1, 0], scale=0.05, size=(20, 3))
        cluster_c = rng.normal(loc=[0, 0, 1], scale=0.05, size=(20, 3))
        vecs = np.vstack([cluster_a, cluster_b, cluster_c])
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        vecs = vecs / norms

        labels = ChunkClusteringService._cluster_sampled(vecs, 0.65, 30)

        # Vectors within same original cluster should share labels
        a_labels = set(int(l) for l in labels[:20])
        b_labels = set(int(l) for l in labels[20:40])
        c_labels = set(int(l) for l in labels[40:])

        # Each group should be mostly one label (allow some noise)
        self.assertLessEqual(len(a_labels), 2)
        self.assertLessEqual(len(b_labels), 2)
        self.assertLessEqual(len(c_labels), 2)

    def test_sample_size_larger_than_n_works(self):
        """When sample_size > n, should still work correctly."""
        n = 10
        rng = np.random.default_rng(0)
        vecs = rng.standard_normal((n, 5))
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        vecs = vecs / norms

        labels = ChunkClusteringService._cluster_sampled(vecs, 0.65, sample_size=100)
        self.assertEqual(len(labels), n)


# ═══════════════════════════════════════════════════════════════
# Thematic XML Parsing Tests (no DB — plain unittest)
# ═══════════════════════════════════════════════════════════════


class ThematicXMLParsingTests(unittest.TestCase):
    """Test _parse_thematic_summary_xml."""

    def _clusters(self, n=2):
        """Generate mock cluster data."""
        return [
            {
                'chunk_count': 10,
                'coverage_pct': 50.0,
                'document_distribution': {'Doc A': 5, 'Doc B': 5},
            },
            {
                'chunk_count': 8,
                'coverage_pct': 40.0,
                'document_distribution': {'Doc C': 8},
            },
        ][:n]

    def test_valid_xml(self):
        xml = '''<thematic_summary>
<overview>This project covers regulations and markets.</overview>
<themes>
<theme label="Regulatory Landscape" coverage_pct="50.0" doc_count="2">
Analysis of FDA pathways and EU compliance.
</theme>
<theme label="Market Strategy" coverage_pct="40.0" doc_count="1">
Competitive positioning and analyst reports.
</theme>
</themes>
<coverage_gaps>Pricing strategy is underexplored.</coverage_gaps>
</thematic_summary>'''

        result = ProjectSummaryService._parse_thematic_summary_xml(
            xml, self._clusters()
        )

        self.assertIn('regulations', result['overview'].lower())
        self.assertEqual(len(result['key_findings']), 2)
        self.assertEqual(
            result['key_findings'][0]['theme_label'], 'Regulatory Landscape'
        )
        self.assertEqual(result['key_findings'][0]['coverage_pct'], 50.0)
        self.assertEqual(result['key_findings'][0]['doc_count'], 2)
        self.assertIn('Pricing', result['coverage_gaps'])
        # Thematic summaries have no citations
        self.assertEqual(result['key_findings'][0]['cited_nodes'], [])
        # Non-thematic sections should be empty
        self.assertEqual(result['emerging_picture'], '')
        self.assertEqual(result['attention_needed'], '')

    def test_malformed_xml_falls_back_to_regex(self):
        """Unclosed tags should fall back to regex parsing."""
        xml = '''<thematic_summary>
<overview>Project overview text.</overview>
<themes>
<theme label="Theme A" coverage_pct="60" doc_count="3">Narrative A.</theme>
</themes>
<coverage_gaps>Gaps here.</coverage_gaps>
</thematic_summary'''  # Missing closing >

        result = ProjectSummaryService._parse_thematic_summary_xml(
            xml, self._clusters(1)
        )

        # Regex fallback should still extract content
        self.assertIn('overview', result['overview'].lower())
        self.assertEqual(len(result['key_findings']), 1)
        self.assertEqual(result['key_findings'][0]['theme_label'], 'Theme A')

    def test_missing_coverage_attrs_use_cluster_data(self):
        """When XML attrs are missing, coverage data from clusters is used."""
        xml = '''<thematic_summary>
<overview>Overview.</overview>
<themes>
<theme label="Theme A">Narrative.</theme>
</themes>
<coverage_gaps></coverage_gaps>
</thematic_summary>'''

        clusters = [{'chunk_count': 15, 'coverage_pct': 75.0,
                      'document_distribution': {'D1': 10, 'D2': 5}}]
        result = ProjectSummaryService._parse_thematic_summary_xml(xml, clusters)

        self.assertEqual(result['key_findings'][0]['coverage_pct'], 75.0)
        self.assertEqual(result['key_findings'][0]['doc_count'], 2)  # len(doc_dist)
        self.assertEqual(result['key_findings'][0]['chunk_count'], 15)

    def test_empty_response_returns_empty_sections(self):
        result = ProjectSummaryService._parse_thematic_summary_xml('', [])
        self.assertEqual(result['overview'], '')
        self.assertEqual(result['key_findings'], [])
        self.assertEqual(result['coverage_gaps'], '')

    def test_extra_text_outside_xml_ignored(self):
        xml = '''Here is the summary:
<thematic_summary>
<overview>Clean overview.</overview>
<themes></themes>
<coverage_gaps></coverage_gaps>
</thematic_summary>
Some trailing text.'''

        result = ProjectSummaryService._parse_thematic_summary_xml(xml, [])
        self.assertEqual(result['overview'], 'Clean overview.')

    def test_multiple_themes_parsed(self):
        """All theme elements should be parsed."""
        xml = '''<thematic_summary>
<overview>Multi-theme project.</overview>
<themes>
<theme label="A" coverage_pct="30" doc_count="1">First.</theme>
<theme label="B" coverage_pct="40" doc_count="2">Second.</theme>
<theme label="C" coverage_pct="20" doc_count="1">Third.</theme>
</themes>
<coverage_gaps></coverage_gaps>
</thematic_summary>'''

        clusters = [
            {'chunk_count': 10, 'coverage_pct': 30.0, 'document_distribution': {'D1': 10}},
            {'chunk_count': 15, 'coverage_pct': 40.0, 'document_distribution': {'D1': 8, 'D2': 7}},
            {'chunk_count': 5, 'coverage_pct': 20.0, 'document_distribution': {'D3': 5}},
        ]
        result = ProjectSummaryService._parse_thematic_summary_xml(xml, clusters)
        self.assertEqual(len(result['key_findings']), 3)
        labels = [f['theme_label'] for f in result['key_findings']]
        self.assertEqual(labels, ['A', 'B', 'C'])

    def test_more_themes_than_clusters(self):
        """LLM returns more themes than clusters: extra themes get zeroed coverage."""
        xml = '''<thematic_summary>
<overview>Overview.</overview>
<themes>
<theme label="A" coverage_pct="50" doc_count="2">First.</theme>
<theme label="B" coverage_pct="30" doc_count="1">Second.</theme>
<theme label="C" coverage_pct="20" doc_count="1">Third.</theme>
</themes>
<coverage_gaps></coverage_gaps>
</thematic_summary>'''

        # Only 1 cluster, but 3 themes in XML
        clusters = [
            {'chunk_count': 10, 'coverage_pct': 50.0, 'document_distribution': {'D1': 10}},
        ]
        result = ProjectSummaryService._parse_thematic_summary_xml(xml, clusters)
        self.assertEqual(len(result['key_findings']), 3)
        # First theme should have cluster data
        self.assertEqual(result['key_findings'][0]['chunk_count'], 10)
        # Extra themes beyond cluster count should degrade gracefully (0 chunk_count)
        self.assertEqual(result['key_findings'][2]['chunk_count'], 0)

    def test_more_clusters_than_themes(self):
        """Fewer themes than clusters: extra clusters are simply unused."""
        xml = '''<thematic_summary>
<overview>Overview.</overview>
<themes>
<theme label="A">Only one theme.</theme>
</themes>
<coverage_gaps></coverage_gaps>
</thematic_summary>'''

        clusters = [
            {'chunk_count': 10, 'coverage_pct': 50.0, 'document_distribution': {'D1': 5, 'D2': 5}},
            {'chunk_count': 8, 'coverage_pct': 40.0, 'document_distribution': {'D3': 8}},
            {'chunk_count': 2, 'coverage_pct': 10.0, 'document_distribution': {'D4': 2}},
        ]
        result = ProjectSummaryService._parse_thematic_summary_xml(xml, clusters)
        # Only 1 theme parsed — extra clusters are fine
        self.assertEqual(len(result['key_findings']), 1)
        self.assertEqual(result['key_findings'][0]['coverage_pct'], 50.0)
        self.assertEqual(result['key_findings'][0]['doc_count'], 2)


# ═══════════════════════════════════════════════════════════════
# DB-Dependent Tests — require PostgreSQL with pgvector
# ═══════════════════════════════════════════════════════════════

# Helper to check if DB is available for test collection
def _db_available():
    """Check if the test database supports pgvector (required by migrations)."""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            # SELECT 1 only proves connectivity — we need pgvector for migrations
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            row = cursor.fetchone()
            return row is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="PostgreSQL with pgvector not available"
)


@requires_db
class ShouldGenerateTests(unittest.TestCase):
    """Test ProjectSummaryService.should_generate(). Requires DB."""

    @classmethod
    def setUpClass(cls):
        """Set up test data once for all tests in this class."""
        super().setUpClass()

    def setUp(self):
        from django.contrib.auth import get_user_model
        from apps.projects.models import Project
        from apps.graph.models import (
            Node, NodeType, NodeStatus, ProjectSummary, SummaryStatus,
        )
        self.Node = Node
        self.NodeType = NodeType
        self.NodeStatus = NodeStatus
        self.ProjectSummary = ProjectSummary
        self.SummaryStatus = SummaryStatus

        User = get_user_model()
        self.user = User.objects.create_user(
            email=f'test-summary-{uuid.uuid4().hex[:8]}@example.com',
            password='testpass',
        )
        self.project = Project.objects.create(
            title='Test Project', user=self.user
        )

    def _create_nodes(self, count):
        nodes = []
        for i in range(count):
            nodes.append(self.Node.objects.create(
                project=self.project,
                node_type=self.NodeType.CLAIM,
                status=self.NodeStatus.SUPPORTED,
                content=f'Test claim {i}',
                source_type='extraction',
                created_by=self.user,
            ))
        return nodes

    def test_no_nodes_returns_false(self):
        should, reason = ProjectSummaryService.should_generate(self.project.id)
        self.assertFalse(should)
        self.assertEqual(reason, 'no_nodes')

    def test_no_summary_returns_true(self):
        self._create_nodes(5)
        should, reason = ProjectSummaryService.should_generate(self.project.id)
        self.assertTrue(should)
        self.assertEqual(reason, 'no_summary')

    def test_stale_summary_returns_true(self):
        from django.utils import timezone
        self._create_nodes(5)
        self.ProjectSummary.objects.create(
            project=self.project,
            status=self.SummaryStatus.FULL,
            is_stale=True,
            stale_since=timezone.now(),
            version=1,
        )
        should, reason = ProjectSummaryService.should_generate(self.project.id)
        self.assertTrue(should)
        self.assertEqual(reason, 'stale')

    def test_thematic_with_enough_nodes_upgrades(self):
        self._create_nodes(5)
        self.ProjectSummary.objects.create(
            project=self.project,
            status=self.SummaryStatus.THEMATIC,
            version=1,
        )
        should, reason = ProjectSummaryService.should_generate(self.project.id)
        self.assertTrue(should)
        self.assertEqual(reason, 'thematic_upgrade')

    def test_thematic_with_few_nodes_does_not_upgrade(self):
        """Thematic should NOT upgrade if <5 nodes (would produce seed = regression)."""
        self._create_nodes(3)
        self.ProjectSummary.objects.create(
            project=self.project,
            status=self.SummaryStatus.THEMATIC,
            version=1,
        )
        should, reason = ProjectSummaryService.should_generate(self.project.id)
        self.assertFalse(should)
        self.assertEqual(reason, 'thematic_insufficient_nodes')

    def test_seed_with_enough_nodes_upgrades(self):
        """Seed summaries should upgrade to full once ≥5 nodes exist."""
        self._create_nodes(5)
        self.ProjectSummary.objects.create(
            project=self.project,
            status=self.SummaryStatus.SEED,
            version=1,
        )
        should, reason = ProjectSummaryService.should_generate(self.project.id)
        self.assertTrue(should)
        self.assertEqual(reason, 'seed_upgrade')

    def test_seed_with_few_nodes_does_not_upgrade(self):
        """Seed should NOT upgrade if <5 nodes."""
        self._create_nodes(3)
        self.ProjectSummary.objects.create(
            project=self.project,
            status=self.SummaryStatus.SEED,
            version=1,
        )
        should, reason = ProjectSummaryService.should_generate(self.project.id)
        self.assertFalse(should)
        self.assertEqual(reason, 'seed_insufficient_nodes')

    def test_already_generating_returns_false(self):
        self._create_nodes(5)
        self.ProjectSummary.objects.create(
            project=self.project,
            status=self.SummaryStatus.FULL,
            version=1,
        )
        self.ProjectSummary.objects.create(
            project=self.project,
            status=self.SummaryStatus.GENERATING,
            version=2,
        )
        should, reason = ProjectSummaryService.should_generate(self.project.id)
        self.assertFalse(should)
        self.assertEqual(reason, 'already_generating')

    def test_up_to_date_returns_false(self):
        self._create_nodes(5)
        self.ProjectSummary.objects.create(
            project=self.project,
            status=self.SummaryStatus.FULL,
            version=1,
        )
        should, reason = ProjectSummaryService.should_generate(self.project.id)
        self.assertFalse(should)
        self.assertEqual(reason, 'up_to_date')


@requires_db
class CleanupStuckGeneratingTests(unittest.TestCase):
    """Test cleanup_stuck_generating_summaries task. Requires DB."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        from apps.projects.models import Project
        from apps.graph.models import ProjectSummary, SummaryStatus
        self.ProjectSummary = ProjectSummary
        self.SummaryStatus = SummaryStatus

        User = get_user_model()
        self.user = User.objects.create_user(
            email=f'test-cleanup-{uuid.uuid4().hex[:8]}@example.com',
            password='testpass',
        )
        self.project = Project.objects.create(
            title='Test Project', user=self.user
        )

    def test_old_generating_gets_failed(self):
        """Summaries stuck in GENERATING >5 min should be marked FAILED."""
        from django.utils import timezone
        from apps.graph.tasks import cleanup_stuck_generating_summaries

        summary = self.ProjectSummary.objects.create(
            project=self.project,
            status=self.SummaryStatus.GENERATING,
            version=1,
        )
        # Backdate created_at to 10 minutes ago
        self.ProjectSummary.objects.filter(id=summary.id).update(
            created_at=timezone.now() - timedelta(minutes=10)
        )

        result = cleanup_stuck_generating_summaries()
        self.assertEqual(result['cleaned_up'], 1)

        summary.refresh_from_db()
        self.assertEqual(summary.status, self.SummaryStatus.FAILED)
        self.assertIn('stuck', summary.generation_metadata.get('error', ''))

    def test_recent_generating_not_touched(self):
        """Summaries that just started generating should NOT be cleaned up."""
        from apps.graph.tasks import cleanup_stuck_generating_summaries

        self.ProjectSummary.objects.create(
            project=self.project,
            status=self.SummaryStatus.GENERATING,
            version=1,
        )

        result = cleanup_stuck_generating_summaries()
        self.assertEqual(result['cleaned_up'], 0)

    def test_exactly_at_threshold_not_touched(self):
        """Summary created exactly 5 min ago is at the boundary — should NOT be cleaned.

        The cleanup query uses created_at__lt=threshold (strict less than),
        so a summary created exactly at the threshold survives. This gives a
        brief grace period and prevents cleaning up summaries that just barely
        exceeded the threshold due to clock skew.
        """
        from django.utils import timezone
        from apps.graph.tasks import cleanup_stuck_generating_summaries

        summary = self.ProjectSummary.objects.create(
            project=self.project,
            status=self.SummaryStatus.GENERATING,
            version=1,
        )
        # Set created_at to exactly 5 minutes ago
        self.ProjectSummary.objects.filter(id=summary.id).update(
            created_at=timezone.now() - timedelta(minutes=5)
        )

        result = cleanup_stuck_generating_summaries()
        self.assertEqual(result['cleaned_up'], 0)

        summary.refresh_from_db()
        self.assertEqual(summary.status, self.SummaryStatus.GENERATING)

    def test_just_over_threshold_gets_cleaned(self):
        """Summary created 5m01s ago should be cleaned up."""
        from django.utils import timezone
        from apps.graph.tasks import cleanup_stuck_generating_summaries

        summary = self.ProjectSummary.objects.create(
            project=self.project,
            status=self.SummaryStatus.GENERATING,
            version=1,
        )
        self.ProjectSummary.objects.filter(id=summary.id).update(
            created_at=timezone.now() - timedelta(minutes=5, seconds=1)
        )

        result = cleanup_stuck_generating_summaries()
        self.assertEqual(result['cleaned_up'], 1)

        summary.refresh_from_db()
        self.assertEqual(summary.status, self.SummaryStatus.FAILED)

    def test_non_generating_not_touched(self):
        """FULL/THEMATIC summaries should never be cleaned up."""
        from django.utils import timezone
        from apps.graph.tasks import cleanup_stuck_generating_summaries

        s1 = self.ProjectSummary.objects.create(
            project=self.project, status=self.SummaryStatus.FULL, version=1,
        )
        s2 = self.ProjectSummary.objects.create(
            project=self.project, status=self.SummaryStatus.THEMATIC, version=2,
        )
        # Backdate
        self.ProjectSummary.objects.filter(id__in=[s1.id, s2.id]).update(
            created_at=timezone.now() - timedelta(minutes=10)
        )

        result = cleanup_stuck_generating_summaries()
        self.assertEqual(result['cleaned_up'], 0)

        s1.refresh_from_db()
        s2.refresh_from_db()
        self.assertEqual(s1.status, self.SummaryStatus.FULL)
        self.assertEqual(s2.status, self.SummaryStatus.THEMATIC)
