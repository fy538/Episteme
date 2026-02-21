"""
SSE streaming view for project summary generation progress.

Streams real-time status + section updates as the Celery summary task runs.
The task writes sections progressively to the ProjectSummary row, and this
view polls that row every 1s, yielding SSE events to the client.

Events:
  event: status   — status change (generating, thematic, full, failed)
  event: sections — partial or complete sections JSON
  event: completed — terminal: summary is ready (full or thematic)
  event: failed   — terminal: generation errored

The stream terminates on completed/failed or after 3 minutes.
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
async def summary_generation_stream(request, project_id):
    """
    SSE endpoint for project summary generation progress.

    GET /api/v2/projects/{project_id}/summary/stream/

    Streams events as the summary generation task runs:
      event: status   — { status, version, tier }
      event: sections — partial sections as they become available
      event: completed — terminal: summary is ready
      event: failed   — terminal: generation errored

    The stream terminates on completed/failed or after 3 minutes.
    Clients should call this after triggering regeneration (POST /regenerate/).
    """
    user = await authenticate_jwt(request)
    if user is None:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    from apps.projects.models import Project

    # Verify ownership
    project = await sync_to_async(
        lambda: Project.objects.filter(id=project_id, user=user).first()
    )()
    if not project:
        return JsonResponse({'error': 'Project not found'}, status=404)

    async def event_stream():
        last_data_json = None
        elapsed_seconds = 0
        max_seconds = 180  # 3-minute timeout (full summary is ~30s)
        poll_interval = 1.0  # 1s polling — summaries update infrequently

        from apps.graph.models import ProjectSummary

        def _fetch_latest_summary(pid):
            return (
                ProjectSummary.objects
                .filter(project_id=pid)
                .order_by('-created_at')
                .values('status', 'sections', 'version', 'generation_metadata')
                .first()
            )

        while elapsed_seconds < max_seconds:
            # Read latest summary row for this project
            summary = await sync_to_async(_fetch_latest_summary)(project_id)

            if not summary:
                await asyncio.sleep(poll_interval)
                elapsed_seconds += poll_interval
                continue

            current_status = summary['status']
            sections = summary['sections'] or {}
            version = summary['version']
            metadata = summary['generation_metadata'] or {}

            # Build event payload
            data = {
                'status': current_status,
                'version': version,
                'tier': metadata.get('tier', ''),
                'sections': sections,
            }
            data_json = json.dumps(data, default=str)

            # Only emit if data changed
            if data_json != last_data_json:
                last_data_json = data_json

                yield f"event: status\ndata: {json.dumps({'status': current_status, 'version': version, 'tier': metadata.get('tier', '')})}\n\n"

                # Emit sections if non-empty
                if sections:
                    yield f"event: sections\ndata: {json.dumps(sections, default=str)}\n\n"

                # Terminal states
                if current_status in ('full', 'thematic', 'seed'):
                    yield f"event: completed\ndata: {data_json}\n\n"
                    return
                if current_status == 'failed':
                    error = metadata.get('error', 'Unknown error')
                    yield f"event: failed\ndata: {json.dumps({'error': error, 'version': version})}\n\n"
                    return

            await asyncio.sleep(poll_interval)
            elapsed_seconds += poll_interval

        # Timeout
        yield f"event: timeout\ndata: {json.dumps({'error': 'Summary generation timed out'})}\n\n"

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


@csrf_exempt
@require_GET
async def orientation_generation_stream(request, project_id):
    """
    SSE endpoint for orientation generation progress.

    GET /api/v2/projects/{project_id}/orientation/stream/

    Streams events as the orientation generation task runs:
      event: status   — { status, lens_type }
      event: lead     — { lead_text } (emitted once when lead is set)
      event: finding  — one per finding as they're created
      event: angle    — one per exploration angle
      event: completed — terminal: orientation is ready
      event: failed   — terminal: generation errored

    The stream terminates on completed/failed or after 60 seconds.
    Clients should call this after triggering regeneration or detecting
    a 'generating' status from the GET endpoint.
    """
    user = await authenticate_jwt(request)
    if user is None:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    from apps.projects.models import Project

    project = await sync_to_async(
        lambda: Project.objects.filter(id=project_id, user=user).first()
    )()
    if not project:
        return JsonResponse({'error': 'Project not found'}, status=404)

    async def event_stream():
        elapsed_seconds = 0
        max_seconds = 60  # Orientation is fast (~5-10s)
        poll_interval = 0.5
        last_status = None
        last_finding_count = 0
        lead_emitted = False

        from apps.graph.models import ProjectOrientation, ProjectInsight

        # Avoid lambda closures over loop-mutable variables — use
        # explicit helper functions with bound arguments instead.
        def _fetch_latest_orientation(pid):
            return (
                ProjectOrientation.objects
                .filter(project_id=pid)
                .order_by('-created_at')
                .first()
            )

        def _fetch_findings(orientation_obj):
            return list(
                ProjectInsight.objects
                .filter(orientation=orientation_obj)
                .order_by('display_order')
                .values(
                    'id', 'insight_type', 'title', 'content',
                    'source_cluster_ids', 'status', 'confidence',
                    'display_order', 'action_type',
                )
            )

        while elapsed_seconds < max_seconds:
            # Read latest orientation for this project
            orientation = await sync_to_async(_fetch_latest_orientation)(project_id)

            if not orientation:
                await asyncio.sleep(poll_interval)
                elapsed_seconds += poll_interval
                continue

            current_status = orientation.status

            # Emit status change
            if current_status != last_status:
                last_status = current_status
                yield f"event: status\ndata: {json.dumps({'status': current_status, 'lens_type': orientation.lens_type or ''})}\n\n"

            # Emit lead text once
            if orientation.lead_text and not lead_emitted:
                lead_emitted = True
                yield f"event: lead\ndata: {json.dumps({'lead_text': orientation.lead_text})}\n\n"

            # Emit new findings/angles progressively
            findings = await sync_to_async(_fetch_findings)(orientation)

            if len(findings) > last_finding_count:
                for finding in findings[last_finding_count:]:
                    # Serialize UUIDs
                    finding['id'] = str(finding['id'])
                    event_type = 'angle' if finding['insight_type'] == 'exploration_angle' else 'finding'
                    yield f"event: {event_type}\ndata: {json.dumps(finding, default=str)}\n\n"
                last_finding_count = len(findings)

            # Terminal states
            if current_status == 'ready':
                metadata = orientation.generation_metadata or {}
                yield f"event: completed\ndata: {json.dumps({'status': 'ready', 'metadata': metadata}, default=str)}\n\n"
                return
            if current_status == 'failed':
                yield f"event: failed\ndata: {json.dumps({'error': 'Orientation generation failed'})}\n\n"
                return

            await asyncio.sleep(poll_interval)
            elapsed_seconds += poll_interval

        # Timeout
        yield f"event: timeout\ndata: {json.dumps({'error': 'Orientation generation timed out'})}\n\n"

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
