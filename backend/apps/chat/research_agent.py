"""
Lightweight research agent for the organic companion.

When the companion detects factual open questions, this agent
researches them in the background and surfaces findings.

Simpler than the full ResearchLoop — does a single search + synthesis
for quick factual questions.
"""
import logging
import uuid
from typing import Optional

from asgiref.sync import sync_to_async

from apps.common.llm_providers import get_llm_provider

logger = logging.getLogger(__name__)


class CompanionResearchAgent:
    """
    Lightweight research agent for companion-detected questions.
    """

    @staticmethod
    async def research_question(
        thread_id: uuid.UUID,
        question: str,
        search_query: str,
    ) -> Optional[dict]:
        """
        Research a single factual question.

        Creates a ResearchResult record, runs the research,
        and updates the record with findings.

        Returns the research result dict or None on failure.
        """
        from .models import ResearchResult, ChatThread

        try:
            thread = await sync_to_async(ChatThread.objects.get)(id=thread_id)
        except ChatThread.DoesNotExist:
            logger.warning("companion_research_thread_not_found", extra={"thread_id": str(thread_id)})
            return None

        # Create research record (in-progress)
        result = await sync_to_async(ResearchResult.objects.create)(
            thread=thread,
            question=question,
            status='researching',
            metadata={'search_query': search_query},
        )

        try:
            # Use web search if available, otherwise fall back to LLM knowledge
            answer, sources = await CompanionResearchAgent._do_research(
                question=question,
                search_query=search_query,
                project_id=thread.project_id,
            )

            # Update result
            result.answer = answer
            result.sources = sources
            result.status = 'complete'
            await sync_to_async(result.save)(
                update_fields=['answer', 'sources', 'status', 'updated_at']
            )

            logger.info(
                "companion_research_complete",
                extra={
                    "thread_id": str(thread_id),
                    "question": question[:80],
                    "sources_count": len(sources),
                }
            )

            return {
                'id': str(result.id),
                'question': result.question,
                'answer': result.answer,
                'sources': result.sources,
                'status': result.status,
            }

        except Exception as e:
            result.status = 'failed'
            result.metadata['error'] = str(e)
            await sync_to_async(result.save)(
                update_fields=['status', 'metadata', 'updated_at']
            )
            logger.warning(
                "companion_research_failed",
                extra={"thread_id": str(thread_id), "question": question[:80], "error": str(e)}
            )
            return None

    @staticmethod
    async def _do_research(
        question: str,
        search_query: str,
        project_id: Optional[uuid.UUID] = None,
    ) -> tuple[str, list]:
        """
        Perform the actual research.

        First tries project documents (if project_id is set),
        then falls back to LLM-based synthesis.

        Returns (answer, sources) where each source has a 'type' field:
        - 'project_chunk': Grounded in project documents
        - 'llm_knowledge': Synthesized from LLM training data (lower confidence)
        """
        sources = []
        has_grounded_sources = False

        # Try project document search if available
        if project_id:
            try:
                project_findings = await CompanionResearchAgent._search_project(
                    question=question,
                    project_id=project_id,
                )
                if project_findings:
                    sources.extend(project_findings)
                    has_grounded_sources = True
            except Exception as e:
                logger.debug(f"Project search failed: {e}")

        # Synthesize answer using LLM
        provider = get_llm_provider('fast')

        source_context = ""
        if sources:
            source_context = "\n\nRelevant findings from project documents:\n"
            for s in sources[:5]:
                source_context += f"- {s.get('title', 'Untitled')}: {s.get('snippet', '')}\n"

        synthesis_prompt = f"""Answer this factual question concisely (2-3 sentences max):

Question: {question}
{source_context}
If you have relevant information, provide a clear, factual answer.
If you don't have enough information, say so honestly.

Provide your answer as plain text, no JSON."""

        answer = await provider.generate(
            messages=[{"role": "user", "content": synthesis_prompt}],
            system_prompt="You are a factual research assistant. Be precise and concise.",
            max_tokens=512,
            temperature=0.2,
        )

        # If no grounded sources, tag the answer as LLM knowledge
        # so the frontend can indicate lower confidence
        if not has_grounded_sources:
            sources.append({
                'type': 'llm_knowledge',
                'title': 'AI knowledge',
                'snippet': 'This answer is based on AI training data, not verified sources.',
            })

        return answer.strip(), sources

    @staticmethod
    async def _search_project(
        question: str,
        project_id: uuid.UUID,
    ) -> list[dict]:
        """Search project documents for relevant information."""
        from apps.chat.retrieval import retrieve_document_context

        try:
            context = await sync_to_async(retrieve_document_context)(
                query=question,
                project_id=project_id,
            )
            if context:
                return [{
                    'type': 'project_chunk',
                    'title': 'Project documents',
                    'snippet': context[:500],
                }]
        except Exception as e:
            logger.debug("RAG retrieval for companion research failed: %s", e)
        return []


async def run_companion_research(
    thread_id: uuid.UUID,
    research_needs: list[dict],
    max_concurrent: int = 2,
) -> list[dict]:
    """
    Run research for multiple questions concurrently.

    Args:
        thread_id: Thread ID
        research_needs: List of {question, search_query, priority}
        max_concurrent: Max concurrent research tasks

    Returns:
        List of completed research result dicts
    """
    import asyncio

    # Sort by priority
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    sorted_needs = sorted(
        research_needs,
        key=lambda x: priority_order.get(x.get('priority', 'low'), 2)
    )

    # Limit to top items
    needs = sorted_needs[:max_concurrent]

    tasks = [
        CompanionResearchAgent.research_question(
            thread_id=thread_id,
            question=need['question'],
            search_query=need.get('search_query', need['question']),
        )
        for need in needs
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    completed = []
    for r in results:
        if isinstance(r, dict):
            completed.append(r)
        elif isinstance(r, Exception):
            logger.warning(f"Research task failed: {r}")

    return completed
