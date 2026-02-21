"""
Orchestration workflows for Episteme

These are higher-level workflows that coordinate multiple tasks/services.
"""
import logging
from asgiref.sync import async_to_sync
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

@shared_task
def assistant_response_workflow(thread_id: str, user_message_id: str):
    """
    Enhanced workflow with agent inflection detection.

    Workflow:
    1. Check for agent confirmation (if pending suggestion)
    2. Analyze for agent inflection points (every N turns)
    3. Generate assistant response OR spawn agent

    Args:
        thread_id: Chat thread ID
        user_message_id: User message that triggered this workflow
    """
    from apps.chat.models import Message, ChatThread
    from apps.chat.services import ChatService
    
    # Get thread and message
    thread = ChatThread.objects.get(id=thread_id)
    user_message = Message.objects.get(id=user_message_id)
    
    # STEP 1: Check for agent confirmation
    # If there's a pending agent suggestion, check if user is confirming
    if thread.metadata and thread.metadata.get('pending_agent_suggestion'):
        from apps.agents.confirmation import check_for_agent_confirmation
        from apps.agents.orchestrator import AgentOrchestrator
        
        confirmation = async_to_sync(check_for_agent_confirmation)(thread, user_message)
        
        if confirmation and confirmation['confirmed']:
            # User confirmed! Spawn agent
            result = async_to_sync(AgentOrchestrator.run_agent_in_chat)(
                thread=thread,
                agent_type=confirmation['agent_type'],
                user=thread.user,
                **confirmation['params']
            )
            
            # Clear pending suggestion
            thread.metadata['pending_agent_suggestion'] = None
            thread.save()
            
            # Agent is running - workflow complete
            return {
                'status': 'agent_spawned',
                'agent_type': confirmation['agent_type'],
                **result
            }
    
    # STEP 2: Analyze for agent inflection points
    # Increment counter and check threshold
    thread.turns_since_agent_check = (thread.turns_since_agent_check or 0) + 1
    
    AGENT_CHECK_INTERVAL = 3  # Check every 3 turns
    
    should_check_agents = (
        thread.turns_since_agent_check >= AGENT_CHECK_INTERVAL or
        thread.last_agent_check_at is None
    )
    
    if should_check_agents:
        from apps.agents.inflection_detector import InflectionDetector
        from apps.agents.messages import create_agent_suggestion_message
        
        # Analyze for inflection points
        inflection = async_to_sync(InflectionDetector.analyze_for_agent_need)(thread)
        
        # Emit event for tracking
        from apps.events.services import EventService
        from apps.events.models import ActorType, EventType

        EventService.append(
            event_type=EventType.CONVERSATION_ANALYZED_FOR_AGENT,
            payload=inflection,
            actor_type=ActorType.SYSTEM,
            thread_id=thread.id,
            case_id=thread.primary_case.id if thread.primary_case else None
        )
        
        # Reset counter
        thread.turns_since_agent_check = 0
        thread.last_agent_check_at = timezone.now()
        thread.last_suggested_agent = inflection.get('suggested_agent', '')
        
        # If high confidence, create suggestion
        if inflection['needs_agent'] and inflection['confidence'] > 0.75:
            # Store pending suggestion
            thread.metadata = thread.metadata or {}
            thread.metadata['pending_agent_suggestion'] = inflection
            
            # Create suggestion message
            async_to_sync(create_agent_suggestion_message)(thread, inflection)
            
            thread.save()
            
            # Don't generate normal response - let user decide
            return {
                'status': 'agent_suggested',
                'agent_type': inflection['suggested_agent'],
                'confidence': inflection['confidence']
            }
        
        thread.save()
    
    # STEP 3: Generate normal assistant response (Phase 1: with memory integration)
    response = ChatService.generate_assistant_response(
        thread_id=thread.id,
        user_message_id=user_message.id
    )
    
    # Title generation now happens inline in the SSE stream (unified_stream view)

    return {
        'status': 'completed',
        'message_id': str(response.id),
    }


def _update_document_progress(doc, stage, stage_label, stage_index, counts=None,
                               *, total_stages=5):
    """Write progress to document for SSE streaming.

    Deduplicates writes when stage hasn't changed (prevents hot-loop DB
    writes if a callback fires repeatedly within the same stage).
    Uses the document's own persisted progress state (not module globals)
    so Celery worker processes cannot leak cross-task progress state.
    """
    existing_progress = doc.processing_progress or {}
    same_stage = (
        existing_progress.get('stage') == stage
        and existing_progress.get('stage_index') == stage_index
    )

    if same_stage and counts is None:
        return

    started = existing_progress.get('started_at', timezone.now().isoformat())
    doc.processing_progress = {
        'stage': stage,
        'stage_label': stage_label,
        'stage_index': stage_index,
        'total_stages': total_stages,
        'counts': counts or existing_progress.get('counts', {}),
        'started_at': started,
        'updated_at': timezone.now().isoformat(),
        'error': None,
    }
    doc.save(update_fields=['processing_progress'])


@shared_task
def process_document_workflow(document_id: str):
    """
    Document processing pipeline.

    Stages (user-facing, fast — ~10-20s):
    0. received — Document received
    1. chunking — Chunk document
    2. embedding — Generate embeddings
    3. completed — Processing complete

    Background tasks dispatched after embedding:
    - Thematic summary generation (fast first-pass, ~3s)
    - Hierarchical clustering + insight discovery (~10-30s)

    Progress is written to document.processing_progress (JSONField)
    and streamed to the frontend via SSE.
    """
    from apps.projects.models import Document
    from apps.projects.services import DocumentService
    from apps.events.services import EventService
    from apps.events.models import EventType, ActorType

    # Phase 1 uses 4 stages (0-3): received → chunking → embedding → completed
    # (Graph extraction removed — replaced by hierarchical clustering)
    def _update_progress(doc, stage, stage_label, stage_index, counts=None):
        _update_document_progress(
            doc, stage, stage_label, stage_index, counts,
            total_stages=4,
        )

    try:
        document = Document.objects.get(id=document_id)

        # Stage 0: Received
        _update_progress(document, 'received', 'Document received', 0)

        # Stages 1-2: Chunk and embed
        def on_doc_progress(stage, label, stage_index, counts=None):
            _update_progress(document, stage, label, stage_index, counts)

        DocumentService.process_document(document, on_progress=on_doc_progress)

        # ── Thematic summary (non-blocking, parallel) ─────────
        # Dispatch thematic summary generation as a fast first-pass (~3s).
        # Runs as a separate Celery task so it does NOT block the main pipeline.
        #
        # Skip if the project already has a full/generating summary — no point
        # in re-creating a thematic when a better one exists.
        try:
            from apps.graph.models import ProjectSummary, SummaryStatus
            current_status = (
                ProjectSummary.objects
                .filter(project_id=document.project_id)
                .exclude(status__in=[SummaryStatus.FAILED])
                .order_by('-created_at')
                .values_list('status', flat=True)
                .first()
            )
            skip_statuses = {
                SummaryStatus.FULL,
                SummaryStatus.GENERATING,
                SummaryStatus.PARTIAL,
            }
            if current_status and current_status in skip_statuses:
                logger.info(
                    "thematic_summary_skipped_existing",
                    extra={
                        'document_id': document_id,
                        'project_id': str(document.project_id),
                        'current_status': current_status,
                    },
                )
            else:
                from apps.graph.tasks import generate_thematic_summary_task
                generate_thematic_summary_task.delay(
                    project_id=str(document.project_id),
                )
                logger.info(
                    "thematic_summary_dispatched",
                    extra={
                        'document_id': document_id,
                        'project_id': str(document.project_id),
                    },
                )
        except Exception:
            # Thematic summary is best-effort; failure must not block pipeline
            logger.warning(
                "thematic_summary_dispatch_failed",
                extra={'document_id': document_id},
                exc_info=True,
            )

        # ── Hierarchical clustering (non-blocking, debounced) ──────
        # Builds the multi-level cluster tree for the project landscape view.
        # Runs in background; does NOT block the main pipeline.
        #
        # Plan 6: Debounce rapid uploads — schedule the hierarchy build
        # with a 30-second countdown so rapid uploads don't trigger N
        # separate builds. The task itself has two safety nets:
        #   1. cache.add lock — prevents concurrent builds (skips if locked)
        #   2. stale check — if chunks grew during the build, re-dispatches
        # So even if multiple delayed tasks fire, only one builds, and
        # it automatically re-triggers if it missed newly-uploaded docs.
        HIERARCHY_REBUILD_DELAY = 30  # seconds
        try:
            from apps.graph.tasks import build_cluster_hierarchy_task

            build_cluster_hierarchy_task.apply_async(
                kwargs={'project_id': str(document.project_id)},
                countdown=HIERARCHY_REBUILD_DELAY,
            )
            logger.info(
                "hierarchy_clustering_scheduled",
                extra={
                    'document_id': document_id,
                    'project_id': str(document.project_id),
                    'delay_seconds': HIERARCHY_REBUILD_DELAY,
                },
            )
        except Exception:
            logger.warning(
                "hierarchy_clustering_dispatch_failed",
                extra={'document_id': document_id},
                exc_info=True,
            )

        # Stage 3: Done — hierarchical clustering runs in background
        # (Graph extraction removed — replaced by cluster hierarchy + insight discovery)
        document.extraction_status = 'completed'
        document.save(update_fields=['extraction_status'])

        _update_progress(
            document, 'completed', 'Processing complete', 3,
            {'chunks': document.chunk_count},
        )

        EventService.append(
            event_type=EventType.WORKFLOW_COMPLETED,
            payload={
                'workflow': 'process_document',
                'document_id': str(document.id),
                'chunks': document.chunk_count,
            },
            actor_type=ActorType.SYSTEM,
            case_id=document.case_id,
        )

        return {
            'status': 'completed',
            'document_id': str(document.id),
            'chunks_created': document.chunk_count,
        }

    except Exception as e:
        logger.exception(
            "process_document_workflow_failed",
            extra={"document_id": str(document_id)},
        )
        try:
            document = Document.objects.get(id=document_id)
            document.processing_status = 'failed'
            document.extraction_status = 'failed'
            document.extraction_error = str(e)[:2000]
            document.processing_progress = {
                **document.processing_progress,
                'stage': 'failed',
                'stage_label': str(e)[:200],
                'error': str(e)[:500],
                'updated_at': timezone.now().isoformat(),
            }
            document.save(update_fields=[
                'processing_status', 'extraction_status', 'extraction_error',
                'processing_progress',
            ])
        except Exception:
            logger.exception(
                "process_document_workflow_status_update_failed",
                extra={"document_id": str(document_id)},
            )
        raise


@shared_task
def integrate_document_workflow(document_id: str, new_node_ids: list):
    """
    Phase 2: Background integration of extracted nodes with existing graph.

    Runs after process_document_workflow completes, without blocking the user.
    Updates document.extraction_status from 'extracted' → 'completed'.
    """
    from apps.projects.models import Document
    from apps.events.services import EventService
    from apps.events.models import EventType, ActorType
    from apps.graph.models import Node, Edge
    from apps.graph.integration import integrate_new_nodes
    from apps.graph.delta_service import GraphDeltaService
    import uuid

    try:
        document = Document.objects.get(id=document_id)

        document.extraction_status = 'integrating'
        document.save(update_fields=['extraction_status'])

        case_id = (
            str(document.case_id)
            if getattr(document, 'scope', 'project') == 'case' and document.case_id
            else None
        )

        node_uuids = [uuid.UUID(nid) for nid in new_node_ids]

        integration_result = integrate_new_nodes(
            project_id=str(document.project_id),
            new_node_ids=node_uuids,
            source_document=document,
            case_id=case_id,
        )

        edges_created = integration_result.get('edges', [])
        tensions_created = integration_result.get('tensions', [])
        updated_nodes = integration_result.get('updated_nodes', [])

        # Create GraphDelta record
        nodes_added = list(Node.objects.filter(id__in=node_uuids))
        edges_added = list(Edge.objects.filter(id__in=edges_created))
        nodes_updated_objs = list(Node.objects.filter(id__in=updated_nodes))

        delta = GraphDeltaService.create_delta(
            project_id=str(document.project_id),
            trigger='document_upload',
            source_document=document,
            nodes_added=nodes_added,
            nodes_updated=nodes_updated_objs,
            edges_added=edges_added,
            tensions_surfaced=len(tensions_created),
            assumptions_challenged=sum(
                1 for n in nodes_updated_objs
                if n.node_type == 'assumption' and n.status in ('challenged', 'refuted')
            ),
        )

        document.extraction_status = 'completed'
        document.save(update_fields=['extraction_status'])

        EventService.append(
            event_type=EventType.GRAPH_EXTRACTION_COMPLETED,
            payload={
                'document_id': str(document.id),
                'project_id': str(document.project_id),
                'document_title': document.title,
                'delta_id': str(delta.id),
                'nodes_created': len(node_uuids),
                'edges_created': len(edges_created),
                'tensions_surfaced': len(tensions_created),
                'narrative': delta.narrative[:200],
            },
            actor_type=ActorType.SYSTEM,
        )

        logger.info(
            "integration_workflow_complete",
            extra={
                'document_id': document_id,
                'edges_created': len(edges_created),
                'tensions_created': len(tensions_created),
                'nodes_updated': len(updated_nodes),
            },
        )

        # ── Auto-trigger full summary (thematic → full upgrade) ──
        # After integration completes, check if a full summary should be
        # generated. This upgrades the thematic summary with argumentative
        # depth (citations, tensions, attention needed).
        try:
            from apps.graph.tasks import generate_project_summary
            from apps.graph.summary_service import ProjectSummaryService
            should, reason = ProjectSummaryService.should_generate(
                document.project_id
            )
            if should:
                generate_project_summary.delay(
                    str(document.project_id), force=True
                )
                logger.info(
                    "full_summary_generation_triggered",
                    extra={
                        'document_id': document_id,
                        'project_id': str(document.project_id),
                        'reason': reason,
                    },
                )
        except Exception:
            logger.warning(
                "full_summary_trigger_failed",
                extra={'document_id': document_id},
                exc_info=True,
            )

        return {
            'status': 'completed',
            'document_id': document_id,
            'edges_created': len(edges_created),
            'delta_id': str(delta.id),
        }

    except Exception as e:
        logger.exception(
            "integrate_document_workflow_failed",
            extra={"document_id": document_id},
        )
        try:
            document = Document.objects.get(id=document_id)
            document.extraction_status = 'integration_failed'
            document.extraction_error = f"Integration failed: {str(e)[:500]}"
            document.save(update_fields=['extraction_status', 'extraction_error'])
        except Exception:
            logger.exception("integration_status_update_failed")
        return {'status': 'failed', 'error': 'Document integration failed.'}


@shared_task
def batch_integrate_documents(project_id: str, document_node_map: dict):
    """
    Batch integration for multiple documents uploaded together.

    Instead of N separate integration calls (one per document), runs a single
    integration pass with all new nodes at once — cutting LLM calls from N to 1.

    Args:
        project_id: Project to integrate into
        document_node_map: {document_id: [node_id_str, ...], ...}
    """
    from apps.projects.models import Document
    from apps.graph.models import Node, Edge
    from apps.graph.integration import integrate_new_nodes
    from apps.graph.delta_service import GraphDeltaService
    from apps.events.services import EventService
    from apps.events.models import EventType, ActorType
    import uuid

    all_node_ids = []
    documents = {}
    for doc_id, node_ids in document_node_map.items():
        uuids = [uuid.UUID(nid) for nid in node_ids]
        all_node_ids.extend(uuids)
        try:
            documents[doc_id] = Document.objects.get(id=doc_id)
            documents[doc_id].extraction_status = 'integrating'
            documents[doc_id].save(update_fields=['extraction_status'])
        except Document.DoesNotExist:
            logger.warning("Document %s not found for batch integration", doc_id)

    if not all_node_ids:
        return {'status': 'skipped', 'reason': 'no nodes to integrate'}

    try:
        integration_result = integrate_new_nodes(
            project_id=project_id,
            new_node_ids=all_node_ids,
        )

        edges_created = integration_result.get('edges', [])
        tensions_created = integration_result.get('tensions', [])
        updated_nodes = integration_result.get('updated_nodes', [])

        nodes_added = list(Node.objects.filter(id__in=all_node_ids))
        edges_added = list(Edge.objects.filter(id__in=edges_created))
        nodes_updated_objs = list(Node.objects.filter(id__in=updated_nodes))

        delta = GraphDeltaService.create_delta(
            project_id=project_id,
            trigger='batch_upload',
            nodes_added=nodes_added,
            nodes_updated=nodes_updated_objs,
            edges_added=edges_added,
            tensions_surfaced=len(tensions_created),
            assumptions_challenged=sum(
                1 for n in nodes_updated_objs
                if n.node_type == 'assumption' and n.status in ('challenged', 'refuted')
            ),
        )

        # Mark all documents as completed
        for doc in documents.values():
            doc.extraction_status = 'completed'
            doc.save(update_fields=['extraction_status'])

        EventService.append(
            event_type=EventType.GRAPH_EXTRACTION_COMPLETED,
            payload={
                'project_id': project_id,
                'batch_size': len(documents),
                'delta_id': str(delta.id),
                'nodes_created': len(all_node_ids),
                'edges_created': len(edges_created),
                'tensions_surfaced': len(tensions_created),
            },
            actor_type=ActorType.SYSTEM,
        )

        logger.info(
            "batch_integration_complete",
            extra={
                'project_id': project_id,
                'documents': len(documents),
                'nodes_integrated': len(all_node_ids),
                'edges_created': len(edges_created),
            },
        )

        return {
            'status': 'completed',
            'edges_created': len(edges_created),
            'delta_id': str(delta.id),
        }

    except Exception as e:
        logger.exception(
            "batch_integration_failed",
            extra={"project_id": project_id},
        )
        for doc in documents.values():
            doc.extraction_status = 'integration_failed'
            doc.extraction_error = f"Batch integration failed: {str(e)[:500]}"
            doc.save(update_fields=['extraction_status', 'extraction_error'])
        return {'status': 'failed', 'error': 'Batch document integration failed.'}


@shared_task
def generate_research_workflow(inquiry_id: str, user_id: int):
    """
    Generate research document asynchronously (Phase 2B).
    
    Workflow:
    1. Get inquiry and user
    2. Generate comprehensive research
    3. Create research document
    4. Emit completion event
    
    Args:
        inquiry_id: Inquiry to research
        user_id: User requesting research
    
    Returns:
        Document creation result
    """
    from apps.inquiries.models import Inquiry
    from apps.agents.document_generator import AIDocumentGenerator
    from django.contrib.auth.models import User
    from apps.events.services import EventService
    from apps.events.models import EventType, ActorType
    
    try:
        inquiry = Inquiry.objects.get(id=inquiry_id)
        user = User.objects.get(id=user_id)
        
        # Generate research
        generator = AIDocumentGenerator()
        research_doc = generator.generate_research_for_inquiry(inquiry, user)
        
        # Emit operational event
        EventService.append(
            event_type=EventType.WORKFLOW_COMPLETED,
            payload={
                'workflow': 'generate_research',
                'inquiry_id': str(inquiry_id),
                'document_id': str(research_doc.id),
                'title': research_doc.title
            },
            actor_type=ActorType.SYSTEM,
            case_id=inquiry.case_id
        )

        # Emit provenance events
        EventService.append(
            event_type=EventType.RESEARCH_COMPLETED,
            payload={
                'inquiry_id': str(inquiry_id),
                'inquiry_title': inquiry.title,
                'research_type': 'research',
                'document_id': str(research_doc.id),
                'title': research_doc.title,
            },
            actor_type=ActorType.ASSISTANT,
            case_id=inquiry.case_id,
        )
        EventService.append(
            event_type=EventType.DOCUMENT_ADDED,
            payload={
                'document_id': str(research_doc.id),
                'document_name': research_doc.title,
                'document_type': research_doc.document_type,
                'source': 'generated',
            },
            actor_type=ActorType.ASSISTANT,
            case_id=inquiry.case_id,
        )

        return {
            'status': 'completed',
            'document_id': str(research_doc.id),
            'title': research_doc.title,
            'document_type': research_doc.document_type
        }
    except Exception as e:
        logger.exception(
            "generate_research_workflow_failed",
            extra={"inquiry_id": str(inquiry_id), "user_id": user_id},
        )
        return {
            'status': 'failed',
            'error': 'Research workflow generation failed.'
        }
