"""
Tests for TrajectoryRecorder and research loop trajectory integration.
"""
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import TestCase

from apps.agents.trajectory import (
    TrajectoryEvent,
    TrajectoryRecorder,
    MAX_PROMPT_CHARS,
)
from apps.agents.research_config import ResearchConfig
from apps.agents.research_loop import ResearchLoop, ResearchContext, ResearchResult
from apps.agents.research_tools import SearchResult
from .helpers import make_test_provider, make_test_tool


# ─── TrajectoryEvent ──────────────────────────────────────────────────────


class TrajectoryEventTest(TestCase):
    """Test TrajectoryEvent serialization."""

    def test_to_dict(self):
        event = TrajectoryEvent(
            step_name="plan",
            input_summary="Question: What is X?",
            output_summary="3 sub-queries",
            decision_rationale="Simple decomposition",
            metrics={"sub_queries": 3},
            duration_ms=150,
        )
        d = event.to_dict()
        self.assertEqual(d["step_name"], "plan")
        self.assertEqual(d["metrics"]["sub_queries"], 3)

    def test_truncation(self):
        """Long fields should be truncated to MAX_PROMPT_CHARS."""
        long_text = "x" * (MAX_PROMPT_CHARS + 500)
        event = TrajectoryEvent(
            step_name="test",
            input_summary=long_text,
            output_summary=long_text,
            decision_rationale=long_text,
        )
        d = event.to_dict()
        self.assertEqual(len(d["input_summary"]), MAX_PROMPT_CHARS)
        self.assertEqual(len(d["output_summary"]), MAX_PROMPT_CHARS)
        self.assertEqual(len(d["decision_rationale"]), MAX_PROMPT_CHARS)


# ─── TrajectoryRecorder ──────────────────────────────────────────────────


class TrajectoryRecorderTest(TestCase):
    """Test the recorder's record/finalize/save lifecycle."""

    def test_record_and_finalize(self):
        recorder = TrajectoryRecorder(correlation_id="test-123")
        recorder.record_step("plan", input_summary="Q", output_summary="3 queries")
        recorder.record_step("search", metrics={"results": 10})

        result = recorder.finalize()
        self.assertEqual(result["correlation_id"], "test-123")
        self.assertEqual(result["total_steps"], 2)
        self.assertEqual(len(result["events"]), 2)
        self.assertEqual(result["events"][0]["step_name"], "plan")
        self.assertEqual(result["events"][1]["step_name"], "search")

    def test_finalize_empty(self):
        recorder = TrajectoryRecorder()
        result = recorder.finalize()
        self.assertEqual(result["total_steps"], 0)
        self.assertEqual(result["events"], [])

    def test_events_property(self):
        recorder = TrajectoryRecorder()
        recorder.record_step("step1")
        recorder.record_step("step2")
        events = recorder.events
        self.assertEqual(len(events), 2)
        # Should return a copy
        events.clear()
        self.assertEqual(len(recorder.events), 2)

    def test_record_with_event_object(self):
        recorder = TrajectoryRecorder()
        event = TrajectoryEvent(step_name="custom", duration_ms=42)
        recorder.record(event)
        self.assertEqual(len(recorder.events), 1)
        self.assertEqual(recorder.events[0].step_name, "custom")
        # timestamp should have been auto-filled
        self.assertTrue(len(recorder.events[0].timestamp) > 0)

    @patch("apps.agents.trajectory.EventService")
    def test_save_to_events(self, mock_event_service):
        recorder = TrajectoryRecorder(correlation_id="save-test")
        recorder.record_step("plan")
        recorder.save_to_events(case_id="case-1")

        mock_event_service.append.assert_called_once()
        call_kwargs = mock_event_service.append.call_args
        # Verify event type is AGENT_TRAJECTORY
        self.assertIn("AGENT_TRAJECTORY", str(call_kwargs))

    @patch("apps.agents.trajectory.EventService")
    def test_save_handles_failure(self, mock_event_service):
        """save_to_events is best-effort."""
        mock_event_service.append.side_effect = RuntimeError("DB down")

        recorder = TrajectoryRecorder(correlation_id="fail")
        recorder.record_step("plan")
        # Should not raise
        recorder.save_to_events()

    def test_duration_tracking(self):
        recorder = TrajectoryRecorder()
        time.sleep(0.01)  # Tiny delay
        result = recorder.finalize()
        self.assertGreater(result["total_duration_ms"], 0)


# ─── Loop Trajectory Integration ─────────────────────────────────────────


class LoopTrajectoryIntegrationTest(TestCase):
    """Test that the research loop records trajectory events."""

    def test_trajectory_recorded_during_loop(self):
        """Loop with trajectory recorder should capture all step events."""
        config = ResearchConfig.default()
        provider = make_test_provider()
        tool = make_test_tool()

        recorder = TrajectoryRecorder(correlation_id="traj-test")

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
            trajectory_recorder=recorder,
        )

        asyncio.run(loop.run("What is X?", ResearchContext()))

        events = recorder.events
        step_names = [e.step_name for e in events]

        # Should have at least: plan, search, extract, evaluate, completeness, synthesize
        self.assertIn("plan", step_names)
        self.assertIn("search", step_names)
        self.assertIn("extract", step_names)
        self.assertIn("evaluate", step_names)
        self.assertIn("completeness", step_names)
        self.assertIn("synthesize", step_names)

    def test_no_trajectory_when_recorder_none(self):
        """Loop without recorder should work fine with zero overhead."""
        config = ResearchConfig.default()
        provider = make_test_provider()
        tool = make_test_tool()

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
            trajectory_recorder=None,
        )

        result = asyncio.run(loop.run("What is X?", ResearchContext()))
        self.assertIsInstance(result, ResearchResult)

    def test_trajectory_finalize_has_metrics(self):
        """Finalized trajectory should contain metrics from each step."""
        config = ResearchConfig.default()
        provider = make_test_provider()
        tool = make_test_tool()

        recorder = TrajectoryRecorder(correlation_id="metrics-test")

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
            trajectory_recorder=recorder,
        )

        asyncio.run(loop.run("What is X?", ResearchContext()))

        final = recorder.finalize()
        self.assertGreater(final["total_steps"], 0)
        self.assertGreater(final["total_duration_ms"], 0)

        # Plan event should have sub_queries metric
        plan_event = next(e for e in final["events"] if e["step_name"] == "plan")
        self.assertIn("sub_queries", plan_event["metrics"])
