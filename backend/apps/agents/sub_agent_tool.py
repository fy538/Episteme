"""
Sub-Agent Tool — wraps agent invocation as a ResearchTool.

Allows a research loop to spawn sub-agents (e.g. a critique agent)
through the standard tool interface. The sub-agent runs inline (async),
returning SearchResult objects.

Safety: depth cap (max 2) prevents circular invocation, and a timeout
prevents runaway sub-agents.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from .registry import AgentRegistry
from .research_tools import ResearchTool, SearchResult

logger = logging.getLogger(__name__)

# ─── Constants ─────────────────────────────────────────────────────────────

MAX_SUB_AGENT_DEPTH = 2
SUB_AGENT_TIMEOUT_SECONDS = 120


class SubAgentTool(ResearchTool):
    """
    A ResearchTool that dispatches to another registered agent.

    The sub-agent is invoked inline (not through Celery) so the parent
    loop can await results directly.
    """

    description = "Invoke a registered sub-agent for specialized analysis"

    def __init__(
        self,
        agent_type: str,
        case_id: str,
        user_id: int,
        depth: int = 0,
        timeout: int = SUB_AGENT_TIMEOUT_SECONDS,
    ):
        self.agent_type = agent_type
        self.name = f"sub_agent_{agent_type}"
        self.case_id = case_id
        self.user_id = user_id
        self.depth = depth
        self.timeout = timeout

    async def execute(
        self,
        query: str,
        domains: list[str] | None = None,
        excluded_domains: list[str] | None = None,
        max_results: int = 5,
    ) -> list[SearchResult]:
        """
        Run a sub-agent and convert its output to SearchResult objects.

        The sub-agent is called directly (not via Celery .delay()) to keep
        results in-process. A timeout prevents indefinite blocking.
        """
        # Depth check
        if self.depth >= MAX_SUB_AGENT_DEPTH:
            logger.warning(
                "sub_agent_depth_exceeded",
                extra={
                    "agent_type": self.agent_type,
                    "depth": self.depth,
                    "max_depth": MAX_SUB_AGENT_DEPTH,
                },
            )
            return []

        # Look up agent
        registry = AgentRegistry()
        descriptor = registry.get(self.agent_type)
        if not descriptor:
            logger.warning(
                "sub_agent_not_found",
                extra={"agent_type": self.agent_type},
            )
            return []

        if not descriptor.can_be_sub_agent:
            logger.warning(
                "sub_agent_not_allowed",
                extra={"agent_type": self.agent_type},
            )
            return []

        try:
            # Run the sub-agent inline with timeout.
            # We call the underlying async function directly (not .delay())
            # to get results in-process.
            entry = descriptor.entry_point
            # Resolve _lazy_task if needed
            if hasattr(entry, '_resolve'):
                entry = entry._resolve()

            result = await asyncio.wait_for(
                entry(
                    case_id=self.case_id,
                    topic=query,
                    user_id=self.user_id,
                ),
                timeout=self.timeout,
            )

            return self._result_to_search_results(result, query)

        except asyncio.TimeoutError:
            logger.warning(
                "sub_agent_timeout",
                extra={
                    "agent_type": self.agent_type,
                    "timeout": self.timeout,
                    "query": query,
                },
            )
            return []
        except Exception as e:
            logger.exception(
                "sub_agent_failed",
                extra={
                    "agent_type": self.agent_type,
                    "query": query,
                    "error": str(e),
                },
            )
            return []

    def _result_to_search_results(
        self, result: dict, query: str
    ) -> list[SearchResult]:
        """Convert a workflow result dict to SearchResult objects."""
        if not isinstance(result, dict):
            return []

        results = []

        document_id = result.get("document_id", "")
        status = result.get("status", "")

        if status != "completed" or not document_id:
            return []

        # The sub-agent produced a document — represent it as a search result
        results.append(SearchResult(
            url=f"document://{document_id}",
            title=f"Sub-agent ({self.agent_type}): {query[:100]}",
            snippet=f"Generated document {document_id} via {self.agent_type} agent",
            full_text="",  # Full text is in the document
            domain="internal",
            published_date="",
        ))

        return results
