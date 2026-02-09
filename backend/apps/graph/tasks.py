"""
Celery tasks for graph extraction pipeline.

The main task `process_document_to_graph` runs after the existing
document processing pipeline completes. It orchestrates Phase A
(node extraction) and Phase B (graph integration) sequentially.
"""
import logging

from celery import shared_task

from apps.events.models import EventType, ActorType
from apps.events.services import EventService

logger = logging.getLogger(__name__)


@shared_task
def process_document_to_graph(document_id: str, project_id: str):
    """
    Full graph extraction pipeline for a document.

    Workflow:
    1. Set extraction_status = 'extracting'
    2. Phase A: extract_nodes_from_document()
    3. Set extraction_status = 'integrating'
    4. Phase B: integrate_new_nodes()
    5. Create GraphDelta with narrative
    6. Set extraction_status = 'completed'
    7. Emit GRAPH_EXTRACTION_COMPLETED event

    Error handling: set extraction_status = 'failed', store error.

    Args:
        document_id: UUID string of the Document to process
        project_id: UUID string of the Project

    Returns:
        Dict with status, node IDs, edge IDs
    """
    from apps.projects.models import Document

    document = None

    try:
        document = Document.objects.get(id=document_id)

        # ── Step 1: Mark as extracting ──────────────────────────
        document.extraction_status = 'extracting'
        document.extraction_error = ''
        document.save(update_fields=['extraction_status', 'extraction_error'])

        # Emit start event
        EventService.append(
            event_type=EventType.GRAPH_EXTRACTION_STARTED,
            payload={
                'document_id': document_id,
                'project_id': project_id,
                'document_title': document.title,
            },
            actor_type=ActorType.SYSTEM,
        )

        # ── Step 2: Phase A — Extract nodes ─────────────────────
        from .extraction import extract_nodes_from_document

        new_node_ids = extract_nodes_from_document(
            document_id=document_id,
            project_id=project_id,
        )

        logger.info(
            "graph_phase_a_complete",
            extra={
                'document_id': document_id,
                'nodes_created': len(new_node_ids),
            },
        )

        # ── Step 3: Mark as integrating ─────────────────────────
        document.extraction_status = 'integrating'
        document.save(update_fields=['extraction_status'])

        # Derive case scope for integration boundary
        case_id = (
            str(document.case_id)
            if document.scope == 'case' and document.case_id
            else None
        )

        # ── Step 4: Phase B — Integrate with graph ──────────────
        from .integration import integrate_new_nodes

        integration_result = integrate_new_nodes(
            project_id=project_id,
            new_node_ids=new_node_ids,
            source_document=document,
            case_id=case_id,
        )

        edges_created = integration_result.get('edges', [])
        tensions_created = integration_result.get('tensions', [])
        updated_nodes = integration_result.get('updated_nodes', [])

        logger.info(
            "graph_phase_b_complete",
            extra={
                'document_id': document_id,
                'edges_created': len(edges_created),
                'tensions_created': len(tensions_created),
                'nodes_updated': len(updated_nodes),
            },
        )

        # ── Step 5: Create GraphDelta ───────────────────────────
        from .models import Node, Edge
        from .delta_service import GraphDeltaService

        nodes_added = list(Node.objects.filter(id__in=new_node_ids))
        edges_added = list(Edge.objects.filter(id__in=edges_created))
        nodes_updated = list(Node.objects.filter(id__in=updated_nodes))

        delta = GraphDeltaService.create_delta(
            project_id=project_id,
            trigger='document_upload',
            source_document=document,
            nodes_added=nodes_added,
            nodes_updated=nodes_updated,
            edges_added=edges_added,
            tensions_surfaced=len(tensions_created),
            assumptions_challenged=sum(
                1 for n in nodes_updated
                if n.node_type == 'assumption' and n.status in ('challenged', 'refuted')
            ),
        )

        # ── Step 6: Mark as completed ───────────────────────────
        document.extraction_status = 'completed'
        document.save(update_fields=['extraction_status'])

        # ── Step 7: Emit completion event ───────────────────────
        EventService.append(
            event_type=EventType.GRAPH_EXTRACTION_COMPLETED,
            payload={
                'document_id': document_id,
                'project_id': project_id,
                'document_title': document.title,
                'delta_id': str(delta.id),
                'nodes_created': len(new_node_ids),
                'edges_created': len(edges_created),
                'tensions_surfaced': len(tensions_created),
                'narrative': delta.narrative[:200],
            },
            actor_type=ActorType.SYSTEM,
        )

        return {
            'status': 'completed',
            'document_id': document_id,
            'nodes_created': len(new_node_ids),
            'edges_created': len(edges_created),
            'tensions_surfaced': len(tensions_created),
            'delta_id': str(delta.id),
        }

    except Exception as e:
        logger.exception(
            "graph_extraction_failed",
            extra={
                'document_id': document_id,
                'project_id': project_id,
            },
        )

        # Update document status
        if document:
            try:
                document.extraction_status = 'failed'
                document.extraction_error = str(e)[:2000]
                document.save(update_fields=['extraction_status', 'extraction_error'])
            except Exception:
                logger.exception("Failed to update extraction_status on failure")

        return {
            'status': 'failed',
            'document_id': document_id,
            'error': str(e)[:500],
        }


# ═══════════════════════════════════════════════════════════════════
# Project Summary Tasks
# ═══════════════════════════════════════════════════════════════════

@shared_task
def generate_project_summary(project_id: str, force: bool = False):
    """
    Generate or regenerate a project summary.

    Called on-demand via the API regenerate endpoint.
    Runs the async generate_summary in a sync context.

    Args:
        project_id: UUID string
        force: Skip staleness check
    """
    import asyncio
    from .summary_service import ProjectSummaryService

    try:
        summary = asyncio.run(
            ProjectSummaryService.generate_summary(
                project_id=project_id,
                force=force,
            )
        )

        logger.info(
            "project_summary_task_complete",
            extra={
                'project_id': project_id,
                'status': summary.status,
                'version': summary.version,
            },
        )

        return {
            'status': summary.status,
            'project_id': project_id,
            'version': summary.version,
        }

    except Exception as e:
        logger.exception(
            "project_summary_task_failed",
            extra={'project_id': project_id},
        )
        return {
            'status': 'failed',
            'project_id': project_id,
            'error': str(e)[:500],
        }


@shared_task
def regenerate_stale_summaries():
    """
    Daily task: find all projects with stale summaries and regenerate.
    Processes at most 20 projects per run to avoid overloading.
    """
    import asyncio
    from .models import ProjectSummary, SummaryStatus

    stale_project_ids = list(
        ProjectSummary.objects
        .filter(is_stale=True)
        .exclude(status__in=[SummaryStatus.GENERATING, SummaryStatus.FAILED])
        .values_list('project_id', flat=True)
        .distinct()[:20]
    )

    logger.info(
        "regenerate_stale_summaries_start",
        extra={'count': len(stale_project_ids)},
    )

    for pid in stale_project_ids:
        try:
            generate_project_summary.delay(str(pid), force=True)
        except Exception:
            logger.warning(
                "Failed to dispatch summary regeneration",
                extra={'project_id': str(pid)},
                exc_info=True,
            )
