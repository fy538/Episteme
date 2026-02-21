"""
Tool Registry — typed tool definitions with permission levels.

Each tool maps to an existing service method (CaseService, InquiryService,
PlanService, DecisionService, GraphService). The registry makes tools
discoverable by the prompt builder and executor.

Permission levels:
  AUTO_EXECUTE — safe operations (create inquiry, add evidence, update stage)
  CONFIRM_REQUIRED — impactful operations (record decision, resolve inquiry, create case)
"""

import json
import uuid
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class ToolPermission(Enum):
    """Permission level for tool execution."""
    AUTO_EXECUTE = "auto"        # Executed immediately after LLM response
    CONFIRM_REQUIRED = "confirm"  # Shown to user for approval first


@dataclass
class ToolDefinition:
    """
    Definition of a tool available to the LLM.

    Attributes:
        name: Unique tool identifier (e.g. "create_inquiry")
        description: Human-readable description shown to LLM
        parameters: JSON Schema for tool parameters
        permission: AUTO_EXECUTE or CONFIRM_REQUIRED
        required_context: Context keys that must be present (e.g. ["case_id"])
        service_method: Dotted path to service method for documentation
        display_name: Short name for frontend cards (e.g. "Create Inquiry")
    """
    name: str
    description: str
    parameters: Dict[str, Any]
    permission: ToolPermission
    required_context: List[str] = field(default_factory=list)
    service_method: str = ""
    display_name: str = ""

    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.name.replace('_', ' ').title()


@dataclass
class ToolResult:
    """
    Result of a tool execution or confirmation request.

    For auto-executed tools:
        success=True/False, output={...}, error=None/str

    For confirmation-required tools:
        success=True, pending_confirmation=True, confirmation_id=str
    """
    success: bool
    tool_name: str = ""
    display_name: str = ""
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    pending_confirmation: bool = False
    confirmation_id: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""

    def __post_init__(self):
        if self.pending_confirmation and not self.confirmation_id:
            self.confirmation_id = str(uuid.uuid4())


class ToolRegistry:
    """
    Singleton registry of available tools.

    Tools are registered at import time (see schemas.py) and looked up
    at runtime based on conversation context (case_id, project_id, etc.).
    """

    _tools: Dict[str, ToolDefinition] = {}

    # M3: section markers that tool descriptions must not contain
    _FORBIDDEN_MARKERS = [
        '<tool_actions>', '</tool_actions>',
        '<response>', '</response>',
        '<reflection>', '</reflection>',
        '<graph_edits>', '</graph_edits>',
        '<plan_edits>', '</plan_edits>',
        '<orientation_edits>', '</orientation_edits>',
        '<action_hints>', '</action_hints>',
    ]

    @classmethod
    def register(cls, tool: ToolDefinition):
        """Register a tool definition. Validates against section marker injection."""
        # M3: prevent tool descriptions from containing section markers
        for marker in cls._FORBIDDEN_MARKERS:
            if marker in tool.description:
                raise ValueError(
                    f"Tool '{tool.name}' description contains forbidden marker: {marker}"
                )
        cls._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name} ({tool.permission.value})")

    @classmethod
    def get(cls, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return cls._tools.get(name)

    @classmethod
    def all_tools(cls) -> List[ToolDefinition]:
        """Return all registered tools."""
        return list(cls._tools.values())

    @classmethod
    def get_available(cls, context: Dict[str, Any]) -> List[ToolDefinition]:
        """
        Return tools whose required_context is satisfied.

        Args:
            context: Dict with keys like 'case_id', 'project_id', etc.
                     Values must be truthy for context to be "satisfied".

        Returns:
            List of ToolDefinition objects available in this context.
        """
        return [
            tool for tool in cls._tools.values()
            if all(key in context and context[key] is not None for key in tool.required_context)
        ]

    @classmethod
    def get_prompt_text(cls, available_tools: List[ToolDefinition]) -> str:
        """
        Generate prompt text describing available tools for the LLM.

        Formats tool descriptions with parameter schemas and permission
        labels so the LLM knows what it can emit in <tool_actions>.

        Args:
            available_tools: List of tools available in current context.

        Returns:
            Formatted prompt text string.
        """
        if not available_tools:
            return ""

        lines = []
        for tool in available_tools:
            permission_label = (
                "[auto]" if tool.permission == ToolPermission.AUTO_EXECUTE
                else "[requires confirmation]"
            )
            lines.append(f"- {tool.name} {permission_label}: {tool.description}")

            # Add parameter descriptions
            props = tool.parameters.get('properties', {})
            required = tool.parameters.get('required', [])
            if props:
                for param_name, param_schema in props.items():
                    req_marker = " (required)" if param_name in required else ""
                    param_type = param_schema.get('type', 'string')
                    param_desc = param_schema.get('description', '')
                    lines.append(f"    - {param_name}: {param_type}{req_marker} — {param_desc}")

        return "\n".join(lines)

    @classmethod
    def clear(cls):
        """Clear all registered tools (for testing)."""
        cls._tools.clear()
