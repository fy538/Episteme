"""
Artifact generation workflows

Celery tasks for generating artifacts.
Includes ADK-based agents (legacy) and ResearchLoop-based agents (v2).
"""
import logging
import warnings

from celery import shared_task
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


# ─── Shared Helpers ──────────────────────────────────────────────────────────

async def _create_artifact_with_version(
    *,
    title: str,
    artifact_type,  # ArtifactType enum
    case,
    user,
    generated_by: str,
    generation_prompt: str,
    blocks: list[dict],
    generation_time_ms: int | None = None,
    input_signals_qs=None,
    input_evidence_qs=None,
    skills_used=None,
) -> tuple:
    """
    Create an Artifact + ArtifactVersion in a transaction.

    Returns (artifact, version) tuple.
    """
    from apps.artifacts.models import Artifact, ArtifactVersion

    with transaction.atomic():
        artifact = await Artifact.objects.acreate(
            title=title,
            type=artifact_type,
            case=case,
            user=user,
            generated_by=generated_by,
            generation_prompt=generation_prompt,
        )

        version = await ArtifactVersion.objects.acreate(
            artifact=artifact,
            version=1,
            blocks=blocks,
            parent_version=None,
            diff={},
            created_by=user,
            generation_time_ms=generation_time_ms,
        )

        artifact.current_version = version
        await artifact.asave()

        if input_signals_qs is not None:
            await artifact.input_signals.aset(input_signals_qs)

        if input_evidence_qs is not None:
            await artifact.input_evidence.aset(input_evidence_qs)

        if skills_used:
            await artifact.skills_used.aset(skills_used)

    return artifact, version


async def _load_skills_and_inject(case, agent_type: str) -> tuple[list, dict]:
    """
    Load active skills for a case and build skill context.

    Returns (active_skills, skill_context) tuple.
    """
    from apps.skills.injection import get_active_skills_for_case, build_skill_context

    active_skills = await get_active_skills_for_case(case)
    skill_context = build_skill_context(active_skills, agent_type=agent_type)
    return active_skills, skill_context


@shared_task
async def generate_research_artifact(
    case_id: str,
    topic: str,
    user_id: int,
    correlation_id: str = None,
    placeholder_message_id: str = None
):
    """
    Generate research report artifact using ADK with web search.

    .. deprecated:: Use generate_research_artifact_v2 instead.
    """
    warnings.warn(
        "generate_research_artifact is deprecated, use generate_research_artifact_v2",
        DeprecationWarning,
        stacklevel=2,
    )
    from apps.cases.models import Case
    from apps.artifacts.models import ArtifactType
    from apps.projects.models import Evidence
    from apps.agents.adk_agents import get_research_agent
    from apps.skills.injection import format_system_prompt_with_skills
    from apps.agents.orchestrator import AgentOrchestrator
    from django.contrib.auth.models import User
    import uuid as uuid_module

    if not correlation_id:
        correlation_id = str(uuid_module.uuid4())

    case = await Case.objects.aget(id=case_id)
    user = await User.objects.aget(id=user_id)

    if placeholder_message_id:
        await AgentOrchestrator.update_progress(
            correlation_id=correlation_id,
            step='gathering_context',
            message='Gathering signals and evidence...',
            placeholder_message_id=placeholder_message_id
        )

    signals = [
        {'type': s.type, 'text': s.text, 'status': s.status}
        async for s in case.signals.filter(status__in=['suggested', 'confirmed'])[:10]
    ]

    evidence = [
        {'text': e.text, 'type': e.type}
        async for e in Evidence.objects.filter(document__case=case, extraction_confidence__gte=0.7)[:5]
    ]

    active_skills, skill_context = await _load_skills_and_inject(case, 'research')

    if placeholder_message_id and active_skills:
        await AgentOrchestrator.update_progress(
            correlation_id=correlation_id,
            step='loading_skills',
            message=f'Loading {len(active_skills)} skill(s)...',
            placeholder_message_id=placeholder_message_id
        )

    agent = get_research_agent()
    if skill_context['system_prompt_extension']:
        base_instruction = agent.agent.system_instruction
        enhanced_instruction = format_system_prompt_with_skills(base_instruction, skill_context)
        agent.agent.system_instruction = enhanced_instruction

    if placeholder_message_id:
        await AgentOrchestrator.update_progress(
            correlation_id=correlation_id,
            step='researching',
            message='Conducting research and gathering sources...',
            placeholder_message_id=placeholder_message_id
        )

    result = await agent.generate_research(topic, signals, evidence)

    if placeholder_message_id:
        await AgentOrchestrator.update_progress(
            correlation_id=correlation_id,
            step='creating_artifact',
            message='Finalizing research artifact...',
            placeholder_message_id=placeholder_message_id
        )

    artifact, version = await _create_artifact_with_version(
        title=f"Research: {topic}",
        artifact_type=ArtifactType.RESEARCH,
        case=case,
        user=user,
        generated_by='adk_research',
        generation_prompt=topic,
        blocks=result['blocks'],
        generation_time_ms=result.get('generation_time_ms'),
        input_signals_qs=case.signals.filter(status='confirmed'),
        input_evidence_qs=Evidence.objects.filter(document__case=case)[:5] if evidence else None,
        skills_used=active_skills if active_skills else None,
    )

    if placeholder_message_id:
        await AgentOrchestrator.complete_agent(
            correlation_id=correlation_id,
            artifact_id=str(artifact.id),
            placeholder_message_id=placeholder_message_id,
            blocks=result['blocks'],
            generation_time_ms=result.get('generation_time_ms', 0)
        )

    return {
        'status': 'completed',
        'artifact_id': str(artifact.id),
        'blocks': len(result['blocks']),
        'generation_time_ms': result.get('generation_time_ms'),
        'skills_used': len(active_skills),
    }


@shared_task
async def generate_critique_artifact(case_id: str, target_signal_id: str, user_id: int):
    """
    Generate critique/red-team artifact.

    .. deprecated:: Use v2 workflow instead.
    """
    warnings.warn(
        "generate_critique_artifact is deprecated, use v2 workflow",
        DeprecationWarning,
        stacklevel=2,
    )
    from apps.cases.models import Case
    from apps.signals.models import Signal
    from apps.artifacts.models import ArtifactType
    from apps.agents.adk_agents import get_critique_agent
    from apps.skills.injection import format_system_prompt_with_skills
    from apps.common.graph_utils import GraphUtils
    from django.contrib.auth.models import User

    case = await Case.objects.aget(id=case_id)
    target_signal = await Signal.objects.aget(id=target_signal_id)
    user = await User.objects.aget(id=user_id)

    dependencies = GraphUtils.get_signal_dependencies(target_signal)
    supporting_evidence = GraphUtils.get_supporting_evidence(target_signal)

    active_skills, skill_context = await _load_skills_and_inject(case, 'critique')

    agent = get_critique_agent()
    if skill_context['system_prompt_extension']:
        base_instruction = agent.agent.system_instruction
        enhanced_instruction = format_system_prompt_with_skills(base_instruction, skill_context)
        agent.agent.system_instruction = enhanced_instruction

    result = await agent.generate_critique(
        target_position=target_signal.text,
        supporting_signals=[
            {'text': s.text, 'type': s.type}
            for s in dependencies.dependencies
        ],
        supporting_evidence=[
            {'text': e.text, 'type': e.type}
            for e in supporting_evidence
        ]
    )

    artifact, version = await _create_artifact_with_version(
        title=f"Critique: {target_signal.text[:50]}",
        artifact_type=ArtifactType.CRITIQUE,
        case=case,
        user=user,
        generated_by='adk_critique',
        generation_prompt=target_signal.text,
        blocks=result['blocks'],
        generation_time_ms=result.get('generation_time_ms'),
        skills_used=active_skills if active_skills else None,
    )

    # Link target signal (special case: single signal, not a queryset)
    await artifact.input_signals.aadd(target_signal)

    return {
        'status': 'completed',
        'artifact_id': str(artifact.id),
        'skills_used': len(active_skills),
    }


@shared_task
async def generate_brief_artifact(case_id: str, user_id: int):
    """
    Generate decision brief for case.

    .. deprecated:: Use v2 workflow instead.
    """
    warnings.warn(
        "generate_brief_artifact is deprecated, use v2 workflow",
        DeprecationWarning,
        stacklevel=2,
    )
    from apps.cases.models import Case
    from apps.artifacts.models import ArtifactType
    from apps.projects.models import Evidence
    from apps.agents.adk_agents import get_brief_agent
    from apps.skills.injection import format_system_prompt_with_skills
    from django.contrib.auth.models import User

    case = await Case.objects.aget(id=case_id)
    user = await User.objects.aget(id=user_id)

    confirmed_signals = [
        {'type': s.type, 'text': s.text}
        async for s in case.signals.filter(status='confirmed')
    ]

    high_cred_evidence = [
        {'text': e.text, 'type': e.type}
        async for e in Evidence.objects.filter(
            document__case=case,
            user_credibility_rating__gte=4
        )
    ] or [
        {'text': e.text, 'type': e.type}
        async for e in Evidence.objects.filter(
            document__case=case,
            extraction_confidence__gte=0.8
        )[:5]
    ]

    active_skills, skill_context = await _load_skills_and_inject(case, 'brief')

    agent = get_brief_agent()
    if skill_context['system_prompt_extension']:
        base_instruction = agent.agent.system_instruction
        enhanced_instruction = format_system_prompt_with_skills(base_instruction, skill_context)
        agent.agent.system_instruction = enhanced_instruction

    result = await agent.generate_brief(
        case_position=case.position,
        confirmed_signals=confirmed_signals,
        high_credibility_evidence=high_cred_evidence
    )

    artifact, version = await _create_artifact_with_version(
        title=f"Brief: {case.title}",
        artifact_type=ArtifactType.BRIEF,
        case=case,
        user=user,
        generated_by='adk_brief',
        generation_prompt=case.position,
        blocks=result['blocks'],
        generation_time_ms=result.get('generation_time_ms'),
        input_signals_qs=case.signals.filter(status='confirmed'),
        input_evidence_qs=Evidence.objects.filter(document__case=case)[:10] if high_cred_evidence else None,
        skills_used=active_skills if active_skills else None,
    )

    return {
        'status': 'completed',
        'artifact_id': str(artifact.id),
        'skills_used': len(active_skills),
    }


# ─── Research Loop v2 ────────────────────────────────────────────────────────

@shared_task
async def generate_research_artifact_v2(
    case_id: str,
    topic: str,
    user_id: int,
    correlation_id: str = None,
    placeholder_message_id: str = None,
):
    """
    Generate research artifact using the multi-step ResearchLoop.

    Uses configurable research_config from skills instead of a single-shot
    ADK agent. Runs Plan → Search → Extract → Evaluate → Synthesize loop.

    Args:
        case_id: Case to generate research for
        topic: Research topic / question
        user_id: User requesting generation
        correlation_id: Optional correlation ID for progress tracking
        placeholder_message_id: Optional message ID to update with progress

    Returns:
        Dict with artifact_id and generation metadata
    """
    from apps.cases.models import Case
    from apps.artifacts.models import ArtifactType
    from apps.projects.models import Evidence
    from apps.agents.orchestrator import AgentOrchestrator
    from apps.agents.research_config import ResearchConfig
    from apps.agents.research_loop import ResearchLoop, ResearchContext
    from apps.agents.research_tools import resolve_tools_for_config
    from apps.common.llm_providers.factory import get_llm_provider
    from django.contrib.auth.models import User
    import uuid as uuid_module

    # Create correlation ID if not provided
    if not correlation_id:
        correlation_id = str(uuid_module.uuid4())

    case = await Case.objects.aget(id=case_id)
    user = await User.objects.aget(id=user_id)

    # ── Gather context ───────────────────────────────────────────────────
    if placeholder_message_id:
        await AgentOrchestrator.update_progress(
            correlation_id=correlation_id,
            step='gathering_context',
            message='Gathering signals and evidence...',
            placeholder_message_id=placeholder_message_id,
        )

    signals = [
        {'type': s.type, 'text': s.text, 'status': s.status}
        async for s in case.signals.filter(status__in=['suggested', 'confirmed'])[:10]
    ]

    evidence = [
        {'text': e.text, 'type': e.type}
        async for e in Evidence.objects.filter(
            document__case=case, extraction_confidence__gte=0.7
        )[:5]
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

    # Get research config (from skills or default)
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
            # Resume from checkpoint
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
                ),
            )

        # Save trajectory after successful completion
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

                # Build handoff summary
                summary = await build_handoff_summary(
                    question=topic,
                    findings_dicts=[f.to_dict() for f in result.findings],
                    plan_dict={"strategy_notes": result.plan.strategy_notes},
                    provider=provider,
                )

                # Build continuation prompt extension
                continuation_prompt = create_continuation_context(
                    summary=summary,
                    question=topic,
                    continuation_number=continuation_count,
                )

                # Run new loop with continuation context
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
                    ),
                )

                # Merge results
                result.findings.extend(continuation_result.findings)
                result.blocks = continuation_result.blocks  # Use latest synthesis
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
        # Notify user of failure if we have a placeholder
        if placeholder_message_id and correlation_id:
            try:
                await AgentOrchestrator.update_progress(
                    correlation_id=correlation_id,
                    step='error',
                    message=f'Research failed: {str(e)[:200]}',
                    placeholder_message_id=placeholder_message_id,
                )
            except Exception:
                pass  # Best-effort error notification
        return {
            'status': 'failed',
            'error': str(e)[:500],
            'case_id': case_id,
            'topic': topic,
        }

    # ── Create artifact ──────────────────────────────────────────────────
    if placeholder_message_id:
        await AgentOrchestrator.update_progress(
            correlation_id=correlation_id,
            step='creating_artifact',
            message='Finalizing research artifact...',
            placeholder_message_id=placeholder_message_id,
        )

    artifact, version = await _create_artifact_with_version(
        title=f"Research: {topic}",
        artifact_type=ArtifactType.RESEARCH,
        case=case,
        user=user,
        generated_by='research_loop_v2',
        generation_prompt=topic,
        blocks=result.blocks,
        generation_time_ms=result.metadata.get('generation_time_ms'),
        input_signals_qs=case.signals.filter(status='confirmed'),
        input_evidence_qs=Evidence.objects.filter(document__case=case)[:5] if evidence else None,
        skills_used=active_skills if active_skills else None,
    )

    # ── Complete agent ───────────────────────────────────────────────────
    if placeholder_message_id:
        await AgentOrchestrator.complete_agent(
            correlation_id=correlation_id,
            artifact_id=str(artifact.id),
            placeholder_message_id=placeholder_message_id,
            blocks=result.blocks,
            generation_time_ms=result.metadata.get('generation_time_ms', 0),
        )

    return {
        'status': 'completed',
        'artifact_id': str(artifact.id),
        'blocks': len(result.blocks),
        'generation_time_ms': result.metadata.get('generation_time_ms'),
        'skills_used': len(active_skills),
        'sources_found': result.metadata.get('total_sources', 0),
        'iterations': result.metadata.get('iterations', 0),
    }
