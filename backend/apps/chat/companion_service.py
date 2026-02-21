"""
Companion service — the core engine for the organic companion.

Manages conversation structure extraction, research detection,
case signal detection, and fact promotion.
"""
import asyncio
import json
import logging
import uuid
from datetime import timedelta
from typing import Optional

from asgiref.sync import sync_to_async
from django.utils import timezone

from apps.common.llm_providers import get_llm_provider, strip_markdown_fences

logger = logging.getLogger(__name__)

# Maximum messages to feed on first creation (full conversation context)
MAX_MESSAGES_FOR_CREATION = 20

# Number of recent messages to include on update (structure already has accumulated state)
RECENT_MESSAGES_FOR_UPDATE = 6

# Debounce: minimum interval between companion updates (seconds)
MIN_UPDATE_INTERVAL_SECONDS = 30

# Debounce: minimum turns between companion updates
MIN_TURNS_BETWEEN_UPDATES = 2

# Maximum structure versions to keep per thread (prune older ones)
MAX_VERSIONS_TO_KEEP = 5


class CompanionService:
    """
    Core engine for the organic companion.

    Reads conversation, decides what structure fits,
    generates/updates it, and produces context for the chat prompt.
    """

    @staticmethod
    async def update_structure(
        thread_id: uuid.UUID,
        new_message_id: uuid.UUID,
    ):
        """
        Called after each assistant response.
        Reads recent conversation, updates the organic structure.

        Returns the new ConversationStructure or None if too early.
        """
        from .models import ChatThread, Message, ConversationStructure
        from .companion_prompts import build_structure_update_prompt

        try:
            thread = await sync_to_async(ChatThread.objects.get)(id=thread_id)
        except ChatThread.DoesNotExist:
            logger.warning("companion_thread_not_found", extra={"thread_id": str(thread_id)})
            return None

        # Get current structure if exists
        current_structure = await sync_to_async(
            lambda: ConversationStructure.objects.filter(
                thread=thread
            ).order_by('-version').first()
        )()

        # --- Debounce: skip update if too soon or not enough turns ---
        if current_structure:
            time_since_last = timezone.now() - current_structure.updated_at
            if time_since_last < timedelta(seconds=MIN_UPDATE_INTERVAL_SECONDS):
                # Count messages since last companion update
                messages_since = await sync_to_async(
                    Message.objects.filter(
                        thread=thread,
                        content_type='text',
                        role='user',
                        created_at__gt=current_structure.updated_at,
                    ).count
                )()
                if messages_since < MIN_TURNS_BETWEEN_UPDATES:
                    logger.debug(
                        "companion_debounced",
                        extra={
                            "thread_id": str(thread_id),
                            "seconds_since": time_since_last.total_seconds(),
                            "turns_since": messages_since,
                        }
                    )
                    return None

        # --- Load messages: fewer on update, more on creation ---
        if current_structure:
            # Update: only need recent messages — structure has accumulated state
            msg_limit = RECENT_MESSAGES_FOR_UPDATE
        else:
            # Creation: need more context to build initial structure
            msg_limit = MAX_MESSAGES_FOR_CREATION

        messages_qs = Message.objects.filter(
            thread=thread,
            content_type='text',
        ).order_by('-created_at')[:msg_limit]
        messages = await sync_to_async(list)(messages_qs)
        messages.reverse()  # Restore chronological order

        current_dict = None
        if current_structure:
            current_dict = {
                'structure_type': current_structure.structure_type,
                'content': current_structure.content,
                'established': current_structure.established,
                'open_questions': current_structure.open_questions,
                'eliminated': current_structure.eliminated,
                'context_summary': current_structure.context_summary,
            }

        # Get project context if available
        project_context = None
        if thread.project_id:
            try:
                from apps.graph.summary_service import ProjectSummaryService
                from apps.chat.prompts import format_summary_for_chat
                summary = await sync_to_async(
                    ProjectSummaryService.get_current_summary
                )(thread.project_id)
                if summary and summary.sections:
                    project_context = format_summary_for_chat(summary.sections)
            except Exception:
                logger.debug("Could not load project summary for companion", exc_info=True)

        # Add case context if thread is linked to a case
        if thread.primary_case_id:
            try:
                case = await sync_to_async(lambda: thread.primary_case)()
                if case:
                    case_context = f"Decision question: {case.decision_question or case.title}"
                    if case.position:
                        case_context += f"\nCurrent position: {case.position}"
                    # Append to project_context or use standalone
                    project_context = f"{project_context}\n\nCASE CONTEXT:\n{case_context}" if project_context else f"CASE CONTEXT:\n{case_context}"
            except Exception:
                logger.debug("Could not load case context for companion", exc_info=True)

        # Get user context for first-session awareness
        user = await sync_to_async(lambda: thread.user)()
        user_context = await CompanionService._get_user_context(user, thread)

        # Build prompt
        message_dicts = [
            {'role': m.role, 'content': m.content}
            for m in messages
        ]
        prompt = build_structure_update_prompt(
            messages=message_dicts,
            current_structure=current_dict,
            project_context=project_context,
            user_context=user_context,
        )

        # Call LLM
        try:
            provider = get_llm_provider('fast')
            result_text = await provider.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=(
                    "You analyze conversations and produce structured representations. "
                    "Return ONLY valid JSON, no explanation."
                ),
                max_tokens=2048,
                temperature=0.3,
            )

            cleaned = strip_markdown_fences(result_text.strip())
            result = json.loads(cleaned)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(
                "companion_structure_parse_failed",
                extra={"thread_id": str(thread_id), "error": str(e)}
            )
            return None

        # Validate required fields
        required_fields = ['structure_type', 'content', 'established', 'open_questions', 'eliminated', 'context_summary']
        if not all(f in result for f in required_fields):
            logger.warning(
                "companion_structure_missing_fields",
                extra={"thread_id": str(thread_id), "fields": list(result.keys())}
            )
            return None

        # Create new version — use DB-level max to avoid race conditions
        from django.db.models import Max
        max_version = await sync_to_async(
            lambda: ConversationStructure.objects.filter(
                thread=thread
            ).aggregate(Max('version'))['version__max']
        )()
        new_version = (max_version or 0) + 1

        structure = await sync_to_async(ConversationStructure.objects.create)(
            thread=thread,
            version=new_version,
            structure_type=result['structure_type'],
            content=result['content'],
            established=result['established'],
            open_questions=result['open_questions'],
            eliminated=result['eliminated'],
            context_summary=result['context_summary'],
            last_message_id=new_message_id,
            metadata={'model': 'fast'},
        )

        logger.info(
            "companion_structure_updated",
            extra={
                "thread_id": str(thread_id),
                "version": new_version,
                "structure_type": result['structure_type'],
                "established_count": len(result['established']),
                "open_questions_count": len(result['open_questions']),
                "eliminated_count": len(result['eliminated']),
            }
        )

        # --- Episode lifecycle management ---
        try:
            await CompanionService._manage_episodes(
                thread=thread,
                structure=structure,
                previous_structure=current_structure,
                topic_continuity=result.get('topic_continuity', 'continuous'),
                topic_label=result.get('topic_label', ''),
            )
        except Exception:
            logger.debug("companion_episode_management_failed", exc_info=True)

        # --- Generate rolling digest for long conversations ---
        total_msg_count = await sync_to_async(
            Message.objects.filter(thread=thread, content_type='text').count
        )()
        if total_msg_count > 12:
            try:
                existing_digest = (
                    current_structure.rolling_digest if current_structure else ""
                )
                digest = await CompanionService._generate_rolling_digest(
                    thread, recent_window=10, current_digest=existing_digest,
                )
                if digest:
                    structure.rolling_digest = digest
                    await sync_to_async(
                        lambda: structure.save(update_fields=['rolling_digest'])
                    )()
                    logger.info(
                        "companion_rolling_digest_updated",
                        extra={
                            "thread_id": str(thread_id),
                            "digest_length": len(digest),
                        }
                    )
            except Exception:
                logger.debug("companion_rolling_digest_failed", exc_info=True)

        # --- Decision readiness detection (heuristic, no LLM call) ---
        try:
            readiness = await CompanionService._detect_decision_readiness(
                structure, thread,
            )
            if readiness:
                metadata = structure.metadata or {}
                metadata['decision_readiness'] = readiness
                structure.metadata = metadata
                await sync_to_async(
                    lambda: structure.save(update_fields=['metadata'])
                )()
                if readiness.get('ready'):
                    logger.info(
                        "companion_decision_ready",
                        extra={
                            "thread_id": str(thread_id),
                            "signal_strength": readiness.get('signal_strength'),
                            "reasons": readiness.get('reasons'),
                        }
                    )
        except Exception:
            logger.debug("companion_decision_readiness_failed", exc_info=True)

        # --- Fact promotion (async fire-and-forget) ---
        try:
            from .fact_promotion import FactPromotionService
            # Fire-and-forget: don't block the companion update
            asyncio.create_task(
                FactPromotionService.promote_to_case(thread, structure)
            )
            asyncio.create_task(
                FactPromotionService.promote_to_insight(thread, structure)
            )
        except Exception:
            logger.debug("companion_fact_promotion_launch_failed", exc_info=True)

        # --- Prune old versions to prevent DB bloat ---
        if new_version > MAX_VERSIONS_TO_KEEP:
            try:
                cutoff_version = new_version - MAX_VERSIONS_TO_KEEP
                await sync_to_async(
                    lambda: ConversationStructure.objects.filter(
                        thread=thread,
                        version__lte=cutoff_version,
                    ).delete()
                )()
            except Exception:
                logger.debug("companion_version_prune_failed", exc_info=True)

        return structure

    @staticmethod
    def get_chat_context(thread_id: uuid.UUID) -> str:
        """
        Returns the context_summary for injection into chat prompt.
        This is the clarifying loop — the companion feeds back into the AI.
        """
        from .models import ConversationStructure

        structure = ConversationStructure.objects.filter(
            thread_id=thread_id
        ).order_by('-version').first()

        if not structure:
            return ''
        return structure.context_summary

    @staticmethod
    async def get_chat_context_async(thread_id: uuid.UUID) -> str:
        """Async version of get_chat_context."""
        return await sync_to_async(CompanionService.get_chat_context)(thread_id)

    @staticmethod
    def get_current_structure(thread_id: uuid.UUID):
        """Get the latest ConversationStructure for a thread."""
        from .models import ConversationStructure

        return ConversationStructure.objects.filter(
            thread_id=thread_id
        ).order_by('-version').first()

    @staticmethod
    async def get_current_structure_async(thread_id: uuid.UUID):
        """Async version of get_current_structure."""
        return await sync_to_async(CompanionService.get_current_structure)(thread_id)

    @staticmethod
    async def detect_case_signal(thread_id: uuid.UUID) -> Optional[dict]:
        """
        Check if the conversation has reached a 'decision shape'.
        Returns case suggestion data or None.
        """
        from .models import ConversationStructure
        from .companion_prompts import build_case_detection_prompt

        structure = await sync_to_async(
            lambda: ConversationStructure.objects.filter(
                thread_id=thread_id
            ).order_by('-version').first()
        )()

        if not structure:
            return None

        # Heuristic pre-check
        has_enough_context = (
            len(structure.established) >= 2
            and len(structure.open_questions) >= 1
            and structure.structure_type in (
                'decision_tree', 'comparison', 'pros_cons', 'exploration_map'
            )
        )
        if not has_enough_context:
            return None

        # LLM check
        prompt = build_case_detection_prompt(
            structure_content=structure.content,
            structure_type=structure.structure_type,
            established=structure.established,
            open_questions=structure.open_questions,
            eliminated=structure.eliminated,
        )

        try:
            provider = get_llm_provider('fast')
            result_text = await provider.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You analyze conversation structures for decision readiness. Return ONLY valid JSON.",
                max_tokens=512,
                temperature=0.2,
            )
            cleaned = strip_markdown_fences(result_text.strip())
            result = json.loads(cleaned)

            if result.get('should_suggest'):
                logger.info(
                    "companion_case_signal_detected",
                    extra={
                        "thread_id": str(thread_id),
                        "decision_question": result.get('decision_question'),
                    }
                )
                # Attach companion state for transfer
                result['companion_state'] = {
                    'established': structure.established,
                    'open_questions': structure.open_questions,
                    'eliminated': structure.eliminated,
                    'structure_snapshot': structure.content,
                    'structure_type': structure.structure_type,
                }
                return result
        except Exception as e:
            logger.warning(
                "companion_case_detection_failed",
                extra={"thread_id": str(thread_id), "error": str(e)}
            )

        return None

    @staticmethod
    def _normalize_question(q: str) -> str:
        """
        Normalize a question for fuzzy dedup.
        Strips punctuation, lowercases, and sorts key words.
        """
        import re
        # Lowercase, strip leading question words, remove punctuation
        q = q.lower().strip()
        q = re.sub(r'^(what|how|does|is|are|can|will|should|do|where|when|why)\s+', '', q)
        q = re.sub(r'[^\w\s]', '', q)
        return ' '.join(sorted(q.split()))

    @staticmethod
    def _is_duplicate_question(new_q: str, existing_qs: set[str], threshold: float = 0.6) -> bool:
        """
        Check if a question is a near-duplicate of any existing question.
        Uses word overlap (Jaccard similarity) on normalized forms.
        """
        new_norm = CompanionService._normalize_question(new_q)
        new_words = set(new_norm.split())
        if not new_words:
            return False

        for existing in existing_qs:
            existing_norm = CompanionService._normalize_question(existing)
            existing_words = set(existing_norm.split())
            if not existing_words:
                continue
            # Jaccard similarity
            intersection = len(new_words & existing_words)
            union = len(new_words | existing_words)
            if union > 0 and (intersection / union) >= threshold:
                return True
        return False

    @staticmethod
    async def _get_user_context(user, thread) -> dict:
        """
        Gather lightweight user context for first-session awareness.

        Returns a dict with:
          - is_first_thread: bool (True if this is the user's only thread)
          - thread_count: int
          - project_count: int
          - document_count: int
          - case_count: int

        All queries are simple COUNTs on indexed FKs, run in parallel.
        """
        from .models import ChatThread
        from apps.projects.models import Project, Document
        from apps.cases.models import Case

        thread_count, project_count, document_count, case_count = await asyncio.gather(
            sync_to_async(ChatThread.objects.filter(user=user).count)(),
            sync_to_async(Project.objects.filter(user=user).count)(),
            sync_to_async(Document.objects.filter(user=user).count)(),
            sync_to_async(Case.objects.filter(user=user).count)(),
        )

        return {
            'is_first_thread': thread_count <= 1,
            'thread_count': thread_count,
            'project_count': project_count,
            'document_count': document_count,
            'case_count': case_count,
        }

    @staticmethod
    async def _detect_decision_readiness(structure, thread) -> Optional[dict]:
        """
        Detect whether the conversation is converging on a decision.

        Pure heuristics — no LLM call. Checks:
          1. Enough established facts (>= 3)
          2. At least one eliminated option
          3. Few open questions remaining (<= 2)
          4. Thread's case is active and in a late stage

        Returns:
            Dict with {ready: bool, signal_strength: float, reasons: [str]}
            or None if not applicable (no case linked).
        """
        # Only relevant for case-linked threads
        case_id = getattr(thread, 'primary_case_id', None)
        if not case_id:
            return None

        established = structure.established or []
        eliminated = structure.eliminated or []
        open_questions = structure.open_questions or []

        reasons = []
        signals = 0
        max_signals = 4

        # Signal 1: enough established facts
        if len(established) >= 3:
            reasons.append(f"{len(established)} facts established")
            signals += 1

        # Signal 2: options eliminated
        if len(eliminated) >= 1:
            reasons.append(f"{len(eliminated)} option(s) eliminated")
            signals += 1

        # Signal 3: few open questions
        if len(open_questions) <= 2:
            reasons.append(
                "no open questions" if not open_questions
                else f"only {len(open_questions)} open question(s) remain"
            )
            signals += 1

        # Signal 4: case stage is late
        try:
            from apps.cases.models import Case, CaseStatus, CaseStage
            case = await sync_to_async(
                lambda: Case.objects.filter(id=case_id).only(
                    'status', 'metadata'
                ).first()
            )()
            if case and case.status == CaseStatus.ACTIVE:
                case_stage = (case.metadata or {}).get('stage', 'exploring')
                if case_stage in ('synthesizing', 'ready'):
                    reasons.append(f"case stage is '{case_stage}'")
                    signals += 1
        except Exception as e:
            logger.debug("Decision readiness case check failed: %s", e)

        signal_strength = round(signals / max_signals, 2)
        ready = signals >= 3  # Need at least 3 of 4 signals

        return {
            'ready': ready,
            'signal_strength': signal_strength,
            'reasons': reasons,
        }

    @staticmethod
    async def _generate_rolling_digest(
        thread,
        recent_window: int = 10,
        current_digest: str = "",
    ) -> str:
        """
        Generate a rolling digest of messages outside the recent window.

        Tier 2 memory: messages 11-20 (just outside the verbatim window)
        are summarised into a 3-5 sentence digest that carries forward.

        Args:
            thread: ChatThread instance
            recent_window: How many recent messages to skip (Tier 1)
            current_digest: The existing rolling digest to update

        Returns:
            Updated digest string, or existing digest on failure
        """
        from .models import Message

        # Fetch messages just outside the recent window (positions 11-20)
        older_messages_qs = (
            Message.objects.filter(thread=thread, content_type='text')
            .order_by('-created_at')[recent_window:recent_window + 10]
        )
        older_messages = await sync_to_async(list)(older_messages_qs)
        older_messages.reverse()  # Restore chronological order

        if not older_messages:
            return current_digest

        # Format the older messages for the digest prompt
        msg_lines = []
        for m in older_messages:
            content = m.content[:400]
            if len(m.content) > 400:
                content += "..."
            msg_lines.append(f"{m.role.upper()}: {content}")
        older_text = "\n".join(msg_lines)

        prompt_parts = []
        if current_digest:
            prompt_parts.append(
                f"EXISTING DIGEST (previous summary of even older messages):\n{current_digest}\n"
            )
        prompt_parts.append(
            f"NEW MESSAGES TO INCORPORATE:\n{older_text}\n\n"
            "Produce a concise 3-5 sentence digest capturing the key topics, "
            "decisions, established facts, and important context from these messages. "
            "If there is an existing digest, merge new information into it. "
            "Focus on information that would be useful for continuing the conversation."
        )

        try:
            provider = get_llm_provider('fast')
            result = await provider.generate(
                messages=[{"role": "user", "content": "\n".join(prompt_parts)}],
                system_prompt=(
                    "You are a conversation summariser. "
                    "Produce a concise, factual digest. No preamble."
                ),
                max_tokens=512,
                temperature=0.2,
            )
            digest = result.strip()
            if digest:
                return digest
        except Exception as e:
            logger.warning(f"Rolling digest generation failed: {e}")

        return current_digest

    @staticmethod
    async def _manage_episodes(
        thread,
        structure,
        previous_structure,
        topic_continuity: str,
        topic_label: str,
    ):
        """
        Manage conversation episode lifecycle based on companion's topic analysis.

        On every companion update:
        - If no current episode: create one (initial)
        - If continuous: increment message count on current episode
        - If partial_shift or discontinuous: seal current episode, create new one

        Episodes are sealed with a content_summary (from the previous structure's
        context_summary) and a reasoning_snapshot (the new structure version).
        Embedding is generated automatically by the post_save signal.
        """
        from .models import ConversationEpisode, Message

        # Load current episode (if any)
        current_episode = None
        if thread.current_episode_id:
            current_episode = await sync_to_async(
                lambda: ConversationEpisode.objects.filter(
                    id=thread.current_episode_id
                ).first()
            )()

        if not current_episode:
            # First episode for this thread — create initial
            first_message = await sync_to_async(
                lambda: Message.objects.filter(
                    thread=thread, content_type='text'
                ).order_by('created_at').first()
            )()

            current_episode = await sync_to_async(ConversationEpisode.objects.create)(
                thread=thread,
                episode_index=0,
                shift_type='initial',
                topic_label=topic_label or thread.title[:200],
                start_message=first_message,
                sealed=False,
            )
            thread.current_episode = current_episode
            await sync_to_async(
                lambda: thread.save(update_fields=['current_episode'])
            )()

            logger.info(
                "episode_created_initial",
                extra={
                    "thread_id": str(thread.id),
                    "episode_id": str(current_episode.id),
                    "topic_label": current_episode.topic_label,
                }
            )

        # Count unlinked messages for this episode
        unlinked_count = await sync_to_async(
            Message.objects.filter(
                thread=thread,
                episode__isnull=True,
                content_type='text',
            ).count
        )()

        if topic_continuity in ('partial_shift', 'discontinuous'):
            # --- Seal current episode ---
            last_message = await sync_to_async(
                lambda: Message.objects.filter(
                    thread=thread, content_type='text'
                ).order_by('-created_at').first()
            )()

            # Content summary comes from the PREVIOUS structure's context_summary
            # (what was established during this episode, before the topic shifted)
            seal_summary = ''
            if previous_structure:
                seal_summary = previous_structure.context_summary or ''

            current_episode.sealed = True
            current_episode.sealed_at = timezone.now()
            current_episode.end_message = last_message
            current_episode.content_summary = seal_summary
            current_episode.reasoning_snapshot = structure
            current_episode.message_count = (
                current_episode.message_count + unlinked_count
            )
            await sync_to_async(
                lambda: current_episode.save(update_fields=[
                    'sealed', 'sealed_at', 'end_message',
                    'content_summary', 'reasoning_snapshot', 'message_count',
                ])
            )()

            logger.info(
                "episode_sealed",
                extra={
                    "thread_id": str(thread.id),
                    "episode_id": str(current_episode.id),
                    "topic_label": current_episode.topic_label,
                    "shift_type": topic_continuity,
                    "message_count": current_episode.message_count,
                }
            )

            # Link all unlinked messages to the sealed episode
            await sync_to_async(
                lambda: Message.objects.filter(
                    thread=thread, episode__isnull=True,
                ).update(episode=current_episode)
            )()

            # --- Create new episode ---
            new_episode = await sync_to_async(ConversationEpisode.objects.create)(
                thread=thread,
                episode_index=current_episode.episode_index + 1,
                shift_type=topic_continuity,
                topic_label=topic_label,
                sealed=False,
            )
            thread.current_episode = new_episode
            await sync_to_async(
                lambda: thread.save(update_fields=['current_episode'])
            )()

            logger.info(
                "episode_created",
                extra={
                    "thread_id": str(thread.id),
                    "episode_id": str(new_episode.id),
                    "topic_label": topic_label,
                    "shift_type": topic_continuity,
                }
            )
        else:
            # Continuous — just update message count and link messages
            current_episode.message_count = (
                current_episode.message_count + unlinked_count
            )
            if topic_label and not current_episode.topic_label:
                current_episode.topic_label = topic_label

            await sync_to_async(
                lambda: current_episode.save(update_fields=[
                    'message_count', 'topic_label',
                ])
            )()

            # Link unlinked messages to current episode
            await sync_to_async(
                lambda: Message.objects.filter(
                    thread=thread, episode__isnull=True,
                ).update(episode=current_episode)
            )()

    @staticmethod
    async def detect_research_needs(thread_id: uuid.UUID) -> list[dict]:
        """
        Identify factual questions that could be researched in background.
        Returns list of {question, search_query, priority}.
        """
        from .models import ConversationStructure, ResearchResult
        from .companion_prompts import build_research_detection_prompt

        structure = await sync_to_async(
            lambda: ConversationStructure.objects.filter(
                thread_id=thread_id
            ).order_by('-version').first()
        )()

        if not structure or not structure.open_questions:
            return []

        # Filter out questions that are already being researched or have results
        # Use fuzzy matching to catch rephrased duplicates
        existing_questions = await sync_to_async(
            lambda: set(
                ResearchResult.objects.filter(
                    thread_id=thread_id,
                    status__in=['researching', 'complete'],
                ).values_list('question', flat=True)
            )
        )()

        new_questions = [
            q for q in structure.open_questions
            if not CompanionService._is_duplicate_question(q, existing_questions)
        ]

        if not new_questions:
            return []

        # LLM classification
        prompt = build_research_detection_prompt(new_questions)

        try:
            provider = get_llm_provider('fast')
            result_text = await provider.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You classify questions as researchable or not. Return ONLY valid JSON.",
                max_tokens=1024,
                temperature=0.2,
            )
            cleaned = strip_markdown_fences(result_text.strip())
            result = json.loads(cleaned)

            researchable = result.get('researchable', [])
            if researchable:
                logger.info(
                    "companion_research_needs_detected",
                    extra={
                        "thread_id": str(thread_id),
                        "researchable_count": len(researchable),
                    }
                )
            return researchable

        except Exception as e:
            logger.warning(
                "companion_research_detection_failed",
                extra={"thread_id": str(thread_id), "error": str(e)}
            )
            return []
