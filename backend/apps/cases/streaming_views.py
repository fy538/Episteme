"""
SSE streaming view for case extraction pipeline progress.

Streams real-time status updates as the Celery extraction task runs.
The task writes status progressively to case.metadata, and this view
polls that field every 1s, yielding SSE events to the client.

Events:
  event: status     — extraction phase change
  event: progress   — partial results (e.g., chunks retrieved)
  event: completed  — terminal: extraction + analysis done
  event: failed     — terminal: pipeline errored
  event: timeout    — terminal: 3-minute timeout

Pattern matches graph/streaming_views.py (summary generation stream).
"""
import asyncio
import json
import logging

from asgiref.sync import sync_to_async
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from apps.common.auth import authenticate_jwt

logger = logging.getLogger(__name__)


@csrf_exempt
@require_GET
async def case_extraction_stream(request, case_id):
    """
    SSE endpoint for case extraction pipeline progress.

    GET /api/cases/{case_id}/extraction/stream/

    Streams events as the extraction pipeline runs:
      event: status    — { extraction_status, chunks_retrieved }
      event: progress  — partial extraction_result data
      event: completed — terminal: extraction + analysis complete
      event: failed    — terminal: pipeline errored

    The stream terminates on completed/failed or after 3 minutes.
    Clients should call this after case creation when extraction is pending.
    """
    user = await authenticate_jwt(request)
    if user is None:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    from apps.cases.models import Case

    # Verify ownership
    case = await sync_to_async(
        lambda: Case.objects.filter(id=case_id, user=user).first()
    )()
    if not case:
        return JsonResponse({'error': 'Case not found'}, status=404)

    async def event_stream():
        last_data_json = None
        elapsed_seconds = 0
        max_seconds = 180  # 3-minute timeout
        poll_interval = 1.0  # 1s polling

        while elapsed_seconds < max_seconds:
            # Read latest metadata
            case_data = await sync_to_async(
                lambda: (
                    Case.objects
                    .filter(id=case_id)
                    .values('metadata')
                    .first()
                )
            )()

            if not case_data:
                await asyncio.sleep(poll_interval)
                elapsed_seconds += poll_interval
                continue

            metadata = case_data.get('metadata') or {}
            extraction_status = metadata.get('extraction_status', 'none')
            extraction_result = metadata.get('extraction_result')
            analysis = metadata.get('analysis')
            error = metadata.get('extraction_error')

            # Build event payload
            data = {
                'extraction_status': extraction_status,
                'chunks_retrieved': metadata.get('chunks_retrieved', 0),
                'extraction_result': extraction_result,
                'has_analysis': analysis is not None,
            }
            data_json = json.dumps(data, default=str)

            # Only emit if data changed
            if data_json != last_data_json:
                last_data_json = data_json

                # Emit status event
                yield f"event: status\ndata: {json.dumps({'extraction_status': extraction_status, 'chunks_retrieved': metadata.get('chunks_retrieved', 0)})}\n\n"

                # Emit progress if extraction result available
                if extraction_result:
                    yield f"event: progress\ndata: {json.dumps(extraction_result, default=str)}\n\n"

                # Terminal: complete
                if extraction_status == 'complete':
                    completion_data = {
                        'extraction_status': 'complete',
                        'extraction_result': extraction_result,
                        'analysis_summary': (analysis or {}).get('readiness', {}),
                    }
                    yield f"event: completed\ndata: {json.dumps(completion_data, default=str)}\n\n"
                    return

                # Terminal: failed
                if extraction_status == 'failed':
                    yield f"event: failed\ndata: {json.dumps({'error': error or 'Unknown error'})}\n\n"
                    return

            await asyncio.sleep(poll_interval)
            elapsed_seconds += poll_interval

        # Timeout
        yield f"event: timeout\ndata: {json.dumps({'error': 'Extraction stream timed out'})}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'

    # CORS headers
    from django.conf import settings
    origin = request.META.get('HTTP_ORIGIN', '')
    allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
    if origin in allowed_origins:
        response['Access-Control-Allow-Origin'] = origin
        response['Access-Control-Allow-Credentials'] = 'true'

    return response
