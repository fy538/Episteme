"""
Context Manager — session continuity across context windows.

Provides two mechanisms for preventing context overflow:
1. Proactive budget tracking — estimate total token usage, warn before overflow
2. Session handoff — when context is exhausted, build a compressed summary
   and seed a new session from checkpoint + summary

Safety: max 2 continuations (3 total sessions) to prevent runaway costs.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ─── Constants ─────────────────────────────────────────────────────────────

# Reserve 20% of context window for the next LLM response
CONTEXT_RESERVE_RATIO = 0.2

# Max continuations to prevent runaway
MAX_CONTINUATIONS = 2

# Chars-per-token estimate (conservative)
CHARS_PER_TOKEN = 4


@dataclass
class ContextBudget:
    """Tracks estimated token usage for the research loop."""

    context_window: int  # Total tokens available
    reserve: int  # Tokens reserved for LLM response
    used_by_prompts: int = 0  # Accumulated prompt tokens
    used_by_findings: int = 0  # Accumulated findings tokens
    used_by_plan: int = 0  # Plan tokens
    continuations: int = 0  # Number of continuations so far

    @property
    def total_used(self) -> int:
        return self.used_by_prompts + self.used_by_findings + self.used_by_plan

    @property
    def available(self) -> int:
        return max(0, self.context_window - self.reserve - self.total_used)

    @property
    def utilization(self) -> float:
        """Fraction of context window used (0.0-1.0)."""
        if self.context_window == 0:
            return 1.0
        return self.total_used / self.context_window

    @property
    def needs_continuation(self) -> bool:
        """True when context is nearly exhausted."""
        return self.available < (self.context_window * 0.1)  # Less than 10% remaining

    @property
    def can_continue(self) -> bool:
        """True if we haven't hit the continuation ceiling."""
        return self.continuations < MAX_CONTINUATIONS


class ContextBudgetTracker:
    """
    Estimates and tracks token budget across the research loop.

    Provides early warning when context is running low, enabling
    proactive compaction or graceful session handoff.
    """

    def __init__(self, context_window_tokens: int = 128_000):
        self.budget = ContextBudget(
            context_window=context_window_tokens,
            reserve=int(context_window_tokens * CONTEXT_RESERVE_RATIO),
        )

    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens using tiktoken when available, else char÷4 fallback."""
        try:
            from apps.common.token_utils import count_tokens
            return count_tokens(text)
        except Exception:
            return len(text) // CHARS_PER_TOKEN

    def track_prompt(self, prompt_text: str) -> None:
        """Track tokens used by a prompt."""
        self.budget.used_by_prompts += self.estimate_tokens(prompt_text)

    def track_findings(self, findings_dicts: list[dict]) -> None:
        """Track tokens used by accumulated findings."""
        total_chars = sum(len(str(f)) for f in findings_dicts)
        self.budget.used_by_findings = total_chars // CHARS_PER_TOKEN

    def track_plan(self, plan_text: str) -> None:
        """Track tokens used by the research plan."""
        self.budget.used_by_plan = self.estimate_tokens(plan_text)

    def check_budget(self) -> dict[str, Any]:
        """
        Check current budget status.

        Returns:
            Dict with budget metrics and whether action is needed.
        """
        return {
            "total_used": self.budget.total_used,
            "available": self.budget.available,
            "utilization": round(self.budget.utilization, 3),
            "needs_continuation": self.budget.needs_continuation,
            "can_continue": self.budget.can_continue,
            "continuations": self.budget.continuations,
        }


# ─── Cost Tracking ────────────────────────────────────────────────────────

# Per-million-token pricing (USD). Updated as of 2025-06.
# Source: https://docs.anthropic.com/en/docs/about-claude/models
MODEL_PRICING: dict[str, dict[str, float]] = {
    # Anthropic
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00, "cache_read": 0.08, "cache_write": 1.00},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00, "cache_read": 1.50, "cache_write": 18.75},
    # OpenAI
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "cache_read": 0.075, "cache_write": 0.15},
    "gpt-4o": {"input": 2.50, "output": 10.00, "cache_read": 1.25, "cache_write": 2.50},
}
DEFAULT_PRICING = {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75}


@dataclass
class LLMCallCost:
    """Cost breakdown for a single LLM call."""

    step_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0


class CostTracker:
    """
    Accumulates token usage and estimated cost across a research session.

    Usage:
        tracker = CostTracker(model="claude-haiku-4-5")
        tracker.record_call("plan", input_tokens=1200, output_tokens=400)
        tracker.record_call("extract", input_tokens=2000, output_tokens=800,
                            cache_read_tokens=1000)
        print(tracker.summary())
    """

    def __init__(self, model: str = "claude-haiku-4-5"):
        self.model = model
        self._pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
        self._calls: list[LLMCallCost] = []

    def record_call(
        self,
        step_name: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> LLMCallCost:
        """Record a single LLM call's token usage and compute cost."""
        cost = (
            (input_tokens * self._pricing["input"])
            + (output_tokens * self._pricing["output"])
            + (cache_read_tokens * self._pricing["cache_read"])
            + (cache_write_tokens * self._pricing["cache_write"])
        ) / 1_000_000  # pricing is per million tokens

        call = LLMCallCost(
            step_name=step_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_write_tokens=cache_write_tokens,
            cost_usd=round(cost, 6),
        )
        self._calls.append(call)
        return call

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self._calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self._calls)

    @property
    def total_cache_read_tokens(self) -> int:
        return sum(c.cache_read_tokens for c in self._calls)

    @property
    def total_cache_write_tokens(self) -> int:
        return sum(c.cache_write_tokens for c in self._calls)

    @property
    def total_cost_usd(self) -> float:
        return round(sum(c.cost_usd for c in self._calls), 6)

    def summary(self) -> dict[str, Any]:
        """Return a JSON-serializable cost summary."""
        return {
            "model": self.model,
            "total_calls": len(self._calls),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cache_read_tokens": self.total_cache_read_tokens,
            "total_cache_write_tokens": self.total_cache_write_tokens,
            "total_cost_usd": self.total_cost_usd,
            "calls": [
                {
                    "step": c.step_name,
                    "input_tokens": c.input_tokens,
                    "output_tokens": c.output_tokens,
                    "cache_read_tokens": c.cache_read_tokens,
                    "cost_usd": c.cost_usd,
                }
                for c in self._calls
            ],
        }


# ─── Session Handoff ──────────────────────────────────────────────────────


async def build_handoff_summary(
    question: str,
    findings_dicts: list[dict],
    plan_dict: dict,
    provider: Any,
    max_summary_tokens: int = 2000,
) -> str:
    """
    Build a compressed session summary for handoff to a new loop.

    Uses the LLM (fast model) to compress findings and plan into
    a concise summary that seeds the next session.
    """
    findings_text = "\n".join(
        f"- {f.get('source_title', 'Unknown')}: {f.get('raw_quote', '')[:150]}"
        for f in findings_dicts[:20]  # Cap at 20 for prompt length
    )

    prompt = f"""Summarize this research session for continuation. Be concise but preserve key information.

RESEARCH QUESTION: {question}

STRATEGY: {plan_dict.get('strategy_notes', 'N/A')}

FINDINGS SO FAR:
{findings_text}

Produce a summary with:
1. Key findings discovered (with source attribution)
2. Gaps that still need investigation
3. Recommended next queries

Keep under {max_summary_tokens} tokens."""

    try:
        if hasattr(provider, 'generate'):
            return await provider.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a research assistant summarizing an ongoing research session.",
                max_tokens=max_summary_tokens,
                temperature=0.2,
            )
        return ""
    except Exception as e:
        logger.exception(
            "handoff_summary_failed",
            extra={"error": str(e)},
        )
        # Fallback: build a basic summary without LLM
        return f"Research question: {question}\nFindings: {len(findings_dicts)} sources collected.\nStrategy: {plan_dict.get('strategy_notes', 'N/A')}"


def create_continuation_context(
    summary: str,
    question: str,
    continuation_number: int,
) -> str:
    """
    Build the prompt extension for a continuation session.

    The summary from the previous session is injected as context,
    so the new loop has full awareness of prior work.
    """
    return f"""## Continuation Session ({continuation_number + 1} of max {MAX_CONTINUATIONS + 1})

This research was started in a previous session. Here is the summary of prior work:

{summary}

ORIGINAL QUESTION: {question}

Continue the research from where the previous session left off. Focus on:
1. Filling gaps identified in the summary
2. Following up on promising leads
3. Do NOT re-search topics already covered
"""
