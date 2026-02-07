"""
Tests for MCP client and MCPResearchTool.
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import TestCase

from apps.agents.mcp_client import MCPClient, MCPToolDefinition, MCPToolResult
from apps.agents.mcp_tool import MCPResearchTool
from apps.agents.research_tools import SearchResult, resolve_tools_for_config
from apps.agents.research_config import SourcesConfig, MCPServerConfig


# ─── MCPClient ────────────────────────────────────────────────────────────


class MCPClientTest(TestCase):
    """Test MCPClient connection and tool listing."""

    def test_not_connected_by_default(self):
        client = MCPClient(name="test")
        self.assertFalse(client.is_connected)

    def test_no_transport_returns_false(self):
        """Client with no command or url should fail to connect."""
        client = MCPClient(name="empty")
        result = asyncio.run(client.connect())
        self.assertFalse(result)

    def test_list_tools_when_not_connected(self):
        client = MCPClient(name="test")
        tools = asyncio.run(client.list_tools())
        self.assertEqual(tools, [])

    def test_call_tool_when_not_connected(self):
        client = MCPClient(name="test")
        result = asyncio.run(client.call_tool("search", {"query": "test"}))
        self.assertTrue(result.is_error)

    def test_tool_filter(self):
        """Only filtered tools should be returned."""
        client = MCPClient(name="test", tool_filter=["search_cases"])
        client._connected = True
        client._tools = [
            MCPToolDefinition(name="search_cases"),
            MCPToolDefinition(name="get_case_text"),
            MCPToolDefinition(name="other_tool"),
        ]

        tools = asyncio.run(client.list_tools())
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].name, "search_cases")

    def test_list_all_tools_when_no_filter(self):
        client = MCPClient(name="test")
        client._connected = True
        client._tools = [
            MCPToolDefinition(name="a"),
            MCPToolDefinition(name="b"),
        ]

        tools = asyncio.run(client.list_tools())
        self.assertEqual(len(tools), 2)

    def test_disconnect(self):
        client = MCPClient(name="test")
        client._connected = True
        asyncio.run(client.disconnect())
        self.assertFalse(client.is_connected)


# ─── MCPResearchTool ──────────────────────────────────────────────────────


class MCPResearchToolTest(TestCase):
    """Test MCPResearchTool normalization."""

    def test_name_includes_server(self):
        client = MCPClient(name="westlaw")
        tool = MCPResearchTool(client=client, server_name="westlaw")
        self.assertEqual(tool.name, "mcp_westlaw")

    def test_structured_json_results(self):
        """JSON array results should be normalized to SearchResult."""
        client = MagicMock()
        client.name = "test_server"
        client.is_connected = True
        client.call_tool = AsyncMock(return_value=MCPToolResult(
            content=json.dumps([
                {
                    "url": "https://case.com/123",
                    "title": "Smith v. Jones",
                    "snippet": "Key holding about X.",
                    "domain": "case.com",
                },
                {
                    "url": "https://case.com/456",
                    "title": "Doe v. Roe",
                    "snippet": "Another key holding.",
                },
            ]),
            is_error=False,
        ))

        tool = MCPResearchTool(client=client, tool_name="search", server_name="test")
        results = asyncio.run(tool.execute("search query"))

        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], SearchResult)
        self.assertEqual(results[0].title, "Smith v. Jones")
        self.assertEqual(results[1].title, "Doe v. Roe")

    def test_plain_text_result(self):
        """Plain text should be wrapped as a single SearchResult."""
        client = MagicMock()
        client.name = "test_server"
        client.is_connected = True
        client.call_tool = AsyncMock(return_value=MCPToolResult(
            content="This is the full text of a legal case about X.",
            is_error=False,
        ))

        tool = MCPResearchTool(client=client, tool_name="get_text", server_name="test")
        results = asyncio.run(tool.execute("find case about X"))

        self.assertEqual(len(results), 1)
        self.assertIn("legal case", results[0].snippet)

    def test_error_result_returns_empty(self):
        """Error from MCP server should return empty results."""
        client = MagicMock()
        client.name = "test_server"
        client.is_connected = True
        client.call_tool = AsyncMock(return_value=MCPToolResult(
            content="",
            is_error=True,
            metadata={"error": "Server unavailable"},
        ))

        tool = MCPResearchTool(client=client, tool_name="search", server_name="test")
        results = asyncio.run(tool.execute("test query"))
        self.assertEqual(results, [])

    def test_empty_content_returns_empty(self):
        """Empty content should return empty results."""
        client = MagicMock()
        client.name = "test_server"
        client.is_connected = True
        client.call_tool = AsyncMock(return_value=MCPToolResult(content="", is_error=False))

        tool = MCPResearchTool(client=client, tool_name="search", server_name="test")
        results = asyncio.run(tool.execute("test"))
        self.assertEqual(results, [])

    def test_auto_connect_on_execute(self):
        """Tool should auto-connect if not connected."""
        client = MagicMock()
        client.name = "test_server"
        client.is_connected = False
        client.connect = AsyncMock(return_value=True)
        client.call_tool = AsyncMock(return_value=MCPToolResult(content="text", is_error=False))

        tool = MCPResearchTool(client=client, tool_name="search", server_name="test")
        results = asyncio.run(tool.execute("test"))

        client.connect.assert_called_once()
        self.assertEqual(len(results), 1)

    def test_auto_connect_failure_returns_empty(self):
        """Failed auto-connect should return empty results."""
        client = MagicMock()
        client.name = "test_server"
        client.is_connected = False
        client.connect = AsyncMock(return_value=False)

        tool = MCPResearchTool(client=client, tool_name="search", server_name="test")
        results = asyncio.run(tool.execute("test"))
        self.assertEqual(results, [])

    def test_dict_wrapper_results(self):
        """JSON dict with 'results' key should be normalized."""
        client = MagicMock()
        client.name = "test_server"
        client.is_connected = True
        client.call_tool = AsyncMock(return_value=MCPToolResult(
            content=json.dumps({
                "results": [
                    {"title": "Result A", "url": "https://a.com"},
                    {"title": "Result B", "url": "https://b.com"},
                ],
            }),
            is_error=False,
        ))

        tool = MCPResearchTool(client=client, tool_name="search", server_name="test")
        results = asyncio.run(tool.execute("test"))
        self.assertEqual(len(results), 2)


# ─── MCPServerConfig ──────────────────────────────────────────────────────


class MCPServerConfigTest(TestCase):
    """Test MCPServerConfig parsing."""

    def test_from_dict(self):
        config = MCPServerConfig.from_dict({
            "name": "westlaw",
            "url": "https://mcp.westlaw.com/sse",
            "tool_filter": ["search_cases"],
        })
        self.assertEqual(config.name, "westlaw")
        self.assertEqual(config.url, "https://mcp.westlaw.com/sse")
        self.assertEqual(config.tool_filter, ["search_cases"])

    def test_from_string(self):
        config = MCPServerConfig.from_dict("simple_server")
        self.assertEqual(config.name, "simple_server")
        self.assertEqual(config.command, "")
        self.assertEqual(config.url, "")

    def test_stdio_config(self):
        config = MCPServerConfig.from_dict({
            "name": "edgar",
            "command": "npx -y @sec/edgar-mcp-server",
        })
        self.assertEqual(config.name, "edgar")
        self.assertEqual(config.command, "npx -y @sec/edgar-mcp-server")


# ─── resolve_tools_for_config with MCP ────────────────────────────────────


class ResolveToolsMCPTest(TestCase):
    """Test that resolve_tools_for_config includes MCP tools."""

    def test_mcp_tools_added(self):
        config = SourcesConfig(
            mcp_servers=[
                MCPServerConfig(name="westlaw", url="https://mcp.westlaw.com/sse", tool_filter=["search_cases"]),
            ],
        )

        tools = resolve_tools_for_config(config)
        mcp_tools = [t for t in tools if t.name.startswith("mcp_")]
        self.assertEqual(len(mcp_tools), 1)
        self.assertEqual(mcp_tools[0].name, "mcp_westlaw")

    def test_no_mcp_by_default(self):
        config = SourcesConfig()
        tools = resolve_tools_for_config(config)
        mcp_tools = [t for t in tools if t.name.startswith("mcp_")]
        self.assertEqual(len(mcp_tools), 0)

    def test_multiple_mcp_servers(self):
        config = SourcesConfig(
            mcp_servers=[
                MCPServerConfig(name="westlaw", url="https://mcp.westlaw.com"),
                MCPServerConfig(name="edgar", command="npx edgar-server"),
            ],
        )

        tools = resolve_tools_for_config(config)
        mcp_tools = [t for t in tools if t.name.startswith("mcp_")]
        self.assertEqual(len(mcp_tools), 2)
        names = {t.name for t in mcp_tools}
        self.assertEqual(names, {"mcp_westlaw", "mcp_edgar"})
