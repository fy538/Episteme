"""
Tests for AgentRegistry, AgentDescriptor, and SubAgentTool.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import TestCase

from apps.agents.registry import AgentRegistry, AgentDescriptor, _lazy_task
from apps.agents.sub_agent_tool import SubAgentTool, MAX_SUB_AGENT_DEPTH
from apps.agents.research_tools import SearchResult, resolve_tools_for_config
from apps.agents.research_config import SourcesConfig, SourceEntry


# ─── AgentDescriptor ──────────────────────────────────────────────────────


class AgentDescriptorTest(TestCase):
    """Test AgentDescriptor validation."""

    def test_validate_params_all_present(self):
        descriptor = AgentDescriptor(
            name="research",
            required_params=["case_id", "user_id"],
        )
        valid, missing = descriptor.validate_params({"case_id": "1", "user_id": 2})
        self.assertTrue(valid)
        self.assertEqual(missing, [])

    def test_validate_params_missing(self):
        descriptor = AgentDescriptor(
            name="research",
            required_params=["case_id", "user_id"],
        )
        valid, missing = descriptor.validate_params({"case_id": "1"})
        self.assertFalse(valid)
        self.assertEqual(missing, ["user_id"])

    def test_validate_params_no_required(self):
        descriptor = AgentDescriptor(name="simple")
        valid, missing = descriptor.validate_params({})
        self.assertTrue(valid)
        self.assertEqual(missing, [])


# ─── AgentRegistry ────────────────────────────────────────────────────────


class AgentRegistryTest(TestCase):
    """Test the singleton registry."""

    def setUp(self):
        # Clear registry before each test
        self.registry = AgentRegistry()
        self.registry.clear()

    def tearDown(self):
        self.registry.clear()

    def test_register_and_get(self):
        descriptor = AgentDescriptor(name="test_agent", description="A test agent")
        self.registry.register(descriptor)

        result = self.registry.get("test_agent")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "test_agent")

    def test_get_unknown_returns_none(self):
        result = self.registry.get("nonexistent")
        self.assertIsNone(result)

    def test_list_agents(self):
        self.registry.register(AgentDescriptor(name="a"))
        self.registry.register(AgentDescriptor(name="b"))

        agents = self.registry.list()
        self.assertEqual(len(agents), 2)
        names = {a.name for a in agents}
        self.assertEqual(names, {"a", "b"})

    def test_list_sub_agents(self):
        self.registry.register(AgentDescriptor(name="can_sub", can_be_sub_agent=True))
        self.registry.register(AgentDescriptor(name="no_sub", can_be_sub_agent=False))

        sub_agents = self.registry.list_sub_agents()
        self.assertEqual(len(sub_agents), 1)
        self.assertEqual(sub_agents[0].name, "can_sub")

    def test_register_overwrites(self):
        self.registry.register(AgentDescriptor(name="dup", description="first"))
        self.registry.register(AgentDescriptor(name="dup", description="second"))

        result = self.registry.get("dup")
        self.assertEqual(result.description, "second")

    def test_singleton(self):
        r1 = AgentRegistry()
        r2 = AgentRegistry()
        self.assertIs(r1, r2)

    def test_clear(self):
        self.registry.register(AgentDescriptor(name="clearme"))
        self.registry.clear()
        self.assertEqual(len(self.registry.list()), 0)


# ─── Lazy Task ────────────────────────────────────────────────────────────


class LazyTaskTest(TestCase):
    """Test _lazy_task deferred resolution."""

    def test_resolves_on_attribute_access(self):
        lazy = _lazy_task("json.dumps")
        # Accessing an attribute should resolve the module path
        # json.dumps is a function, so we test that it resolves
        result = lazy._resolve()
        import json
        self.assertIs(result, json.dumps)

    def test_repr(self):
        lazy = _lazy_task("some.module.task")
        self.assertIn("some.module.task", repr(lazy))


# ─── SubAgentTool ─────────────────────────────────────────────────────────


class SubAgentToolTest(TestCase):
    """Test SubAgentTool dispatch and safety."""

    def setUp(self):
        self.registry = AgentRegistry()
        self.registry.clear()

    def tearDown(self):
        self.registry.clear()

    def test_depth_exceeded_returns_empty(self):
        """Sub-agent at max depth should return empty results."""
        tool = SubAgentTool(
            agent_type="research",
            case_id="c1",
            user_id=1,
            depth=MAX_SUB_AGENT_DEPTH,
        )

        results = asyncio.run(tool.execute("test query"))
        self.assertEqual(results, [])

    def test_unknown_agent_returns_empty(self):
        """Unknown agent type should return empty results."""
        tool = SubAgentTool(
            agent_type="nonexistent",
            case_id="c1",
            user_id=1,
        )

        results = asyncio.run(tool.execute("test query"))
        self.assertEqual(results, [])

    def test_non_sub_agent_returns_empty(self):
        """Agent that can't be a sub-agent should return empty."""
        self.registry.register(AgentDescriptor(
            name="no_sub",
            can_be_sub_agent=False,
            entry_point=MagicMock(),
        ))

        tool = SubAgentTool(
            agent_type="no_sub",
            case_id="c1",
            user_id=1,
        )

        results = asyncio.run(tool.execute("test query"))
        self.assertEqual(results, [])

    def test_successful_sub_agent_returns_search_result(self):
        """Successful sub-agent should return a SearchResult."""
        mock_task = AsyncMock(return_value={
            "status": "completed",
            "artifact_id": "art-123",
        })

        self.registry.register(AgentDescriptor(
            name="research",
            can_be_sub_agent=True,
            entry_point=mock_task,
        ))

        tool = SubAgentTool(
            agent_type="research",
            case_id="c1",
            user_id=1,
        )

        results = asyncio.run(tool.execute("test query"))
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], SearchResult)
        self.assertIn("art-123", results[0].url)
        self.assertEqual(results[0].domain, "internal")

    def test_failed_sub_agent_returns_empty(self):
        """Sub-agent that returns failed status should return empty."""
        mock_task = AsyncMock(return_value={
            "status": "failed",
            "error": "something broke",
        })

        self.registry.register(AgentDescriptor(
            name="research",
            can_be_sub_agent=True,
            entry_point=mock_task,
        ))

        tool = SubAgentTool(
            agent_type="research",
            case_id="c1",
            user_id=1,
        )

        results = asyncio.run(tool.execute("test query"))
        self.assertEqual(results, [])

    def test_sub_agent_exception_returns_empty(self):
        """Sub-agent that raises should return empty, not crash."""
        mock_task = AsyncMock(side_effect=RuntimeError("kaboom"))

        self.registry.register(AgentDescriptor(
            name="research",
            can_be_sub_agent=True,
            entry_point=mock_task,
        ))

        tool = SubAgentTool(
            agent_type="research",
            case_id="c1",
            user_id=1,
        )

        results = asyncio.run(tool.execute("test query"))
        self.assertEqual(results, [])

    def test_tool_name_includes_agent_type(self):
        tool = SubAgentTool(agent_type="critique", case_id="c1", user_id=1)
        self.assertEqual(tool.name, "sub_agent_critique")


# ─── resolve_tools_for_config with sub_agents ─────────────────────────────


class ResolveToolsSubAgentTest(TestCase):
    """Test that resolve_tools_for_config includes SubAgentTool when configured."""

    def test_sub_agents_added_when_configured(self):
        config = SourcesConfig(
            primary=[SourceEntry(type="web")],
            sub_agents=["critique", "research"],
        )

        tools = resolve_tools_for_config(config, case_id="c1", user_id=1)
        tool_names = [t.name for t in tools]

        self.assertIn("web_search", tool_names)
        self.assertIn("sub_agent_critique", tool_names)
        self.assertIn("sub_agent_research", tool_names)

    def test_sub_agents_not_added_without_case_or_user(self):
        config = SourcesConfig(sub_agents=["critique"])

        # No case_id
        tools = resolve_tools_for_config(config, case_id=None, user_id=1)
        tool_names = [t.name for t in tools]
        self.assertNotIn("sub_agent_critique", tool_names)

        # No user_id
        tools = resolve_tools_for_config(config, case_id="c1", user_id=None)
        tool_names = [t.name for t in tools]
        self.assertNotIn("sub_agent_critique", tool_names)

    def test_no_sub_agents_by_default(self):
        config = SourcesConfig()
        tools = resolve_tools_for_config(config, case_id="c1", user_id=1)
        sub_agent_tools = [t for t in tools if t.name.startswith("sub_agent_")]
        self.assertEqual(len(sub_agent_tools), 0)
