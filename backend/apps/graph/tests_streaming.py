"""
Tests for SSE streaming views — JWT authentication, CORS headers,
event format, polling behavior, and terminal state handling.

Tests both:
- graph/streaming_views.py  (summary_generation_stream)
- projects/streaming_views.py (document_processing_stream)
"""

import asyncio
import json
import os
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

# Allow synchronous DB access from within async event loops in tests.
# Our _fake_sync_to_async intentionally runs DB queries on the main thread
# so they can see TestCase's uncommitted transaction data.
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

from asgiref.sync import sync_to_async
from django.test import TestCase, TransactionTestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse, StreamingHttpResponse

from apps.graph.models import ProjectSummary, SummaryStatus
from apps.projects.models import Project, Document

User = get_user_model()


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════


def _make_request(path='/', method='GET', user=None, headers=None):
    """Create a fake Django request with optional JWT header and CORS origin."""
    factory = RequestFactory()
    request = factory.get(path)

    if headers:
        for key, value in headers.items():
            # RequestFactory uses META keys
            meta_key = key.replace('-', '_').upper()
            if not meta_key.startswith('HTTP_'):
                meta_key = f'HTTP_{meta_key}'
            request.META[meta_key] = value

    return request


def _run_async(coro):
    """Run an async coroutine synchronously for test assertions.

    Forces the async event loop to reuse the calling thread's DB connection
    so that TestCase's uncommitted transaction data remains visible.
    """
    from django.db import connection, connections
    original_conn = connection.connection
    original_atomic = connection.in_atomic_block

    async def _wrapped():
        # Force Django to reuse the test's DB connection inside the event loop.
        # Without this, Django creates a new connection that can't see
        # the TestCase's uncommitted transaction data.
        db = connections['default']
        if db.connection is not original_conn:
            db.close()
            db.connection = original_conn
            db.in_atomic_block = original_atomic
        return await coro

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_wrapped())
    finally:
        loop.close()


def _fake_sync_to_async(fn=None, thread_sensitive=True):
    """Replace sync_to_async for testing: runs fn on the calling thread.

    This avoids TestCase thread-isolation issues where sync_to_async opens a
    new DB connection that cannot see the test transaction's uncommitted rows.
    """
    if fn is None:
        # Called as decorator factory: sync_to_async(thread_sensitive=True)
        def decorator(fn):
            async def wrapper(*args, **kwargs):
                return fn(*args, **kwargs)
            return wrapper
        return decorator
    # Called directly: sync_to_async(lambda: ...)
    async def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper


async def _collect_events(response, max_events=10):
    """Collect SSE events from a StreamingHttpResponse."""
    events = []
    count = 0
    async for chunk in response.streaming_content:
        if isinstance(chunk, bytes):
            chunk = chunk.decode('utf-8')
        for block in chunk.split('\n\n'):
            block = block.strip()
            if not block:
                continue
            lines = block.split('\n')
            event = {}
            for line in lines:
                if line.startswith('event: '):
                    event['type'] = line[7:]
                elif line.startswith('data: '):
                    try:
                        event['data'] = json.loads(line[6:])
                    except json.JSONDecodeError:
                        event['data'] = line[6:]
            if event:
                events.append(event)
            count += 1
            if count >= max_events:
                return events
    return events


# ═══════════════════════════════════════════════════════════════════
# JWT Authentication Tests
# ═══════════════════════════════════════════════════════════════════


class JWTAuthenticationTests(TestCase):
    """Test authenticate_jwt for both streaming views."""

    def test_graph_missing_auth_header_returns_none(self):
        from apps.graph.streaming_views import authenticate_jwt
        request = _make_request()
        result = _run_async(authenticate_jwt(request))
        self.assertIsNone(result)

    def test_graph_non_bearer_header_returns_none(self):
        from apps.graph.streaming_views import authenticate_jwt
        request = _make_request(headers={'Authorization': 'Basic dXNlcjpwYXNz'})
        result = _run_async(authenticate_jwt(request))
        self.assertIsNone(result)

    def test_graph_invalid_token_returns_none(self):
        from apps.graph.streaming_views import authenticate_jwt
        request = _make_request(headers={'Authorization': 'Bearer invalid.jwt.token'})
        result = _run_async(authenticate_jwt(request))
        self.assertIsNone(result)

    def test_projects_missing_auth_header_returns_none(self):
        from apps.projects.streaming_views import authenticate_jwt
        request = _make_request()
        result = _run_async(authenticate_jwt(request))
        self.assertIsNone(result)

    def test_projects_non_bearer_header_returns_none(self):
        from apps.projects.streaming_views import authenticate_jwt
        request = _make_request(headers={'Authorization': 'Token abc123'})
        result = _run_async(authenticate_jwt(request))
        self.assertIsNone(result)

    @patch('apps.graph.streaming_views.sync_to_async')
    def test_graph_valid_token_returns_user(self, mock_sync_to_async):
        """Valid JWT should return the authenticated user."""
        from apps.graph.streaming_views import authenticate_jwt

        mock_user = MagicMock()
        mock_user.id = 1

        # Mock the sync_to_async chain to return our user
        mock_get_token = AsyncMock(return_value='validated_token')
        mock_get_user = AsyncMock(return_value=mock_user)

        call_count = [0]
        def side_effect(fn):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_get_token
            return mock_get_user

        mock_sync_to_async.side_effect = side_effect

        request = _make_request(headers={'Authorization': 'Bearer valid.jwt.token'})
        result = _run_async(authenticate_jwt(request))
        self.assertEqual(result, mock_user)


# ═══════════════════════════════════════════════════════════════════
# Summary Stream — Auth & Ownership
# ═══════════════════════════════════════════════════════════════════


@patch('apps.graph.streaming_views.sync_to_async', _fake_sync_to_async)
class SummaryStreamAuthTests(TestCase):
    """Test summary_generation_stream auth and ownership checks."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='stream_auth', email='stream_auth@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='Stream Auth Project', user=self.user
        )

    @patch('apps.graph.streaming_views.authenticate_jwt')
    def test_unauthenticated_returns_401(self, mock_auth):
        from apps.graph.streaming_views import summary_generation_stream

        mock_auth.return_value = None  # async mock not needed since we mock the func
        # Wrap to make it awaitable
        mock_auth.side_effect = None
        mock_auth.return_value = None

        request = _make_request()

        # Need to handle async view
        async def _test():
            mock_auth.return_value = None
            response = await summary_generation_stream(request, self.project.id)
            return response

        response = _run_async(_test())
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 401)

    @patch('apps.graph.streaming_views.authenticate_jwt')
    def test_wrong_owner_returns_404(self, mock_auth):
        from apps.graph.streaming_views import summary_generation_stream

        other_user = User.objects.create_user(
            username='other_stream', email='other_stream@example.com', password='testpass'
        )

        request = _make_request()

        async def _test():
            mock_auth.return_value = other_user
            response = await summary_generation_stream(request, self.project.id)
            return response

        response = _run_async(_test())
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 404)

    @patch('apps.graph.streaming_views.authenticate_jwt')
    def test_valid_owner_returns_streaming_response(self, mock_auth):
        from apps.graph.streaming_views import summary_generation_stream

        # Create a completed summary so the stream terminates immediately
        ProjectSummary.objects.create(
            project=self.project,
            status=SummaryStatus.FULL,
            sections={'overview': 'Test summary overview text'},
            version=1,
            generation_metadata={'tier': 'full'},
        )

        request = _make_request()
        request.META['HTTP_ORIGIN'] = ''

        async def _test():
            mock_auth.return_value = self.user
            response = await summary_generation_stream(request, self.project.id)
            return response

        response = _run_async(_test())
        self.assertIsInstance(response, StreamingHttpResponse)
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        self.assertEqual(response['Cache-Control'], 'no-cache')
        self.assertEqual(response['X-Accel-Buffering'], 'no')


# ═══════════════════════════════════════════════════════════════════
# CORS Header Tests
# ═══════════════════════════════════════════════════════════════════


@patch('apps.graph.streaming_views.sync_to_async', _fake_sync_to_async)
class CORSHeaderTests(TestCase):
    """Test CORS header handling in streaming views."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='cors_test', email='cors_test@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='CORS Test Project', user=self.user
        )
        # Create a completed summary so stream terminates
        ProjectSummary.objects.create(
            project=self.project,
            status=SummaryStatus.FULL,
            sections={'overview': 'CORS test summary'},
            version=1,
            generation_metadata={'tier': 'full'},
        )

    @patch('apps.graph.streaming_views.authenticate_jwt')
    @override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:3000', 'https://app.example.com'])
    def test_allowed_origin_gets_cors_headers(self, mock_auth):
        from apps.graph.streaming_views import summary_generation_stream

        request = _make_request(headers={'Origin': 'http://localhost:3000'})

        async def _test():
            mock_auth.return_value = self.user
            response = await summary_generation_stream(request, self.project.id)
            return response

        response = _run_async(_test())
        self.assertEqual(
            response.get('Access-Control-Allow-Origin'),
            'http://localhost:3000',
        )
        self.assertEqual(
            response.get('Access-Control-Allow-Credentials'),
            'true',
        )

    @patch('apps.graph.streaming_views.authenticate_jwt')
    @override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:3000'])
    def test_disallowed_origin_no_cors_headers(self, mock_auth):
        from apps.graph.streaming_views import summary_generation_stream

        request = _make_request(headers={'Origin': 'http://evil.example.com'})

        async def _test():
            mock_auth.return_value = self.user
            response = await summary_generation_stream(request, self.project.id)
            return response

        response = _run_async(_test())
        self.assertIsNone(response.get('Access-Control-Allow-Origin'))

    @patch('apps.graph.streaming_views.authenticate_jwt')
    @override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:3000'])
    def test_no_origin_header_no_cors(self, mock_auth):
        from apps.graph.streaming_views import summary_generation_stream

        request = _make_request()  # no origin header

        async def _test():
            mock_auth.return_value = self.user
            response = await summary_generation_stream(request, self.project.id)
            return response

        response = _run_async(_test())
        self.assertIsNone(response.get('Access-Control-Allow-Origin'))


# ═══════════════════════════════════════════════════════════════════
# SSE Event Format Tests — Summary Stream
# ═══════════════════════════════════════════════════════════════════


@patch('apps.graph.streaming_views.sync_to_async', _fake_sync_to_async)
class SummaryStreamEventTests(TestCase):
    """Test SSE event format and terminal state handling for summary stream."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='sse_events', email='sse_events@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='SSE Events Project', user=self.user
        )

    @patch('apps.graph.streaming_views.authenticate_jwt')
    def test_completed_summary_emits_status_sections_completed(self, mock_auth):
        from apps.graph.streaming_views import summary_generation_stream

        ProjectSummary.objects.create(
            project=self.project,
            status=SummaryStatus.FULL,
            sections={'overview': 'Full summary of project', 'key_findings': []},
            version=2,
            generation_metadata={'tier': 'full'},
        )

        request = _make_request()
        request.META['HTTP_ORIGIN'] = ''

        async def _test():
            mock_auth.return_value = self.user
            response = await summary_generation_stream(request, self.project.id)
            events = await _collect_events(response)
            return events

        events = _run_async(_test())

        # Should have: status, sections, completed
        event_types = [e['type'] for e in events]
        self.assertIn('status', event_types)
        self.assertIn('sections', event_types)
        self.assertIn('completed', event_types)

    @patch('apps.graph.streaming_views.authenticate_jwt')
    def test_failed_summary_emits_failed_event(self, mock_auth):
        from apps.graph.streaming_views import summary_generation_stream

        ProjectSummary.objects.create(
            project=self.project,
            status=SummaryStatus.FAILED,
            sections={},
            version=1,
            generation_metadata={'error': 'LLM timeout', 'tier': 'full'},
        )

        request = _make_request()
        request.META['HTTP_ORIGIN'] = ''

        async def _test():
            mock_auth.return_value = self.user
            response = await summary_generation_stream(request, self.project.id)
            events = await _collect_events(response)
            return events

        events = _run_async(_test())

        event_types = [e['type'] for e in events]
        self.assertIn('failed', event_types)
        # Failed event should include error message
        failed_event = next(e for e in events if e['type'] == 'failed')
        self.assertIn('error', failed_event['data'])

    @patch('apps.graph.streaming_views.authenticate_jwt')
    def test_thematic_status_is_terminal(self, mock_auth):
        from apps.graph.streaming_views import summary_generation_stream

        ProjectSummary.objects.create(
            project=self.project,
            status=SummaryStatus.THEMATIC,
            sections={'overview': 'Thematic summary'},
            version=1,
            generation_metadata={'tier': 'thematic'},
        )

        request = _make_request()
        request.META['HTTP_ORIGIN'] = ''

        async def _test():
            mock_auth.return_value = self.user
            response = await summary_generation_stream(request, self.project.id)
            events = await _collect_events(response)
            return events

        events = _run_async(_test())
        event_types = [e['type'] for e in events]
        self.assertIn('completed', event_types)

    @patch('apps.graph.streaming_views.authenticate_jwt')
    def test_seed_status_is_terminal(self, mock_auth):
        from apps.graph.streaming_views import summary_generation_stream

        ProjectSummary.objects.create(
            project=self.project,
            status=SummaryStatus.SEED,
            sections={'overview': 'Seed summary'},
            version=1,
            generation_metadata={'tier': 'seed'},
        )

        request = _make_request()
        request.META['HTTP_ORIGIN'] = ''

        async def _test():
            mock_auth.return_value = self.user
            response = await summary_generation_stream(request, self.project.id)
            events = await _collect_events(response)
            return events

        events = _run_async(_test())
        event_types = [e['type'] for e in events]
        self.assertIn('completed', event_types)

    @patch('apps.graph.streaming_views.authenticate_jwt')
    def test_status_event_includes_version_and_tier(self, mock_auth):
        from apps.graph.streaming_views import summary_generation_stream

        ProjectSummary.objects.create(
            project=self.project,
            status=SummaryStatus.FULL,
            sections={'overview': 'Test'},
            version=3,
            generation_metadata={'tier': 'full'},
        )

        request = _make_request()
        request.META['HTTP_ORIGIN'] = ''

        async def _test():
            mock_auth.return_value = self.user
            response = await summary_generation_stream(request, self.project.id)
            events = await _collect_events(response)
            return events

        events = _run_async(_test())
        status_event = next(e for e in events if e['type'] == 'status')
        self.assertEqual(status_event['data']['version'], 3)
        self.assertEqual(status_event['data']['tier'], 'full')

    @patch('apps.graph.streaming_views.authenticate_jwt')
    def test_empty_sections_not_emitted(self, mock_auth):
        from apps.graph.streaming_views import summary_generation_stream

        ProjectSummary.objects.create(
            project=self.project,
            status=SummaryStatus.FAILED,
            sections={},  # empty
            version=1,
            generation_metadata={'error': 'Boom', 'tier': 'full'},
        )

        request = _make_request()
        request.META['HTTP_ORIGIN'] = ''

        async def _test():
            mock_auth.return_value = self.user
            response = await summary_generation_stream(request, self.project.id)
            events = await _collect_events(response)
            return events

        events = _run_async(_test())
        event_types = [e['type'] for e in events]
        self.assertNotIn('sections', event_types)


# ═══════════════════════════════════════════════════════════════════
# Document Processing Stream — Auth & Events
# ═══════════════════════════════════════════════════════════════════


@patch('apps.projects.streaming_views.sync_to_async', _fake_sync_to_async)
class DocumentStreamAuthTests(TestCase):
    """Test document_processing_stream auth and ownership."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='doc_stream', email='doc_stream@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='Doc Stream Project', user=self.user
        )
        self.document = Document.objects.create(
            project=self.project,
            user=self.user,
            title='Test Document',
            content_text='Document content for processing.',
            processing_progress={'stage': 'completed'},
        )

    @patch('apps.projects.streaming_views.authenticate_jwt')
    def test_unauthenticated_returns_401(self, mock_auth):
        from apps.projects.streaming_views import document_processing_stream

        request = _make_request()

        async def _test():
            mock_auth.return_value = None
            response = await document_processing_stream(request, self.document.id)
            return response

        response = _run_async(_test())
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 401)

    @patch('apps.projects.streaming_views.authenticate_jwt')
    def test_wrong_owner_returns_404(self, mock_auth):
        from apps.projects.streaming_views import document_processing_stream

        other_user = User.objects.create_user(
            username='other_doc', email='other_doc@example.com', password='testpass'
        )

        request = _make_request()

        async def _test():
            mock_auth.return_value = other_user
            response = await document_processing_stream(request, self.document.id)
            return response

        response = _run_async(_test())
        self.assertEqual(response.status_code, 404)

    @patch('apps.projects.streaming_views.authenticate_jwt')
    def test_valid_returns_streaming_response(self, mock_auth):
        from apps.projects.streaming_views import document_processing_stream

        request = _make_request()
        request.META['HTTP_ORIGIN'] = ''

        async def _test():
            mock_auth.return_value = self.user
            response = await document_processing_stream(request, self.document.id)
            return response

        response = _run_async(_test())
        self.assertIsInstance(response, StreamingHttpResponse)
        self.assertEqual(response['Content-Type'], 'text/event-stream')


@patch('apps.projects.streaming_views.sync_to_async', _fake_sync_to_async)
class DocumentStreamEventTests(TestCase):
    """Test SSE event format for document processing stream."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='doc_events', email='doc_events@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='Doc Events Project', user=self.user
        )

    def _make_document(self, progress):
        return Document.objects.create(
            project=self.project,
            user=self.user,
            title='Test Doc',
            content_text='Content for processing test.',
            processing_progress=progress,
        )

    @patch('apps.projects.streaming_views.authenticate_jwt')
    def test_completed_emits_progress_and_completed(self, mock_auth):
        from apps.projects.streaming_views import document_processing_stream

        doc = self._make_document({'stage': 'completed', 'chunks': 10})

        request = _make_request()
        request.META['HTTP_ORIGIN'] = ''

        async def _test():
            mock_auth.return_value = self.user
            response = await document_processing_stream(request, doc.id)
            events = await _collect_events(response)
            return events

        events = _run_async(_test())
        event_types = [e['type'] for e in events]
        self.assertIn('progress', event_types)
        self.assertIn('completed', event_types)

    @patch('apps.projects.streaming_views.authenticate_jwt')
    def test_failed_emits_failed_event(self, mock_auth):
        from apps.projects.streaming_views import document_processing_stream

        doc = self._make_document({'stage': 'failed', 'error': 'Parse error'})

        request = _make_request()
        request.META['HTTP_ORIGIN'] = ''

        async def _test():
            mock_auth.return_value = self.user
            response = await document_processing_stream(request, doc.id)
            events = await _collect_events(response)
            return events

        events = _run_async(_test())
        event_types = [e['type'] for e in events]
        self.assertIn('failed', event_types)

    @patch('apps.projects.streaming_views.authenticate_jwt')
    @override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:3000'])
    def test_cors_headers_set_for_allowed_origin(self, mock_auth):
        from apps.projects.streaming_views import document_processing_stream

        doc = self._make_document({'stage': 'completed'})
        request = _make_request(headers={'Origin': 'http://localhost:3000'})

        async def _test():
            mock_auth.return_value = self.user
            response = await document_processing_stream(request, doc.id)
            return response

        response = _run_async(_test())
        self.assertEqual(
            response.get('Access-Control-Allow-Origin'),
            'http://localhost:3000',
        )
        self.assertEqual(
            response.get('Access-Control-Allow-Credentials'),
            'true',
        )

    @patch('apps.projects.streaming_views.authenticate_jwt')
    @override_settings(CORS_ALLOWED_ORIGINS=['http://localhost:3000'])
    def test_cors_headers_not_set_for_disallowed_origin(self, mock_auth):
        from apps.projects.streaming_views import document_processing_stream

        doc = self._make_document({'stage': 'completed'})
        request = _make_request(headers={'Origin': 'http://attacker.com'})

        async def _test():
            mock_auth.return_value = self.user
            response = await document_processing_stream(request, doc.id)
            return response

        response = _run_async(_test())
        self.assertIsNone(response.get('Access-Control-Allow-Origin'))


# ═══════════════════════════════════════════════════════════════════
# Response header tests
# ═══════════════════════════════════════════════════════════════════


@patch('apps.graph.streaming_views.sync_to_async', _fake_sync_to_async)
class StreamingResponseHeaderTests(TestCase):
    """Test that streaming responses have correct headers for SSE."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='headers', email='headers@example.com', password='testpass'
        )
        self.project = Project.objects.create(
            title='Headers Project', user=self.user
        )
        ProjectSummary.objects.create(
            project=self.project,
            status=SummaryStatus.FULL,
            sections={'overview': 'Test'},
            version=1,
            generation_metadata={'tier': 'full'},
        )

    @patch('apps.graph.streaming_views.authenticate_jwt')
    def test_content_type_is_event_stream(self, mock_auth):
        from apps.graph.streaming_views import summary_generation_stream

        request = _make_request()
        request.META['HTTP_ORIGIN'] = ''

        async def _test():
            mock_auth.return_value = self.user
            return await summary_generation_stream(request, self.project.id)

        response = _run_async(_test())
        self.assertEqual(response['Content-Type'], 'text/event-stream')

    @patch('apps.graph.streaming_views.authenticate_jwt')
    def test_cache_control_no_cache(self, mock_auth):
        from apps.graph.streaming_views import summary_generation_stream

        request = _make_request()
        request.META['HTTP_ORIGIN'] = ''

        async def _test():
            mock_auth.return_value = self.user
            return await summary_generation_stream(request, self.project.id)

        response = _run_async(_test())
        self.assertEqual(response['Cache-Control'], 'no-cache')

    @patch('apps.graph.streaming_views.authenticate_jwt')
    def test_nginx_buffering_disabled(self, mock_auth):
        from apps.graph.streaming_views import summary_generation_stream

        request = _make_request()
        request.META['HTTP_ORIGIN'] = ''

        async def _test():
            mock_auth.return_value = self.user
            return await summary_generation_stream(request, self.project.id)

        response = _run_async(_test())
        self.assertEqual(response['X-Accel-Buffering'], 'no')
