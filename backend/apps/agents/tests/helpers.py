"""
Shared test fixtures and helpers for agent tests.
"""
import json
from unittest.mock import AsyncMock, MagicMock

from apps.agents.research_tools import SearchResult


def make_test_provider(responses: list[str] | None = None):
    """
    Create a mock LLM provider with canned responses.

    Args:
        responses: List of string responses returned in order.
                   If None, uses a default sequence sufficient for
                   a single-iteration research loop (plan, extract,
                   evaluate, completeness, synthesize).
    """
    if responses is None:
        responses = [
            json.dumps({
                "sub_queries": [
                    {"query": "What is X?", "source_target": "web"},
                ],
                "strategy_notes": "Simple",
            }),
            json.dumps({
                "findings": [
                    {
                        "source_index": 0,
                        "extracted_fields": {"claim": "test"},
                        "raw_quote": "Q",
                        "relationships": [],
                    },
                ],
            }),
            json.dumps({
                "evaluations": [
                    {
                        "finding_index": 0,
                        "relevance_score": 0.9,
                        "quality_score": 0.8,
                        "evaluation_notes": "OK",
                    },
                ],
            }),
            json.dumps({"complete": True}),
            "# Summary\n\nResult.",
        ]

    provider = MagicMock()
    provider.generate = AsyncMock(side_effect=responses)
    # Prevent MagicMock from auto-creating these attributes (hasattr returns True
    # for any attr on MagicMock). The ResearchLoop checks these to decide whether
    # to create ContextBudgetTracker and CostTracker.
    del provider.context_window_tokens
    del provider.model
    return provider


def make_test_tool(
    name: str = "web_search",
    results: list[SearchResult] | None = None,
):
    """
    Create a mock research tool.

    Args:
        name: Tool name (default "web_search").
        results: List of SearchResult objects to return. If None, returns
                 a single result from "a.com".
    """
    if results is None:
        results = [
            SearchResult(
                url="https://a.com",
                title="A",
                snippet="Snippet",
                domain="a.com",
            ),
        ]

    tool = MagicMock()
    tool.name = name
    tool.execute = AsyncMock(return_value=results)
    return tool
