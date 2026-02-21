"""Tests for task workflow progress helpers."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.projects.models import Document, Project
from tasks.workflows import _update_document_progress


User = get_user_model()


class DocumentProgressTests(TestCase):
    """Regression tests for document processing progress updates."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='workflow-tests@example.com',
            password='testpass',
        )
        self.project = Project.objects.create(
            title='Workflow Project',
            user=self.user,
        )
        self.document = Document.objects.create(
            title='Workflow Doc',
            source_type='text',
            content_text='Testing progress updates.',
            project=self.project,
            user=self.user,
        )

    def test_progress_update_does_not_depend_on_process_global_state(self):
        """
        If persisted progress is cleared, update should still write.

        This protects against stale in-process dedup state leaking across
        Celery tasks for the same document.
        """
        _update_document_progress(
            self.document, 'chunking', 'Chunking document', 1,
        )
        self.document.processing_progress = {}
        self.document.save(update_fields=['processing_progress'])

        _update_document_progress(
            self.document, 'chunking', 'Chunking document', 1,
        )
        self.document.refresh_from_db()

        self.assertEqual(self.document.processing_progress.get('stage'), 'chunking')
        self.assertEqual(self.document.processing_progress.get('stage_index'), 1)

    def test_progress_update_deduplicates_same_stage_without_counts(self):
        _update_document_progress(
            self.document, 'embedding', 'Generating embeddings', 2,
        )
        first_updated_at = self.document.processing_progress.get('updated_at')

        _update_document_progress(
            self.document, 'embedding', 'Generating embeddings', 2,
        )
        self.document.refresh_from_db()

        self.assertEqual(
            self.document.processing_progress.get('updated_at'),
            first_updated_at,
        )
