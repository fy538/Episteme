"""
MCP Research Tool — wraps an MCP server's tools as a ResearchTool.

Normalizes MCP tool responses to SearchResult objects, making MCP servers
pluggable into the research loop's tool interface.

Usage in skill config:
    sources:
      mcp_servers:
        - name: westlaw
          url: https://mcp.westlaw.com/sse
          tool_filter: [search_cases, get_case_text]
"""
from __future__ import annotations

import logging
from typing import Any

from .mcp_client import MCPClient, MCPToolResult
from .research_tools import ResearchTool, SearchResult

logger = logging.getLogger(__name__)


class MCPResearchTool(ResearchTool):
    """
    Wraps an MCP server as a ResearchTool for the research loop.

    Each MCPResearchTool corresponds to one MCP server and one search tool
    on that server. Tool results are normalized to SearchResult objects.
    """

    def __init__(
        self,
        client: MCPClient,
        tool_name: str = "",
        server_name: str = "",
    ):
        self.client = client
        self.tool_name = tool_name or "search"
        self.name = f"mcp_{server_name or client.name}"
        self.description = f"Search via MCP server: {server_name or client.name}"

    async def execute(
        self,
        query: str,
        domains: list[str] | None = None,
        excluded_domains: list[str] | None = None,
        max_results: int = 5,
    ) -> list[SearchResult]:
        """
        Execute a search via the MCP server.

        Maps generic search parameters to MCP tool arguments and normalizes
        the response to SearchResult objects.
        """
        if not self.client.is_connected:
            connected = await self.client.connect()
            if not connected:
                logger.warning(
                    "mcp_tool_not_connected",
                    extra={"server": self.client.name, "tool": self.tool_name},
                )
                return []

        # Build MCP tool arguments
        arguments: dict[str, Any] = {
            "query": query,
            "max_results": max_results,
        }
        if domains:
            arguments["domains"] = domains
        if excluded_domains:
            arguments["excluded_domains"] = excluded_domains

        result = await self.client.call_tool(self.tool_name, arguments)

        if result.is_error:
            logger.warning(
                "mcp_tool_error",
                extra={
                    "server": self.client.name,
                    "tool": self.tool_name,
                    "error": result.metadata.get("error", ""),
                },
            )
            return []

        return self._normalize_results(result, query)

    def _normalize_results(
        self, result: MCPToolResult, query: str
    ) -> list[SearchResult]:
        """
        Convert MCP tool output to SearchResult objects.

        MCP tools may return structured or plain text. This method
        attempts to parse structured results first, falling back to
        wrapping plain text as a single result.
        """
        if not result.content:
            return []

        # Try parsing as JSON array of results
        try:
            import json
            data = json.loads(result.content)

            if isinstance(data, list):
                return [
                    self._item_to_search_result(item)
                    for item in data[:10]  # Cap at 10 results
                ]
            elif isinstance(data, dict):
                # Single result or wrapper with "results" key
                items = data.get("results", [data])
                return [
                    self._item_to_search_result(item)
                    for item in items[:10]
                ]
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: wrap plain text as a single result
        return [SearchResult(
            url=f"mcp://{self.client.name}/{self.tool_name}",
            title=f"MCP result: {query[:100]}",
            snippet=result.content[:500],
            full_text=result.content[:3000],
            domain=self.client.name,
            published_date="",
        )]

    def _item_to_search_result(self, item: dict) -> SearchResult:
        """Convert a single structured MCP item to SearchResult."""
        return SearchResult(
            url=item.get("url", item.get("link", f"mcp://{self.client.name}")),
            title=item.get("title", item.get("name", "")),
            snippet=item.get("snippet", item.get("summary", item.get("text", "")))[:500],
            full_text=item.get("full_text", item.get("content", item.get("text", "")))[:3000],
            domain=item.get("domain", self.client.name),
            published_date=item.get("published_date", item.get("date", "")),
        )
