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
def generate_thematic_summary_task(project_id: str, document_ids: list = None):
    """
    Generate a thematic summary from chunk clustering.

    Called right after embedding completion in process_document_workflow.
    Fast (~3s total: ~100ms clustering + ~2-3s LLM).

    This is fire-and-forget — failure here must never block graph extraction.

    Args:
        project_id: UUID string
        document_ids: Optional list of UUID strings to cluster.
                      If None, clusters all project chunks.
    """
    import uuid as _uuid
    from asgiref.sync import async_to_sync
    from .summary_service import ProjectSummaryService

    try:
        doc_uuids = (
            [_uuid.UUID(d) for d in document_ids]
            if document_ids
            else None
        )
        summary = async_to_sync(
            ProjectSummaryService.generate_thematic_summary
        )(
            project_id=_uuid.UUID(project_id),
            document_ids=doc_uuids,
        )

        if summary:
            logger.info(
                "thematic_summary_task_complete",
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

        return {
            'status': 'skipped',
            'project_id': project_id,
            'reason': 'lock_held',
        }

    except Exception as e:
        logger.exception(
            "thematic_summary_task_failed",
            extra={'project_id': project_id},
        )
        return {
            'status': 'failed',
            'project_id': project_id,
            'error': str(e)[:500],
        }


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
    from asgiref.sync import async_to_sync
    from .summary_service import ProjectSummaryService

    try:
        summary = async_to_sync(
            ProjectSummaryService.generate_summary
        )(
            project_id=project_id,
            force=force,
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
def cleanup_stuck_generating_summaries():
    """
    Periodic cleanup: fail summaries stuck in GENERATING for >5 minutes.

    This handles the case where a Celery worker crashes mid-generation,
    leaving a ProjectSummary row permanently in GENERATING status.
    Without this, should_generate() returns 'already_generating' and
    no new summary is ever created.

    Should be scheduled every ~10 minutes via Celery Beat.
    """
    from datetime import timedelta
    from django.conf import settings
    from django.utils import timezone
    from .models import ProjectSummary, SummaryStatus

    cleanup_minutes = getattr(settings, 'SUMMARY_SETTINGS', {}).get(
        'cleanup_threshold_minutes', 5,
    )
    threshold = timezone.now() - timedelta(minutes=cleanup_minutes)

    stuck = ProjectSummary.objects.filter(
        status=SummaryStatus.GENERATING,
        created_at__lt=threshold,
    )
    count = stuck.count()

    if count > 0:
        stuck.update(
            status=SummaryStatus.FAILED,
            generation_metadata={
                'error': 'Timed out: stuck in GENERATING for >5 minutes',
                'cleanup': True,
            },
        )
        logger.warning(
            "cleanup_stuck_generating_summaries",
            extra={'failed_count': count},
        )
    else:
        logger.debug("cleanup_stuck_generating_summaries: none found")

    return {'cleaned_up': count}


@shared_task
def regenerate_stale_summaries():
    """
    Daily task: find all projects with stale summaries and regenerate.
    Processes at most 20 projects per run to avoid overloading.
    """
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


# ═══════════════════════════════════════════════════════════════════
# Hierarchical Clustering Tasks
# ═══════════════════════════════════════════════════════════════════

@shared_task
def build_cluster_hierarchy_task(project_id: str):
    """
    Build hierarchical cluster tree for a project.

    Runs asynchronously after document chunking + embedding completes.
    Creates a ClusterHierarchy record with a multi-level tree.

    After hierarchy is built, dispatches insight discovery.

    Args:
        project_id: UUID string of the Project.
    """
    import uuid as _uuid
    from django.core.cache import cache
    from asgiref.sync import async_to_sync
    from .models import ClusterHierarchy, HierarchyStatus
    from .hierarchical_clustering import HierarchicalClusteringService

    lock_key = f'hierarchy_build:{project_id}'

    # Concurrency guard: skip if another build is already running
    if not cache.add(lock_key, '1', timeout=300):  # 5-min lock
        logger.info(
            "hierarchy_build_skipped_lock",
            extra={'project_id': project_id},
        )
        return {'status': 'skipped', 'reason': 'lock_held'}

    hierarchy = None
    try:
        pid = _uuid.UUID(project_id)

        # Snapshot the current chunk count before building.
        # After the build finishes, if the count has grown (rapid uploads),
        # we automatically dispatch a follow-up build so the landscape
        # includes all documents.
        from apps.projects.models import DocumentChunk
        chunk_count_before = DocumentChunk.objects.filter(
            document__project_id=pid,
        ).count()

        # Determine next version
        latest = (
            ClusterHierarchy.objects
            .filter(project_id=pid)
            .order_by('-version')
            .values_list('version', flat=True)
            .first()
        )
        next_version = (latest or 0) + 1

        # Create building record
        hierarchy = ClusterHierarchy.objects.create(
            project_id=pid,
            version=next_version,
            status=HierarchyStatus.BUILDING,
            tree={},
            is_current=False,
        )

        # Build hierarchy
        service = HierarchicalClusteringService()
        result = async_to_sync(service.build_hierarchy)(pid)

        # Atomically swap is_current: unset old, then set new
        from django.db import transaction
        with transaction.atomic():
            ClusterHierarchy.objects.filter(
                project_id=pid,
                is_current=True,
            ).select_for_update().update(is_current=False)

            hierarchy.tree = result['tree']
            hierarchy.metadata = result['metadata']
            hierarchy.status = HierarchyStatus.READY
            hierarchy.is_current = True
            hierarchy.save(update_fields=['tree', 'metadata', 'status', 'is_current'])

        logger.info(
            "hierarchy_build_complete",
            extra={
                'project_id': project_id,
                'version': next_version,
                'duration_ms': result['metadata'].get('duration_ms'),
                'total_clusters': result['metadata'].get('total_clusters'),
            },
        )

        # ── Compute diff against previous version (Plan 6) ──────
        diff_dict = None
        try:
            from .hierarchy_diff import compute_hierarchy_diff

            previous = (
                ClusterHierarchy.objects
                .filter(project_id=pid, is_current=False)
                .exclude(id=hierarchy.id)
                .order_by('-version')
                .first()
            )

            diff = compute_hierarchy_diff(previous, hierarchy)

            if diff.has_changes:
                hierarchy.metadata['diff'] = diff.to_dict()
                hierarchy.metadata['diff_summary'] = diff.summary_text()
                hierarchy.save(update_fields=['metadata'])
                diff_dict = diff.to_dict()

                logger.info(
                    "hierarchy_diff_computed",
                    extra={
                        'project_id': project_id,
                        'version': next_version,
                        'new_themes': len(diff.new_themes),
                        'merged_themes': len(diff.merged_themes),
                        'expanded_themes': len(diff.expanded_themes),
                        'new_documents': len(diff.new_documents),
                    },
                )
        except Exception:
            logger.warning(
                "hierarchy_diff_failed",
                extra={'project_id': project_id},
                exc_info=True,
            )

        # Dispatch insight discovery (with diff context for targeted analysis)
        try:
            run_insight_discovery_task.delay(
                project_id=project_id,
                hierarchy_diff=diff_dict,
            )
        except Exception:
            logger.warning(
                "insight_discovery_dispatch_failed",
                extra={'project_id': project_id},
                exc_info=True,
            )

        # Dispatch orientation generation (parallel with insight discovery)
        try:
            generate_orientation_task.delay(
                project_id=project_id,
                hierarchy_id=str(hierarchy.id),
            )
        except Exception:
            logger.warning(
                "orientation_dispatch_failed",
                extra={'project_id': project_id},
                exc_info=True,
            )

        # ── Staleness check: did new chunks arrive during the build? ──
        # If a user uploaded more documents while this build was running,
        # those chunks were skipped because the lock blocked their builds.
        # Re-dispatch a follow-up build so the landscape stays current.
        chunk_count_after = DocumentChunk.objects.filter(
            document__project_id=pid,
        ).count()
        if chunk_count_after > chunk_count_before:
            logger.info(
                "hierarchy_stale_after_build",
                extra={
                    'project_id': project_id,
                    'chunks_before': chunk_count_before,
                    'chunks_after': chunk_count_after,
                },
            )
            # Small delay to let the lock release, then rebuild
            build_cluster_hierarchy_task.apply_async(
                kwargs={'project_id': project_id},
                countdown=5,
            )

        return {
            'status': 'completed',
            'project_id': project_id,
            'version': next_version,
        }

    except Exception as e:
        logger.exception(
            "hierarchy_build_failed",
            extra={'project_id': project_id},
        )

        if hierarchy:
            try:
                hierarchy.status = HierarchyStatus.FAILED
                hierarchy.metadata = {'error': str(e)[:2000]}
                hierarchy.save(update_fields=['status', 'metadata'])
            except Exception:
                logger.exception("Failed to update hierarchy status on failure")

        return {
            'status': 'failed',
            'project_id': project_id,
            'error': str(e)[:500],
        }

    finally:
        cache.delete(lock_key)


@shared_task
def run_insight_discovery_task(project_id: str, hierarchy_diff: dict = None):
    """
    Discover insights from project hierarchy.

    Runs after hierarchy build completes. Detects cross-cluster tensions,
    coverage gaps, and other observations.

    When hierarchy_diff is provided (Plan 6), the agent scopes tension
    detection to only pairs involving changed themes and generates
    theme emergence/merge insights.

    Args:
        project_id: UUID string of the Project.
        hierarchy_diff: Optional dict from HierarchyDiff.to_dict() with
            change information from the previous hierarchy version.
    """
    import uuid as _uuid
    from asgiref.sync import async_to_sync
    from .insight_agent import InsightDiscoveryAgent

    try:
        # Reconstruct HierarchyDiff from serialized dict if provided
        diff = None
        if hierarchy_diff:
            from .hierarchy_diff import HierarchyDiff
            diff = HierarchyDiff(**hierarchy_diff)

        agent = InsightDiscoveryAgent()
        insights = async_to_sync(agent.run)(
            _uuid.UUID(project_id),
            hierarchy_diff=diff,
        )

        logger.info(
            "insight_discovery_complete",
            extra={
                'project_id': project_id,
                'insights_created': len(insights),
                'diff_aware': diff is not None,
            },
        )

        return {
            'status': 'completed',
            'project_id': project_id,
            'insights_created': len(insights),
        }

    except Exception as e:
        logger.exception(
            "insight_discovery_failed",
            extra={'project_id': project_id},
        )
        return {
            'status': 'failed',
            'project_id': project_id,
            'error': str(e)[:500],
        }


# ═══════════════════════════════════════════════════════════════════
# Orientation Tasks
# ═══════════════════════════════════════════════════════════════════

@shared_task
def generate_orientation_task(project_id: str, hierarchy_id: str):
    """
    Generate lens-based orientation for a project.

    Runs after hierarchy build completes, in parallel with insight discovery.
    Performs lens detection (1 LLM call) + orientation synthesis (1 LLM call),
    creates ProjectOrientation and ProjectInsight records.

    Args:
        project_id: UUID string of the Project.
        hierarchy_id: UUID string of the ClusterHierarchy to orient from.
    """
    import uuid as _uuid
    from asgiref.sync import async_to_sync
    from .orientation_service import OrientationService

    try:
        orientation = async_to_sync(OrientationService.generate_orientation)(
            project_id=_uuid.UUID(project_id),
            hierarchy_id=_uuid.UUID(hierarchy_id),
        )

        logger.info(
            "orientation_task_complete",
            extra={
                'project_id': project_id,
                'orientation_id': str(orientation.id),
                'lens_type': orientation.lens_type,
            },
        )

        return {
            'status': 'completed',
            'project_id': project_id,
            'orientation_id': str(orientation.id),
            'lens_type': orientation.lens_type,
        }

    except Exception as e:
        logger.exception(
            "orientation_task_failed",
            extra={'project_id': project_id},
        )
        return {
            'status': 'failed',
            'project_id': project_id,
            'error': str(e)[:500],
        }


@shared_task
def research_insight_gap_task(project_id: str, insight_id: str):
    """
    Background research for a gap-type insight.

    Triggered when a user clicks "Research this" on a gap finding.
    Performs semantic search against project chunks, synthesises an answer,
    and stores the result in insight.research_result.

    Args:
        project_id: UUID string of the Project.
        insight_id: UUID string of the ProjectInsight to research.
    """
    import uuid as _uuid
    from asgiref.sync import async_to_sync
    from .models import ProjectInsight, InsightStatus

    try:
        insight = ProjectInsight.objects.get(id=insight_id)

        # Mark as researching
        insight.status = InsightStatus.RESEARCHING
        insight.save(update_fields=['status', 'updated_at'])

        # Build research query from insight context
        research_query = f"{insight.title}. {insight.content}"

        # Perform research using project chunks
        result = async_to_sync(_do_insight_research)(
            project_id=_uuid.UUID(project_id),
            query=research_query,
            source_cluster_ids=insight.source_cluster_ids,
        )

        # Store result and restore status
        from django.utils import timezone
        insight.research_result = {
            'answer': result.get('answer', ''),
            'sources': result.get('sources', []),
            'researched_at': timezone.now().isoformat(),
        }
        insight.status = InsightStatus.ACTIVE
        insight.save(update_fields=['research_result', 'status', 'updated_at'])

        logger.info(
            "insight_research_complete",
            extra={
                'project_id': project_id,
                'insight_id': insight_id,
                'sources_found': len(result.get('sources', [])),
            },
        )

        return {
            'status': 'completed',
            'project_id': project_id,
            'insight_id': insight_id,
        }

    except Exception as e:
        logger.exception(
            "insight_research_failed",
            extra={
                'project_id': project_id,
                'insight_id': insight_id,
            },
        )

        # Restore status on failure
        try:
            insight = ProjectInsight.objects.get(id=insight_id)
            insight.status = InsightStatus.ACTIVE
            insight.save(update_fields=['status', 'updated_at'])
        except Exception as e:
            logger.debug("Failed to restore insight status after failure: %s", e)

        return {
            'status': 'failed',
            'project_id': project_id,
            'insight_id': insight_id,
            'error': str(e)[:500],
        }


async def _do_insight_research(
    project_id,
    query: str,
    source_cluster_ids: list,
) -> dict:
    """
    Lightweight research: semantic search + LLM synthesis.

    Reuses the existing retrieve_document_context() for chunk retrieval
    and synthesises an answer via the fast LLM provider.

    Returns:
        {answer: str, sources: [{title, snippet, document_id}]}
    """
    from asgiref.sync import sync_to_async
    from apps.common.llm_providers.factory import get_llm_provider
    from apps.chat.retrieval import retrieve_document_context

    # Retrieve relevant chunks using existing retrieval infrastructure
    retrieval_result = await sync_to_async(retrieve_document_context)(
        query=query,
        project_id=project_id,
        top_k=8,
        threshold=0.4,
    )

    if not retrieval_result.has_sources:
        return {
            'answer': 'No relevant passages found in your documents to address this gap.',
            'sources': [],
        }

    # Build sources list from retrieval chunks
    sources = []
    seen_docs = set()
    for chunk in retrieval_result.chunks:
        if chunk.document_id not in seen_docs:
            seen_docs.add(chunk.document_id)
            sources.append({
                'title': chunk.document_title,
                'snippet': chunk.excerpt,
                'document_id': chunk.document_id,
            })

    # LLM synthesis using retrieved context
    provider = get_llm_provider('fast')
    system_prompt = (
        "You are a research assistant. Based on the provided document excerpts, "
        "answer the research question in 3-5 concise sentences. Ground your answer "
        "in the source material. If the documents don't fully address the question, "
        "say so clearly."
    )
    user_prompt = (
        f"Research question: {query}\n\n"
        f"Document excerpts:\n{retrieval_result.context_text}\n\n"
        f"Provide a concise research answer grounded in these excerpts."
    )

    answer = await provider.generate(
        messages=[{"role": "user", "content": user_prompt}],
        system_prompt=system_prompt,
        max_tokens=400,
        temperature=0.2,
    )

    return {
        'answer': answer.strip(),
        'sources': sources,
    }
