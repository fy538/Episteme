"""
Celery tasks for the case extraction pipeline.

The main task `run_case_extraction_pipeline` orchestrates:
1. Chunk retrieval (find relevant document chunks)
2. Case-level extraction (LLM extracts decision-focused nodes)
3. Graph integration (cross-document relationship discovery)
4. Case analysis (blind spots, assumptions, tensions, readiness)

Follows the same patterns as `process_document_to_graph` in
apps.graph.tasks — status progression, error handling, event emission.
"""
import logging

from celery import shared_task
from django.utils import timezone

from apps.events.models import EventType, ActorType
from apps.events.services import EventService

logger = logging.getLogger(__name__)


@shared_task
def run_case_extraction_pipeline(case_id: str, incremental: bool = False) -> dict:
    """
    Full case extraction pipeline. Runs async after case creation.

    Workflow:
    1. Set extraction_status = 'retrieving'
    2. CaseChunkRetriever.retrieve_relevant_chunks()
    3. Set extraction_status = 'extracting'
    4. CaseExtractionService.extract_case_graph() or incremental_extract()
    5. Set extraction_status = 'integrating'
    6. integrate_new_nodes() (Phase B cross-document edges)
    7. Set extraction_status = 'analyzing'
    8. CaseAnalysisService.analyze_case()
    9. Set extraction_status = 'complete'
    10. Emit CASE_EXTRACTION_COMPLETED event

    Error handling: set extraction_status = 'failed', store error.
    Stale detection: the status API endpoint detects extractions stuck for
    >15 minutes and auto-marks them as failed (covers OOM/SIGKILL cases).

    Args:
        case_id: UUID string of the Case to process
        incremental: If True, extract only from new chunks not already
            covered by existing case nodes

    Returns:
        Dict with status, node/edge counts, analysis summary
    """
    from apps.cases.models import Case

    case = None

    try:
        case = Case.objects.select_related('project', 'user').get(id=case_id)

        # ── Step 1: Mark as retrieving ─────────────────────────
        _update_extraction_status(case, 'retrieving')

        EventService.append(
            event_type=EventType.CASE_EXTRACTION_STARTED,
            payload={
                'case_id': case_id,
                'decision_question': case.decision_question[:200] if case.decision_question else '',
            },
            actor_type=ActorType.SYSTEM,
            case_id=case.id,
        )

        # ── Step 2: Retrieve relevant chunks ───────────────────
        from apps.cases.chunk_retrieval import CaseChunkRetriever
        from django.conf import settings

        extraction_settings = getattr(settings, 'CASE_EXTRACTION_SETTINGS', {})
        max_chunks = extraction_settings.get('max_chunks', 50)
        similarity_threshold = extraction_settings.get('similarity_threshold', 0.45)

        retriever = CaseChunkRetriever()
        chunks = retriever.retrieve_relevant_chunks(
            case,
            max_chunks=max_chunks,
            similarity_threshold=similarity_threshold,
        )

        _update_extraction_metadata(case, {'chunks_retrieved': len(chunks)})

        if not chunks:
            logger.info("No relevant chunks found for case %s", case_id)
            _update_extraction_status(case, 'complete')
            _update_extraction_metadata(case, {
                'extraction_result': {
                    'node_count': 0,
                    'edge_count': 0,
                    'chunk_count': 0,
                },
            })
            return {
                'status': 'completed',
                'case_id': case_id,
                'nodes_created': 0,
                'edges_created': 0,
                'chunks_retrieved': 0,
            }

        # ── Step 3: Extract case graph ─────────────────────────
        _update_extraction_status(case, 'extracting')

        from apps.cases.extraction_service import CaseExtractionService
        from apps.graph.models import Node

        extractor = CaseExtractionService()

        if incremental:
            # Incremental: get existing case nodes and extract only from new chunks
            existing_nodes = list(
                Node.objects.filter(case=case).prefetch_related('source_chunks')
            )
            existing_chunk_ids = set()
            for node in existing_nodes:
                existing_chunk_ids.update(
                    sc.id for sc in node.source_chunks.all()
                )
            new_chunks = [c for c in chunks if c.id not in existing_chunk_ids]

            if not new_chunks:
                logger.info("No new chunks for incremental extraction on case %s", case_id)
                # Still run analysis on existing graph
                from apps.cases.extraction_service import CaseExtractionResult
                extraction_result = CaseExtractionResult(chunk_count=len(chunks))
            else:
                extraction_result = extractor.incremental_extract(
                    case, new_chunks, existing_nodes
                )
        else:
            extraction_result = extractor.extract_case_graph(case, chunks)

        node_ids = [str(n.id) for n in extraction_result.nodes]

        logger.info(
            "case_extraction_phase_a_complete",
            extra={
                'case_id': case_id,
                'nodes_created': extraction_result.node_count,
                'edges_created': extraction_result.edge_count,
            },
        )

        # ── Step 4: Integration (cross-document edges) ─────────
        if node_ids:
            _update_extraction_status(case, 'integrating')

            from apps.graph.integration import integrate_new_nodes

            integration_result = integrate_new_nodes(
                project_id=str(case.project_id),
                new_node_ids=node_ids,
                case_id=case_id,
            )

            integration_edges = integration_result.get('edges', [])
            integration_tensions = integration_result.get('tensions', [])

            logger.info(
                "case_extraction_phase_b_complete",
                extra={
                    'case_id': case_id,
                    'integration_edges': len(integration_edges),
                    'integration_tensions': len(integration_tensions),
                },
            )

        # ── Step 5: Analysis ───────────────────────────────────
        _update_extraction_status(case, 'analyzing')

        from apps.cases.analysis_service import CaseAnalysisService

        analyzer = CaseAnalysisService()
        analysis = analyzer.analyze_case(case)

        # Store analysis results in case metadata
        case.refresh_from_db()
        metadata = case.metadata or {}
        metadata['extraction_result'] = {
            'node_count': extraction_result.node_count,
            'edge_count': extraction_result.edge_count,
            'chunk_count': extraction_result.chunk_count,
        }
        metadata['analysis'] = analysis.to_dict()
        metadata['extraction_completed_at'] = timezone.now().isoformat()
        case.metadata = metadata
        case.save(update_fields=['metadata', 'updated_at'])

        # ── Step 6: Mark as complete ───────────────────────────
        _update_extraction_status(case, 'complete')

        # ── Step 7: Emit completion event ──────────────────────
        EventService.append(
            event_type=EventType.CASE_EXTRACTION_COMPLETED,
            payload={
                'case_id': case_id,
                'nodes_created': extraction_result.node_count,
                'edges_created': extraction_result.edge_count,
                'chunks_used': extraction_result.chunk_count,
                'analysis_summary': analysis.readiness.to_dict() if analysis.readiness else {},
                'delta_id': str(extraction_result.delta.id) if extraction_result.delta else None,
            },
            actor_type=ActorType.SYSTEM,
            case_id=case.id,
        )

        EventService.append(
            event_type=EventType.CASE_ANALYSIS_COMPLETED,
            payload={
                'case_id': case_id,
                'blind_spots': len(analysis.blind_spots),
                'assumptions': len(analysis.assumption_assessment),
                'tensions': len(analysis.key_tensions),
                'readiness': analysis.readiness.ready if analysis.readiness else False,
            },
            actor_type=ActorType.SYSTEM,
            case_id=case.id,
        )

        return {
            'status': 'completed',
            'case_id': case_id,
            'nodes_created': extraction_result.node_count,
            'edges_created': extraction_result.edge_count,
            'chunks_retrieved': len(chunks),
            'delta_id': str(extraction_result.delta.id) if extraction_result.delta else None,
        }

    except Exception as e:
        logger.exception(
            "case_extraction_pipeline_failed",
            extra={'case_id': case_id},
        )

        if case:
            try:
                _update_extraction_status(case, 'failed')
                case.refresh_from_db()
                metadata = case.metadata or {}
                metadata['extraction_error'] = str(e)[:2000]
                case.metadata = metadata
                case.save(update_fields=['metadata'])
            except Exception:
                logger.exception("Failed to update case extraction status on failure")

            try:
                EventService.append(
                    event_type=EventType.CASE_EXTRACTION_FAILED,
                    payload={
                        'case_id': case_id,
                        'error': str(e)[:500],
                    },
                    actor_type=ActorType.SYSTEM,
                    case_id=case.id,
                )
            except Exception:
                logger.warning("Failed to emit extraction failure event", exc_info=True)

        return {
            'status': 'failed',
            'case_id': case_id,
            'error': str(e)[:500],
        }


def _update_extraction_status(case, status: str):
    """Update case.metadata['extraction_status'] atomically."""
    case.refresh_from_db()
    metadata = case.metadata or {}
    metadata['extraction_status'] = status
    if status == 'retrieving' and 'extraction_started_at' not in metadata:
        metadata['extraction_started_at'] = timezone.now().isoformat()
    case.metadata = metadata
    case.save(update_fields=['metadata', 'updated_at'])


def _update_extraction_metadata(case, updates: dict):
    """Merge updates into case.metadata."""
    case.refresh_from_db()
    metadata = case.metadata or {}
    metadata.update(updates)
    case.metadata = metadata
    case.save(update_fields=['metadata', 'updated_at'])
