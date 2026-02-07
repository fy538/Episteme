"""
Tests for ContextBudgetTracker, handoff summary, and session continuity.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

from django.test import TestCase

from apps.agents.context_manager import (
    ContextBudget,
    ContextBudgetTracker,
    build_handoff_summary,
    create_continuation_context,
    MAX_CONTINUATIONS,
    CONTEXT_RESERVE_RATIO,
    CHARS_PER_TOKEN,
)


# ─── ContextBudget ────────────────────────────────────────────────────────


class ContextBudgetTest(TestCase):
    """Test ContextBudget properties."""

    def test_total_used(self):
        budget = ContextBudget(
            context_window=100_000,
            reserve=20_000,
            used_by_prompts=10_000,
            used_by_findings=5_000,
            used_by_plan=1_000,
        )
        self.assertEqual(budget.total_used, 16_000)

    def test_available(self):
        budget = ContextBudget(
            context_window=100_000,
            reserve=20_000,
            used_by_prompts=10_000,
        )
        # 100_000 - 20_000 - 10_000 = 70_000
        self.assertEqual(budget.available, 70_000)

    def test_available_never_negative(self):
        budget = ContextBudget(
            context_window=100,
            reserve=50,
            used_by_prompts=200,
        )
        self.assertEqual(budget.available, 0)

    def test_utilization(self):
        budget = ContextBudget(
            context_window=100_000,
            reserve=20_000,
            used_by_prompts=50_000,
        )
        self.assertAlmostEqual(budget.utilization, 0.5)

    def test_needs_continuation(self):
        """needs_continuation when less than 10% remaining."""
        budget = ContextBudget(
            context_window=100_000,
            reserve=20_000,
            used_by_prompts=75_000,  # 75k + 20k reserve = 95k used, 5k available (< 10k)
        )
        self.assertTrue(budget.needs_continuation)

    def test_no_continuation_when_plenty_available(self):
        budget = ContextBudget(
            context_window=100_000,
            reserve=20_000,
            used_by_prompts=10_000,
        )
        self.assertFalse(budget.needs_continuation)

    def test_can_continue(self):
        budget = ContextBudget(context_window=100_000, reserve=20_000, continuations=0)
        self.assertTrue(budget.can_continue)

        budget.continuations = MAX_CONTINUATIONS
        self.assertFalse(budget.can_continue)


# ─── ContextBudgetTracker ─────────────────────────────────────────────────


class ContextBudgetTrackerTest(TestCase):
    """Test the budget tracker."""

    def test_initial_state(self):
        tracker = ContextBudgetTracker(context_window_tokens=128_000)
        status = tracker.check_budget()
        self.assertEqual(status["total_used"], 0)
        self.assertGreater(status["available"], 0)
        self.assertFalse(status["needs_continuation"])

    def test_estimate_tokens(self):
        tracker = ContextBudgetTracker()
        # 400 chars / 4 = 100 tokens
        self.assertEqual(tracker.estimate_tokens("x" * 400), 100)

    def test_track_prompt(self):
        tracker = ContextBudgetTracker(context_window_tokens=1000)
        tracker.track_prompt("x" * 400)  # 100 tokens
        self.assertEqual(tracker.budget.used_by_prompts, 100)

    def test_track_findings_replaces(self):
        """track_findings should replace (not accumulate) findings budget."""
        tracker = ContextBudgetTracker(context_window_tokens=1000)
        tracker.track_findings([{"text": "x" * 400}])
        first = tracker.budget.used_by_findings
        tracker.track_findings([{"text": "y" * 200}])
        second = tracker.budget.used_by_findings
        # Second should be different (replaced, not added)
        self.assertNotEqual(first, second)

    def test_check_budget_format(self):
        tracker = ContextBudgetTracker(context_window_tokens=100_000)
        status = tracker.check_budget()
        self.assertIn("total_used", status)
        self.assertIn("available", status)
        self.assertIn("utilization", status)
        self.assertIn("needs_continuation", status)
        self.assertIn("can_continue", status)

    def test_budget_exhaustion(self):
        """Tracker should report needs_continuation when budget is low."""
        tracker = ContextBudgetTracker(context_window_tokens=1000)
        # Use up 95% of the window
        tracker.track_prompt("x" * (950 * CHARS_PER_TOKEN))
        status = tracker.check_budget()
        self.assertTrue(status["needs_continuation"])


# ─── Handoff Summary ──────────────────────────────────────────────────────


class HandoffSummaryTest(TestCase):
    """Test build_handoff_summary."""

    def test_builds_summary(self):
        provider = MagicMock()
        provider.generate = AsyncMock(return_value="Key findings: X is important. Gaps: Need more on Y.")

        findings = [
            {"source_title": "Article A", "raw_quote": "X is important."},
            {"source_title": "Article B", "raw_quote": "Y needs research."},
        ]

        summary = asyncio.run(build_handoff_summary(
            question="What is X?",
            findings_dicts=findings,
            plan_dict={"strategy_notes": "Broad search"},
            provider=provider,
        ))

        self.assertIn("Key findings", summary)
        provider.generate.assert_called_once()

    def test_fallback_on_failure(self):
        """Should return basic summary if LLM fails."""
        provider = MagicMock()
        provider.generate = AsyncMock(side_effect=RuntimeError("LLM down"))

        findings = [{"source_title": "A"}]

        summary = asyncio.run(build_handoff_summary(
            question="What is X?",
            findings_dicts=findings,
            plan_dict={"strategy_notes": "Test"},
            provider=provider,
        ))

        self.assertIn("What is X?", summary)
        self.assertIn("1 sources", summary)

    def test_no_generate_method(self):
        """Provider without generate should return empty string."""
        provider = MagicMock(spec=[])  # No generate method

        summary = asyncio.run(build_handoff_summary(
            question="Q", findings_dicts=[], plan_dict={}, provider=provider,
        ))
        self.assertEqual(summary, "")


# ─── Continuation Context ─────────────────────────────────────────────────


class ContinuationContextTest(TestCase):
    """Test create_continuation_context."""

    def test_builds_prompt(self):
        context = create_continuation_context(
            summary="Prior work summary here.",
            question="What is X?",
            continuation_number=0,
        )
        self.assertIn("Continuation Session", context)
        self.assertIn("Prior work summary here.", context)
        self.assertIn("What is X?", context)
        self.assertIn("Do NOT re-search", context)

    def test_continuation_number(self):
        context = create_continuation_context("summary", "Q", continuation_number=1)
        self.assertIn("2 of", context)
