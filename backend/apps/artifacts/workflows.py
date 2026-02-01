"""
Artifact generation workflows

Celery tasks for generating artifacts using Google ADK agents.
"""
from celery import shared_task
from django.utils import timezone
from django.db import transaction


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
    
    Args:
        case_id: Case to generate research for
        topic: Research topic
        user_id: User requesting generation
        correlation_id: Optional correlation ID for progress tracking
        placeholder_message_id: Optional message ID to update with progress
    
    Returns:
        Dict with artifact_id and generation metadata
    """
    from apps.cases.models import Case
    from apps.artifacts.models import Artifact, ArtifactVersion, ArtifactType
    from apps.signals.models import Signal
    from apps.projects.models import Evidence
    from apps.agents.adk_agents import get_research_agent
    from apps.skills.injection import get_active_skills_for_case, build_skill_context, format_system_prompt_with_skills
    from apps.agents.orchestrator import AgentOrchestrator
    from django.contrib.auth.models import User
    import uuid as uuid_module
    
    # Create correlation ID if not provided
    if not correlation_id:
        correlation_id = str(uuid_module.uuid4())
    
    case = await Case.objects.aget(id=case_id)
    user = await User.objects.aget(id=user_id)
    
    # Progress: Gathering context
    if placeholder_message_id:
        await AgentOrchestrator.update_progress(
            correlation_id=correlation_id,
            step='gathering_context',
            message='Gathering signals and evidence...',
            placeholder_message_id=placeholder_message_id
        )
    
    # Get context from case
    signals = [
        {
            'type': s.type,
            'text': s.text,
            'status': s.status
        }
        async for s in case.signals.filter(status__in=['suggested', 'confirmed'])[:10]
    ]
    
    evidence = [
        {'text': e.text, 'type': e.type}
        async for e in Evidence.objects.filter(document__case=case, extraction_confidence__gte=0.7)[:5]
    ]
    
    # Get active skills for this case
    active_skills = await get_active_skills_for_case(case)
    
    # Progress: Loading skills
    if placeholder_message_id and active_skills:
        await AgentOrchestrator.update_progress(
            correlation_id=correlation_id,
            step='loading_skills',
            message=f'Loading {len(active_skills)} skill(s)...',
            placeholder_message_id=placeholder_message_id
        )
    
    # Build skill context
    skill_context = build_skill_context(active_skills, agent_type='research')
    
    # Generate using ADK agent with skill context
    agent = get_research_agent()
    
    # Inject skill context into agent's system prompt
    if skill_context['system_prompt_extension']:
        base_instruction = agent.agent.system_instruction
        enhanced_instruction = format_system_prompt_with_skills(base_instruction, skill_context)
        agent.agent.system_instruction = enhanced_instruction
    
    # Progress: Researching
    if placeholder_message_id:
        await AgentOrchestrator.update_progress(
            correlation_id=correlation_id,
            step='researching',
            message='Conducting research and gathering sources...',
            placeholder_message_id=placeholder_message_id
        )
    
    result = await agent.generate_research(topic, signals, evidence)
    
    # Progress: Creating artifact
    if placeholder_message_id:
        await AgentOrchestrator.update_progress(
            correlation_id=correlation_id,
            step='creating_artifact',
            message='Finalizing research artifact...',
            placeholder_message_id=placeholder_message_id
        )
    
    # Create artifact
    with transaction.atomic():
        artifact = await Artifact.objects.acreate(
            title=f"Research: {topic}",
            type=ArtifactType.RESEARCH,
            case=case,
            user=user,
            generated_by='adk_research',
            generation_prompt=topic,
        )
        
        # Create first version
        version = await ArtifactVersion.objects.acreate(
            artifact=artifact,
            version=1,
            blocks=result['blocks'],
            parent_version=None,
            diff={},
            created_by=user,
            generation_time_ms=result.get('generation_time_ms'),
        )
        
        # Set as current version
        artifact.current_version = version
        await artifact.asave()
        
        # Link input signals and evidence
        await artifact.input_signals.aset(case.signals.filter(status='confirmed'))
        
        if evidence:
            evidence_objects = Evidence.objects.filter(document__case=case)[:5]
            await artifact.input_evidence.aset(evidence_objects)
        
        # Track which skills were used
        if active_skills:
            await artifact.skills_used.aset(active_skills)
    
    # Complete agent and update chat
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
    
    Args:
        case_id: Case context
        target_signal_id: Signal to critique
        user_id: User requesting
    
    Returns:
        Dict with artifact_id
    """
    from apps.cases.models import Case
    from apps.signals.models import Signal
    from apps.artifacts.models import Artifact, ArtifactVersion, ArtifactType
    from apps.projects.models import Evidence
    from apps.agents.adk_agents import get_critique_agent
    from apps.skills.injection import get_active_skills_for_case, build_skill_context, format_system_prompt_with_skills
    from apps.common.graph_utils import GraphUtils
    from django.contrib.auth.models import User
    
    case = await Case.objects.aget(id=case_id)
    target_signal = await Signal.objects.aget(id=target_signal_id)
    user = await User.objects.aget(id=user_id)
    
    # Get dependencies and supporting evidence
    dependencies = GraphUtils.get_signal_dependencies(target_signal)
    supporting_evidence = GraphUtils.get_supporting_evidence(target_signal)
    
    # Get active skills for this case
    active_skills = await get_active_skills_for_case(case)
    
    # Build skill context
    skill_context = build_skill_context(active_skills, agent_type='critique')
    
    # Generate critique with skill context
    agent = get_critique_agent()
    
    # Inject skill context into agent's system prompt
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
    
    # Create artifact
    with transaction.atomic():
        artifact = await Artifact.objects.acreate(
            title=f"Critique: {target_signal.text[:50]}",
            type=ArtifactType.CRITIQUE,
            case=case,
            user=user,
            generated_by='adk_critique',
            generation_prompt=target_signal.text,
        )
        
        version = await ArtifactVersion.objects.acreate(
            artifact=artifact,
            version=1,
            blocks=result['blocks'],
            created_by=user,
            generation_time_ms=result.get('generation_time_ms'),
        )
        
        artifact.current_version = version
        await artifact.asave()
        
        # Link target signal
        await artifact.input_signals.aadd(target_signal)
        
        # Track which skills were used
        if active_skills:
            await artifact.skills_used.aset(active_skills)
    
    return {
        'status': 'completed',
        'artifact_id': str(artifact.id),
        'skills_used': len(active_skills),
    }


@shared_task
async def generate_brief_artifact(case_id: str, user_id: int):
    """
    Generate decision brief for case.
    
    Args:
        case_id: Case to generate brief for
        user_id: User requesting
    
    Returns:
        Dict with artifact_id
    """
    from apps.cases.models import Case
    from apps.artifacts.models import Artifact, ArtifactVersion, ArtifactType
    from apps.signals.models import Signal
    from apps.projects.models import Evidence
    from apps.agents.adk_agents import get_brief_agent
    from apps.skills.injection import get_active_skills_for_case, build_skill_context, format_system_prompt_with_skills
    from django.contrib.auth.models import User
    
    case = await Case.objects.aget(id=case_id)
    user = await User.objects.aget(id=user_id)
    
    # Get confirmed signals
    confirmed_signals = [
        {'type': s.type, 'text': s.text}
        async for s in case.signals.filter(status='confirmed')
    ]
    
    # Get high-credibility evidence
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
    
    # Get active skills for this case
    active_skills = await get_active_skills_for_case(case)
    
    # Build skill context
    skill_context = build_skill_context(active_skills, agent_type='brief')
    
    # Generate brief with skill context
    agent = get_brief_agent()
    
    # Inject skill context into agent's system prompt
    if skill_context['system_prompt_extension']:
        base_instruction = agent.agent.system_instruction
        enhanced_instruction = format_system_prompt_with_skills(base_instruction, skill_context)
        agent.agent.system_instruction = enhanced_instruction
    
    result = await agent.generate_brief(
        case_position=case.position,
        confirmed_signals=confirmed_signals,
        high_credibility_evidence=high_cred_evidence
    )
    
    # Create artifact
    with transaction.atomic():
        artifact = await Artifact.objects.acreate(
            title=f"Brief: {case.title}",
            type=ArtifactType.BRIEF,
            case=case,
            user=user,
            generated_by='adk_brief',
            generation_prompt=case.position,
        )
        
        version = await ArtifactVersion.objects.acreate(
            artifact=artifact,
            version=1,
            blocks=result['blocks'],
            created_by=user,
            generation_time_ms=result.get('generation_time_ms'),
        )
        
        artifact.current_version = version
        await artifact.asave()
        
        # Link inputs
        await artifact.input_signals.aset(case.signals.filter(status='confirmed'))
        
        if high_cred_evidence:
            await artifact.input_evidence.aset(
                Evidence.objects.filter(document__case=case)[:10]
            )
        
        # Track which skills were used
        if active_skills:
            await artifact.skills_used.aset(active_skills)
    
    return {
        'status': 'completed',
        'artifact_id': str(artifact.id),
        'skills_used': len(active_skills),
    }
