"""
Research tools — pluggable search backends for the research loop.

Tools are the interface between the research loop and the outside world.
The loop calls tools with queries; tools return SearchResult objects.
Source type mapping happens here: the config says "sec_filings",
the tool maps that to the right API/domain filter.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .research_config import SourcesConfig

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single result from a search tool."""
    url: str
    title: str
    snippet: str
    full_text: str = ""
    domain: str = ""
    published_date: str = ""

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "full_text": self.full_text,
            "domain": self.domain,
            "published_date": self.published_date,
        }


class ResearchTool(ABC):
    """Base class for research tools."""

    name: str = ""
    description: str = ""

    @abstractmethod
    async def execute(
        self,
        query: str,
        domains: list[str] | None = None,
        excluded_domains: list[str] | None = None,
        max_results: int = 5,
    ) -> list[SearchResult]:
        """
        Execute a search query.

        Args:
            query: Search query string
            domains: Optional list of domains to restrict search to
            excluded_domains: Domains to exclude from results
            max_results: Maximum number of results to return

        Returns:
            List of SearchResult objects
        """
        ...


class WebSearchTool(ResearchTool):
    """
    Web search using the best available provider.

    Priority: Exa API > Tavily API > Perplexity Sonar > fallback to LLM knowledge.
    Falls back gracefully if no search API is configured.
    """

    name = "web_search"
    description = "Search the web for information on any topic"

    async def execute(
        self,
        query: str,
        domains: list[str] | None = None,
        excluded_domains: list[str] | None = None,
        max_results: int = 5,
    ) -> list[SearchResult]:
        """Execute web search using the best available provider."""
        from django.conf import settings

        # Try Exa first
        exa_key = getattr(settings, "EXA_API_KEY", None)
        if exa_key:
            return await self._search_exa(query, domains, excluded_domains, max_results, exa_key)

        # Try Tavily
        tavily_key = getattr(settings, "TAVILY_API_KEY", None)
        if tavily_key:
            return await self._search_tavily(query, domains, excluded_domains, max_results, tavily_key)

        # Fallback: return empty (the LLM will use its training knowledge)
        logger.warning(
            "no_search_api_configured",
            extra={"query": query, "hint": "Set EXA_API_KEY or TAVILY_API_KEY for web search"},
        )
        return []

    async def _search_exa(
        self, query: str, domains: list[str] | None,
        excluded_domains: list[str] | None, max_results: int, api_key: str,
    ) -> list[SearchResult]:
        """Search using Exa API."""
        try:
            import httpx

            headers = {"x-api-key": api_key, "Content-Type": "application/json"}
            payload = {
                "query": query,
                "num_results": max_results,
                "type": "auto",
                "contents": {"text": {"maxCharacters": 3000}},
            }
            if domains:
                payload["includeDomains"] = domains
            if excluded_domains:
                payload["excludeDomains"] = excluded_domains

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.exa.ai/search",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

            results = []
            for r in data.get("results", []):
                url = r.get("url", "")
                results.append(SearchResult(
                    url=url,
                    title=r.get("title", ""),
                    snippet=r.get("text", "")[:500],
                    full_text=r.get("text", ""),
                    domain=_extract_domain(url),
                    published_date=r.get("publishedDate", ""),
                ))
            return results

        except Exception as e:
            logger.exception("exa_search_failed", extra={"query": query, "error": str(e)})
            return []

    async def _search_tavily(
        self, query: str, domains: list[str] | None,
        excluded_domains: list[str] | None, max_results: int, api_key: str,
    ) -> list[SearchResult]:
        """Search using Tavily API."""
        try:
            import httpx

            payload = {
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "include_raw_content": True,
                "search_depth": "advanced",
            }
            if domains:
                payload["include_domains"] = domains
            if excluded_domains:
                payload["exclude_domains"] = excluded_domains

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

            results = []
            for r in data.get("results", []):
                url = r.get("url", "")
                full_text = r.get("raw_content", "") or r.get("content", "")
                results.append(SearchResult(
                    url=url,
                    title=r.get("title", ""),
                    snippet=r.get("content", "")[:500],
                    full_text=full_text[:3000],
                    domain=_extract_domain(url),
                    published_date=r.get("published_date", ""),
                ))
            return results

        except Exception as e:
            logger.exception("tavily_search_failed", extra={"query": query, "error": str(e)})
            return []


class DocumentSearchTool(ResearchTool):
    """
    Search uploaded project documents via embeddings.

    Uses existing Episteme document chunking and vector search.
    """

    name = "document_search"
    description = "Search uploaded project documents for relevant information"

    def __init__(self, case_id: str | None = None):
        self.case_id = case_id

    async def execute(
        self,
        query: str,
        domains: list[str] | None = None,
        excluded_domains: list[str] | None = None,
        max_results: int = 5,
    ) -> list[SearchResult]:
        """Search project documents using embedding similarity."""
        if not self.case_id:
            return []

        try:
            from apps.common.embeddings import generate_embedding
            from apps.projects.models import DocumentChunk

            # Generate query embedding
            query_embedding = generate_embedding(query)

            # Search for similar chunks
            # Uses pgvector cosine similarity
            chunks = (
                DocumentChunk.objects
                .filter(document__case_id=self.case_id)
                .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
                [:max_results]
            )

            results = []
            for chunk in chunks:
                results.append(SearchResult(
                    url=f"document://{chunk.document_id}#chunk-{chunk.id}",
                    title=chunk.document.title if hasattr(chunk, "document") else "Project Document",
                    snippet=chunk.text[:500],
                    full_text=chunk.text,
                    domain="internal",
                    published_date="",
                ))
            return results

        except Exception as e:
            logger.exception(
                "document_search_failed",
                extra={"query": query, "case_id": self.case_id, "error": str(e)},
            )
            return []


# ─── Utilities ──────────────────────────────────────────────────────────────

def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc or ""
    except Exception:
        return ""


def resolve_tools_for_config(
    sources_config: SourcesConfig,
    case_id: str | None = None,
    user_id: int | None = None,
) -> list[ResearchTool]:
    """
    Build the list of tools based on source configuration.

    Maps semantic source types to available tools.
    """
    tools: list[ResearchTool] = []

    # Always include web search (the universal fallback)
    tools.append(WebSearchTool())

    # Include document search if we have a case context
    if case_id:
        tools.append(DocumentSearchTool(case_id=case_id))

    # Sub-agent tools (when config declares sub_agents)
    if sources_config.sub_agents and case_id and user_id:
        from .sub_agent_tool import SubAgentTool

        for agent_type in sources_config.sub_agents:
            tools.append(SubAgentTool(
                agent_type=agent_type,
                case_id=case_id,
                user_id=user_id,
            ))

    # MCP tool resolution
    if sources_config.mcp_servers:
        from .mcp_client import MCPClient
        from .mcp_tool import MCPResearchTool

        for mcp_config in sources_config.mcp_servers:
            client = MCPClient(
                name=mcp_config.name,
                command=mcp_config.command,
                url=mcp_config.url,
                tool_filter=mcp_config.tool_filter,
            )
            # Use first tool in filter as the search tool, or "search" as default
            tool_name = mcp_config.tool_filter[0] if mcp_config.tool_filter else "search"
            tools.append(MCPResearchTool(
                client=client,
                tool_name=tool_name,
                server_name=mcp_config.name,
            ))

    return tools
