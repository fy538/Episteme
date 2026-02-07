"""
Tests for checkpoint save/load and research loop resume.
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import TestCase

from apps.agents.checkpoint import (
    ResearchCheckpoint,
    save_checkpoint,
    load_latest_checkpoint,
)
from apps.agents.research_config import ResearchConfig
from apps.agents.research_loop import (
    ResearchLoop,
    ResearchContext,
    ResearchResult,
    ScoredFinding,
    _rebuild_findings,
)
from apps.agents.research_tools import SearchResult
from apps.agents.trajectory import TrajectoryRecorder
from .helpers import make_test_provider, make_test_tool


# ─── Checkpoint Serialization ─────────────────────────────────────────────


class CheckpointSerializationTest(TestCase):
    """Test ResearchCheckpoint round-trip serialization."""

    def test_round_trip(self):
        checkpoint = ResearchCheckpoint(
            correlation_id="abc-123",
            question="What is X?",
            iteration=2,
            phase="evaluate",
            total_sources_found=7,
            search_rounds=2,
            plan_dict={
                "sub_queries": [
                    {"query": "X definition", "source_target": "web", "rationale": "Define"},
                ],
                "strategy_notes": "Broad search first",
                "followups": [],
            },
            findings_dicts=[
                {
                    "source_title": "Article A",
                    "source_url": "https://a.com",
                    "source_domain": "a.com",
                    "extracted_fields": {"claim": "X is good"},
                    "raw_quote": "X is widely considered good.",
                    "relationships": [],
                    "relevance_score": 0.9,
                    "quality_score": 0.8,
                    "evaluation_notes": "Authoritative",
                },
            ],
            config_dict={"search": {"decomposition": "simple"}},
            prompt_extension="Test instructions.",
            context_dict={"case_title": "Test Case"},
        )

        d = checkpoint.to_dict()
        restored = ResearchCheckpoint.from_dict(d)

        self.assertEqual(restored.correlation_id, "abc-123")
        self.assertEqual(restored.question, "What is X?")
        self.assertEqual(restored.iteration, 2)
        self.assertEqual(restored.phase, "evaluate")
        self.assertEqual(restored.total_sources_found, 7)
        self.assertEqual(restored.search_rounds, 2)
        self.assertEqual(len(restored.findings_dicts), 1)
        self.assertEqual(restored.findings_dicts[0]["source_title"], "Article A")
        self.assertEqual(restored.prompt_extension, "Test instructions.")

    def test_empty_checkpoint(self):
        checkpoint = ResearchCheckpoint(
            correlation_id="empty",
            question="",
            iteration=0,
            phase="plan",
            total_sources_found=0,
            search_rounds=0,
        )
        d = checkpoint.to_dict()
        restored = ResearchCheckpoint.from_dict(d)
        self.assertEqual(restored.correlation_id, "empty")
        self.assertEqual(restored.findings_dicts, [])
        self.assertEqual(restored.plan_dict, {})

    def test_from_dict_missing_keys(self):
        """from_dict should handle missing keys gracefully."""
        restored = ResearchCheckpoint.from_dict({"correlation_id": "partial"})
        self.assertEqual(restored.correlation_id, "partial")
        self.assertEqual(restored.iteration, 0)
        self.assertEqual(restored.phase, "")
        self.assertEqual(restored.findings_dicts, [])


# ─── Checkpoint Persistence ───────────────────────────────────────────────


class CheckpointPersistenceTest(TestCase):
    """Test save/load through the event store."""

    @patch("apps.agents.checkpoint.EventService")
    def test_save_checkpoint_calls_event_service(self, mock_event_service):
        checkpoint = ResearchCheckpoint(
            correlation_id="save-test",
            question="Test?",
            iteration=1,
            phase="evaluate",
            total_sources_found=3,
            search_rounds=1,
        )

        save_checkpoint(checkpoint)

        mock_event_service.append.assert_called_once()
        call_kwargs = mock_event_service.append.call_args
        # Check event_type regardless of positional/keyword args
        all_args = str(call_kwargs)
        self.assertIn("AGENT_CHECKPOINT", all_args)

    @patch("apps.agents.checkpoint.EventService")
    def test_save_checkpoint_handles_failure(self, mock_event_service):
        """save_checkpoint is best-effort — should not raise."""
        mock_event_service.append.side_effect = RuntimeError("DB down")

        checkpoint = ResearchCheckpoint(
            correlation_id="fail-test",
            question="Test?",
            iteration=0,
            phase="plan",
            total_sources_found=0,
            search_rounds=0,
        )

        # Should not raise
        save_checkpoint(checkpoint)

    @patch("apps.agents.checkpoint.Event")
    def test_load_latest_returns_none_when_empty(self, mock_event):
        mock_event.objects.filter.return_value.order_by.return_value.first.return_value = None
        result = load_latest_checkpoint("nonexistent")
        self.assertIsNone(result)

    @patch("apps.agents.checkpoint.Event")
    def test_load_latest_returns_checkpoint(self, mock_event):
        mock_event_obj = MagicMock()
        mock_event_obj.payload = {
            "correlation_id": "found-it",
            "question": "What?",
            "iteration": 2,
            "phase": "evaluate",
            "total_sources_found": 5,
            "search_rounds": 2,
            "plan_dict": {},
            "findings_dicts": [{"source_title": "A"}],
            "config_dict": {},
            "prompt_extension": "",
            "context_dict": {},
        }
        mock_event.objects.filter.return_value.order_by.return_value.first.return_value = mock_event_obj

        result = load_latest_checkpoint("found-it")
        self.assertIsNotNone(result)
        self.assertEqual(result.correlation_id, "found-it")
        self.assertEqual(result.iteration, 2)
        self.assertEqual(len(result.findings_dicts), 1)


# ─── Rebuild Findings ─────────────────────────────────────────────────────


class RebuildFindingsTest(TestCase):
    """Test _rebuild_findings from serialized dicts."""

    def test_rebuild_basic(self):
        dicts = [
            {
                "source_title": "Article",
                "source_url": "https://example.com",
                "source_domain": "example.com",
                "extracted_fields": {"claim": "test"},
                "raw_quote": "A quote.",
                "relationships": [],
                "relevance_score": 0.9,
                "quality_score": 0.8,
                "evaluation_notes": "Good source",
            },
        ]
        findings = _rebuild_findings(dicts)
        self.assertEqual(len(findings), 1)
        self.assertIsInstance(findings[0], ScoredFinding)
        self.assertEqual(findings[0].source.title, "Article")
        self.assertEqual(findings[0].relevance_score, 0.9)

    def test_rebuild_empty(self):
        findings = _rebuild_findings([])
        self.assertEqual(findings, [])

    def test_rebuild_missing_fields(self):
        """Should handle missing fields gracefully with defaults."""
        dicts = [{"source_title": "Minimal"}]
        findings = _rebuild_findings(dicts)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].source.title, "Minimal")
        self.assertEqual(findings[0].relevance_score, 0.5)


# ─── Loop Checkpoint Integration ──────────────────────────────────────────


class LoopCheckpointCallbackTest(TestCase):
    """Test that the loop emits checkpoints at phase boundaries."""

    def test_checkpoint_callback_invoked(self):
        """Loop should call checkpoint_callback at phase boundaries."""
        config = ResearchConfig.default()
        provider = make_test_provider()
        tool = make_test_tool()
        checkpoints = []

        def on_checkpoint(cp):
            checkpoints.append(cp)

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
            checkpoint_callback=on_checkpoint,
            trace_id="test-corr",
        )

        asyncio.run(loop.run("What is X?", ResearchContext()))

        # Should have at least 2 checkpoints: after plan and after evaluate
        self.assertGreaterEqual(len(checkpoints), 2)
        phases = [cp.phase for cp in checkpoints]
        self.assertIn("plan", phases)
        self.assertIn("evaluate", phases)

    def test_no_checkpoint_when_callback_is_none(self):
        """No errors when checkpoint_callback is None."""
        config = ResearchConfig.default()
        provider = make_test_provider()
        tool = make_test_tool()

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
            checkpoint_callback=None,
        )

        result = asyncio.run(loop.run("What is X?", ResearchContext()))
        self.assertIsInstance(result, ResearchResult)


# ─── Resume from Checkpoint ───────────────────────────────────────────────


class ResumeFromCheckpointTest(TestCase):
    """Test resuming a research loop from a saved checkpoint."""

    def test_resume_produces_result(self):
        """Resume should complete the loop and produce a valid result."""
        checkpoint = ResearchCheckpoint(
            correlation_id="resume-test",
            question="What is X?",
            iteration=1,
            phase="evaluate",
            total_sources_found=2,
            search_rounds=1,
            plan_dict={
                "sub_queries": [
                    {"query": "X definition", "source_target": "web", "rationale": "Define"},
                ],
                "strategy_notes": "Broad first",
                "followups": [
                    {"query": "X risks", "source_target": "web", "rationale": "Risks"},
                ],
            },
            findings_dicts=[
                {
                    "source_title": "Prior Article",
                    "source_url": "https://prior.com",
                    "source_domain": "prior.com",
                    "extracted_fields": {"claim": "X is defined"},
                    "raw_quote": "X is defined as...",
                    "relationships": [],
                    "relevance_score": 0.85,
                    "quality_score": 0.8,
                    "evaluation_notes": "Good",
                },
            ],
            config_dict={},
            prompt_extension="Test.",
            context_dict={"case_title": "Resume Test", "case_position": "Test position"},
        )

        # Provider responses for the resumed portion:
        # extract, evaluate, completeness, synthesize
        responses = [
            json.dumps({
                "findings": [
                    {"source_index": 0, "extracted_fields": {"claim": "new"}, "raw_quote": "New.", "relationships": []},
                ],
            }),
            json.dumps({
                "evaluations": [
                    {"finding_index": 0, "relevance_score": 0.7, "quality_score": 0.6, "evaluation_notes": "OK"},
                ],
            }),
            json.dumps({"complete": True}),
            "# Resumed Summary\n\nResult after resume.",
        ]
        provider = MagicMock()
        provider.generate = AsyncMock(side_effect=responses)

        tool = MagicMock()
        tool.name = "web_search"
        tool.execute = AsyncMock(return_value=[
            SearchResult(url="https://new.com", title="New", snippet="New snippet", domain="new.com"),
        ])

        config = ResearchConfig.default()

        result = asyncio.run(ResearchLoop.resume_from_checkpoint(
            checkpoint=checkpoint,
            config=config,
            prompt_extension="Test.",
            provider=provider,
            tools=[tool],
        ))

        self.assertIsInstance(result, ResearchResult)
        self.assertTrue(len(result.content) > 0)
        self.assertTrue(result.metadata.get("resumed_from_checkpoint"))
        self.assertEqual(result.metadata.get("resumed_at_iteration"), 1)
        # Should have prior finding + new finding
        self.assertGreaterEqual(result.metadata.get("findings_count", 0), 2)

    def test_resume_with_no_followups_just_synthesizes(self):
        """If no followups remain, resume should go straight to synthesize."""
        checkpoint = ResearchCheckpoint(
            correlation_id="no-followups",
            question="Simple Q",
            iteration=3,
            phase="evaluate",
            total_sources_found=5,
            search_rounds=3,
            plan_dict={
                "sub_queries": [],
                "strategy_notes": "",
                "followups": [],
            },
            findings_dicts=[
                {
                    "source_title": "Existing",
                    "source_url": "https://exist.com",
                    "source_domain": "exist.com",
                    "extracted_fields": {},
                    "raw_quote": "Existing finding",
                    "relationships": [],
                    "relevance_score": 0.7,
                    "quality_score": 0.7,
                    "evaluation_notes": "",
                },
            ],
            context_dict={"case_title": "Test"},
        )

        # Only need synthesize response
        provider = MagicMock()
        provider.generate = AsyncMock(return_value="# Summary\n\nDone.")

        tool = MagicMock()
        tool.name = "web_search"
        tool.execute = AsyncMock(return_value=[])

        config = ResearchConfig.default()
        # Set max_iterations to 4 so starting from iteration 4 means no iteration loop
        config.search.max_iterations = 4

        result = asyncio.run(ResearchLoop.resume_from_checkpoint(
            checkpoint=checkpoint,
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        ))

        self.assertIsInstance(result, ResearchResult)
        self.assertTrue(result.metadata.get("resumed_from_checkpoint"))

    def test_resume_with_trajectory_recorder(self):
        """Resume should record trajectory events when recorder is provided."""
        checkpoint = ResearchCheckpoint(
            correlation_id="traj-resume",
            question="What is X?",
            iteration=0,
            phase="plan",
            total_sources_found=0,
            search_rounds=0,
            plan_dict={
                "sub_queries": [],
                "strategy_notes": "",
                "followups": [
                    {"query": "X details", "source_target": "web", "rationale": "Detail"},
                ],
            },
            findings_dicts=[],
            context_dict={"case_title": "Traj Test"},
        )

        # Responses for resumed portion: extract, evaluate, completeness, synthesize
        responses = [
            json.dumps({
                "findings": [
                    {"source_index": 0, "extracted_fields": {"claim": "found"}, "raw_quote": "Q", "relationships": []},
                ],
            }),
            json.dumps({
                "evaluations": [
                    {"finding_index": 0, "relevance_score": 0.8, "quality_score": 0.7, "evaluation_notes": "Good"},
                ],
            }),
            json.dumps({"complete": True}),
            "# Result\n\nDone.",
        ]
        provider = make_test_provider(responses)
        tool = make_test_tool()
        recorder = TrajectoryRecorder(correlation_id="traj-resume")

        config = ResearchConfig.default()

        result = asyncio.run(ResearchLoop.resume_from_checkpoint(
            checkpoint=checkpoint,
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
            trajectory_recorder=recorder,
        ))

        self.assertIsInstance(result, ResearchResult)
        self.assertTrue(result.metadata.get("resumed_from_checkpoint"))

        # Verify trajectory events were recorded
        events = recorder.events
        step_names = [e.step_name for e in events]
        self.assertIn("search", step_names)
        self.assertIn("extract", step_names)
        self.assertIn("evaluate", step_names)
        self.assertIn("synthesize", step_names)
