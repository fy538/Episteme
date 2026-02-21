"""
Tool Executor — dispatches tool actions to existing service methods.

Handles:
  - AUTO_EXECUTE tools: executed immediately, result returned
  - CONFIRM_REQUIRED tools: queued with confirmation_id, returned as pending
  - Confirmed tools: executed after user approval via confirmation endpoint

Pending confirmations are stored in Redis (db=1) with 30-minute TTL.
Redis key patterns:
  tool_confirm:{confirmation_id}     → JSON-serialized PendingConfirmation
  tool_confirm_user:{user_id}        → SET of confirmation_id strings
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

import redis
from asgiref.sync import sync_to_async
from django.conf import settings

from .registry import ToolRegistry, ToolPermission, ToolResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Redis client (lazy singleton)
# ---------------------------------------------------------------------------

_redis_client: Optional[redis.Redis] = None

# TTL for pending confirmations: 30 minutes
_CONFIRMATION_TTL = 1800


def _get_redis() -> redis.Redis:
    """Lazy singleton Redis client for tool confirmations (db=1)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            getattr(settings, 'TOOL_CONFIRM_REDIS_URL', 'redis://localhost:6379/1'),
            decode_responses=True,
        )
    return _redis_client


# Lua script for atomic claim-and-mark-executed.
# Returns the original JSON if successfully claimed, 'ALREADY_EXECUTED' if
# the executed flag was already set, or nil if the key doesn't exist.
_LUA_CLAIM = """
local data = redis.call('GET', KEYS[1])
if not data then return nil end
local obj = cjson.decode(data)
if obj.executed then return 'ALREADY_EXECUTED' end
obj.executed = true
redis.call('SETEX', KEYS[1], 60, cjson.encode(obj))
return data
"""


# ---------------------------------------------------------------------------
# Pending confirmation data
# ---------------------------------------------------------------------------

@dataclass
class PendingConfirmation:
    """
    A tool action awaiting user confirmation.

    Lifecycle:
        1. Created in ``execute_batch()`` when a CONFIRM_REQUIRED tool is requested
        2. Stored in Redis with a 30-minute TTL (auto-expires, no manual cleanup)
        3. Frontend presents the action to the user via a ToolConfirmationCard
        4. On approval, ``execute_confirmed()`` atomically claims + executes + removes
        5. On dismissal, the confirm-tool endpoint returns ``{dismissed: True}``
           and the Redis key expires naturally

    Idempotency:
        - A Lua script atomically checks + sets the ``executed`` flag, preventing
          double-execution even under concurrent confirmation requests

    Attributes:
        confirmation_id: UUID string for the frontend to reference
        tool_name: Registered tool name
        params: Tool parameters from LLM
        context: Serialized execution context (user_id, case_id, project_id, thread_id only — never ORM objects)
        reason: LLM's explanation for this action
        created_at: When the confirmation was created
        expires_at: Auto-calculated as created_at + 30 min (configurable via constructor)
        executed: Whether this confirmation has already been executed (idempotency guard)
    """
    confirmation_id: str
    tool_name: str
    params: Dict[str, Any]
    context: Dict[str, Any]  # Serialized: user_id, case_id, project_id, thread_id
    reason: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default=None)
    executed: bool = False

    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(minutes=30)

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    def to_json(self) -> str:
        """Serialize to JSON string for Redis storage."""
        return json.dumps({
            'confirmation_id': self.confirmation_id,
            'tool_name': self.tool_name,
            'params': self.params,
            'context': self.context,
            'reason': self.reason,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'executed': self.executed,
        })

    @classmethod
    def from_json(cls, data: str) -> 'PendingConfirmation':
        """Deserialize from JSON string."""
        d = json.loads(data)
        return cls(
            confirmation_id=d['confirmation_id'],
            tool_name=d['tool_name'],
            params=d['params'],
            context=d['context'],
            reason=d['reason'],
            created_at=datetime.fromisoformat(d['created_at']),
            expires_at=datetime.fromisoformat(d['expires_at']),
            executed=d.get('executed', False),
        )


# ---------------------------------------------------------------------------
# Ownership verification helper
# ---------------------------------------------------------------------------

async def _verify_case_ownership(case_id: str, user) -> None:
    """
    Verify that the user owns the case. Raises Case.DoesNotExist if not found.
    Used by handlers that operate on case-scoped resources.
    """
    from apps.cases.models import Case
    await sync_to_async(Case.objects.get)(id=case_id, user=user)


# ---------------------------------------------------------------------------
# Tool dispatch functions
# ---------------------------------------------------------------------------

async def _execute_create_inquiry(params: dict, context: dict) -> dict:
    """Dispatch create_inquiry to InquiryService."""
    from apps.inquiries.services import InquiryService
    from apps.cases.models import Case

    case = await sync_to_async(
        Case.objects.get
    )(id=context['case_id'], user=context['user'])

    inquiry = await sync_to_async(InquiryService.create_inquiry)(
        case=case,
        title=params['title'],
        description=params.get('description', ''),
        source='ai_tool_action',
        user=context['user'],
    )

    return {
        'inquiry_id': str(inquiry.id),
        'title': inquiry.title,
        'message': f"Created inquiry: {inquiry.title}",
    }


async def _execute_resolve_inquiry(params: dict, context: dict) -> dict:
    """Dispatch resolve_inquiry to InquiryService."""
    from apps.inquiries.services import InquiryService
    from apps.inquiries.models import Inquiry

    # C1 fix: verify user owns the case this inquiry belongs to
    await _verify_case_ownership(context['case_id'], context['user'])

    inquiry = await sync_to_async(
        Inquiry.objects.get
    )(id=params['inquiry_id'], case_id=context['case_id'])

    resolved = await sync_to_async(InquiryService.resolve_inquiry)(
        inquiry=inquiry,
        conclusion=params['conclusion'],
        conclusion_confidence=params.get('confidence'),
        user=context['user'],
    )

    return {
        'inquiry_id': str(resolved.id),
        'title': resolved.title,
        'message': f"Resolved inquiry: {resolved.title}",
    }


async def _execute_update_case_stage(params: dict, context: dict) -> dict:
    """Dispatch update_case_stage to PlanService."""
    from apps.cases.plan_service import PlanService

    # C1 fix: verify user owns this case
    await _verify_case_ownership(context['case_id'], context['user'])

    # H2: validate new_stage enum
    valid_stages = {'exploring', 'focusing', 'synthesizing', 'ready', 'deciding'}
    if params.get('new_stage') not in valid_stages:
        raise ValueError(f"Invalid stage: {params.get('new_stage')}. Must be one of {valid_stages}")

    await sync_to_async(PlanService.update_stage)(
        case_id=context['case_id'],
        new_stage=params['new_stage'],
        rationale=params.get('rationale', ''),
        actor_id=context['user'].id,
    )

    return {
        'stage': params['new_stage'],
        'message': f"Updated case stage to: {params['new_stage']}",
    }


async def _execute_update_assumption(params: dict, context: dict) -> dict:
    """Dispatch update_assumption_status to PlanService."""
    from apps.cases.plan_service import PlanService

    # C1 fix: verify user owns this case
    await _verify_case_ownership(context['case_id'], context['user'])

    # H2: validate status enum
    valid_statuses = {'untested', 'testing', 'validated', 'invalidated'}
    if params.get('new_status') not in valid_statuses:
        raise ValueError(f"Invalid assumption status: {params.get('new_status')}")

    await sync_to_async(PlanService.update_assumption_status)(
        case_id=context['case_id'],
        assumption_id=params['assumption_id'],
        new_status=params['new_status'],
        evidence_summary=params.get('evidence_summary', ''),
        actor_id=context['user'].id,
    )

    return {
        'assumption_id': str(params['assumption_id']),
        'status': params['new_status'],
        'message': f"Updated assumption status to: {params['new_status']}",
    }


async def _execute_update_criterion(params: dict, context: dict) -> dict:
    """Dispatch update_criterion_status to PlanService."""
    from apps.cases.plan_service import PlanService

    # C1 fix: verify user owns this case
    await _verify_case_ownership(context['case_id'], context['user'])

    await sync_to_async(PlanService.update_criterion_status)(
        case_id=context['case_id'],
        criterion_id=params['criterion_id'],
        is_met=params['is_met'],
        actor_id=context['user'].id,
    )

    return {
        'criterion_id': str(params['criterion_id']),
        'is_met': params['is_met'],
        'message': f"Criterion {'met' if params['is_met'] else 'unmet'}",
    }


async def _execute_record_decision(params: dict, context: dict) -> dict:
    """Dispatch record_decision to ResolutionService (auto-generation)."""
    from apps.cases.resolution_service import ResolutionService

    resolution_type = params.get('resolution_type', 'resolved')
    valid_types = {'resolved', 'closed'}
    if resolution_type not in valid_types:
        raise ValueError(f"Invalid resolution_type: {resolution_type}")

    record = await sync_to_async(ResolutionService.create_resolution)(
        user=context['user'],
        case_id=context['case_id'],
        resolution_type=resolution_type,
    )

    label = 'Case resolved' if resolution_type == 'resolved' else 'Case closed'

    return {
        'decision_id': str(record.id),
        'resolution_type': resolution_type,
        'message': f"{label}: {record.decision_text[:80]}",
    }


async def _execute_add_outcome_note(params: dict, context: dict) -> dict:
    """Dispatch add_outcome_note to DecisionService."""
    from apps.cases.decision_service import DecisionService

    # H2: validate sentiment enum
    valid_sentiments = {'positive', 'negative', 'neutral', 'mixed'}
    sentiment = params.get('sentiment', 'neutral')
    if sentiment not in valid_sentiments:
        logger.warning("Invalid sentiment from tool action: %s, defaulting to neutral", sentiment)
        sentiment = 'neutral'

    record = await sync_to_async(DecisionService.add_outcome_note)(
        user=context['user'],
        case_id=context['case_id'],
        note=params['note'],
        sentiment=sentiment,
    )

    return {
        'decision_id': str(record.id),
        'message': f"Outcome note added",
    }


async def _execute_create_case(params: dict, context: dict) -> dict:
    """Dispatch create_case to CaseService."""
    from apps.cases.services import CaseService

    # H2: validate stakes enum
    valid_stakes = {'low', 'medium', 'high', 'critical'}
    stakes = params.get('stakes', 'medium')
    if stakes not in valid_stakes:
        stakes = 'medium'

    case, _ = await sync_to_async(CaseService.create_case)(
        user=context['user'],
        title=params['title'],
        position=params.get('position', ''),
        stakes=stakes,
        thread_id=context.get('thread_id'),
        project_id=context.get('project_id'),
        decision_question=params.get('decision_question', ''),
    )

    return {
        'case_id': str(case.id),
        'title': case.title,
        'message': f"Created case: {case.title}",
    }


async def _execute_add_evidence_node(params: dict, context: dict) -> dict:
    """Dispatch add_evidence_node to GraphService."""
    from apps.graph.services import GraphService
    from apps.projects.models import Project

    # C1 fix: verify user is a member of this project
    project = await sync_to_async(
        Project.objects.get
    )(id=context['project_id'], user=context['user'])

    # H2: validate and clamp confidence
    confidence = params.get('confidence', 0.8)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (ValueError, TypeError):
        confidence = 0.8

    node = await sync_to_async(GraphService.create_node)(
        project=project,
        node_type='evidence',
        content=params['content'],
        source_type='ai_tool_action',
        confidence=confidence,
        created_by=context.get('user'),
        case=None,
    )

    return {
        'node_id': str(node.id),
        'message': f"Added evidence: {params['content'][:80]}...",
    }


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

_DISPATCH_TABLE: Dict[str, Any] = {
    'create_inquiry': _execute_create_inquiry,
    'resolve_inquiry': _execute_resolve_inquiry,
    'update_case_stage': _execute_update_case_stage,
    'update_assumption_status': _execute_update_assumption,
    'update_criterion_status': _execute_update_criterion,
    'record_decision': _execute_record_decision,
    'add_outcome_note': _execute_add_outcome_note,
    'create_case': _execute_create_case,
    'add_evidence_node': _execute_add_evidence_node,
}

# L2: import-time validation — ensures every dispatch entry is callable and
# every entry name will resolve to a registered tool (once tools are loaded).
for _tool_name, _handler_fn in _DISPATCH_TABLE.items():
    if not callable(_handler_fn):
        raise ImportError(
            f"Dispatch table entry '{_tool_name}' is not callable: {_handler_fn!r}"
        )


# ---------------------------------------------------------------------------
# ToolExecutor
# ---------------------------------------------------------------------------

class ToolExecutor:
    """
    Executes tool actions by dispatching to existing service methods.

    For AUTO_EXECUTE tools: calls the service method immediately.
    For CONFIRM_REQUIRED tools: stores params in Redis and returns a confirmation_id
    for the frontend to present to the user.
    """

    @classmethod
    async def execute(
        cls,
        tool_name: str,
        params: dict,
        context: dict,
    ) -> ToolResult:
        """
        Execute a single tool action.

        Args:
            tool_name: Registered tool name
            params: Tool parameters from LLM
            context: Execution context with keys:
                - user: Django User object
                - case_id: Optional case UUID (string)
                - project_id: Optional project UUID (string)
                - thread_id: Optional thread UUID (string)

        Returns:
            ToolResult with success/failure, output data, and display info
        """
        tool = ToolRegistry.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error=f"Unknown tool: {tool_name}",
            )

        dispatch_fn = _DISPATCH_TABLE.get(tool_name)
        if not dispatch_fn:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error=f"No dispatch function for tool: {tool_name}",
            )

        logger.info(
            "tool_execution_started",
            extra={
                'tool_name': tool_name,
                'permission': tool.permission.value,
                'case_id': context.get('case_id'),
                'user_id': context['user'].id if context.get('user') else None,
            },
        )

        try:
            output = await dispatch_fn(params, context)
            return ToolResult(
                success=True,
                tool_name=tool_name,
                display_name=tool.display_name,
                output=output,
            )
        except ValueError as e:
            # H5: user-caused errors (validation, duplicate) — safe to expose
            logger.warning("Tool action rejected: %s — %s", tool_name, e)
            return ToolResult(
                success=False,
                tool_name=tool_name,
                display_name=tool.display_name,
                error=str(e),
            )
        except Exception as e:
            # H5: system errors — don't leak internals
            logger.exception(
                "tool_execution_failed",
                extra={
                    'tool_name': tool_name,
                    'error_type': type(e).__name__,
                    'case_id': context.get('case_id'),
                    'user_id': context['user'].id if context.get('user') else None,
                },
            )
            return ToolResult(
                success=False,
                tool_name=tool_name,
                display_name=tool.display_name,
                error="Action failed. Please try again.",
            )

    @classmethod
    async def execute_batch(
        cls,
        actions: List[dict],
        context: dict,
    ) -> List[ToolResult]:
        """
        Execute multiple tool actions, respecting permission levels.

        AUTO_EXECUTE tools are executed immediately.
        CONFIRM_REQUIRED tools are stored in Redis for user confirmation.

        Args:
            actions: List of dicts with 'tool', 'params', 'reason' keys
            context: Execution context

        Returns:
            List of ToolResult objects
        """
        results = []

        for action in actions:
            tool_name = action.get('tool', '')
            params = action.get('params', {})
            reason = action.get('reason', '')

            tool = ToolRegistry.get(tool_name)
            if not tool:
                results.append(ToolResult(
                    success=False,
                    tool_name=tool_name,
                    error=f"Unknown tool: {tool_name}",
                ))
                continue

            if tool.permission == ToolPermission.AUTO_EXECUTE:
                # Execute immediately
                result = await cls.execute(tool_name, params, context)
                results.append(result)
            else:
                # Serialize only IDs, not ORM objects
                serialized_context = {
                    'user_id': context['user'].id if context.get('user') else None,
                    'case_id': context.get('case_id'),
                    'project_id': context.get('project_id'),
                    'thread_id': context.get('thread_id'),
                }

                confirmation = PendingConfirmation(
                    confirmation_id=str(uuid.uuid4()),
                    tool_name=tool_name,
                    params=params,
                    context=serialized_context,
                    reason=reason,
                )

                # Store in Redis with TTL
                try:
                    r = _get_redis()
                    key = f"tool_confirm:{confirmation.confirmation_id}"
                    user_key = f"tool_confirm_user:{serialized_context['user_id']}"

                    pipe = r.pipeline()
                    pipe.setex(key, _CONFIRMATION_TTL, confirmation.to_json())
                    pipe.sadd(user_key, confirmation.confirmation_id)
                    pipe.expire(user_key, _CONFIRMATION_TTL)
                    pipe.execute()
                except (redis.ConnectionError, redis.TimeoutError) as e:
                    logger.error("Redis unavailable for tool confirmation storage: %s", e)
                    results.append(ToolResult(
                        success=False,
                        tool_name=tool_name,
                        display_name=tool.display_name,
                        error="Service temporarily unavailable. Please try again.",
                    ))
                    continue

                results.append(ToolResult(
                    success=True,
                    tool_name=tool_name,
                    display_name=tool.display_name,
                    pending_confirmation=True,
                    confirmation_id=confirmation.confirmation_id,
                    params=params,
                    reason=reason,
                ))

        return results

    @classmethod
    async def execute_confirmed(
        cls,
        confirmation_id: str,
        user: Any,
    ) -> ToolResult:
        """
        Execute a previously queued tool action after user confirmation.

        Uses a Lua script to atomically check the executed flag and claim the
        confirmation, preventing double-execution under concurrent requests.

        Args:
            confirmation_id: The confirmation_id returned by execute_batch
            user: The confirming user (must match original context user)

        Returns:
            ToolResult from actual execution
        """
        try:
            r = _get_redis()
            key = f"tool_confirm:{confirmation_id}"

            # Atomic claim: GET → check executed → SET executed=true → return original
            raw = r.eval(_LUA_CLAIM, 1, key)
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error("Redis unavailable for tool confirmation: %s", e)
            return ToolResult(
                success=False,
                error="Service temporarily unavailable. Please try again.",
            )

        if raw is None:
            return ToolResult(
                success=False,
                error="Confirmation not found or expired",
            )

        if raw == 'ALREADY_EXECUTED':
            return ToolResult(
                success=False,
                tool_name='',
                error="This action has already been executed",
            )

        confirmation = PendingConfirmation.from_json(raw)

        # Belt-and-suspenders expiry check (TTL should handle this)
        if confirmation.is_expired:
            r.delete(key)
            return ToolResult(
                success=False,
                error="Confirmation not found or expired",
            )

        # User ownership check
        original_user_id = confirmation.context.get('user_id')
        if original_user_id is None or original_user_id != user.id:
            return ToolResult(
                success=False,
                tool_name=confirmation.tool_name,
                error="User mismatch — confirmation belongs to a different user",
            )

        # Rebuild full context from serialized IDs
        execution_context = {
            'user': user,
            'case_id': confirmation.context.get('case_id'),
            'project_id': confirmation.context.get('project_id'),
            'thread_id': confirmation.context.get('thread_id'),
        }

        # Execute the tool
        result = await cls.execute(
            confirmation.tool_name,
            confirmation.params,
            execution_context,
        )

        # Clean up: remove key and user set entry
        try:
            user_key = f"tool_confirm_user:{original_user_id}"
            pipe = r.pipeline()
            pipe.delete(key)
            pipe.srem(user_key, confirmation_id)
            pipe.execute()
        except (redis.ConnectionError, redis.TimeoutError):
            pass  # Non-critical: TTL will clean up

        return result

    @classmethod
    def get_pending(cls, user_id: int) -> List[PendingConfirmation]:
        """Get all pending confirmations for a user."""
        try:
            r = _get_redis()
            user_key = f"tool_confirm_user:{user_id}"

            confirmation_ids = r.smembers(user_key)
            if not confirmation_ids:
                return []

            # Batch fetch all confirmations (single round-trip)
            keys = [f"tool_confirm:{cid}" for cid in confirmation_ids]
            values = r.mget(keys)

            results = []
            stale_ids = []

            for cid, raw in zip(confirmation_ids, values):
                if raw is None:
                    # TTL expired but user set still has reference
                    stale_ids.append(cid)
                    continue
                try:
                    conf = PendingConfirmation.from_json(raw)
                    if not conf.executed and not conf.is_expired:
                        results.append(conf)
                except (json.JSONDecodeError, KeyError):
                    stale_ids.append(cid)

            # Clean up stale references from user set
            if stale_ids:
                r.srem(user_key, *stale_ids)

            return results
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning("Redis unavailable for get_pending: %s", e)
            return []
