"""
Research document generation workflow.

Celery task that runs the multi-step ResearchLoop and produces a
WorkingDocument (instead of the legacy Artifact).
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


async def _load_skills_and_inject(case, agent_type: str) -> tuple[list, dict]:
    """
    Load active skills for a case and build skill context.

    Returns (active_skills, skill_context) tuple.
    """
    from apps.skills.injection import get_active_skills_for_case, build_skill_context

    active_skills = await get_active_skills_for_case(case)
    skill_context = build_skill_context(active_skills, agent_type=agent_type)
    return active_skills, skill_context


@shared_task(
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=2,
)
async def generate_research_document(
    case_id: str,
    topic: str,
    user_id: int,
    correlation_id: str = None,
    placeholder_message_id: str = None,
    graph_context: str = None,
):
    """
    Generate a research WorkingDocument using the multi-step ResearchLoop.

    Uses configurable research_config from skills instead of a single-shot
    ADK agent. Runs Plan → Search → Extract → Evaluate → Synthesize loop.

    The research content is also routed through the document extraction
    pipeline (projects.Document → chunking → graph extraction) so that:
      - Nodes have a source_document FK (CASCADE delete on doc removal)
      - Cross-document integration runs (edges, tensions, status updates)
      - A GraphDelta is recorded
      - Chunks + embeddings are created for RAG search

    Args:
        case_id: Case to generate research for
        topic: Research topic / question
        user_id: User requesting generation
        correlation_id: Optional correlation ID for progress tracking
        placeholder_message_id: Optional message ID to update with progress
        graph_context: Optional serialized knowledge graph for context

    Returns:
        Dict with document_id and generation metadata
    """
    from apps.cases.models import Case, DocumentType, EditFriction, WorkingDocument
    from apps.graph.models import Node, NodeType
    from apps.agents.orchestrator import AgentOrchestrator
    from apps.agents.research_config import ResearchConfig
    from apps.agents.research_loop import ResearchLoop, ResearchContext
    from apps.agents.research_tools import resolve_tools_for_config
    from apps.common.llm_providers.factory import get_llm_provider
    from django.contrib.auth.models import User
    import uuid as uuid_module

    if not correlation_id:
        correlation_id = str(uuid_module.uuid4())

    case = await Case.objects.aget(id=case_id)
    user = await User.objects.aget(id=user_id)

    # ── Gather context ───────────────────────────────────────────────────
    if placeholder_message_id:
        await AgentOrchestrator.update_progress(
            correlation_id=correlation_id,
            step='gathering_context',
            message='Gathering evidence from knowledge graph...',
            placeholder_message_id=placeholder_message_id,
        )

    signals = []  # Signal model removed; graph nodes used instead

    evidence_nodes = Node.objects.filter(
        project=case.project,
        node_type=NodeType.EVIDENCE,
        confidence__gte=0.7,
    )[:5]
    evidence = [
        {'text': n.content, 'type': n.properties.get('evidence_type', 'fact')}
        async for n in evidence_nodes
    ]

    # ── Load skills and config ───────────────────────────────────────────
    active_skills, skill_context = await _load_skills_and_inject(case, 'research')

    if placeholder_message_id and active_skills:
        await AgentOrchestrator.update_progress(
            correlation_id=correlation_id,
            step='loading_skills',
            message=f'Loading {len(active_skills)} skill(s)...',
            placeholder_message_id=placeholder_message_id,
        )

    research_config = skill_context.get('research_config') or ResearchConfig.default()

    # ── Set up provider and tools ────────────────────────────────────────
    provider = get_llm_provider('chat')
    tools = resolve_tools_for_config(research_config.sources, case_id=str(case.id), user_id=user.id)

    # ── Build progress callback ──────────────────────────────────────────
    async def progress_callback(step: str, message: str):
        if placeholder_message_id:
            await AgentOrchestrator.update_progress(
                correlation_id=correlation_id,
                step=step,
                message=message,
                placeholder_message_id=placeholder_message_id,
            )

    # ── Check for existing checkpoint (resume support) ──────────────────
    from apps.agents.checkpoint import save_checkpoint, load_latest_checkpoint

    existing_checkpoint = load_latest_checkpoint(correlation_id)

    # ── Run research loop ────────────────────────────────────────────────
    if placeholder_message_id:
        await AgentOrchestrator.update_progress(
            correlation_id=correlation_id,
            step='researching',
            message='Resuming research loop...' if existing_checkpoint else 'Starting multi-step research loop...',
            placeholder_message_id=placeholder_message_id,
        )

    # ── Set up trajectory recorder (opt-in observability) ──────────────
    from apps.agents.trajectory import TrajectoryRecorder

    trajectory = TrajectoryRecorder(correlation_id=correlation_id)

    try:
        if existing_checkpoint:
            result = await ResearchLoop.resume_from_checkpoint(
                checkpoint=existing_checkpoint,
                config=research_config,
                prompt_extension=skill_context['system_prompt_extension'],
                provider=provider,
                tools=tools,
                progress_callback=progress_callback,
                trace_id=correlation_id,
                checkpoint_callback=save_checkpoint,
                trajectory_recorder=trajectory,
            )
        else:
            loop = ResearchLoop(
                config=research_config,
                prompt_extension=skill_context['system_prompt_extension'],
                provider=provider,
                tools=tools,
                progress_callback=progress_callback,
                trace_id=correlation_id,
                checkpoint_callback=save_checkpoint,
                trajectory_recorder=trajectory,
            )

            result = await loop.run(
                question=topic,
                context=ResearchContext(
                    case_title=case.title,
                    case_position=case.position,
                    signals=signals,
                    evidence=evidence,
                    graph_context=graph_context or "",
                ),
            )

        trajectory.save_to_events(case_id=case_id)

        # Handle session continuation if context was exhausted
        if result.metadata.get('needs_continuation'):
            from apps.agents.context_manager import (
                build_handoff_summary,
                create_continuation_context,
                MAX_CONTINUATIONS,
            )

            continuation_count = 0
            while (
                result.metadata.get('needs_continuation')
                and continuation_count < MAX_CONTINUATIONS
            ):
                continuation_count += 1
                if placeholder_message_id:
                    await AgentOrchestrator.update_progress(
                        correlation_id=correlation_id,
                        step='continuing',
                        message=f'Context exhausted — starting continuation session {continuation_count}...',
                        placeholder_message_id=placeholder_message_id,
                    )

                summary = await build_handoff_summary(
                    question=topic,
                    findings_dicts=[f.to_dict() for f in result.findings],
                    plan_dict={"strategy_notes": result.plan.strategy_notes},
                    provider=provider,
                )

                continuation_prompt = create_continuation_context(
                    summary=summary,
                    question=topic,
                    continuation_number=continuation_count,
                )

                continuation_loop = ResearchLoop(
                    config=research_config,
                    prompt_extension=skill_context['system_prompt_extension'] + "\n\n" + continuation_prompt,
                    provider=provider,
                    tools=tools,
                    progress_callback=progress_callback,
                    trace_id=correlation_id,
                    checkpoint_callback=save_checkpoint,
                    trajectory_recorder=trajectory,
                )

                continuation_result = await continuation_loop.run(
                    question=topic,
                    context=ResearchContext(
                        case_title=case.title,
                        case_position=case.position,
                        signals=signals,
                        evidence=evidence,
                        graph_context=graph_context or "",
                    ),
                )

                result.findings.extend(continuation_result.findings)
                result.blocks = continuation_result.blocks
                result.content = continuation_result.content
                result.metadata['generation_time_ms'] = (
                    result.metadata.get('generation_time_ms', 0)
                    + continuation_result.metadata.get('generation_time_ms', 0)
                )
                result.metadata['total_sources'] = (
                    result.metadata.get('total_sources', 0)
                    + continuation_result.metadata.get('total_sources', 0)
                )
                result.metadata['continuations'] = continuation_count
                result.metadata['needs_continuation'] = continuation_result.metadata.get('needs_continuation', False)

            trajectory.save_to_events(case_id=case_id)

    except Exception as e:
        logger.exception(
            "research_loop_failed",
            extra={
                "case_id": case_id,
                "topic": topic,
                "correlation_id": correlation_id,
                "error": str(e),
            },
        )
        try:
            from apps.events.services import EventService
            from apps.events.models import ActorType
            EventService.append(
                event_type="AgentFailed",
                payload={
                    "agent_type": "research",
                    "topic": topic,
                    "error": str(e)[:500],
                    "error_type": type(e).__name__,
                },
                actor_type=ActorType.SYSTEM,
                correlation_id=correlation_id,
                case_id=case_id,
            )
        except Exception:
            pass

        if placeholder_message_id and correlation_id:
            try:
                await AgentOrchestrator.update_progress(
                    correlation_id=correlation_id,
                    step='error',
                    message=f'Research failed: {str(e)[:200]}',
                    placeholder_message_id=placeholder_message_id,
                )
            except Exception:
                pass
        return {
            'status': 'failed',
            'error': str(e)[:500],
            'case_id': case_id,
            'topic': topic,
        }

    # ── Create WorkingDocument ───────────────────────────────────────────
    if placeholder_message_id:
        await AgentOrchestrator.update_progress(
            correlation_id=correlation_id,
            step='creating_document',
            message='Finalizing research document...',
            placeholder_message_id=placeholder_message_id,
        )

    working_doc = await WorkingDocument.objects.acreate(
        case=case,
        document_type=DocumentType.RESEARCH,
        title=f"Research: {topic}",
        content_markdown=result.content,
        edit_friction=EditFriction.HIGH,
        generated_by_ai=True,
        agent_type='research_loop_v2',
        generation_prompt=topic,
        ai_structure={
            'blocks': result.blocks,
            'findings_count': len(result.findings),
            'sources_found': result.metadata.get('total_sources', 0),
            'iterations': result.metadata.get('iterations', 0),
        },
        created_by=user,
    )

    # ── Route through document extraction pipeline ───────────────────────
    research_document_id = None
    try:
        if result.content:
            from asgiref.sync import sync_to_async
            from apps.projects.services import DocumentService

            research_document = await sync_to_async(DocumentService.create_document)(
                user=user,
                project_id=case.project_id,
                title=f"Research: {topic}",
                source_type='text',
                content_text=result.content,
                case_id=case.id,
            )
            research_document_id = str(research_document.id)

            from tasks.workflows import process_document_workflow
            process_document_workflow.delay(research_document_id)

            logger.info(
                "research_document_created",
                extra={
                    "case_id": case_id,
                    "document_id": str(working_doc.id),
                    "source_document_id": research_document_id,
                },
            )
    except Exception as e:
        logger.warning(
            "research_document_creation_failed",
            extra={"case_id": case_id, "error": str(e)},
        )

    # ── Complete agent ───────────────────────────────────────────────────
    if placeholder_message_id:
        await AgentOrchestrator.complete_agent(
            correlation_id=correlation_id,
            document_id=str(working_doc.id),
            placeholder_message_id=placeholder_message_id,
            blocks=result.blocks,
            generation_time_ms=result.metadata.get('generation_time_ms', 0),
        )

    return {
        'status': 'completed',
        'document_id': str(working_doc.id),
        'blocks': len(result.blocks),
        'generation_time_ms': result.metadata.get('generation_time_ms'),
        'skills_used': len(active_skills),
        'sources_found': result.metadata.get('total_sources', 0),
        'iterations': result.metadata.get('iterations', 0),
        'research_document_id': research_document_id,
    }
