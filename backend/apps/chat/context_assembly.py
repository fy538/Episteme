"""
Context Assembly Service

Centralizes all context loading for LLM calls in Episteme.
Replaces the scattered context assembly in views.py unified_stream(),
services.py generate_assistant_response(), and orchestrator.py run_agent_in_chat().

Three entry points:
  - assemble()             — main path (unified_stream)
  - assemble_for_agent()   — agent orchestrator path
  - assemble_for_sync_chat() — sync ChatService path

The downstream interface (UnifiedAnalysisEngine.analyze_simple) is unchanged.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AssembledContext:
    """
    Everything the engine needs to make an LLM call.
    Produced by ContextAssemblyService.
    """
    # Strings that feed directly into analyze_simple()
    conversation_context: str = ""
    system_prompt_override: Optional[str] = None
    retrieval_context: str = ""

    # Retrieval metadata for post-stream citation tracking
    retrieval_result: Any = None  # RetrievalResult | None

    # Post-stream merge data — views.py needs these for diff merging
    current_plan_content: Optional[Dict] = None
    current_orientation_id: Optional[str] = None

    # Tool actions — available tools for this context
    available_tools: List[Any] = field(default_factory=list)

    # Observability
    mode_resolved: str = "default"
    context_sources: List[str] = field(default_factory=list)


@dataclass
class ModeContext:
    """
    Parsed mode_context from the frontend request body.
    Centralizes the scattered dict-key lookups.
    """
    mode: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    case_id: Optional[str] = None
    inquiry_id: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> ModeContext:
        return cls(
            mode=d.get('mode'),
            source_type=d.get('source_type'),
            source_id=d.get('source_id'),
            case_id=d.get('caseId'),
            inquiry_id=d.get('inquiryId'),
        )


@dataclass
class TokenBudget:
    """
    Token allocation budget for context assembly.

    Each source gets a maximum allocation. Sources that use fewer tokens
    than allocated release their surplus to retrieval (the most elastic source).

    Priority order (highest → lowest):
        conversation → companion → mode prompt → retrieval (gets surplus)
    """
    total: int = 14_000
    system_prompt: int = 4_000
    conversation: int = 4_000
    retrieval: int = 3_000
    companion: int = 1_000
    reserved: int = 2_000  # safety margin for framing text + user message
    used: Dict[str, int] = field(default_factory=dict)

    @property
    def surplus(self) -> int:
        """Tokens not yet consumed by any source (excluding reserved)."""
        return max(0, self.total - sum(self.used.values()) - self.reserved)

    def effective_retrieval_budget(self) -> int:
        """Retrieval budget = base allocation + surplus from other sources."""
        other_used = sum(v for k, v in self.used.items() if k != 'retrieval')
        other_budgets = self.conversation + self.companion + self.system_prompt
        freed = max(0, other_budgets - other_used)
        return self.retrieval + freed


# Per-mode budget presets.
# Modes that need larger system prompts borrow from conversation & retrieval.
MODE_BUDGETS: Dict[str, TokenBudget] = {
    'default':     TokenBudget(),
    'case':        TokenBudget(system_prompt=5000, conversation=3500, retrieval=3000, companion=500),
    'graph':       TokenBudget(system_prompt=6000, conversation=3000, retrieval=2000, companion=1000),
    'orientation': TokenBudget(system_prompt=5000, conversation=3500, retrieval=2500, companion=1000),
    'scaffolding': TokenBudget(system_prompt=5000, conversation=3500, retrieval=3000, companion=500),
}


def _count_tokens(text: str) -> int:
    """Count tokens, with fast fallback if tiktoken is unavailable."""
    if not text:
        return 0
    try:
        from apps.common.token_utils import count_tokens
        return count_tokens(text)
    except Exception:
        # Fallback: ~4 chars per token
        return len(text) // 4


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to fit within a token budget."""
    if not text or max_tokens <= 0:
        return ""
    try:
        from apps.common.token_utils import split_text_to_fit_tokens
        return split_text_to_fit_tokens(text, max_tokens)
    except Exception:
        # Fallback: rough char-based truncation
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        return text[:max_chars]


# ---------------------------------------------------------------------------
# Helper: resolve theme labels (moved from views.py line 45)
# ---------------------------------------------------------------------------

def _resolve_theme_labels(tree: dict, cluster_ids: list) -> list[str]:
    """Walk a hierarchy tree to resolve cluster IDs to human-readable theme labels."""
    labels = []
    id_set = set(str(cid) for cid in cluster_ids)

    for child in (tree.get('children') or []):
        cid = str(child.get('id', ''))
        if cid in id_set and child.get('label'):
            labels.append(child['label'])
        for grandchild in (child.get('children') or []):
            gcid = str(grandchild.get('id', ''))
            if gcid in id_set and grandchild.get('label'):
                labels.append(grandchild['label'])

    return labels


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ContextAssemblyService:
    """
    Assembles all context for an LLM call: conversation history,
    companion state, RAG retrieval, and mode-specific system prompts.
    """

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    async def assemble(
        self,
        thread,
        user_message: str,
        mode_context: dict,
        user,
    ) -> AssembledContext:
        """
        Main entry point for unified_stream().
        Replaces views.py lines 615-963.

        Token budget flow:
            1. Load all sources (conversation, companion, retrieval, mode prompt)
            2. Count tokens for each
            3. Truncate higher-priority sources to their budget
            4. Flow surplus from under-budget sources into retrieval
            5. Track usage for observability
        """
        ctx = AssembledContext()
        mc = ModeContext.from_dict(mode_context)

        # Select token budget for this mode
        mode_key = mc.mode or mc.source_type or 'default'
        budget = MODE_BUDGETS.get(mode_key, MODE_BUDGETS['default'])
        # Make a copy so we don't mutate the preset
        budget = TokenBudget(
            total=budget.total,
            system_prompt=budget.system_prompt,
            conversation=budget.conversation,
            retrieval=budget.retrieval,
            companion=budget.companion,
            reserved=budget.reserved,
        )

        # Intent classification — adjust budget if no mode override
        intent_result = None
        if not mc.mode and not mc.source_type:
            try:
                from .intent_router import IntentRouter, INTENT_BUDGET_ADJUSTMENTS
                intent_result = IntentRouter().classify(user_message)
                if intent_result.confidence >= 0.5:
                    adjustments = INTENT_BUDGET_ADJUSTMENTS.get(
                        intent_result.category, {}
                    )
                    for key, delta in adjustments.items():
                        current = getattr(budget, key, 0)
                        setattr(budget, key, max(0, current + delta))
                    ctx.context_sources.append(
                        f"intent:{intent_result.category.value}"
                        f"({intent_result.confidence:.2f})"
                    )
            except Exception as e:
                logger.debug(f"Intent classification skipped: {e}")

        # --- 1. Conversation history ---
        raw_conversation = await self._build_conversation_context(thread)
        ctx.conversation_context = _truncate_to_tokens(raw_conversation, budget.conversation)
        budget.used['conversation'] = _count_tokens(ctx.conversation_context)
        ctx.context_sources.append("conversation")

        # --- 2. Companion context ---
        raw_companion = await self._load_companion_context(thread.id)
        companion_context = _truncate_to_tokens(raw_companion, budget.companion)
        budget.used['companion'] = _count_tokens(companion_context)

        # --- 3. RAG retrieval ---
        ctx.retrieval_result, raw_retrieval = await self._retrieve_documents(
            thread, user_message, user
        )
        # Retrieval gets its base budget + surplus from under-budget sources
        effective_retrieval = budget.effective_retrieval_budget()
        ctx.retrieval_context = _truncate_to_tokens(raw_retrieval, effective_retrieval)
        budget.used['retrieval'] = _count_tokens(ctx.retrieval_context)
        if ctx.retrieval_context:
            ctx.context_sources.append("rag")

        # --- 3b. Related entity retrieval (cross-case decisions, insights) ---
        # Only fire for analytical/cross-reference intents to avoid noise
        _entity_intents = {'retrieval_analytical', 'cross_reference', 'meta_process'}
        if (
            intent_result
            and intent_result.confidence >= 0.5
            and intent_result.category.value in _entity_intents
            and thread.project_id
        ):
            entity_context = await self._retrieve_related_entities(
                user_message=user_message,
                project_id=thread.project_id,
                current_case_id=getattr(thread, 'primary_case_id', None),
            )
            if entity_context:
                entity_tokens = _count_tokens(entity_context)
                # Use remaining retrieval surplus for entity context
                remaining_retrieval = max(0, effective_retrieval - budget.used.get('retrieval', 0))
                entity_budget = min(entity_tokens, remaining_retrieval, 500)
                entity_context = _truncate_to_tokens(entity_context, entity_budget)
                if entity_context:
                    ctx.retrieval_context = (
                        f"{ctx.retrieval_context}\n\n{entity_context}"
                        if ctx.retrieval_context else entity_context
                    )
                    budget.used['retrieval'] = _count_tokens(ctx.retrieval_context)
                    ctx.context_sources.append("entities")

        # --- 3c. Past reasoning retrieval (cross-conversation episodes) ---
        try:
            past_reasoning = await self._retrieve_past_reasoning(
                user_message=user_message,
                thread=thread,
                user=user,
                budget=min(500, max(0, budget.effective_retrieval_budget() - budget.used.get('retrieval', 0))),
            )
            if past_reasoning:
                ctx.retrieval_context = (
                    f"{ctx.retrieval_context}\n\n{past_reasoning}"
                    if ctx.retrieval_context else past_reasoning
                )
                budget.used['retrieval'] = _count_tokens(ctx.retrieval_context)
                ctx.context_sources.append("past_reasoning")
        except Exception as e:
            logger.debug(f"Past reasoning retrieval skipped: {e}")

        # --- 3d. Resolve available tools ---
        # Tools are injected into system prompts when the conversation context
        # makes them useful. Gate on: (a) intent category, (b) mode, (c) depth.
        try:
            from apps.intelligence.tools.registry import ToolRegistry
            from .models import Message as ChatMessage

            _tool_context = {}
            if thread.project_id:
                _tool_context['project_id'] = str(thread.project_id)
            _case_id = mc.case_id or (
                str(thread.primary_case_id) if thread.primary_case_id else None
            )
            if _case_id:
                _tool_context['case_id'] = _case_id

            # Gate 1: Intent-based activation — only inject tools for intents
            # where actions are likely useful (skip factual lookups, greetings)
            _TOOL_ACTIVE_INTENTS = {
                'retrieval_analytical',
                'cross_reference',
                'meta_process',
            }
            _intent_allows_tools = True
            if (
                intent_result
                and intent_result.confidence >= 0.5
                and intent_result.category.value not in _TOOL_ACTIVE_INTENTS
            ):
                _intent_allows_tools = False

            # Gate 2: Mode-based activation — always allow tools in explicit
            # case mode (the primary use case); skip in graph/orientation modes
            _mode_allows_tools = True
            if mc.mode in ('graph', 'orientation', 'scaffolding'):
                _mode_allows_tools = False

            # Gate 3: Conversation depth — skip tools on first message
            # (let the conversation warm up before offering actions)
            # H1: use annotated _message_count from thread fetch if available,
            # otherwise fall back to a count query
            _msg_count = getattr(thread, '_message_count', None)
            if _msg_count is None:
                _msg_count = await sync_to_async(
                    ChatMessage.objects.filter(thread=thread).count
                )()
            _depth_allows_tools = _msg_count >= 2

            # Explicit case mode bypasses intent and depth gates
            _is_case_mode = mc.mode == 'case' and _case_id

            if _is_case_mode or (_intent_allows_tools and _mode_allows_tools and _depth_allows_tools):
                ctx.available_tools = ToolRegistry.get_available(_tool_context)
            else:
                ctx.available_tools = []

        except Exception as e:
            logger.debug(f"Tool resolution skipped: {e}")

        # --- 4. Mode-specific system prompt ---
        system_prompt, plan_content, orientation_id = await self._resolve_mode(
            thread, mc, available_tools=ctx.available_tools,
        )
        if system_prompt:
            system_prompt = _truncate_to_tokens(system_prompt, budget.system_prompt)
            budget.used['system_prompt'] = _count_tokens(system_prompt)
        ctx.system_prompt_override = system_prompt
        ctx.current_plan_content = plan_content
        ctx.current_orientation_id = orientation_id
        ctx.mode_resolved = mode_key
        if ctx.system_prompt_override:
            ctx.context_sources.append(f"mode:{ctx.mode_resolved}")
        if ctx.available_tools:
            ctx.context_sources.append(f"tools:{len(ctx.available_tools)}")

        # --- 5. Inject companion into conversation context (the clarifying loop) ---
        if companion_context:
            # Check for decision readiness nudge from companion metadata
            readiness_nudge = ""
            latest_structure = None
            try:
                from .models import ConversationStructure
                latest_structure = await sync_to_async(
                    lambda: ConversationStructure.objects.filter(
                        thread=thread
                    ).order_by('-version').first()
                )()
                if latest_structure:
                    readiness = (latest_structure.metadata or {}).get('decision_readiness', {})
                    if readiness.get('ready'):
                        established = latest_structure.established or []
                        top_facts = '; '.join(str(f) for f in established[:3])
                        readiness_nudge = (
                            f"\nCOMPANION NOTE: The conversation appears ready for a decision. "
                            f"Key established facts: {top_facts}. "
                            f"Consider asking if the user is ready to decide.\n"
                        )
                        ctx.context_sources.append("decision_readiness")
            except Exception as e:
                logger.debug(f"Decision readiness check skipped: {e}")

            # --- 5a. Challenge context (case-aware) ---
            challenge_context = ""
            _challenge_case_id = mc.case_id or (
                str(thread.primary_case_id) if thread.primary_case_id else None
            )
            if _challenge_case_id:
                try:
                    from .challenge_service import ChallengeContextService
                    _open_questions = (
                        latest_structure.open_questions
                        if latest_structure else None
                    )
                    challenge_context = await sync_to_async(
                        ChallengeContextService.get_challenge_context
                    )(_challenge_case_id, open_questions=_open_questions)
                    if challenge_context:
                        ctx.context_sources.append("challenge")
                except Exception as e:
                    logger.debug(f"Challenge context skipped: {e}")

            ctx.conversation_context = (
                f"CONVERSATION STATE (tracked by companion):\n{companion_context}\n"
                f"{readiness_nudge}\n"
                f"{challenge_context}\n"
                f"IMPORTANT: Do NOT suggest eliminated options. "
                f"Do NOT ask about established facts.\n\n"
                f"{ctx.conversation_context}"
            )
            ctx.context_sources.append("companion")

        # --- 5b. Pending outcome reviews (project-wide, default mode only) ---
        if not mc.mode and not mc.source_type and thread.project_id and user:
            try:
                from apps.cases.outcome_service import OutcomeReviewService
                pending = await sync_to_async(
                    OutcomeReviewService.get_pending_reviews
                )(user, project_id=thread.project_id, limit=3)
                if pending:
                    titles = ', '.join(
                        f'"{r["case_title"]}"' for r in pending[:3]
                    )
                    review_note = (
                        f"\nPENDING REVIEWS: You have {len(pending)} decision(s) "
                        f"due for outcome review: {titles}. "
                        f"Consider mentioning these if relevant to the conversation.\n"
                    )
                    ctx.conversation_context = (
                        f"{ctx.conversation_context}\n{review_note}"
                    )
                    ctx.context_sources.append("pending_reviews")
            except Exception as e:
                logger.debug(f"Pending reviews check skipped: {e}")

        # --- 6. Budget observability ---
        total_used = sum(budget.used.values())
        budget_summary = ",".join(f"{k}={v}" for k, v in sorted(budget.used.items()))
        ctx.context_sources.append(f"budget:total={total_used}({budget_summary})")

        return ctx

    async def assemble_for_agent(
        self,
        thread,
        case,
    ) -> AssembledContext:
        """
        Entry point for AgentOrchestrator.run_agent_in_chat().
        Provides graph context for agents.
        """
        ctx = AssembledContext()

        try:
            from apps.graph.serialization import GraphSerializationService
            project_id = await sync_to_async(lambda: case.project_id)()
            graph_context, _ = await sync_to_async(
                GraphSerializationService.serialize_for_llm
            )(project_id, case_id=case.id)
            if graph_context and 'No knowledge graph nodes yet' not in graph_context:
                ctx.retrieval_context = graph_context
                ctx.context_sources.append("graph")
        except Exception as e:
            logger.debug(f"Agent graph context skipped: {e}")

        return ctx

    async def assemble_for_sync_chat(
        self,
        thread,
        user_message_content: str,
    ) -> tuple:
        """
        Entry point for ChatService.generate_assistant_response().
        Returns (conversation_context, project_summary_context, companion_context)
        matching the existing get_assistant_response_prompt() interface.

        Note: kept as a tuple return to minimize changes to the sync path.
        """
        # Conversation history (sync path uses 5 messages, truncated to 400 chars)
        conversation_context = await self._build_conversation_context(
            thread, limit=6, truncate_chars=400, use_last_n=5,
        )

        # Project summary
        project_summary_context = ""
        if thread.project_id:
            project_summary_context = await self._load_project_summary(thread.project_id)

        # Companion context
        companion_context = await self._load_companion_context(thread.id)

        return conversation_context, project_summary_context, companion_context

    # ------------------------------------------------------------------
    # Conversation history
    # ------------------------------------------------------------------

    async def _build_conversation_context(
        self,
        thread,
        limit: int = 10,
        truncate_chars: Optional[int] = None,
        use_last_n: Optional[int] = None,
        include_digest: bool = True,
    ) -> str:
        """
        Fetch recent messages and format as conversation context.

        Three tiers of memory:
            Tier 1 (verbatim): Last N messages, full content
            Tier 2 (digest):   ConversationStructure.rolling_digest
            Tier 3 (companion): ConversationStructure.context_summary (injected separately)

        Args:
            thread: ChatThread instance
            limit: How many messages to fetch from DB
            truncate_chars: If set, truncate each message to this many chars
            use_last_n: If set, only use the last N of the fetched messages
            include_digest: If True, prepend rolling digest from companion
        """
        from .models import Message

        messages = await sync_to_async(list)(
            Message.objects.filter(thread=thread)
            .order_by('-created_at')[:limit]
        )

        # Reverse to chronological order
        messages = list(reversed(messages))

        # Optionally take only last N
        if use_last_n and len(messages) > use_last_n:
            messages = messages[-use_last_n:]

        parts = []
        for m in messages:
            content = m.content
            if truncate_chars and len(content) > truncate_chars:
                content = content[:truncate_chars] + "..."
            parts.append(f"{m.role.upper()}: {content}")

        tier1 = "\n\n".join(parts)

        # Tier 2: rolling digest from ConversationStructure
        if include_digest:
            try:
                from .models import ConversationStructure
                structure = await sync_to_async(
                    lambda: ConversationStructure.objects.filter(
                        thread=thread
                    ).order_by('-version').first()
                )()
                if structure and structure.rolling_digest:
                    return (
                        f"EARLIER CONVERSATION CONTEXT:\n"
                        f"{structure.rolling_digest}\n\n"
                        f"{tier1}"
                    )
            except Exception as e:
                logger.debug(f"Could not load rolling digest: {e}")

        return tier1

    # ------------------------------------------------------------------
    # Companion context
    # ------------------------------------------------------------------

    async def _load_companion_context(self, thread_id: uuid.UUID) -> str:
        """Load companion context_summary for the clarifying loop."""
        try:
            from .companion_service import CompanionService
            return await CompanionService.get_chat_context_async(thread_id)
        except Exception as e:
            logger.debug(f"Could not load companion context: {e}")
            return ""

    # ------------------------------------------------------------------
    # RAG retrieval
    # ------------------------------------------------------------------

    async def _retrieve_documents(
        self,
        thread,
        user_message: str,
        user,
    ) -> Tuple[Any, str]:
        """
        Run RAG retrieval if thread has a project.

        Returns:
            (RetrievalResult | None, context_text: str)
        """
        if not thread.project_id:
            return None, ""
        try:
            from .retrieval import retrieve_document_context
            result = await sync_to_async(retrieve_document_context)(
                query=user_message,
                project_id=thread.project_id,
                case_id=getattr(thread, 'primary_case_id', None),
                user=user,
            )
            return result, (result.context_text if result else "")
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")
            return None, ""

    # ------------------------------------------------------------------
    # Project summary (for sync chat path)
    # ------------------------------------------------------------------

    async def _load_project_summary(self, project_id) -> str:
        """Load project summary for sync chat path."""
        try:
            from apps.graph.summary_service import ProjectSummaryService
            from .prompts import format_summary_for_chat

            summary = await sync_to_async(
                ProjectSummaryService.get_current_summary
            )(project_id)
            if summary and summary.sections:
                return format_summary_for_chat(summary.sections)
        except Exception:
            logger.debug("Could not load project summary for chat context", exc_info=True)
        return ""

    # ------------------------------------------------------------------
    # Related entity retrieval (Cases, Decisions, Insights)
    # ------------------------------------------------------------------

    async def _retrieve_related_entities(
        self,
        user_message: str,
        project_id,
        current_case_id=None,
        max_per_model: int = 3,
        threshold: float = 0.5,
    ) -> str:
        """
        Semantic search across Cases, DecisionRecords, and ProjectInsights.

        Called after document retrieval when intent suggests analytical or
        cross-reference needs. Returns formatted context or empty string.

        Args:
            user_message: The user's query text
            project_id: Scope to this project
            current_case_id: Exclude this case from results (avoid self-reference)
            max_per_model: Max results per model type
            threshold: Minimum cosine similarity

        Returns:
            Formatted context string or empty string
        """
        if not project_id:
            return ""

        try:
            from apps.common.vector_utils import generate_embedding, similarity_search

            query_vector = await sync_to_async(generate_embedding)(user_message)
            if not query_vector:
                return ""

            parts = []

            # --- Past decisions from other cases ---
            try:
                from apps.cases.models import DecisionRecord, CaseStatus

                decision_qs = DecisionRecord.objects.filter(
                    case__project_id=project_id,
                    case__status=CaseStatus.DECIDED,
                ).select_related('case')

                if current_case_id:
                    decision_qs = decision_qs.exclude(case_id=current_case_id)

                decisions = await sync_to_async(list)(
                    similarity_search(
                        queryset=decision_qs,
                        embedding_field='embedding',
                        query_vector=query_vector,
                        threshold=threshold,
                        top_k=max_per_model,
                    )
                )

                for d in decisions[:2]:  # Max 2 past decisions
                    case_title = d.case.title[:60] if d.case else 'Unknown'
                    decided_at = d.decided_at.strftime('%Y-%m-%d') if d.decided_at else '?'
                    reasons = ', '.join(d.key_reasons[:3]) if d.key_reasons else ''

                    resolution_label = getattr(d, 'resolution_type', 'resolved') or 'resolved'
                    entry = (
                        f'[Past {resolution_label.replace("_", " ").title()}] Case "{case_title}" '
                        f'(resolved {decided_at}):\n'
                        f'  Position: {d.decision_text[:200]}\n'
                    )
                    if getattr(d, 'resolution_profile', ''):
                        entry += f'  Profile: {d.resolution_profile[:200]}\n'
                    if reasons:
                        entry += f'  Key reasons: {reasons}\n'
                    if d.outcome_notes:
                        latest = d.outcome_notes[-1]
                        entry += (
                            f'  Latest outcome ({latest.get("sentiment", "neutral")}, '
                            f'{latest.get("date", "?")[:10]}): '
                            f'{latest.get("note", "")[:150]}\n'
                        )
                    parts.append(entry)

            except Exception as e:
                logger.debug(f"Decision entity search failed: {e}")

            # --- Related cases ---
            try:
                from apps.cases.models import Case

                case_qs = Case.objects.filter(
                    project_id=project_id,
                ).only('id', 'title', 'position', 'status', 'embedding')

                if current_case_id:
                    case_qs = case_qs.exclude(id=current_case_id)

                cases = await sync_to_async(list)(
                    similarity_search(
                        queryset=case_qs,
                        embedding_field='embedding',
                        query_vector=query_vector,
                        threshold=threshold,
                        top_k=max_per_model,
                    )
                )

                for c in cases[:2]:
                    parts.append(
                        f'[Related Case] "{c.title[:60]}" ({c.status}):\n'
                        f'  Position: {(c.position or "No position yet")[:200]}\n'
                    )

            except Exception as e:
                logger.debug(f"Case entity search failed: {e}")

            # --- Project insights ---
            try:
                from apps.graph.models import ProjectInsight, InsightStatus

                insight_qs = ProjectInsight.objects.filter(
                    project_id=project_id,
                ).exclude(
                    status=InsightStatus.DISMISSED,
                ).only('id', 'title', 'content', 'insight_type', 'embedding')

                insights = await sync_to_async(list)(
                    similarity_search(
                        queryset=insight_qs,
                        embedding_field='embedding',
                        query_vector=query_vector,
                        threshold=threshold,
                        top_k=max_per_model,
                    )
                )

                for ins in insights[:2]:
                    parts.append(
                        f'[Insight ({ins.insight_type})] {ins.title}:\n'
                        f'  {ins.content[:250]}\n'
                    )

            except Exception as e:
                logger.debug(f"Insight entity search failed: {e}")

            if not parts:
                return ""

            return "RELATED CONTEXT (from project knowledge):\n\n" + "\n".join(parts)

        except Exception as e:
            logger.debug(f"Entity retrieval failed: {e}")
            return ""

    # ------------------------------------------------------------------
    # Past reasoning retrieval (cross-conversation episodes)
    # ------------------------------------------------------------------

    async def _retrieve_past_reasoning(
        self,
        user_message: str,
        thread,
        user,
        budget: int = 500,
        threshold: float = 0.5,
        top_k: int = 3,
    ) -> str:
        """
        Retrieve relevant past reasoning from sealed conversation episodes
        in other threads.

        Searches ConversationEpisode embeddings to find topically related
        past discussions, then formats their reasoning snapshots for context
        injection.

        Args:
            user_message: The user's query text
            thread: Current ChatThread (excluded from results)
            user: Authenticated user (scope search to their threads)
            budget: Max token budget for this context
            threshold: Minimum cosine similarity
            top_k: Max episodes to retrieve

        Returns:
            Formatted context string or empty string
        """
        if budget <= 0:
            return ""

        try:
            from apps.common.vector_utils import generate_embedding, similarity_search
            from .models import ConversationEpisode
            from django.db.models import Q

            query_vector = await sync_to_async(generate_embedding)(user_message)
            if not query_vector:
                return ""

            # Search sealed episodes from OTHER threads belonging to this user
            queryset = ConversationEpisode.objects.filter(
                thread__user=user,
                sealed=True,
            ).exclude(
                thread_id=thread.id,
            ).select_related('thread', 'reasoning_snapshot')

            # Optionally scope to same project if thread has one
            if thread.project_id:
                queryset = queryset.filter(
                    Q(thread__project_id=thread.project_id)
                    | Q(thread__primary_case__project_id=thread.project_id)
                )

            episodes = await sync_to_async(list)(
                similarity_search(
                    queryset=queryset,
                    embedding_field='embedding',
                    query_vector=query_vector,
                    threshold=threshold,
                    top_k=top_k,
                )
            )

            if not episodes:
                return ""

            parts = []
            for ep in episodes:
                thread_title = ep.thread.title[:60] if ep.thread else 'Unknown'
                label = ep.topic_label or f"Episode {ep.episode_index}"
                summary = ep.content_summary[:200] if ep.content_summary else ''

                entry = (
                    f"- [Past Discussion] '{thread_title}' — {label}\n"
                    f"  Summary: {summary}\n"
                )

                # Include key reasoning from snapshot if available
                snapshot = ep.reasoning_snapshot
                if snapshot:
                    established = snapshot.established or []
                    eliminated = snapshot.eliminated or []
                    if established:
                        top_facts = '; '.join(str(f) for f in established[:3])
                        entry += f"  Established: {top_facts}\n"
                    if eliminated:
                        top_eliminated = '; '.join(str(e) for e in eliminated[:2])
                        entry += f"  Eliminated: {top_eliminated}\n"

                parts.append(entry)

            if not parts:
                return ""

            full_text = "RELATED PAST REASONING:\n" + "\n".join(parts)
            return _truncate_to_tokens(full_text, budget)

        except Exception as e:
            logger.debug(f"Past reasoning retrieval failed: {e}")
            return ""

    # ------------------------------------------------------------------
    # Mode resolution — dispatches to one of 7 mode-specific resolvers
    # ------------------------------------------------------------------

    async def _resolve_mode(
        self,
        thread,
        mc: ModeContext,
        available_tools: Optional[List] = None,
    ) -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
        """
        Resolve mode-specific system prompt.

        Returns:
            (system_prompt_override, current_plan_content, current_orientation_id)
        """
        thread_metadata = thread.metadata or {}

        # Branch 1: Scaffolding (from thread metadata, not mode_context)
        if thread_metadata.get('mode') == 'scaffolding':
            prompt = await self._resolve_scaffolding_mode(thread)
            return prompt, None, None

        # Branch 2: Inquiry focus
        if mc.mode == 'inquiry_focus' and mc.inquiry_id:
            prompt = await self._resolve_inquiry_focus_mode(mc.inquiry_id)
            return prompt, None, None

        # Branch 3: Case
        if mc.mode == 'case' and mc.case_id:
            prompt, plan_content = await self._resolve_case_mode(
                mc.case_id, available_tools=available_tools,
            )
            return prompt, plan_content, None

        # Branch 4: Graph
        if mc.mode == 'graph' and thread.project_id:
            prompt = await self._resolve_graph_mode(thread)
            return prompt, None, None

        # Branch 5: Node-focused
        if mc.source_type == 'graph_node' and mc.source_id and thread.project_id:
            prompt = await self._resolve_node_focused_mode(mc.source_id)
            return prompt, None, None

        # Branch 6: Finding-focused
        if mc.source_type == 'orientation_finding' and mc.source_id and thread.project_id:
            prompt = await self._resolve_finding_focused_mode(
                mc.source_id, thread.project_id
            )
            return prompt, None, None

        # Branch 7: Orientation editing
        if mc.mode == 'orientation' and thread.project_id:
            prompt, orientation_id = await self._resolve_orientation_mode(thread.project_id)
            return prompt, None, orientation_id

        # No mode matched — use default system prompt
        return None, None, None

    # ------------------------------------------------------------------
    # Mode resolvers (each extracted 1:1 from views.py)
    # ------------------------------------------------------------------

    async def _resolve_scaffolding_mode(self, thread) -> Optional[str]:
        """Scaffolding mode: loads skills, builds scaffolding prompt. (views.py 664-686)"""
        try:
            from apps.intelligence.prompts import build_scaffolding_system_prompt

            scaffolding_skill_context = None
            try:
                from apps.skills.injection import build_skill_context
                _case = thread.primary_case
                if _case:
                    _skills = await sync_to_async(
                        lambda: list(_case.active_skills.filter(status='active'))
                    )()
                    if _skills:
                        scaffolding_skill_context = await sync_to_async(
                            lambda: build_skill_context(_skills, 'brief')
                        )()
            except Exception as e:
                logger.warning(f"Could not load skills for scaffolding: {e}")

            return build_scaffolding_system_prompt(
                skill_context=scaffolding_skill_context
            )
        except Exception as e:
            logger.warning(f"Could not build scaffolding prompt: {e}")
            return None

    async def _resolve_inquiry_focus_mode(self, inquiry_id: str) -> Optional[str]:
        """Inquiry focus mode: builds inquiry-aware prompt. (views.py 687-706)"""
        try:
            from apps.inquiries.models import Inquiry
            inquiry = await sync_to_async(
                lambda: Inquiry.objects.filter(id=inquiry_id).first()
            )()
            if inquiry:
                return (
                    "You are Episteme, a thoughtful decision-support assistant. "
                    f"The user is currently investigating a specific inquiry: \"{inquiry.title}\". "
                    f"{('Context: ' + inquiry.description + '. ') if inquiry.description else ''}"
                    "Focus your responses on helping them gather evidence, validate assumptions, "
                    "and reach a well-supported conclusion for this inquiry. "
                    "Be specific, cite reasoning, and suggest concrete next steps for investigation. "
                    "When the user's question relates to this inquiry, frame your answer in that context."
                )
        except Exception as e:
            logger.warning(f"Could not load inquiry for mode context: {e}")
        return None

    async def _resolve_case_mode(
        self,
        case_id: str,
        available_tools: Optional[List] = None,
    ) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Case mode: parallel loads Case+Plan+PlanVersion, builds case-aware prompt.
        Returns (system_prompt, current_plan_content). (views.py 707-746)
        """
        try:
            from apps.cases.models import Case, InvestigationPlan, PlanVersion
            from apps.intelligence.prompts import build_case_aware_system_prompt

            # Parallel fetch: Case and InvestigationPlan are independent
            case_obj, plan_obj = await asyncio.gather(
                sync_to_async(
                    lambda: Case.objects.filter(id=case_id).first()
                )(),
                sync_to_async(
                    lambda: InvestigationPlan.objects.filter(case_id=case_id).first()
                )(),
            )

            plan_content = None
            if plan_obj:
                current_version = await sync_to_async(
                    lambda: PlanVersion.objects.filter(
                        plan=plan_obj, version_number=plan_obj.current_version
                    ).first()
                )()
                plan_content = current_version.content if current_version else None

            system_prompt = build_case_aware_system_prompt(
                stage=plan_obj.stage if plan_obj else 'exploring',
                plan_content=plan_content,
                decision_question=case_obj.decision_question if case_obj else '',
                position_statement=plan_obj.position_statement if plan_obj else '',
                constraints=case_obj.constraints if case_obj else None,
                success_criteria=case_obj.success_criteria if case_obj else None,
                available_tools=available_tools,
            )

            # Check for pending outcome review on this case
            try:
                from apps.cases.outcome_service import OutcomeReviewService
                review = await sync_to_async(
                    OutcomeReviewService.get_review_for_case
                )(case_id)
                if review:
                    system_prompt += (
                        f"\n\nOUTCOME REVIEW DUE: This case's decision was made on "
                        f"{review['decided_at']}. The user set a review date of "
                        f"{review['outcome_check_date']} ({review['days_overdue']} days ago). "
                        f"Consider naturally asking how the decision played out."
                    )
            except Exception as e:
                logger.debug(f"Outcome review check skipped: {e}")

            return system_prompt, plan_content
        except Exception as e:
            logger.warning(f"Could not build case-aware prompt: {e}")
            return None, None

    async def _resolve_graph_mode(self, thread) -> Optional[str]:
        """Graph mode: serializes graph + health. (views.py 747-773)"""
        try:
            from apps.graph.serialization import GraphSerializationService
            from apps.graph.services import GraphService
            from apps.intelligence.graph_prompts import build_graph_aware_system_prompt

            _case_id = thread.primary_case_id
            graph_context, _ = await sync_to_async(
                GraphSerializationService.serialize_for_llm
            )(thread.project_id, case_id=_case_id)

            if _case_id:
                graph_health = await sync_to_async(
                    GraphService.compute_case_graph_health
                )(_case_id)
            else:
                graph_health = await sync_to_async(
                    GraphService.compute_graph_health
                )(thread.project_id)

            return build_graph_aware_system_prompt(
                graph_context=graph_context,
                graph_health=graph_health,
            )
        except Exception as e:
            logger.warning(f"Could not build graph-aware prompt: {e}")
            return None

    async def _resolve_node_focused_mode(self, node_id_str: str) -> Optional[str]:
        """Node-focused mode: serializes node neighborhood. (views.py 775-793)"""
        try:
            import uuid as uuid_module
            from apps.graph.serialization import GraphSerializationService
            from apps.intelligence.graph_prompts import build_node_focused_system_prompt

            node_id = uuid_module.UUID(node_id_str)
            node_context = await sync_to_async(
                GraphSerializationService.serialize_node_neighborhood
            )(node_id)

            return build_node_focused_system_prompt(
                node_context=node_context,
            )
        except (ValueError, Exception) as e:
            logger.warning(f"Could not build node-focused prompt: {e}")
            return None

    async def _resolve_finding_focused_mode(
        self, insight_id_str: str, project_id
    ) -> Optional[str]:
        """
        Finding-focused mode: loads insight + hierarchy + siblings + research.
        (views.py 795-892)
        """
        try:
            import uuid as uuid_module
            from apps.graph.models import ProjectInsight, ClusterHierarchy
            from apps.intelligence.graph_prompts import (
                build_finding_focused_system_prompt,
                _FINDING_TYPE_GUIDANCE,
            )

            insight_id = uuid_module.UUID(insight_id_str)
            insight = await sync_to_async(
                lambda: ProjectInsight.objects.select_related('orientation').get(
                    id=insight_id, project_id=project_id
                )
            )()

            # Build finding context string
            type_guidance = _FINDING_TYPE_GUIDANCE.get(
                insight.insight_type,
                "The user is exploring a finding from their document analysis."
            )
            finding_lines = [
                f"## Finding Context\n",
                f"**Type:** {insight.insight_type}",
                f"**Title:** {insight.title}",
                f"**Analysis:** {insight.content}",
                f"\n{type_guidance}",
            ]

            # Resolve source themes from hierarchy
            if insight.source_cluster_ids and insight.orientation:
                hierarchy = await sync_to_async(
                    lambda: ClusterHierarchy.objects.filter(
                        project_id=project_id
                    ).order_by('-created_at').first()
                )()
                if hierarchy and hierarchy.tree:
                    theme_labels = _resolve_theme_labels(
                        hierarchy.tree, insight.source_cluster_ids
                    )
                    if theme_labels:
                        finding_lines.append(
                            f"\n**Source themes:** {', '.join(theme_labels)}"
                        )

            # Add orientation lens context
            if insight.orientation:
                orientation = insight.orientation
                finding_lines.append(
                    f"\n**Analytical lens:** {orientation.lens_type.replace('_', ' ').title()}"
                )
                if orientation.lead_text:
                    finding_lines.append(
                        f"**Orientation lead:** {orientation.lead_text}"
                    )

                # Sibling findings for cross-reference
                siblings = await sync_to_async(list)(
                    ProjectInsight.objects.filter(
                        orientation=orientation
                    ).exclude(
                        id=insight_id
                    ).exclude(
                        insight_type='exploration_angle'
                    ).order_by('display_order')[:5]
                )
                if siblings:
                    finding_lines.append("\n**Related findings from this orientation:**")
                    for sib in siblings:
                        finding_lines.append(
                            f"- [{sib.insight_type}] {sib.title}"
                        )

            finding_context = "\n".join(finding_lines)

            # Research context (if the finding was already researched)
            research_context = None
            if insight.research_result and insight.research_result.get('answer'):
                rr = insight.research_result
                research_lines = [rr['answer']]
                sources = rr.get('sources', [])
                if sources:
                    research_lines.append(
                        "Sources: " + ", ".join(
                            s.get('title', 'Untitled') for s in sources
                        )
                    )
                research_context = "\n".join(research_lines)

            return build_finding_focused_system_prompt(
                finding_context=finding_context,
                research_context=research_context,
            )
        except Exception as e:
            logger.warning(f"Could not build finding-focused prompt: {e}")
            return None

    async def _resolve_orientation_mode(
        self, project_id
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Orientation editing mode: parallel loads orientation + insights.
        Returns (system_prompt, current_orientation_id). (views.py 894-955)
        """
        try:
            from apps.graph.models import (
                ProjectOrientation, ProjectInsight, InsightType, InsightStatus,
            )
            from apps.intelligence.orientation_prompts import (
                build_orientation_aware_system_prompt,
            )

            # Load current orientation and its active insights in parallel
            orientation_coro = sync_to_async(
                lambda: ProjectOrientation.objects.filter(
                    project_id=project_id, is_current=True,
                ).first()
            )()
            insights_coro = sync_to_async(list)(
                ProjectInsight.objects.filter(
                    orientation__project_id=project_id,
                    orientation__is_current=True,
                ).exclude(
                    status=InsightStatus.DISMISSED,
                ).order_by('display_order')
            )

            orientation_obj, all_insights = await asyncio.gather(
                orientation_coro, insights_coro,
            )

            if not orientation_obj:
                return None, None

            orientation_id = str(orientation_obj.id)

            # Separate findings from angles
            findings = []
            angles = []
            for insight in all_insights:
                if insight.insight_type == InsightType.EXPLORATION_ANGLE:
                    angles.append({
                        'id': str(insight.id),
                        'title': insight.title,
                    })
                else:
                    findings.append({
                        'id': str(insight.id),
                        'insight_type': insight.insight_type,
                        'title': insight.title,
                        'content': insight.content,
                        'status': insight.status,
                        'confidence': insight.confidence,
                    })

            system_prompt = build_orientation_aware_system_prompt(
                lens_type=orientation_obj.lens_type,
                lead_text=orientation_obj.lead_text,
                findings=findings,
                angles=angles,
                secondary_lens=orientation_obj.secondary_lens,
                secondary_lens_reason=orientation_obj.secondary_lens_reason,
            )

            return system_prompt, orientation_id
        except Exception as e:
            logger.warning(f"Could not build orientation-aware prompt: {e}")
            return None, None
