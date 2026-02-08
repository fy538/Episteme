"""
Tests for the Universal Evidence Ingestion Pipeline.

Tests cover:
- EvidenceIngestionService.ingest() core flow
- Provenance fields on created Evidence records
- Embedding generation
- Auto-reasoning integration (mocked)
- extract_evidence_from_findings() refactor
- inquiries.Evidence → projects.Evidence bridge
- API endpoints (ingest, fetch-url)
- URL fetcher
"""
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from apps.cases.models import Case
from apps.projects.models import (
    Document,
    DocumentChunk,
    Evidence as ProjectEvidence,
    EvidenceType,
    Project,
    RetrievalMethod,
)
from apps.projects.ingestion_service import (
    EvidenceIngestionService,
    EvidenceInput,
    IngestionResult,
)


DUMMY_EVENT_ID = '00000000-0000-0000-0000-000000000000'


class EvidenceIngestionServiceTest(TestCase):
    """Test EvidenceIngestionService.ingest()"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.project = Project.objects.create(
            user=self.user, title='Test Project'
        )
        self.case = Case.objects.create(
            title='Test Case',
            user=self.user,
            project=self.project,
            created_from_event_id=DUMMY_EVENT_ID,
        )

    @patch('apps.projects.ingestion_service._run_auto_reasoning')
    @patch('apps.projects.ingestion_service._generate_missing_embeddings')
    def test_ingest_creates_evidence_with_provenance(self, mock_embed, mock_reason):
        """Evidence records should have correct provenance fields."""
        mock_reason.return_value = {
            'links_created': 0, 'contradictions': 0, 'cascade_triggered': False,
        }

        inputs = [
            EvidenceInput(
                text='Market is growing 20% YoY',
                evidence_type='metric',
                extraction_confidence=0.9,
                source_url='https://example.com/article',
                source_title='Market Report 2025',
                source_domain='example.com',
                source_published_date='2025-03-15',
                retrieval_method='external_paste',
            ),
        ]

        result = EvidenceIngestionService.ingest(
            inputs=inputs,
            case=self.case,
            user=self.user,
            source_label='Test Ingestion',
        )

        self.assertEqual(len(result.evidence_ids), 1)
        self.assertIsNotNone(result.document_id)

        evidence = ProjectEvidence.objects.get(id=result.evidence_ids[0])
        self.assertEqual(evidence.text, 'Market is growing 20% YoY')
        self.assertEqual(evidence.type, 'metric')
        self.assertAlmostEqual(evidence.extraction_confidence, 0.9)
        self.assertEqual(evidence.source_url, 'https://example.com/article')
        self.assertEqual(evidence.source_title, 'Market Report 2025')
        self.assertEqual(evidence.source_domain, 'example.com')
        self.assertEqual(evidence.source_published_date, date(2025, 3, 15))
        self.assertEqual(evidence.retrieval_method, 'external_paste')

    @patch('apps.projects.ingestion_service._run_auto_reasoning')
    @patch('apps.projects.ingestion_service._generate_missing_embeddings')
    def test_ingest_creates_synthetic_document(self, mock_embed, mock_reason):
        """When no document_id is provided, creates a synthetic Document + Chunk."""
        mock_reason.return_value = {
            'links_created': 0, 'contradictions': 0, 'cascade_triggered': False,
        }

        inputs = [EvidenceInput(text='Some fact', retrieval_method='external_paste')]

        result = EvidenceIngestionService.ingest(
            inputs=inputs,
            case=self.case,
            user=self.user,
            source_label='External Research',
        )

        doc = Document.objects.get(id=result.document_id)
        self.assertIn('External Research', doc.title)
        self.assertEqual(doc.source_type, 'text')
        self.assertEqual(doc.file_type, 'ingested')
        self.assertEqual(doc.case, self.case)
        self.assertEqual(doc.processing_status, 'indexed')

        # Should have a chunk
        self.assertEqual(doc.chunks.count(), 1)

    @patch('apps.projects.ingestion_service._run_auto_reasoning')
    @patch('apps.projects.ingestion_service._generate_missing_embeddings')
    def test_ingest_multiple_items(self, mock_embed, mock_reason):
        """Multiple inputs should create multiple Evidence records."""
        mock_reason.return_value = {
            'links_created': 0, 'contradictions': 0, 'cascade_triggered': False,
        }

        inputs = [
            EvidenceInput(text=f'Fact {i}', retrieval_method='research_loop')
            for i in range(5)
        ]

        result = EvidenceIngestionService.ingest(
            inputs=inputs,
            case=self.case,
            user=self.user,
        )

        self.assertEqual(len(result.evidence_ids), 5)

        # Document evidence_count should be updated
        doc = Document.objects.get(id=result.document_id)
        self.assertEqual(doc.evidence_count, 5)

    @patch('apps.projects.ingestion_service._run_auto_reasoning')
    @patch('apps.projects.ingestion_service._generate_missing_embeddings')
    def test_ingest_skips_empty_text(self, mock_embed, mock_reason):
        """Inputs with empty text should be skipped."""
        mock_reason.return_value = {
            'links_created': 0, 'contradictions': 0, 'cascade_triggered': False,
        }

        inputs = [
            EvidenceInput(text='Valid fact'),
            EvidenceInput(text=''),
            EvidenceInput(text='   '),
        ]

        result = EvidenceIngestionService.ingest(
            inputs=inputs,
            case=self.case,
            user=self.user,
        )

        self.assertEqual(len(result.evidence_ids), 1)

    @patch('apps.projects.ingestion_service._run_auto_reasoning')
    @patch('apps.projects.ingestion_service._generate_missing_embeddings')
    def test_ingest_empty_inputs(self, mock_embed, mock_reason):
        """Empty inputs list should return empty result."""
        result = EvidenceIngestionService.ingest(
            inputs=[],
            case=self.case,
            user=self.user,
        )

        self.assertEqual(len(result.evidence_ids), 0)
        self.assertIsNone(result.document_id)
        mock_embed.assert_not_called()
        mock_reason.assert_not_called()

    @patch('apps.projects.ingestion_service._run_auto_reasoning')
    @patch('apps.projects.ingestion_service._generate_missing_embeddings')
    def test_ingest_parses_domain_from_url(self, mock_embed, mock_reason):
        """source_domain should be parsed from source_url if not provided."""
        mock_reason.return_value = {
            'links_created': 0, 'contradictions': 0, 'cascade_triggered': False,
        }

        inputs = [
            EvidenceInput(
                text='Some fact',
                source_url='https://www.perplexity.ai/search/test',
                source_domain='',  # Not provided
            ),
        ]

        result = EvidenceIngestionService.ingest(
            inputs=inputs,
            case=self.case,
            user=self.user,
        )

        evidence = ProjectEvidence.objects.get(id=result.evidence_ids[0])
        self.assertEqual(evidence.source_domain, 'www.perplexity.ai')

    @patch('apps.projects.ingestion_service._generate_missing_embeddings')
    def test_ingest_calls_auto_reasoning(self, mock_embed):
        """Auto-reasoning should be called when run_auto_reasoning=True."""
        with patch(
            'apps.projects.ingestion_service._run_auto_reasoning'
        ) as mock_reason:
            mock_reason.return_value = {
                'links_created': 3,
                'contradictions': 1,
                'cascade_triggered': True,
            }

            inputs = [EvidenceInput(text='Some fact')]

            result = EvidenceIngestionService.ingest(
                inputs=inputs,
                case=self.case,
                user=self.user,
                run_auto_reasoning=True,
            )

            mock_reason.assert_called_once()
            self.assertEqual(result.links_created, 3)
            self.assertEqual(result.contradictions_detected, 1)
            self.assertTrue(result.cascade_triggered)

    @patch('apps.projects.ingestion_service._generate_missing_embeddings')
    def test_ingest_skips_auto_reasoning_when_disabled(self, mock_embed):
        """Auto-reasoning should NOT be called when run_auto_reasoning=False."""
        with patch(
            'apps.projects.ingestion_service._run_auto_reasoning'
        ) as mock_reason:
            inputs = [EvidenceInput(text='Some fact')]

            result = EvidenceIngestionService.ingest(
                inputs=inputs,
                case=self.case,
                user=self.user,
                run_auto_reasoning=False,
            )

            mock_reason.assert_not_called()
            self.assertEqual(result.links_created, 0)

    @patch('apps.projects.ingestion_service._run_auto_reasoning')
    @patch('apps.projects.ingestion_service._generate_missing_embeddings')
    def test_ingest_truncates_long_text(self, mock_embed, mock_reason):
        """Evidence text should be truncated to EVIDENCE_TEXT_MAX_LEN."""
        mock_reason.return_value = {
            'links_created': 0, 'contradictions': 0, 'cascade_triggered': False,
        }

        long_text = 'x' * 5000
        inputs = [EvidenceInput(text=long_text)]

        result = EvidenceIngestionService.ingest(
            inputs=inputs,
            case=self.case,
            user=self.user,
        )

        evidence = ProjectEvidence.objects.get(id=result.evidence_ids[0])
        self.assertEqual(len(evidence.text), 2000)  # EVIDENCE_TEXT_MAX_LEN


class ExtractEvidenceFromFindingsTest(TestCase):
    """Test the refactored extract_evidence_from_findings()."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.project = Project.objects.create(
            user=self.user, title='Test Project'
        )
        self.case = Case.objects.create(
            title='Test Case',
            user=self.user,
            project=self.project,
            created_from_event_id=DUMMY_EVENT_ID,
        )

    @patch('apps.projects.ingestion_service._run_auto_reasoning')
    @patch('apps.projects.ingestion_service._generate_missing_embeddings')
    def test_findings_create_evidence_with_provenance(self, mock_embed, mock_reason):
        """Research findings should create evidence with research_loop provenance."""
        mock_reason.return_value = {
            'links_created': 0, 'contradictions': 0, 'cascade_triggered': False,
        }

        from apps.artifacts.workflows import extract_evidence_from_findings

        findings = [
            {
                'relevance_score': 0.9,
                'quality_score': 0.8,
                'raw_quote': 'Market is growing at 20% CAGR',
                'source_title': 'Industry Report',
                'source_url': 'https://example.com/report',
                'source_domain': 'example.com',
                'extracted_fields': {},
            },
        ]

        ids = extract_evidence_from_findings(findings, self.case)

        self.assertEqual(len(ids), 1)

        evidence = ProjectEvidence.objects.get(id=ids[0])
        self.assertEqual(evidence.retrieval_method, 'research_loop')
        self.assertEqual(evidence.source_url, 'https://example.com/report')
        self.assertEqual(evidence.source_title, 'Industry Report')
        self.assertEqual(evidence.source_domain, 'example.com')
        # Text should NOT have [Source: ...] suffix anymore
        self.assertNotIn('[Source:', evidence.text)

    @patch('apps.projects.ingestion_service._run_auto_reasoning')
    @patch('apps.projects.ingestion_service._generate_missing_embeddings')
    def test_findings_filter_low_relevance(self, mock_embed, mock_reason):
        """Findings below the relevance threshold should be filtered out."""
        mock_reason.return_value = {
            'links_created': 0, 'contradictions': 0, 'cascade_triggered': False,
        }

        from apps.artifacts.workflows import extract_evidence_from_findings

        findings = [
            {
                'relevance_score': 0.3,  # Below 0.6 threshold
                'quality_score': 0.9,
                'raw_quote': 'This should be filtered',
                'source_title': 'Low Relevance',
                'source_url': '',
                'extracted_fields': {},
            },
            {
                'relevance_score': 0.9,
                'quality_score': 0.8,
                'raw_quote': 'This should pass',
                'source_title': 'High Relevance',
                'source_url': '',
                'extracted_fields': {},
            },
        ]

        ids = extract_evidence_from_findings(findings, self.case)

        self.assertEqual(len(ids), 1)

    @patch('apps.projects.ingestion_service._run_auto_reasoning')
    @patch('apps.projects.ingestion_service._generate_missing_embeddings')
    def test_findings_calls_auto_reasoning(self, mock_embed, mock_reason):
        """Research evidence should trigger auto-reasoning (the key fix)."""
        mock_reason.return_value = {
            'links_created': 2, 'contradictions': 0, 'cascade_triggered': True,
        }

        from apps.artifacts.workflows import extract_evidence_from_findings

        findings = [
            {
                'relevance_score': 0.9,
                'quality_score': 0.8,
                'raw_quote': 'Important finding',
                'source_title': 'Report',
                'source_url': '',
                'extracted_fields': {},
            },
        ]

        extract_evidence_from_findings(findings, self.case)

        # Auto-reasoning should have been called
        mock_reason.assert_called_once()


class URLFetcherTest(TestCase):
    """Test URL content fetcher."""

    @patch('apps.projects.url_fetcher.requests.get')
    def test_fetch_extracts_content(self, mock_get):
        """Should extract title, text, and metadata from HTML."""
        from apps.projects.url_fetcher import fetch_url_content

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
        <head>
            <title>Test Article</title>
            <meta property="article:published_time" content="2025-06-15T10:00:00Z">
            <meta name="author" content="Jane Doe">
        </head>
        <body>
            <nav>Navigation stuff</nav>
            <article>This is the main content of the article.</article>
            <footer>Footer stuff</footer>
        </body>
        </html>
        '''
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = fetch_url_content('https://example.com/article')

        self.assertEqual(result.title, 'Test Article')
        self.assertEqual(result.domain, 'example.com')
        self.assertIn('main content', result.text)
        self.assertNotIn('Navigation stuff', result.text)
        self.assertNotIn('Footer stuff', result.text)
        self.assertEqual(result.published_date, '2025-06-15')
        self.assertEqual(result.author, 'Jane Doe')
        self.assertIsNone(result.error)

    @patch('apps.projects.url_fetcher.requests.get')
    def test_fetch_handles_timeout(self, mock_get):
        """Should return error on timeout."""
        import requests as req
        from apps.projects.url_fetcher import fetch_url_content

        mock_get.side_effect = req.exceptions.Timeout('timed out')

        result = fetch_url_content('https://example.com/slow')

        self.assertIsNotNone(result.error)
        self.assertIn('timed out', result.error)
        self.assertEqual(result.text, '')

    @patch('apps.projects.url_fetcher.requests.get')
    def test_fetch_handles_http_error(self, mock_get):
        """Should return error on HTTP error."""
        import requests as req
        from apps.projects.url_fetcher import fetch_url_content

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = req.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        result = fetch_url_content('https://example.com/missing')

        self.assertIsNotNone(result.error)
        self.assertEqual(result.text, '')


class EvidenceBridgeTest(TestCase):
    """Test inquiries.Evidence → projects.Evidence bridge."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.project = Project.objects.create(
            user=self.user, title='Test Project'
        )
        self.case = Case.objects.create(
            title='Test Case',
            user=self.user,
            project=self.project,
            created_from_event_id=DUMMY_EVENT_ID,
        )

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch('apps.cases.brief_signals._bridge_to_project_evidence')
    def test_bridge_called_for_meaningful_evidence(self, mock_bridge):
        """Bridge should be called when inquiry evidence has >= 20 chars."""
        from apps.inquiries.models import Inquiry, Evidence as InquiryEvidence

        inquiry = Inquiry.objects.create(
            title='Test Inquiry',
            case=self.case,
            elevation_reason='user_created',
            sequence_index=0,
        )
        # Creating InquiryEvidence fires the post_save signal
        # which should call _bridge_to_project_evidence
        inq_evidence = InquiryEvidence.objects.create(
            inquiry=inquiry,
            evidence_type='user_observation',
            evidence_text='This is a meaningful observation about the market conditions',
            direction='supports',
            strength=0.7,
            credibility=0.8,
            created_by=self.user,
        )

        # The post_save signal should have called the bridge
        mock_bridge.assert_called_once_with(inq_evidence)
