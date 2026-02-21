"""
Decomposed phases for the unified_stream SSE pipeline.

Each phase function is an async generator (yields SSE strings) or an async
coroutine (no SSE output). They communicate through the shared StreamState
dataclass, which carries all inter-phase state explicitly.

The orchestrator in views.py calls these in order:
  1. assemble_context        (coroutine — no SSE)
  2. stream_llm_response     (generator — bulk of SSE events)
  3. persist_message          (generator — source_chunks)
  4. apply_graph_edits        (coroutine — no SSE)
  5. execute_tool_actions     (generator — tool_confirmation / tool_executed)
  6. kick_off_companion       (coroutine — no SSE)
  7. resolve_title            (generator — title_update)
  8. process_companion_results(generator — episode_sealed, companion_structure, etc.)
  9. build_done_event         (pure function — returns one SSE string)
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Optional

from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SSE formatting helper
# ---------------------------------------------------------------------------

def sse(event_name: str, data: dict) -> str:
    """Format a single Server-Sent Event string."""
    return f"event: {event_name}\ndata: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# State carrier
# ---------------------------------------------------------------------------

@dataclass
class StreamState:
    """Mutable state carrier for the unified stream pipeline.

    Passed through every phase function so that inter-phase data flow is
    explicit and auditable.
    """
    # --- Inputs (set before pipeline starts) ---
    thread: Any                                   # ChatThread
    user: Any                                     # User
    content: str = ""                             # user message text
    mode_context: dict = field(default_factory=dict)
    title_task: Optional[asyncio.Task] = None
    correlation_id: uuid.UUID = field(default_factory=uuid.uuid4)

    # --- From context assembly (phase 1) ---
    assembled: Any = None                         # AssembledContext
    engine: Any = None                            # UnifiedAnalysisEngine

    # --- Accumulators (populated during phase 2 streaming) ---
    response_content: str = ""
    reflection_content: str = ""
    action_hints_json: str = ""
    action_hints_count: int = 0
    graph_edits_json: str = ""
    plan_edits_json: str = ""
    orientation_edits_json: str = ""
    tool_actions_json: str = ""

    # --- Post-stream derived state ---
    message_id: Optional[str] = None
    reflection_id: Optional[str] = None
    graph_edit_summary: Optional[dict] = None
    companion_task: Optional[asyncio.Task] = None
    companion_structure_data: Optional[dict] = None


# ---------------------------------------------------------------------------
# Phase 1: Context Assembly
# ---------------------------------------------------------------------------

async def assemble_context(state: StreamState) -> None:
    """Call ContextAssemblyService and initialise the analysis engine."""
    from apps.intelligence.engine import UnifiedAnalysisEngine
    from .context_assembly import ContextAssemblyService

    state.engine = UnifiedAnalysisEngine()

    assembly_service = ContextAssemblyService()
    state.assembled = await assembly_service.assemble(
        thread=state.thread,
        user_message=state.content,
        mode_context=state.mode_context,
        user=state.user,
    )


# ---------------------------------------------------------------------------
# Phase 2: LLM Streaming Loop
# ---------------------------------------------------------------------------

async def _merge_orientation_diff(
    orientation_edits_data: dict,
    current_orientation_id: str,
) -> None:
    """Load current orientation state from DB and merge the LLM diff in-place.

    Mutates *orientation_edits_data* by setting 'proposed_state' and
    'orientation_id' if the merge succeeds.
    """
    from apps.graph.orientation_service import OrientationService
    from apps.graph.models import (
        ProjectInsight, InsightType, InsightStatus,
        ProjectOrientation,
    )

    orient = await sync_to_async(
        lambda: ProjectOrientation.objects.filter(
            id=current_orientation_id,
        ).first()
    )()
    insights = await sync_to_async(list)(
        ProjectInsight.objects.filter(
            orientation_id=current_orientation_id,
        ).exclude(
            status=InsightStatus.DISMISSED,
        ).order_by('display_order')
    )

    findings = []
    angles = []
    for ins in insights:
        if ins.insight_type == InsightType.EXPLORATION_ANGLE:
            angles.append({
                'id': str(ins.id),
                'title': ins.title,
            })
        else:
            findings.append({
                'id': str(ins.id),
                'insight_type': ins.insight_type,
                'title': ins.title,
                'content': ins.content,
                'status': ins.status,
                'confidence': ins.confidence,
            })

    proposed = OrientationService.merge_orientation_diff(
        current_findings=findings,
        current_angles=angles,
        current_lead=orient.lead_text if orient else '',
        current_lens=orient.lens_type if orient else '',
        diff_data=orientation_edits_data['diff_data'],
    )
    orientation_edits_data['proposed_state'] = proposed
    orientation_edits_data['orientation_id'] = current_orientation_id


async def stream_llm_response(state: StreamState) -> AsyncGenerator[str, None]:
    """Iterate engine events and yield SSE chunks.

    Accumulates completed content into *state* accumulators for use by
    downstream phases.
    """
    from apps.intelligence.engine import StreamEventType

    assembled = state.assembled
    current_plan_content = assembled.current_plan_content
    current_orientation_id = assembled.current_orientation_id

    async for event in state.engine.analyze_simple(
        thread=state.thread,
        user_message=state.content,
        conversation_context=assembled.conversation_context,
        system_prompt_override=assembled.system_prompt_override,
        retrieval_context=assembled.retrieval_context,
        available_tools=assembled.available_tools,
    ):
        if event.type == StreamEventType.RESPONSE_CHUNK:
            state.response_content += event.data
            yield sse("response_chunk", {"delta": event.data})

        elif event.type == StreamEventType.REFLECTION_CHUNK:
            state.reflection_content += event.data
            yield sse("reflection_chunk", {"delta": event.data})

        elif event.type == StreamEventType.RESPONSE_COMPLETE:
            state.response_content = event.data
            yield sse("response_complete", {"content": event.data})

        elif event.type == StreamEventType.REFLECTION_COMPLETE:
            state.reflection_content = event.data
            yield sse("reflection_complete", {"content": event.data})

        elif event.type == StreamEventType.ACTION_HINTS_COMPLETE:
            action_hints = event.data.get('action_hints', [])
            state.action_hints_json = event.data.get('raw', '[]')
            state.action_hints_count = len(action_hints)
            yield sse("action_hints", {"action_hints": action_hints})

        elif event.type == StreamEventType.GRAPH_EDITS_COMPLETE:
            graph_edits = event.data.get('graph_edits', [])
            state.graph_edits_json = event.data.get('raw', '[]')
            yield sse("graph_edits", {"graph_edits": graph_edits})

        elif event.type == StreamEventType.PLAN_EDITS_COMPLETE:
            plan_edits_data = event.data.get('plan_edits', {})
            state.plan_edits_json = event.data.get('raw', '{}')
            if plan_edits_data and isinstance(plan_edits_data, dict) and plan_edits_data.get('diff_data'):
                if not plan_edits_data.get('proposed_content') and current_plan_content:
                    from apps.cases.plan_service import PlanService
                    plan_edits_data['proposed_content'] = PlanService.merge_plan_diff(
                        current_plan_content, plan_edits_data['diff_data']
                    )
                if plan_edits_data.get('proposed_content'):
                    yield sse("plan_edits", {"plan_edits": plan_edits_data})

        elif event.type == StreamEventType.ORIENTATION_EDITS_COMPLETE:
            orientation_edits_data = event.data.get('orientation_edits', {})
            state.orientation_edits_json = event.data.get('raw', '{}')
            if (orientation_edits_data
                    and isinstance(orientation_edits_data, dict)
                    and orientation_edits_data.get('diff_data')):
                if not orientation_edits_data.get('proposed_state') and current_orientation_id:
                    try:
                        await _merge_orientation_diff(
                            orientation_edits_data, current_orientation_id,
                        )
                    except Exception as e:
                        logger.warning("Could not merge orientation diff: %s", e)
                if orientation_edits_data.get('proposed_state'):
                    yield sse("orientation_edits", {"orientation_edits": orientation_edits_data})

        elif event.type == StreamEventType.TOOL_ACTIONS_COMPLETE:
            tool_actions = event.data.get('tool_actions', [])
            state.tool_actions_json = event.data.get('raw', '[]')
            if tool_actions and isinstance(tool_actions, list):
                yield sse("tool_actions", {"tool_actions": tool_actions})

        elif event.type == StreamEventType.ERROR:
            error_msg = event.data.get('error', 'Unknown error')
            yield sse("error", {"error": error_msg})

        elif event.type == StreamEventType.DONE:
            pass  # Saving happens in persist_message; done event emitted later


# ---------------------------------------------------------------------------
# Phase 3: Message Persistence + Source Chunks
# ---------------------------------------------------------------------------

async def persist_message(state: StreamState) -> AsyncGenerator[str, None]:
    """Save assistant message via handler and yield source_chunks if available."""
    from apps.intelligence.handlers import UnifiedAnalysisHandler

    assembled = state.assembled
    retrieval_result = assembled.retrieval_result

    result = await UnifiedAnalysisHandler.handle_completion(
        thread=state.thread,
        user=state.user,
        response_content=state.response_content,
        reflection_content=state.reflection_content,
        model_key='chat',
        correlation_id=state.correlation_id,
        retrieval_result=retrieval_result,
    )

    state.message_id = result.get('message_id')
    state.reflection_id = result.get('reflection_id')

    # Emit source chunks for citation rendering
    if retrieval_result and retrieval_result.has_sources:
        yield sse("source_chunks", {
            'chunks': [
                {
                    'index': i,
                    'chunk_id': chunk.chunk_id,
                    'document_id': chunk.document_id,
                    'document_title': chunk.document_title,
                    'chunk_index': chunk.chunk_index,
                    'excerpt': chunk.excerpt,
                    'similarity': round(chunk.similarity, 3),
                }
                for i, chunk in enumerate(retrieval_result.chunks)
            ]
        })


# ---------------------------------------------------------------------------
# Phase 4: Graph Edit Application
# ---------------------------------------------------------------------------

async def apply_graph_edits(state: StreamState) -> None:
    """Parse and apply graph edits produced by the LLM."""
    if not state.graph_edits_json or state.graph_edits_json.strip() in ('', '[]'):
        return

    try:
        from apps.graph.edit_handler import GraphEditHandler
        edits = json.loads(state.graph_edits_json)
        if isinstance(edits, list) and edits and state.thread.project_id:
            state.graph_edit_summary = await sync_to_async(
                GraphEditHandler.apply_edits
            )(
                project_id=state.thread.project_id,
                edits=edits,
                source_message_id=state.message_id,
                user=state.user,
                case_id=state.thread.primary_case_id,
            )
            logger.info(
                "graph_edits_applied_from_chat",
                extra={
                    'thread_id': str(state.thread.id),
                    **state.graph_edit_summary,
                },
            )
    except Exception:
        logger.exception("Failed to apply graph edits from chat")


# ---------------------------------------------------------------------------
# Phase 5: Tool Action Execution
# ---------------------------------------------------------------------------

async def execute_tool_actions(state: StreamState) -> AsyncGenerator[str, None]:
    """Execute tool actions and yield confirmation/result SSE events."""
    if not state.tool_actions_json or state.tool_actions_json.strip() in ('', '[]'):
        return

    try:
        from apps.intelligence.tools.executor import ToolExecutor

        try:
            actions = json.loads(state.tool_actions_json)
        except json.JSONDecodeError as e:
            logger.warning(
                "Malformed tool_actions JSON from LLM: %s (buffer: %.200s)",
                e, state.tool_actions_json,
            )
            yield sse("tool_actions_error", {
                "error": "AI produced malformed tool action data",
            })
            return

        if isinstance(actions, list) and actions:
            exec_context = {
                'user': state.user,
                'thread_id': str(state.thread.id),
                'project_id': (
                    str(state.thread.project_id)
                    if state.thread.project_id else None
                ),
                'case_id': (
                    str(state.thread.primary_case_id)
                    if state.thread.primary_case_id else None
                ),
            }
            tool_results = await ToolExecutor.execute_batch(
                actions, exec_context
            )

            for tool_result in tool_results:
                if tool_result.pending_confirmation:
                    yield sse("tool_confirmation", {
                        'tool': tool_result.tool_name,
                        'display_name': tool_result.display_name,
                        'params': tool_result.params,
                        'reason': tool_result.reason,
                        'confirmation_id': tool_result.confirmation_id,
                    })
                else:
                    yield sse("tool_executed", {
                        'tool': tool_result.tool_name,
                        'display_name': tool_result.display_name,
                        'success': tool_result.success,
                        'output': tool_result.output,
                        'error': tool_result.error,
                    })

            logger.info(
                "tool_actions_processed",
                extra={
                    'thread_id': str(state.thread.id),
                    'total': len(actions),
                    'executed': sum(
                        1 for r in tool_results
                        if not r.pending_confirmation and r.success
                    ),
                    'pending': sum(
                        1 for r in tool_results
                        if r.pending_confirmation
                    ),
                },
            )
    except Exception:
        logger.exception("Failed to execute tool actions from chat")


# ---------------------------------------------------------------------------
# Phase 6: Companion Kickoff
# ---------------------------------------------------------------------------

async def kick_off_companion(state: StreamState) -> None:
    """Fire-and-forget the companion structure update task."""
    if not state.message_id:
        return

    try:
        from .companion_service import CompanionService
        message_uuid = (
            uuid.UUID(state.message_id)
            if isinstance(state.message_id, str)
            else state.message_id
        )
        state.companion_task = asyncio.create_task(
            CompanionService.update_structure(
                thread_id=state.thread.id,
                new_message_id=message_uuid,
            )
        )
    except Exception as e:
        logger.debug("Could not start companion update: %s", e)


# ---------------------------------------------------------------------------
# Phase 7: Title Generation
# ---------------------------------------------------------------------------

async def resolve_title(state: StreamState) -> AsyncGenerator[str, None]:
    """Await pending title task or check for periodic title refresh."""
    from apps.intelligence.title_generator import generate_thread_title
    from .models import Message

    thread = state.thread

    if state.title_task is not None:
        # Await the parallel title task kicked off before the stream
        try:
            generated_title = await state.title_task
            if generated_title:
                thread.title = generated_title
                metadata = thread.metadata or {}
                msg_count = await sync_to_async(
                    lambda: Message.objects.filter(thread=thread, role='user').count()
                )()
                metadata['title_gen_at_msg_count'] = msg_count
                thread.metadata = metadata
                await sync_to_async(thread.save)(
                    update_fields=['title', 'metadata']
                )
                yield sse("title_update", {"title": generated_title})
        except Exception:
            logger.warning(
                "title_generation_failed",
                extra={"thread_id": str(thread.id)}
            )
    else:
        # Check if title should be refreshed (conversation drift)
        if not thread.title_manually_edited and thread.title not in ('', 'New Chat'):
            try:
                metadata = thread.metadata or {}
                msg_count = await sync_to_async(
                    lambda: Message.objects.filter(thread=thread, role='user').count()
                )()
                last_title_gen_at_msg = metadata.get('title_gen_at_msg_count', 0)

                if msg_count >= 10 and (msg_count - last_title_gen_at_msg) >= 8:
                    recent_msgs = await sync_to_async(list)(
                        Message.objects.filter(thread=thread)
                        .order_by('-created_at')[:6]
                    )
                    refreshed_title = await generate_thread_title([
                        {"role": m.role, "content": m.content}
                        for m in reversed(recent_msgs)
                    ])
                    if refreshed_title and refreshed_title != thread.title:
                        thread.title = refreshed_title
                        metadata['title_gen_at_msg_count'] = msg_count
                        thread.metadata = metadata
                        await sync_to_async(thread.save)(
                            update_fields=['title', 'metadata']
                        )
                        yield sse("title_update", {"title": refreshed_title})
            except Exception:
                logger.warning(
                    "title_refresh_failed",
                    extra={"thread_id": str(thread.id)}
                )


# ---------------------------------------------------------------------------
# Phase 8: Companion Await + Streaming
# ---------------------------------------------------------------------------

async def process_companion_results(state: StreamState) -> AsyncGenerator[str, None]:
    """Await companion update and yield structure/episode/research/case SSE events."""
    if state.companion_task is None:
        return

    from .companion_service import CompanionService

    try:
        structure = await state.companion_task
        if not structure:
            return

        # Serialize companion structure
        state.companion_structure_data = {
            'id': str(structure.id),
            'version': structure.version,
            'structure_type': structure.structure_type,
            'content': structure.content,
            'established': structure.established,
            'open_questions': structure.open_questions,
            'eliminated': structure.eliminated,
            'context_summary': structure.context_summary,
            'updated_at': structure.updated_at.isoformat() if structure.updated_at else None,
        }

        # Fetch current episode + recently sealed episodes in parallel
        from .models import ConversationEpisode
        from django.utils import timezone as _tz
        from datetime import timedelta as _td

        thread = state.thread
        recent_cutoff = _tz.now() - _td(seconds=10)

        async def _get_current_episode():
            await sync_to_async(thread.refresh_from_db)(fields=['current_episode_id'])
            if not thread.current_episode_id:
                return None
            return await sync_to_async(
                lambda: ConversationEpisode.objects.filter(
                    id=thread.current_episode_id,
                ).first()
            )()

        async def _get_recently_sealed():
            return await sync_to_async(list)(
                ConversationEpisode.objects.filter(
                    thread=thread,
                    sealed=True,
                    sealed_at__gte=recent_cutoff,
                ).order_by('-sealed_at')[:1]
            )

        current_ep, recently_sealed = await asyncio.gather(
            _get_current_episode(), _get_recently_sealed()
        )

        if current_ep:
            state.companion_structure_data['current_episode'] = {
                'id': str(current_ep.id),
                'episode_index': current_ep.episode_index,
                'topic_label': current_ep.topic_label,
                'sealed': current_ep.sealed,
            }
        if recently_sealed:
            sealed_ep = recently_sealed[0]
            sealed_payload = {
                'episode': {
                    'id': str(sealed_ep.id),
                    'episode_index': sealed_ep.episode_index,
                    'topic_label': sealed_ep.topic_label,
                    'content_summary': sealed_ep.content_summary,
                    'message_count': sealed_ep.message_count,
                    'shift_type': sealed_ep.shift_type,
                    'sealed': True,
                    'sealed_at': sealed_ep.sealed_at.isoformat() if sealed_ep.sealed_at else None,
                },
            }
            # Include new episode info if available
            if (thread.current_episode_id
                    and str(thread.current_episode_id) != str(sealed_ep.id)):
                new_ep = await sync_to_async(
                    lambda: ConversationEpisode.objects.filter(
                        id=thread.current_episode_id,
                    ).first()
                )()
                if new_ep:
                    sealed_payload['new_episode'] = {
                        'id': str(new_ep.id),
                        'episode_index': new_ep.episode_index,
                        'topic_label': new_ep.topic_label,
                    }
            yield sse("episode_sealed", sealed_payload)

        # Emit companion structure
        yield sse("companion_structure", {"structure": state.companion_structure_data})

        # Detect and kick off background research (fire-and-forget)
        try:
            research_needs = await CompanionService.detect_research_needs(thread.id)
            if research_needs:
                from .research_agent import run_companion_research
                asyncio.create_task(
                    run_companion_research(thread.id, research_needs)
                )
                for need in research_needs[:2]:
                    yield sse("research_started", {
                        "question": need['question'],
                        "priority": need.get('priority', 'medium'),
                    })
        except Exception as e:
            logger.debug("Research detection failed: %s", e)

        # Case signal detection (every 3 turns, only if no case linked)
        if not thread.primary_case_id:
            turns_since = thread.turns_since_agent_check
            if turns_since >= 3:
                try:
                    case_signal = await CompanionService.detect_case_signal(thread.id)
                    if case_signal:
                        yield sse("case_signal", {
                            "suggested_title": case_signal.get('title', ''),
                            "decision_question": case_signal.get('decision_question', ''),
                            "reason": case_signal.get('reason', ''),
                            "companion_state": case_signal.get('companion_state', {}),
                        })
                    thread.turns_since_agent_check = 0
                    await sync_to_async(thread.save)(
                        update_fields=['turns_since_agent_check']
                    )
                except Exception as e:
                    logger.debug("Case signal detection failed: %s", e)

    except Exception as e:
        logger.warning(
            "companion_update_failed",
            extra={"thread_id": str(state.thread.id), "error": str(e)}
        )


# ---------------------------------------------------------------------------
# Phase 9: Done Event
# ---------------------------------------------------------------------------

def build_done_event(state: StreamState) -> str:
    """Assemble and return the final 'done' SSE string."""
    done_data = {
        "message_id": state.message_id,
        "reflection_id": state.reflection_id,
        "action_hints_count": state.action_hints_count,
    }
    if state.graph_edit_summary:
        done_data["graph_edits_applied"] = state.graph_edit_summary
    if state.plan_edits_json and state.plan_edits_json.strip() not in ('', '{}'):
        done_data["has_plan_edits"] = True
    if state.companion_structure_data:
        done_data["has_companion_structure"] = True
    return sse("done", done_data)
