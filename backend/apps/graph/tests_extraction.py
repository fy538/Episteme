"""
Tests for extraction pipeline — validation, normalization, deduplication,
source matching, section splitting, and LLM integration.

Pure-logic tests use SimpleTestCase (no DB). DB-dependent integration tests
use TransactionTestCase and are tagged with 'requires_db'.
"""

import json
import uuid
from typing import List
from unittest.mock import patch, MagicMock, AsyncMock

import numpy as np
import pytest
from django.test import SimpleTestCase, TestCase, TransactionTestCase, tag
from django.contrib.auth import get_user_model

from apps.graph.extraction import (
    _validate_extraction_item,
    _validate_extraction_edge,
    _normalize_extraction_result,
    _deduplicate_nodes,
    _match_source_chunks,
    _split_into_sections,
    _build_extraction_prompt,
    _consolidate_sections,
    _call_extraction_llm,
    extract_nodes_from_document,
    VALID_DOCUMENT_ROLES,
    VALID_EDGE_TYPES,
    MIN_DOCUMENT_LENGTH,
    SECTION_OVERLAP_TOKENS,
)
from apps.projects.models import Project, Document, DocumentChunk
from apps.graph.models import Node

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════
# Node validation
# ═══════════════════════════════════════════════════════════════════


class ValidateExtractionItemTests(TestCase):
    """Test _validate_extraction_item — normalization + edge cases."""

    def test_valid_claim(self):
        item = {
            'id': 'n0',
            'type': 'claim',
            'content': 'The market is growing at 15% annually',
            'importance': 3,
            'document_role': 'thesis',
            'confidence': 0.9,
            'source_passage': 'The market is growing...',
        }
        result = _validate_extraction_item(item)
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'claim')
        self.assertEqual(result['importance'], 3)
        self.assertEqual(result['document_role'], 'thesis')
        self.assertEqual(result['confidence'], 0.9)
        self.assertEqual(result['status'], 'unsubstantiated')  # default for claim

    def test_valid_evidence(self):
        item = {
            'id': 'n1',
            'type': 'evidence',
            'content': 'Survey of 500 users showed 78% satisfaction rate',
            'importance': 2,
        }
        result = _validate_extraction_item(item)
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'evidence')
        self.assertEqual(result['status'], 'uncertain')  # default for evidence

    def test_valid_assumption(self):
        item = {
            'id': 'n2',
            'type': 'assumption',
            'content': 'Users will continue to prefer mobile apps over web',
        }
        result = _validate_extraction_item(item)
        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'untested')

    def test_valid_tension(self):
        item = {
            'id': 'n3',
            'type': 'tension',
            'content': 'Claims of growth contradict revenue decline data',
        }
        result = _validate_extraction_item(item)
        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'surfaced')

    def test_rejects_non_dict(self):
        self.assertIsNone(_validate_extraction_item("not a dict"))
        self.assertIsNone(_validate_extraction_item(42))
        self.assertIsNone(_validate_extraction_item(None))

    def test_rejects_invalid_type(self):
        item = {'id': 'n0', 'type': 'opinion', 'content': 'Something important here'}
        self.assertIsNone(_validate_extraction_item(item))

    def test_rejects_empty_content(self):
        item = {'id': 'n0', 'type': 'claim', 'content': ''}
        self.assertIsNone(_validate_extraction_item(item))

    def test_rejects_short_content(self):
        item = {'id': 'n0', 'type': 'claim', 'content': 'Too short'}
        self.assertIsNone(_validate_extraction_item(item))

    def test_content_length_boundary(self):
        # Exactly 10 chars should pass
        item = {'id': 'n0', 'type': 'claim', 'content': 'A' * 10}
        result = _validate_extraction_item(item)
        self.assertIsNotNone(result)

        # 9 chars should fail
        item['content'] = 'A' * 9
        self.assertIsNone(_validate_extraction_item(item))

    def test_confidence_clamping(self):
        # Over 1.0
        item = {'id': 'n0', 'type': 'claim', 'content': 'Valid claim content here', 'confidence': 1.5}
        result = _validate_extraction_item(item)
        self.assertEqual(result['confidence'], 1.0)

        # Under 0.0
        item['confidence'] = -0.5
        result = _validate_extraction_item(item)
        self.assertEqual(result['confidence'], 0.0)

    def test_confidence_non_numeric_defaults(self):
        item = {'id': 'n0', 'type': 'claim', 'content': 'Valid claim content here', 'confidence': 'high'}
        result = _validate_extraction_item(item)
        self.assertEqual(result['confidence'], 0.8)  # default

    def test_importance_clamping(self):
        item = {'id': 'n0', 'type': 'claim', 'content': 'Valid claim content here', 'importance': 5}
        result = _validate_extraction_item(item)
        self.assertEqual(result['importance'], 3)

        item['importance'] = 0
        result = _validate_extraction_item(item)
        self.assertEqual(result['importance'], 1)

    def test_importance_non_integer_coercion(self):
        item = {'id': 'n0', 'type': 'claim', 'content': 'Valid claim content here', 'importance': '2'}
        result = _validate_extraction_item(item)
        self.assertEqual(result['importance'], 2)

        item['importance'] = 'invalid'
        result = _validate_extraction_item(item)
        self.assertEqual(result['importance'], 2)  # default

    def test_invalid_document_role_defaults_to_detail(self):
        item = {'id': 'n0', 'type': 'claim', 'content': 'Valid claim content here', 'document_role': 'protagonist'}
        result = _validate_extraction_item(item)
        self.assertEqual(result['document_role'], 'detail')

    def test_all_valid_document_roles_accepted(self):
        for role in VALID_DOCUMENT_ROLES:
            item = {'id': 'n0', 'type': 'claim', 'content': 'Valid claim content here', 'document_role': role}
            result = _validate_extraction_item(item)
            self.assertEqual(result['document_role'], role, f"Role {role} not accepted")

    def test_invalid_status_reset_to_default(self):
        # 'surfaced' is not valid for a claim
        item = {'id': 'n0', 'type': 'claim', 'content': 'Valid claim content here', 'status': 'surfaced'}
        result = _validate_extraction_item(item)
        self.assertEqual(result['status'], 'unsubstantiated')

    def test_valid_status_preserved(self):
        item = {'id': 'n0', 'type': 'claim', 'content': 'Valid claim content here', 'status': 'supported'}
        result = _validate_extraction_item(item)
        self.assertEqual(result['status'], 'supported')

    def test_type_case_insensitive(self):
        item = {'id': 'n0', 'type': 'CLAIM', 'content': 'Valid claim content here'}
        result = _validate_extraction_item(item)
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'claim')

    def test_preserves_properties(self):
        props = {'credibility': 'high', 'evidence_type': 'metric'}
        item = {'id': 'n0', 'type': 'evidence', 'content': 'Study data shows 45% increase', 'properties': props}
        result = _validate_extraction_item(item)
        self.assertEqual(result['properties'], props)


# ═══════════════════════════════════════════════════════════════════
# Edge validation
# ═══════════════════════════════════════════════════════════════════


class ValidateExtractionEdgeTests(TestCase):
    """Test _validate_extraction_edge."""

    def test_valid_supports_edge(self):
        edge = {'source_id': 'n0', 'target_id': 'n1', 'edge_type': 'supports'}
        result = _validate_extraction_edge(edge)
        self.assertIsNotNone(result)
        self.assertEqual(result['edge_type'], 'supports')

    def test_valid_contradicts_edge(self):
        edge = {'source_id': 'n0', 'target_id': 'n1', 'edge_type': 'contradicts'}
        result = _validate_extraction_edge(edge)
        self.assertIsNotNone(result)

    def test_valid_depends_on_edge(self):
        edge = {'source_id': 'n0', 'target_id': 'n1', 'edge_type': 'depends_on'}
        result = _validate_extraction_edge(edge)
        self.assertIsNotNone(result)

    def test_rejects_invalid_edge_type(self):
        edge = {'source_id': 'n0', 'target_id': 'n1', 'edge_type': 'relates_to'}
        self.assertIsNone(_validate_extraction_edge(edge))

    def test_rejects_missing_source_id(self):
        edge = {'source_id': '', 'target_id': 'n1', 'edge_type': 'supports'}
        self.assertIsNone(_validate_extraction_edge(edge))

    def test_rejects_missing_target_id(self):
        edge = {'source_id': 'n0', 'target_id': '', 'edge_type': 'supports'}
        self.assertIsNone(_validate_extraction_edge(edge))

    def test_rejects_non_dict(self):
        self.assertIsNone(_validate_extraction_edge("not a dict"))
        self.assertIsNone(_validate_extraction_edge(None))

    def test_edge_type_case_insensitive(self):
        edge = {'source_id': 'n0', 'target_id': 'n1', 'edge_type': 'SUPPORTS'}
        result = _validate_extraction_edge(edge)
        self.assertIsNotNone(result)
        self.assertEqual(result['edge_type'], 'supports')

    def test_preserves_provenance(self):
        edge = {'source_id': 'n0', 'target_id': 'n1', 'edge_type': 'supports', 'provenance': 'data backs it up'}
        result = _validate_extraction_edge(edge)
        self.assertEqual(result['provenance'], 'data backs it up')


# ═══════════════════════════════════════════════════════════════════
# Normalization
# ═══════════════════════════════════════════════════════════════════


class NormalizeExtractionResultTests(TestCase):
    """Test _normalize_extraction_result — handles various LLM output shapes."""

    def test_standard_dict_format(self):
        parsed = {
            'nodes': [
                {'id': 'n0', 'type': 'claim', 'content': 'The market is growing significantly'},
            ],
            'edges': [
                {'source_id': 'n0', 'target_id': 'n1', 'edge_type': 'supports'},
            ],
        }
        result = _normalize_extraction_result(parsed)
        self.assertEqual(len(result['nodes']), 1)
        self.assertEqual(len(result['edges']), 1)

    def test_extractions_key_alias(self):
        """LLM sometimes uses 'extractions' instead of 'nodes'."""
        parsed = {
            'extractions': [
                {'id': 'n0', 'type': 'claim', 'content': 'Valid claim content here for extraction'},
            ],
        }
        result = _normalize_extraction_result(parsed)
        self.assertEqual(len(result['nodes']), 1)

    def test_list_input_treated_as_nodes(self):
        parsed = [
            {'id': 'n0', 'type': 'claim', 'content': 'Valid claim from list input format'},
        ]
        result = _normalize_extraction_result(parsed)
        self.assertEqual(len(result['nodes']), 1)
        self.assertEqual(len(result['edges']), 0)

    def test_filters_invalid_nodes(self):
        parsed = {
            'nodes': [
                {'id': 'n0', 'type': 'claim', 'content': 'Valid claim content here in mixed batch'},
                {'id': 'n1', 'type': 'invalid_type', 'content': 'Bad type'},
                {'id': 'n2', 'type': 'claim', 'content': 'Short'},  # too short
                'not_a_dict',
            ],
            'edges': [],
        }
        result = _normalize_extraction_result(parsed)
        self.assertEqual(len(result['nodes']), 1)

    def test_non_list_nodes_returns_empty(self):
        parsed = {'nodes': 'not a list'}
        result = _normalize_extraction_result(parsed)
        self.assertEqual(result['nodes'], [])

    def test_non_list_edges_returns_empty_list(self):
        parsed = {
            'nodes': [{'id': 'n0', 'type': 'claim', 'content': 'Valid claim for edge normalization test'}],
            'edges': 'bad edges',
        }
        result = _normalize_extraction_result(parsed)
        self.assertEqual(result['edges'], [])

    def test_empty_dict(self):
        result = _normalize_extraction_result({})
        self.assertEqual(result['nodes'], [])
        self.assertEqual(result['edges'], [])


# ═══════════════════════════════════════════════════════════════════
# Deduplication
# ═══════════════════════════════════════════════════════════════════


class DeduplicateNodesTests(TestCase):
    """Test _deduplicate_nodes — cosine similarity dedup with importance tiebreaking."""

    def _make_node(self, node_id, content, importance=2, node_type='claim'):
        return {
            'id': node_id,
            'type': node_type,
            'content': content,
            'importance': importance,
            'document_role': 'detail',
        }

    @patch('apps.graph.extraction.generate_embeddings_batch')
    def test_no_duplicates_all_kept(self, mock_batch):
        """Distinct nodes should all survive dedup."""
        nodes = [
            self._make_node('s0_n0', 'The market is growing rapidly'),
            self._make_node('s1_n0', 'Competitors are losing market share'),
        ]
        # Orthogonal embeddings — similarity near 0
        mock_batch.return_value = [
            [1.0, 0.0, 0.0] + [0.0] * 381,
            [0.0, 1.0, 0.0] + [0.0] * 381,
        ]
        deduped, remap = _deduplicate_nodes(nodes)
        self.assertEqual(len(deduped), 2)
        self.assertEqual(len(remap), 0)

    @patch('apps.graph.extraction.generate_embeddings_batch')
    def test_exact_duplicates_merged(self, mock_batch):
        """Identical embeddings (sim=1.0) should be deduplicated."""
        nodes = [
            self._make_node('s0_n0', 'The market is growing rapidly', importance=2),
            self._make_node('s1_n0', 'The market is growing rapidly', importance=2),
        ]
        embedding = [0.5] * 384
        mock_batch.return_value = [embedding, embedding]

        deduped, remap = _deduplicate_nodes(nodes)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(len(remap), 1)
        # Lower importance or shorter content gets merged into survivor
        self.assertIn('s1_n0', remap)
        self.assertEqual(remap['s1_n0'], 's0_n0')

    @patch('apps.graph.extraction.generate_embeddings_batch')
    def test_higher_importance_survives(self, mock_batch):
        """When deduplicating, the node with higher importance survives."""
        nodes = [
            self._make_node('s0_n0', 'The market is growing rapidly', importance=1),
            self._make_node('s1_n0', 'The market is growing rapidly', importance=3),
        ]
        embedding = [0.5] * 384
        mock_batch.return_value = [embedding, embedding]

        deduped, remap = _deduplicate_nodes(nodes)
        self.assertEqual(len(deduped), 1)
        # s0_n0 (imp=1) should be merged into s1_n0 (imp=3)
        self.assertIn('s0_n0', remap)
        self.assertEqual(remap['s0_n0'], 's1_n0')
        self.assertEqual(deduped[0]['id'], 's1_n0')

    @patch('apps.graph.extraction.generate_embeddings_batch')
    def test_same_importance_longer_content_survives(self, mock_batch):
        """When importance is equal, longer content wins."""
        nodes = [
            self._make_node('s0_n0', 'Short content here', importance=2),
            self._make_node('s1_n0', 'This is a much longer content that has more detail', importance=2),
        ]
        embedding = [0.5] * 384
        mock_batch.return_value = [embedding, embedding]

        deduped, remap = _deduplicate_nodes(nodes)
        self.assertEqual(len(deduped), 1)
        # s0_n0 (shorter) should be merged into s1_n0 (longer)
        self.assertIn('s0_n0', remap)
        self.assertEqual(remap['s0_n0'], 's1_n0')

    @patch('apps.graph.extraction.generate_embeddings_batch')
    def test_below_threshold_not_merged(self, mock_batch):
        """Similarity < 0.90 should not trigger dedup."""
        nodes = [
            self._make_node('s0_n0', 'The market is growing rapidly'),
            self._make_node('s1_n0', 'Revenue increased this quarter'),
        ]
        # Create orthogonal-ish embeddings with similarity ~0.5 (well below 0.90)
        vec1 = np.array([1.0, 0.0, 0.0] + [0.0] * 381)
        vec2 = np.array([0.5, 0.866, 0.0] + [0.0] * 381)
        # Normalize
        vec1 = vec1 / np.linalg.norm(vec1)
        vec2 = vec2 / np.linalg.norm(vec2)
        sim = np.dot(vec1, vec2)
        self.assertLess(sim, 0.90)  # verify our test data

        mock_batch.return_value = [vec1.tolist(), vec2.tolist()]

        deduped, remap = _deduplicate_nodes(nodes)
        self.assertEqual(len(deduped), 2)
        self.assertEqual(len(remap), 0)

    @patch('apps.graph.extraction.generate_embeddings_batch')
    def test_single_node_returns_as_is(self, mock_batch):
        nodes = [self._make_node('s0_n0', 'Only one node in the batch')]
        deduped, remap = _deduplicate_nodes(nodes)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(len(remap), 0)
        mock_batch.assert_not_called()

    def test_empty_list(self):
        deduped, remap = _deduplicate_nodes([])
        self.assertEqual(len(deduped), 0)
        self.assertEqual(len(remap), 0)

    @patch('apps.graph.extraction.generate_embeddings_batch')
    def test_embedding_failure_skips_dedup(self, mock_batch):
        """If embedding batch fails, return nodes unchanged."""
        nodes = [
            self._make_node('s0_n0', 'Node A content is interesting'),
            self._make_node('s1_n0', 'Node B content is also interesting'),
        ]
        mock_batch.side_effect = RuntimeError("Embedding service down")

        deduped, remap = _deduplicate_nodes(nodes)
        self.assertEqual(len(deduped), 2)
        self.assertEqual(len(remap), 0)

    @patch('apps.graph.extraction.generate_embeddings_batch')
    def test_none_embeddings_skips_dedup(self, mock_batch):
        """If any embedding is None, skip dedup to avoid errors."""
        nodes = [
            self._make_node('s0_n0', 'Node A has content'),
            self._make_node('s1_n0', 'Node B has content'),
        ]
        mock_batch.return_value = [[0.5] * 384, None]

        deduped, remap = _deduplicate_nodes(nodes)
        self.assertEqual(len(deduped), 2)
        self.assertEqual(len(remap), 0)

    @patch('apps.graph.extraction.generate_embeddings_batch')
    def test_caches_embedding_on_survivors(self, mock_batch):
        """Surviving nodes should have _embedding cached for later reuse."""
        nodes = [
            self._make_node('s0_n0', 'Unique node with important content'),
            self._make_node('s1_n0', 'Completely different topic here'),
        ]
        emb_a = [1.0] + [0.0] * 383
        emb_b = [0.0, 1.0] + [0.0] * 382
        mock_batch.return_value = [emb_a, emb_b]

        deduped, _ = _deduplicate_nodes(nodes)
        self.assertEqual(len(deduped), 2)
        self.assertEqual(deduped[0]['_embedding'], emb_a)
        self.assertEqual(deduped[1]['_embedding'], emb_b)

    @patch('apps.graph.extraction.generate_embeddings_batch')
    def test_three_way_dedup(self, mock_batch):
        """Three near-identical nodes should be reduced to one."""
        nodes = [
            self._make_node('s0_n0', 'Market growth rate is impressive', importance=1),
            self._make_node('s1_n0', 'Market growth rate is very impressive', importance=2),
            self._make_node('s2_n0', 'Market growth rate is truly impressive', importance=3),
        ]
        # All identical embeddings → all pairs > 0.90
        embedding = [0.5] * 384
        mock_batch.return_value = [embedding, embedding, embedding]

        deduped, remap = _deduplicate_nodes(nodes)
        # The highest-importance node should survive
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0]['id'], 's2_n0')

    @patch('apps.graph.extraction.generate_embeddings_batch')
    def test_zero_norm_embedding_handled(self, mock_batch):
        """Zero-norm embeddings should not crash (division by zero)."""
        nodes = [
            self._make_node('s0_n0', 'Node with zero norm embedding'),
            self._make_node('s1_n0', 'Another node here for testing'),
        ]
        mock_batch.return_value = [[0.0] * 384, [0.5] * 384]

        # Should not raise
        deduped, remap = _deduplicate_nodes(nodes)
        self.assertEqual(len(deduped), 2)


# ═══════════════════════════════════════════════════════════════════
# Source chunk matching
# ═══════════════════════════════════════════════════════════════════


class MatchSourceChunksTests(TestCase):
    """Test _match_source_chunks — text match, prefix match, embedding fallback."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='chunk_test', email='chunk_test@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='Chunk Test Project', user=self.user
        )
        self.document = Document.objects.create(
            project=self.project,
            user=self.user,
            title='Test Doc',
            content_text='Full document text here.',
        )

    def _make_chunk(self, text, index=0):
        return DocumentChunk.objects.create(
            document=self.document,
            chunk_text=text,
            chunk_index=index,
            token_count=len(text.split()),
        )

    def test_exact_text_match(self):
        chunk = self._make_chunk('The market grew by 15% in Q3 according to Gartner research data.')
        item = {'source_passage': 'grew by 15% in Q3'}
        result = _match_source_chunks(item, [chunk])
        self.assertEqual(result, [chunk.id])

    def test_case_insensitive_match(self):
        chunk = self._make_chunk('Revenue INCREASED by 20% year over year showing strong growth.')
        item = {'source_passage': 'revenue increased by 20%'}
        result = _match_source_chunks(item, [chunk])
        self.assertEqual(result, [chunk.id])

    def test_no_match_returns_empty(self):
        chunk = self._make_chunk('Totally unrelated content about something else entirely.')
        item = {'source_passage': 'market growth was impressive'}
        with patch('apps.graph.extraction.generate_embedding') as mock_emb, \
             patch('apps.graph.extraction.similarity_search') as mock_sim:
            mock_emb.return_value = [0.1] * 384
            mock_sim.return_value = []
            result = _match_source_chunks(item, [chunk])
        self.assertEqual(result, [])

    def test_empty_source_passage(self):
        chunk = self._make_chunk('Some content in the document chunk for testing.')
        item = {'source_passage': ''}
        result = _match_source_chunks(item, [chunk])
        self.assertEqual(result, [])

    def test_no_chunks(self):
        item = {'source_passage': 'some passage from the document'}
        result = _match_source_chunks(item, [])
        self.assertEqual(result, [])

    def test_prefix_match_fallback(self):
        """When full text match fails, try first 80 chars prefix."""
        long_passage = 'A' * 40 + ' specific passage that is quite long and detailed'
        chunk = self._make_chunk(long_passage[:80] + ' different ending text here')
        item = {'source_passage': long_passage}

        # Full match fails (chunk has different ending), but prefix match should work
        result = _match_source_chunks(item, [chunk])
        self.assertEqual(result, [chunk.id])

    def test_prefix_too_short_skipped(self):
        """Prefix match skipped when passage < 30 chars."""
        chunk = self._make_chunk('Some text with partial info.')
        item = {'source_passage': 'short passage here'}  # < 30 chars

        # Full text doesn't match, prefix too short, should fall to embedding
        with patch('apps.graph.extraction.generate_embedding') as mock_emb, \
             patch('apps.graph.extraction.similarity_search') as mock_sim:
            mock_emb.return_value = [0.1] * 384
            mock_sim.return_value = []
            result = _match_source_chunks(item, [chunk])
        self.assertEqual(result, [])

    def test_multiple_chunks_matched(self):
        """Source passage may span multiple chunks."""
        chunk1 = self._make_chunk('The market data shows growth in revenue and profits.', index=0)
        chunk2 = self._make_chunk('Additionally, market data shows growth in user acquisition.', index=1)
        chunk3 = self._make_chunk('Unrelated content about something else.', index=2)

        item = {'source_passage': 'market data shows growth'}
        result = _match_source_chunks(item, [chunk1, chunk2, chunk3])
        self.assertEqual(len(result), 2)
        self.assertIn(chunk1.id, result)
        self.assertIn(chunk2.id, result)


# ═══════════════════════════════════════════════════════════════════
# Section splitting
# ═══════════════════════════════════════════════════════════════════


class SplitIntoSectionsTests(TestCase):
    """Test _split_into_sections — paragraph-boundary splitting."""

    def test_short_text_single_section(self):
        """Text within token limit should return as single section."""
        text = "Short document text."
        # Using a very large max_tokens
        sections = _split_into_sections(text, 100000)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0], text)

    def test_splits_on_double_newlines(self):
        """Should split on paragraph boundaries."""
        # Create text with many paragraphs
        paragraphs = [f"Paragraph {i} " * 200 for i in range(10)]
        text = "\n\n".join(paragraphs)

        # Use small enough max_tokens to force splitting
        sections = _split_into_sections(text, 500)
        self.assertGreater(len(sections), 1)
        # Each section should be a valid string
        for section in sections:
            self.assertTrue(len(section) > 0)

    def test_rejoins_with_double_newlines(self):
        """Split sections should rejoin with double-newlines."""
        para1 = "First paragraph content " * 100
        para2 = "Second paragraph content " * 100
        text = f"{para1}\n\n{para2}"

        sections = _split_into_sections(text, 200)
        if len(sections) > 1:
            # Each section should be a substring of the original
            for section in sections:
                self.assertIn(section, text)

    def test_fallback_single_section_on_no_boundaries(self):
        """If no paragraph boundaries and text is long, still returns something."""
        text = "One very long paragraph " * 1000
        sections = _split_into_sections(text, 100)
        self.assertGreaterEqual(len(sections), 1)


# ═══════════════════════════════════════════════════════════════════
# Prompt construction
# ═══════════════════════════════════════════════════════════════════


class BuildExtractionPromptTests(TestCase):
    """Test _build_extraction_prompt."""

    def test_includes_title_and_text(self):
        prompt = _build_extraction_prompt("My Doc Title", "The document content.")
        self.assertIn("My Doc Title", prompt)
        self.assertIn("The document content.", prompt)

    def test_includes_extraction_instructions(self):
        prompt = _build_extraction_prompt("Title", "Text")
        self.assertIn("argument structure", prompt)
        self.assertIn("nodes", prompt)
        self.assertIn("edges", prompt)


# ═══════════════════════════════════════════════════════════════════
# LLM call (mocked)
# ═══════════════════════════════════════════════════════════════════


class CallExtractionLLMTests(TestCase):
    """Test _call_extraction_llm with mocked LLM provider."""

    @patch('apps.common.llm_providers.get_llm_provider')
    def test_successful_extraction(self, mock_provider_factory):
        mock_provider = MagicMock()
        mock_provider.generate_with_tools = AsyncMock(return_value={
            'nodes': [
                {'id': 'n0', 'type': 'claim', 'content': 'Valid extracted claim from document text'},
            ],
            'edges': [],
        })
        mock_provider_factory.return_value = mock_provider

        result = _call_extraction_llm("Test Doc", "Some document text here.")
        self.assertEqual(len(result['nodes']), 1)
        self.assertEqual(result['nodes'][0]['type'], 'claim')

    @patch('apps.common.llm_providers.get_llm_provider')
    def test_empty_response(self, mock_provider_factory):
        mock_provider = MagicMock()
        mock_provider.generate_with_tools = AsyncMock(return_value=None)
        mock_provider_factory.return_value = mock_provider

        result = _call_extraction_llm("Test Doc", "Some text.")
        self.assertEqual(result['nodes'], [])
        self.assertEqual(result['edges'], [])

    @patch('apps.common.llm_providers.get_llm_provider')
    def test_filters_invalid_nodes_from_llm(self, mock_provider_factory):
        mock_provider = MagicMock()
        mock_provider.generate_with_tools = AsyncMock(return_value={
            'nodes': [
                {'id': 'n0', 'type': 'claim', 'content': 'Valid claim from LLM output'},
                {'id': 'n1', 'type': 'bogus', 'content': 'Invalid type from LLM'},
            ],
            'edges': [],
        })
        mock_provider_factory.return_value = mock_provider

        result = _call_extraction_llm("Doc", "Text content for extraction.")
        self.assertEqual(len(result['nodes']), 1)


# ═══════════════════════════════════════════════════════════════════
# Consolidation
# ═══════════════════════════════════════════════════════════════════


class ConsolidateSectionsTests(TestCase):
    """Test _consolidate_sections — multi-section consolidation pass."""

    @patch('apps.common.llm_providers.get_llm_provider')
    @patch('apps.graph.extraction.parse_json_from_response')
    def test_applies_importance_updates(self, mock_parse, mock_provider_factory):
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value='{"importance_updates": []}')
        mock_provider_factory.return_value = mock_provider

        mock_parse.return_value = {
            'importance_updates': [
                {'id': 's0_n0', 'importance': 3, 'document_role': 'thesis'},
            ],
            'new_edges': [],
            'new_tension_nodes': [],
        }

        nodes = [
            {'id': 's0_n0', 'type': 'claim', 'content': 'Core thesis statement from the document', 'importance': 2, 'document_role': 'detail'},
            {'id': 's1_n0', 'type': 'evidence', 'content': 'Supporting evidence data from study', 'importance': 2, 'document_role': 'supporting_evidence'},
        ]
        edges = []

        result = _consolidate_sections("Doc Title", nodes, edges, "Summary text")
        # The first node should have been promoted to thesis
        updated_node = next(n for n in result['nodes'] if n['id'] == 's0_n0')
        self.assertEqual(updated_node['importance'], 3)
        self.assertEqual(updated_node['document_role'], 'thesis')

    @patch('apps.common.llm_providers.get_llm_provider')
    @patch('apps.graph.extraction.parse_json_from_response')
    def test_adds_cross_section_edges(self, mock_parse, mock_provider_factory):
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value='{}')
        mock_provider_factory.return_value = mock_provider

        mock_parse.return_value = {
            'importance_updates': [],
            'new_edges': [
                {'source_id': 's0_n0', 'target_id': 's1_n0', 'edge_type': 'supports'},
            ],
            'new_tension_nodes': [],
        }

        nodes = [
            {'id': 's0_n0', 'type': 'evidence', 'content': 'Evidence from first section of document', 'importance': 2, 'document_role': 'detail'},
            {'id': 's1_n0', 'type': 'claim', 'content': 'Claim from second section of document', 'importance': 2, 'document_role': 'detail'},
        ]
        edges = []

        result = _consolidate_sections("Doc", nodes, edges, "Summary")
        self.assertEqual(len(result['edges']), 1)
        self.assertEqual(result['edges'][0]['source_id'], 's0_n0')

    @patch('apps.common.llm_providers.get_llm_provider')
    @patch('apps.graph.extraction.parse_json_from_response')
    def test_adds_tension_nodes(self, mock_parse, mock_provider_factory):
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value='{}')
        mock_provider_factory.return_value = mock_provider

        mock_parse.return_value = {
            'importance_updates': [],
            'new_edges': [],
            'new_tension_nodes': [
                {
                    'content': 'Section 1 claims growth but section 3 shows decline',
                    'between_ids': ['s0_n0', 's2_n0'],
                },
            ],
        }

        nodes = [
            {'id': 's0_n0', 'type': 'claim', 'content': 'Growth is strong according to data', 'importance': 2, 'document_role': 'detail'},
        ]
        edges = []

        result = _consolidate_sections("Doc", nodes, edges, "Summary")
        tension_nodes = [n for n in result['nodes'] if n['type'] == 'tension']
        self.assertEqual(len(tension_nodes), 1)
        self.assertIn('growth', tension_nodes[0]['content'].lower())

    @patch('apps.common.llm_providers.get_llm_provider')
    @patch('apps.graph.extraction.parse_json_from_response')
    def test_llm_failure_returns_original(self, mock_parse, mock_provider_factory):
        """If consolidation LLM fails, return original nodes/edges."""
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(side_effect=RuntimeError("LLM down"))
        mock_provider_factory.return_value = mock_provider

        nodes = [
            {'id': 's0_n0', 'type': 'claim', 'content': 'Original claim should be preserved', 'importance': 2, 'document_role': 'detail'},
        ]
        edges = [{'source_id': 's0_n0', 'target_id': 's0_n1', 'edge_type': 'supports'}]

        result = _consolidate_sections("Doc", nodes, edges, "Summary")
        self.assertEqual(len(result['nodes']), 1)
        self.assertEqual(len(result['edges']), 1)


# ═══════════════════════════════════════════════════════════════════
# End-to-end: extract_nodes_from_document
# ═══════════════════════════════════════════════════════════════════


class ExtractNodesFromDocumentTests(TestCase):
    """Integration tests for extract_nodes_from_document (with mocked LLM)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='extract_e2e', email='extract_e2e@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='E2E Extraction Project', user=self.user
        )

    def _make_document(self, content_text, title='Test Doc'):
        return Document.objects.create(
            project=self.project,
            user=self.user,
            title=title,
            content_text=content_text,
        )

    def test_short_document_skipped(self):
        doc = self._make_document('Too short')
        result = extract_nodes_from_document(doc.id, self.project.id, created_by=self.user)
        self.assertEqual(result, [])

    def test_empty_document_skipped(self):
        doc = self._make_document('')
        result = extract_nodes_from_document(doc.id, self.project.id, created_by=self.user)
        self.assertEqual(result, [])

    @patch('apps.graph.extraction.generate_embeddings_batch', return_value=[[0.1] * 384])
    @patch('apps.graph.extraction._extract_from_full_document')
    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_creates_nodes_from_extraction(self, mock_embed, mock_extract, mock_batch):
        doc = self._make_document('A' * 100)

        mock_extract.return_value = {
            'nodes': [
                {
                    'id': 'n0',
                    'type': 'claim',
                    'content': 'The market is growing at 15% annually',
                    'importance': 3,
                    'document_role': 'thesis',
                    'confidence': 0.9,
                    'source_passage': '',
                },
            ],
            'edges': [],
        }

        result = extract_nodes_from_document(doc.id, self.project.id, created_by=self.user)
        self.assertEqual(len(result), 1)
        node = Node.objects.get(id=result[0])
        self.assertEqual(node.node_type, 'claim')
        self.assertEqual(node.content, 'The market is growing at 15% annually')
        self.assertEqual(node.properties['importance'], 3)
        self.assertEqual(node.source_document, doc)

    @patch('apps.graph.extraction.generate_embeddings_batch', return_value=[[0.1] * 384, [0.2] * 384])
    @patch('apps.graph.extraction._extract_from_full_document')
    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    @patch('apps.graph.services.GraphService.create_edge')
    def test_creates_edges(self, mock_create_edge, mock_embed, mock_extract, mock_batch):
        """Verify edge creation is attempted with correct params.

        Note: We mock create_edge because the real implementation uses
        ThreadPoolExecutor, and threads cannot see the TestCase's
        uncommitted transaction (user row invisible to the thread).
        """
        doc = self._make_document('A' * 100)

        mock_extract.return_value = {
            'nodes': [
                {'id': 'n0', 'type': 'claim', 'content': 'Main thesis about market growth trends', 'importance': 3},
                {'id': 'n1', 'type': 'evidence', 'content': 'Survey data shows 15% annual growth', 'importance': 2},
            ],
            'edges': [
                {'source_id': 'n1', 'target_id': 'n0', 'edge_type': 'supports'},
            ],
        }

        result = extract_nodes_from_document(doc.id, self.project.id, created_by=self.user)
        self.assertEqual(len(result), 2)

        # Verify create_edge was called with the correct edge type
        mock_create_edge.assert_called_once()
        _, kwargs = mock_create_edge.call_args
        self.assertEqual(kwargs['edge_type'], 'supports')

    @patch('apps.graph.extraction._extract_from_full_document')
    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_no_nodes_extracted(self, mock_embed, mock_extract):
        doc = self._make_document('A' * 100)
        mock_extract.return_value = {'nodes': [], 'edges': []}

        result = extract_nodes_from_document(doc.id, self.project.id, created_by=self.user)
        self.assertEqual(result, [])

    @patch('apps.graph.extraction._extract_from_full_document')
    @patch('apps.graph.services.generate_embedding', return_value=[0.1] * 384)
    def test_null_extraction_result(self, mock_embed, mock_extract):
        doc = self._make_document('A' * 100)
        mock_extract.return_value = None

        result = extract_nodes_from_document(doc.id, self.project.id, created_by=self.user)
        self.assertEqual(result, [])
