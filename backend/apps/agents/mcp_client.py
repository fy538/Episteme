"""
MCP Client — connect to Model Context Protocol servers.

Supports stdio and SSE transports. Each client manages a single connection
to an MCP server, providing tool listing and invocation.

Reference: https://modelcontextprotocol.io
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Timeout for individual MCP tool calls
MCP_CALL_TIMEOUT_SECONDS = 30


@dataclass
class MCPToolDefinition:
    """A tool exposed by an MCP server."""
    name: str
    description: str = ""
    input_schema: dict = field(default_factory=dict)


@dataclass
class MCPToolResult:
    """Result from an MCP tool call."""
    content: str = ""
    is_error: bool = False
    metadata: dict = field(default_factory=dict)


class MCPClient:
    """
    Client for a single MCP server connection.

    Handles both stdio (command-based) and SSE (URL-based) transports.
    Falls back gracefully on connection failure.
    """

    def __init__(
        self,
        name: str,
        command: str = "",
        url: str = "",
        tool_filter: list[str] | None = None,
    ):
        self.name = name
        self.command = command
        self.url = url
        self.tool_filter = tool_filter or []
        self._connected = False
        self._tools: list[MCPToolDefinition] = []
        self._process: Optional[asyncio.subprocess.Process] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """
        Establish connection to the MCP server.

        For stdio: spawns the command as a subprocess.
        For SSE: opens an HTTP connection.

        Returns True if connection succeeded.
        """
        try:
            if self.command:
                return await self._connect_stdio()
            elif self.url:
                return await self._connect_sse()
            else:
                logger.warning(
                    "mcp_no_transport",
                    extra={"server": self.name, "hint": "Set command or url"},
                )
                return False
        except Exception as e:
            logger.exception(
                "mcp_connect_failed",
                extra={"server": self.name, "error": str(e)},
            )
            return False

    async def disconnect(self) -> None:
        """Close the connection to the MCP server."""
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except Exception:
                self._process.kill()
            self._process = None
        self._connected = False
        self._tools = []

    async def list_tools(self) -> list[MCPToolDefinition]:
        """
        List available tools from the MCP server.

        If tool_filter is set, only matching tools are returned.
        """
        if not self._connected:
            return []

        if self.tool_filter:
            return [t for t in self._tools if t.name in self.tool_filter]
        return list(self._tools)

    async def call_tool(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> MCPToolResult:
        """
        Invoke a tool on the MCP server.

        Returns MCPToolResult with content or error flag.
        """
        if not self._connected:
            return MCPToolResult(
                content="", is_error=True,
                metadata={"error": "Not connected to MCP server"},
            )

        try:
            if self._process:
                return await self._call_stdio(name, arguments or {})
            elif self.url:
                return await self._call_sse(name, arguments or {})
            return MCPToolResult(content="", is_error=True)
        except asyncio.TimeoutError:
            logger.warning(
                "mcp_call_timeout",
                extra={"server": self.name, "tool": name},
            )
            return MCPToolResult(
                content="", is_error=True,
                metadata={"error": f"Timeout calling {name}"},
            )
        except Exception as e:
            logger.exception(
                "mcp_call_failed",
                extra={"server": self.name, "tool": name, "error": str(e)},
            )
            return MCPToolResult(
                content="", is_error=True,
                metadata={"error": str(e)},
            )

    # ── Stdio Transport ──────────────────────────────────────────────────

    async def _connect_stdio(self) -> bool:
        """Spawn a subprocess and exchange MCP initialize messages."""
        parts = self.command.split()
        self._process = await asyncio.create_subprocess_exec(
            *parts,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "episteme", "version": "1.0"},
            },
        }
        response = await self._stdio_request(init_request)
        if not response:
            return False

        # Send initialized notification
        await self._stdio_notify({"jsonrpc": "2.0", "method": "notifications/initialized"})

        # List tools
        tools_response = await self._stdio_request({
            "jsonrpc": "2.0", "id": 2, "method": "tools/list",
        })
        if tools_response and "result" in tools_response:
            for tool_data in tools_response["result"].get("tools", []):
                self._tools.append(MCPToolDefinition(
                    name=tool_data.get("name", ""),
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {}),
                ))

        self._connected = True
        logger.info(
            "mcp_connected_stdio",
            extra={"server": self.name, "tools": len(self._tools)},
        )
        return True

    async def _stdio_request(self, message: dict) -> Optional[dict]:
        """Send a JSON-RPC request via stdio and read the response."""
        if not self._process or not self._process.stdin or not self._process.stdout:
            return None

        line = json.dumps(message) + "\n"
        self._process.stdin.write(line.encode())
        await self._process.stdin.drain()

        try:
            response_line = await asyncio.wait_for(
                self._process.stdout.readline(), timeout=MCP_CALL_TIMEOUT_SECONDS
            )
            if response_line:
                return json.loads(response_line.decode())
        except (asyncio.TimeoutError, json.JSONDecodeError):
            pass
        return None

    async def _stdio_notify(self, message: dict) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        if self._process and self._process.stdin:
            line = json.dumps(message) + "\n"
            self._process.stdin.write(line.encode())
            await self._process.stdin.drain()

    async def _call_stdio(self, name: str, arguments: dict) -> MCPToolResult:
        """Invoke a tool via stdio transport."""
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        response = await self._stdio_request(request)
        if not response or "result" not in response:
            error_msg = response.get("error", {}).get("message", "Unknown error") if response else "No response"
            return MCPToolResult(content="", is_error=True, metadata={"error": error_msg})

        result = response["result"]
        content_parts = result.get("content", [])
        text = "\n".join(
            part.get("text", "") for part in content_parts if part.get("type") == "text"
        )
        return MCPToolResult(
            content=text,
            is_error=result.get("isError", False),
        )

    # ── SSE Transport ────────────────────────────────────────────────────

    async def _connect_sse(self) -> bool:
        """Connect via SSE (HTTP) transport."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=MCP_CALL_TIMEOUT_SECONDS) as client:
                # Initialize
                resp = await client.post(
                    self.url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "episteme", "version": "1.0"},
                        },
                    },
                )
                resp.raise_for_status()

                # List tools
                resp = await client.post(
                    self.url,
                    json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                )
                resp.raise_for_status()
                data = resp.json()

                for tool_data in data.get("result", {}).get("tools", []):
                    self._tools.append(MCPToolDefinition(
                        name=tool_data.get("name", ""),
                        description=tool_data.get("description", ""),
                        input_schema=tool_data.get("inputSchema", {}),
                    ))

            self._connected = True
            logger.info(
                "mcp_connected_sse",
                extra={"server": self.name, "url": self.url, "tools": len(self._tools)},
            )
            return True

        except Exception as e:
            logger.exception(
                "mcp_sse_connect_failed",
                extra={"server": self.name, "url": self.url, "error": str(e)},
            )
            return False

    async def _call_sse(self, name: str, arguments: dict) -> MCPToolResult:
        """Invoke a tool via SSE (HTTP) transport."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=MCP_CALL_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    self.url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {"name": name, "arguments": arguments},
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            result = data.get("result", {})
            content_parts = result.get("content", [])
            text = "\n".join(
                part.get("text", "") for part in content_parts if part.get("type") == "text"
            )
            return MCPToolResult(
                content=text,
                is_error=result.get("isError", False),
            )

        except Exception as e:
            return MCPToolResult(
                content="", is_error=True,
                metadata={"error": str(e)},
            )
