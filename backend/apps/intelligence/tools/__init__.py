"""
Tool Actions — AI-initiated actions during conversation.

Provides a registry of typed tool schemas with permission levels,
an executor that dispatches to existing service methods, and
prompt generation for teaching the LLM about available tools.

Architecture: The LLM emits a <tool_actions> JSON section (same
pattern as <graph_edits>, <plan_edits>) which is parsed post-stream,
then executed or queued for user confirmation.
"""

from .registry import ToolRegistry, ToolPermission, ToolDefinition, ToolResult
from .schemas import register_all_tools

# Auto-register tool definitions on import
register_all_tools()

__all__ = [
    'ToolRegistry',
    'ToolPermission',
    'ToolDefinition',
    'ToolResult',
]
