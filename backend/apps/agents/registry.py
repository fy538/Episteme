"""
Agent Registry — pluggable agent dispatch replacing hardcoded if/elif.

Each agent type is described by an AgentDescriptor and registered at
app startup. The orchestrator uses ``registry.get(agent_type)`` to
dispatch to the correct Celery task.

Sub-agents can also be discovered through the registry, enabling
hierarchical agent composition.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentDescriptor:
    """Metadata describing a registered agent type."""

    name: str  # e.g. "research", "critique", "brief"
    description: str = ""
    entry_point: Any = None  # Celery shared_task
    accepts_params: list[str] = field(default_factory=list)
    can_be_sub_agent: bool = False
    required_params: list[str] = field(default_factory=list)

    def validate_params(self, params: dict) -> tuple[bool, list[str]]:
        """Check that required params are present."""
        missing = [p for p in self.required_params if p not in params]
        return len(missing) == 0, missing


class AgentRegistry:
    """
    Singleton registry for agent types.

    Usage:
        registry = AgentRegistry()
        registry.register(AgentDescriptor(name="research", ...))
        descriptor = registry.get("research")
    """

    _instance: Optional[AgentRegistry] = None

    def __new__(cls) -> AgentRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
        return cls._instance

    def register(self, descriptor: AgentDescriptor) -> None:
        """Register an agent descriptor."""
        if descriptor.name in self._agents:
            logger.warning(
                "agent_registry_overwrite",
                extra={"agent_name": descriptor.name},
            )
        self._agents[descriptor.name] = descriptor
        logger.info(
            "agent_registered",
            extra={
                "agent_name": descriptor.name,
                "can_be_sub_agent": descriptor.can_be_sub_agent,
            },
        )

    def get(self, agent_type: str) -> Optional[AgentDescriptor]:
        """Look up an agent descriptor by type name."""
        return self._agents.get(agent_type)

    def list(self) -> list[AgentDescriptor]:
        """Return all registered agent descriptors."""
        return list(self._agents.values())

    def list_sub_agents(self) -> list[AgentDescriptor]:
        """Return only agents that can be used as sub-agents."""
        return [d for d in self._agents.values() if d.can_be_sub_agent]

    def clear(self) -> None:
        """Clear all registrations (for testing)."""
        self._agents.clear()


# ─── Default Registrations ────────────────────────────────────────────────


def register_default_agents() -> None:
    """
    Register the built-in agent types.

    Called from apps.agents.apps.AgentsConfig.ready() at Django startup.
    Lazy-imports Celery tasks to avoid circular imports.
    """
    registry = AgentRegistry()

    # Research agent (v2 loop → WorkingDocument)
    registry.register(AgentDescriptor(
        name="research",
        description="Multi-step research loop: Plan → Search → Extract → Evaluate → Synthesize",
        entry_point=_lazy_task("apps.agents.research_workflow.generate_research_document"),
        accepts_params=["topic", "case_id", "user_id", "correlation_id", "placeholder_message_id", "graph_context"],
        required_params=["case_id", "user_id"],
        can_be_sub_agent=True,
    ))

    # Critique agent — REMOVED (feature cut)
    # Brief agent — REMOVED (briefs are now generated via WorkingDocument system)

    logger.info("default_agents_registered", extra={"count": len(registry.list())})


class _lazy_task:
    """
    Deferred Celery task reference to avoid circular imports at module level.

    Resolves the actual task object on first attribute access (e.g. .delay()).
    """

    def __init__(self, task_path: str):
        self._task_path = task_path
        self._resolved: Any = None

    def _resolve(self) -> Any:
        if self._resolved is None:
            module_path, task_name = self._task_path.rsplit(".", 1)
            import importlib
            module = importlib.import_module(module_path)
            self._resolved = getattr(module, task_name)
        return self._resolved

    def __getattr__(self, name: str) -> Any:
        return getattr(self._resolve(), name)

    def __repr__(self) -> str:
        return f"_lazy_task({self._task_path!r})"
