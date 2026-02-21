"""
SSE streaming views for document processing progress.

Streams real-time progress updates as the document processing pipeline
runs in Celery. The Celery task writes progress to
document.processing_progress (JSONField), and this view polls that field
every 500ms, yielding SSE events to the client.
"""
import asyncio
import json
import logging

from asgiref.sync import sync_to_async
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from apps.common.auth import authenticate_jwt

logger = logging.getLogger(__name__)


@csrf_exempt
@require_GET
async def document_processing_stream(request, document_id):
    """
    SSE endpoint for document processing progress.

    GET /api/documents/{document_id}/processing-stream/

    Streams events as the Celery pipeline processes the document:
      event: progress   — stage update with counts
      event: completed  — terminal: processing finished
      event: failed     — terminal: processing errored

    The stream terminates on completed/failed or after 5 minutes.
    """
    user = await authenticate_jwt(request)
    if user is None:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    from apps.projects.models import Document

    # Verify ownership
    document = await sync_to_async(
        lambda: Document.objects.filter(id=document_id, user=user).first()
    )()
    if not document:
        return JsonResponse({'error': 'Document not found'}, status=404)

    async def event_stream():
        last_progress_json = None
        no_change_count = 0
        elapsed_seconds = 0
        max_seconds = 300  # 5-minute timeout

        # Adaptive polling: fast during early stages, slower during LLM stages
        FAST_INTERVAL = 0.5   # 500ms for chunking/embedding
        SLOW_INTERVAL = 2.0   # 2s for LLM extraction (saves DB reads)
        SLOW_STAGES = {'extracting_graph'}

        while elapsed_seconds < max_seconds:
            # Read current progress from DB
            progress = await sync_to_async(
                lambda: Document.objects.values_list(
                    'processing_progress', flat=True
                ).get(id=document_id)
            )()

            progress_json = json.dumps(progress or {}, default=str)

            # Only emit if progress changed
            if progress_json != last_progress_json:
                last_progress_json = progress_json
                no_change_count = 0
                stage = (progress or {}).get('stage', 'pending')

                yield f"event: progress\ndata: {progress_json}\n\n"

                # Terminal states
                if stage == 'completed':
                    yield f"event: completed\ndata: {progress_json}\n\n"
                    return
                if stage == 'failed':
                    yield f"event: failed\ndata: {progress_json}\n\n"
                    return
            else:
                no_change_count += 1

            # Adaptive sleep — poll slower during LLM-heavy stages
            current_stage = (progress or {}).get('stage', '')
            if current_stage in SLOW_STAGES or no_change_count > 10:
                interval = SLOW_INTERVAL
            else:
                interval = FAST_INTERVAL

            await asyncio.sleep(interval)
            elapsed_seconds += interval

        # Timeout
        yield f"event: timeout\ndata: {json.dumps({'error': 'Processing timed out'})}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'

    # CORS headers (match the pattern from chat/views.py)
    from django.conf import settings
    origin = request.META.get('HTTP_ORIGIN', '')
    allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
    if origin in allowed_origins:
        response['Access-Control-Allow-Origin'] = origin
        response['Access-Control-Allow-Credentials'] = 'true'

    return response
