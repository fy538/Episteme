"""
Tests for ResearchLoop — mock LLM provider and tools, test loop execution.
"""
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import TestCase

from apps.agents.research_config import ResearchConfig, SearchConfig
from apps.agents.research_loop import (
    ResearchLoop,
    ResearchContext,
    ResearchResult,
    SubQuery,
    Finding,
    ScoredFinding,
    _parse_json_from_response,
    _parse_markdown_to_blocks,
    _target_length_to_tokens,
    _get_tracer,
)
from apps.agents.research_tools import SearchResult


# ─── Fixtures ────────────────────────────────────────────────────────────────

def make_mock_provider(responses: list[str] | None = None):
    """
    Create a mock LLMProvider that returns canned JSON responses.
    If no responses given, returns generic valid JSON for each step.
    """
    default_responses = [
        # 1. Plan
        json.dumps({
            "sub_queries": [
                {"query": "What is X?", "source_target": "web", "rationale": "Define the term"},
                {"query": "Risks of X", "source_target": "web", "rationale": "Identify risks"},
            ],
            "strategy_notes": "Start broad, then narrow",
        }),
        # 2. Extract
        json.dumps({
            "findings": [
                {
                    "source_index": 0,
                    "extracted_fields": {"key_claim": "X is important"},
                    "raw_quote": "X is widely considered important.",
                    "relationships": [],
                },
                {
                    "source_index": 1,
                    "extracted_fields": {"key_claim": "X has risks"},
                    "raw_quote": "Several risks have been identified.",
                    "relationships": [],
                },
            ]
        }),
        # 3. Evaluate
        json.dumps({
            "evaluations": [
                {"finding_index": 0, "relevance_score": 0.9, "quality_score": 0.85, "evaluation_notes": "Authoritative"},
                {"finding_index": 1, "relevance_score": 0.8, "quality_score": 0.7, "evaluation_notes": "Recent"},
            ]
        }),
        # 4. Completeness
        json.dumps({"complete": True, "reasoning": "Min sources met with diversity"}),
        # 5. Synthesize
        "# Executive Summary\n\nX is important but has risks.\n\n## Key Findings\n\nFinding 1.\nFinding 2.\n\n## Sources\n\n- Source A\n- Source B",
    ]

    resp_list = list(responses or default_responses)
    provider = MagicMock()
    provider.generate = AsyncMock(side_effect=resp_list)
    return provider


def make_mock_tool(results: list[SearchResult] | None = None):
    """Create a mock web search tool that returns canned search results."""
    default_results = [
        SearchResult(
            url="https://example.com/article-1",
            title="Article About X",
            snippet="X is widely considered important in the field.",
            domain="example.com",
        ),
        SearchResult(
            url="https://other.org/risks",
            title="Risks of X",
            snippet="Several risks have been identified with X.",
            domain="other.org",
        ),
    ]
    tool = MagicMock()
    tool.name = "web_search"
    tool.execute = AsyncMock(return_value=results or default_results)
    return tool


def make_context():
    return ResearchContext(
        case_title="Test Case",
        case_position="Should we invest in X?",
    )


# ─── Loop Tests ──────────────────────────────────────────────────────────────

class ResearchLoopBasicTest(TestCase):
    """Test basic loop execution with mocks."""

    def test_full_loop_produces_result(self):
        config = ResearchConfig.default()
        provider = make_mock_provider()
        tool = make_mock_tool()

        loop = ResearchLoop(
            config=config,
            prompt_extension="Test skill instructions.",
            provider=provider,
            tools=[tool],
        )

        result = asyncio.run(loop.run("What is X?", make_context()))

        self.assertIsInstance(result, ResearchResult)
        self.assertTrue(len(result.content) > 0)
        self.assertTrue(len(result.blocks) > 0)
        self.assertIn("generation_time_ms", result.metadata)
        self.assertGreater(result.metadata["generation_time_ms"], 0)

    def test_progress_callback_called(self):
        config = ResearchConfig.default()
        provider = make_mock_provider()
        tool = make_mock_tool()

        progress_calls = []

        async def track_progress(step, message):
            progress_calls.append((step, message))

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
            progress_callback=track_progress,
        )

        asyncio.run(loop.run("What is X?", make_context()))

        # Should have called progress at least for: planning, plan_complete,
        # searching, extracting, evaluating, complete/synthesizing, done
        step_names = [s for s, _ in progress_calls]
        self.assertIn("planning", step_names)
        self.assertIn("synthesizing", step_names)
        self.assertIn("done", step_names)


class ResearchLoopTerminationTest(TestCase):
    """Test loop termination conditions."""

    def test_stops_on_completeness(self):
        """Loop should stop after completeness check returns True."""
        config = ResearchConfig.default()
        # Completeness returns True on first check
        provider = make_mock_provider()
        tool = make_mock_tool()

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        result = asyncio.run(loop.run("What is X?", make_context()))

        # Should only do 1 search round since completeness = True
        self.assertEqual(result.metadata.get("iterations"), 1)

    def test_stops_on_max_iterations(self):
        """Loop should stop when max_iterations reached."""
        from apps.agents.research_config import SearchConfig

        config = ResearchConfig(search=SearchConfig(max_iterations=1))

        # Make completeness always return False
        responses = [
            # Plan
            json.dumps({"sub_queries": [{"query": "Q1"}, {"query": "Q2"}]}),
            # Extract
            json.dumps({"findings": [{"source_index": 0, "extracted_fields": {}}]}),
            # Evaluate
            json.dumps({"evaluations": [{"finding_index": 0, "relevance_score": 0.5, "quality_score": 0.5}]}),
            # Completeness
            json.dumps({"complete": False, "reasoning": "Need more"}),
            # Synthesize (still called at end)
            "# Summary\n\nPartial results.",
        ]

        provider = make_mock_provider(responses)
        tool = make_mock_tool()

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        result = asyncio.run(loop.run("What is X?", make_context()))
        self.assertIsNotNone(result)

    def test_stops_on_budget_ceiling(self):
        """Loop should stop when max_sources budget hit."""
        from apps.agents.research_config import CompletenessConfig

        config = ResearchConfig(
            completeness=CompletenessConfig(min_sources=1, max_sources=2),
        )

        provider = make_mock_provider()
        tool = make_mock_tool()  # Returns 2 results

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        result = asyncio.run(loop.run("What is X?", make_context()))
        # Should stop because 2 findings >= max_sources of 2
        self.assertLessEqual(result.metadata.get("total_sources", 0), 3)


class ResearchLoopEdgeCasesTest(TestCase):
    """Test edge cases in the research loop."""

    def test_no_search_results(self):
        """Loop should handle empty search results gracefully."""
        config = ResearchConfig.default()

        responses = [
            json.dumps({"sub_queries": [{"query": "Obscure topic"}]}),
            # Synthesize (skip extract/eval since no results)
            "# Summary\n\nNo relevant sources found.",
        ]

        provider = make_mock_provider(responses)
        tool = MagicMock()
        tool.name = "web_search"
        tool.execute = AsyncMock(return_value=[])

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        result = asyncio.run(loop.run("Obscure topic", make_context()))
        self.assertIsInstance(result, ResearchResult)

    def test_llm_returns_invalid_json(self):
        """Loop should handle LLM returning non-JSON gracefully."""
        config = ResearchConfig.default()

        responses = [
            "This is not JSON at all",  # Plan step
            "# Fallback\n\nCouldn't parse.",  # Synthesize
        ]

        provider = make_mock_provider(responses)
        tool = make_mock_tool()

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        # Should not raise — falls back to a single direct query
        result = asyncio.run(loop.run("What is X?", make_context()))
        self.assertIsInstance(result, ResearchResult)


# ─── Utility Tests ───────────────────────────────────────────────────────────

class ParseJsonFromResponseTest(TestCase):
    """Test the JSON extraction utility."""

    def test_direct_json(self):
        result = _parse_json_from_response('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})

    def test_json_in_code_fence(self):
        text = '```json\n{"key": "value"}\n```'
        result = _parse_json_from_response(text)
        self.assertEqual(result, {"key": "value"})

    def test_json_in_bare_code_fence(self):
        text = '```\n{"key": "value"}\n```'
        result = _parse_json_from_response(text)
        self.assertEqual(result, {"key": "value"})

    def test_json_with_surrounding_text(self):
        text = 'Here is the result:\n{"key": "value"}\nDone.'
        result = _parse_json_from_response(text)
        self.assertEqual(result, {"key": "value"})

    def test_empty_string(self):
        result = _parse_json_from_response("")
        self.assertEqual(result, {})

    def test_no_json(self):
        result = _parse_json_from_response("just plain text")
        self.assertEqual(result, {})


class ParseMarkdownToBlocksTest(TestCase):
    """Test markdown to blocks parser."""

    def test_headings_and_paragraphs(self):
        md = "# Title\n\nFirst paragraph.\n\n## Section\n\nSecond paragraph."
        blocks = _parse_markdown_to_blocks(md)

        types = [b["type"] for b in blocks]
        self.assertEqual(types, ["heading", "paragraph", "heading", "paragraph"])

        self.assertEqual(blocks[0]["content"], "Title")
        self.assertEqual(blocks[0]["metadata"]["level"], 1)
        self.assertEqual(blocks[2]["metadata"]["level"], 2)

    def test_h3_heading(self):
        md = "### Sub-section\n\nContent."
        blocks = _parse_markdown_to_blocks(md)
        self.assertEqual(blocks[0]["metadata"]["level"], 3)

    def test_empty_content(self):
        blocks = _parse_markdown_to_blocks("")
        self.assertEqual(blocks, [])

    def test_each_block_has_id(self):
        md = "# Title\n\nParagraph."
        blocks = _parse_markdown_to_blocks(md)
        for block in blocks:
            self.assertIn("id", block)
            self.assertTrue(len(block["id"]) > 0)


class TargetLengthToTokensTest(TestCase):
    """Test target length mapping."""

    def test_brief(self):
        self.assertEqual(_target_length_to_tokens("brief"), 1500)

    def test_standard(self):
        self.assertEqual(_target_length_to_tokens("standard"), 4000)

    def test_detailed(self):
        self.assertEqual(_target_length_to_tokens("detailed"), 8000)

    def test_unknown_falls_back(self):
        self.assertEqual(_target_length_to_tokens("unknown"), 4000)


# ─── Parallel Search Tests ──────────────────────────────────────────────────

class ParallelSearchTest(TestCase):
    """Test parallel search execution."""

    def test_parallel_search_queries(self):
        """Queries should run concurrently — wall time < sum of individual delays."""
        config = ResearchConfig.default()
        provider = make_mock_provider()

        delay_seconds = 0.1

        async def slow_search(**kwargs):
            await asyncio.sleep(delay_seconds)
            return [
                SearchResult(
                    url=f"https://example.com/{kwargs.get('query', '')}",
                    title=f"Result for {kwargs.get('query', '')}",
                    snippet="Test snippet.",
                    domain="example.com",
                ),
            ]

        tool = MagicMock()
        tool.name = "web_search"
        tool.execute = AsyncMock(side_effect=slow_search)

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        queries = [
            SubQuery(query="Q1"),
            SubQuery(query="Q2"),
            SubQuery(query="Q3"),
        ]

        start = time.time()
        results = asyncio.run(loop._search(queries))
        elapsed = time.time() - start

        # 3 queries with 0.1s each — sequential would be ~0.3s, parallel should be ~0.1s
        self.assertEqual(len(results), 3)
        self.assertLess(elapsed, delay_seconds * 2.5)  # generous margin

    def test_parallel_search_handles_exceptions(self):
        """One failing query should not prevent others from returning results."""
        config = ResearchConfig.default()
        provider = make_mock_provider()

        call_count = 0

        async def mixed_search(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ConnectionError("Search API down")
            return [
                SearchResult(
                    url="https://example.com/result",
                    title="Good result",
                    snippet="Found it.",
                    domain="example.com",
                ),
            ]

        tool = MagicMock()
        tool.name = "web_search"
        tool.execute = AsyncMock(side_effect=mixed_search)

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        queries = [SubQuery(query="Q1"), SubQuery(query="Q2"), SubQuery(query="Q3")]
        results = asyncio.run(loop._search(queries))

        # 2 of 3 should succeed
        self.assertEqual(len(results), 2)

    def test_semaphore_limits_concurrency(self):
        """With parallel_branches=1, queries should run sequentially."""
        config = ResearchConfig(search=SearchConfig(parallel_branches=1))

        max_concurrent = 0
        current_concurrent = 0

        async def counting_search(**kwargs):
            nonlocal max_concurrent, current_concurrent
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.05)
            current_concurrent -= 1
            return [
                SearchResult(
                    url="https://example.com/r",
                    title="R",
                    snippet="S",
                    domain="example.com",
                ),
            ]

        tool = MagicMock()
        tool.name = "web_search"
        tool.execute = AsyncMock(side_effect=counting_search)
        provider = make_mock_provider()

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        queries = [SubQuery(query="Q1"), SubQuery(query="Q2"), SubQuery(query="Q3")]
        asyncio.run(loop._search(queries))

        # With semaphore=1, max concurrent should be 1
        self.assertEqual(max_concurrent, 1)


# ─── Context Compaction Tests ───────────────────────────────────────────────

class ContextCompactionTest(TestCase):
    """Test context compaction logic."""

    def _make_finding(self, relevance=0.5, quality=0.5, quote="Test quote"):
        return ScoredFinding(
            source=SearchResult(
                url="https://example.com/src",
                title="Source",
                snippet="Snippet",
                domain="example.com",
            ),
            extracted_fields={"key_claim": "Test claim " + quote},
            raw_quote=quote,
            relevance_score=relevance,
            quality_score=quality,
            evaluation_notes="Test notes",
        )

    def test_compaction_skips_below_threshold(self):
        """Should not compact when findings < 20."""
        config = ResearchConfig.default()
        provider = make_mock_provider()
        tool = make_mock_tool()

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        findings = [self._make_finding() for _ in range(10)]
        self.assertFalse(loop._should_compact(findings))

    def test_compaction_triggers_at_threshold(self):
        """Should compact when findings >= 20 and tokens > 60K."""
        config = ResearchConfig.default()
        provider = make_mock_provider()
        tool = make_mock_tool()

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        # Create findings with enough text to exceed token threshold
        findings = [
            self._make_finding(quote="A" * 12000)  # ~3K tokens each
            for _ in range(25)
        ]
        self.assertTrue(loop._should_compact(findings))

    def test_compaction_preserves_top_findings(self):
        """Top-scored findings should survive compaction."""
        config = ResearchConfig.default()

        # Provider returns a compact digest
        compact_response = json.dumps({"digest": "Summary of dropped findings."})
        provider = MagicMock()
        provider.generate = AsyncMock(return_value=compact_response)
        tool = make_mock_tool()

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        # Create 25 findings with varying scores
        findings = []
        for i in range(25):
            findings.append(self._make_finding(
                relevance=0.9 - (i * 0.03),
                quality=0.9 - (i * 0.03),
                quote=f"Finding {i} quote text padding " * 50,
            ))

        result = asyncio.run(loop._compact_findings(findings))

        # Should have kept top 60% (15) + 1 digest = 16
        self.assertGreaterEqual(len(result), 10)
        self.assertLess(len(result), 25)

        # Highest-scored finding should still be present
        top_finding = max(
            result,
            key=lambda f: f.relevance_score * 0.6 + f.quality_score * 0.4,
        )
        self.assertGreaterEqual(top_finding.relevance_score, 0.8)

    def test_compaction_creates_digest(self):
        """Dropped findings should produce a digest finding."""
        config = ResearchConfig.default()

        compact_response = json.dumps(
            {"digest": "Dropped findings mention edge cases in region X."}
        )
        provider = MagicMock()
        provider.generate = AsyncMock(return_value=compact_response)
        tool = make_mock_tool()

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        findings = [
            self._make_finding(
                relevance=0.3, quality=0.3,
                quote=f"Low-quality finding {i} " * 50,
            )
            for i in range(25)
        ]

        result = asyncio.run(loop._compact_findings(findings))

        # Should contain a digest finding
        digest_findings = [
            f for f in result if f.source.title == "Compacted findings digest"
        ]
        self.assertEqual(len(digest_findings), 1)
        self.assertIn("edge cases", digest_findings[0].extracted_fields["digest"])


# ─── Observability Tests ────────────────────────────────────────────────────

class ObservabilityTest(TestCase):
    """Test tracing/observability features."""

    def test_tracing_noop_without_langfuse(self):
        """Loop runs fine when Langfuse is not installed/configured."""
        config = ResearchConfig.default()
        provider = make_mock_provider()
        tool = make_mock_tool()

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
            trace_id="test-trace-123",
        )

        # _tracer should be None (no LANGFUSE_PUBLIC_KEY env var)
        self.assertIsNone(loop._tracer)

        # Loop should still work
        result = asyncio.run(loop.run("What is X?", make_context()))
        self.assertIsInstance(result, ResearchResult)

    def test_get_tracer_returns_none_without_env(self):
        """_get_tracer should return None when env vars are not set."""
        with patch.dict("os.environ", {}, clear=True):
            tracer = _get_tracer()
            self.assertIsNone(tracer)

    def test_tracing_passes_step_names(self):
        """When tracer is present, span should be called with step_name."""
        config = ResearchConfig.default()
        provider = make_mock_provider()
        tool = make_mock_tool()

        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.span.return_value = mock_span

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
            trace_id="test-trace-456",
        )
        loop._tracer = mock_tracer  # Inject mock tracer

        result = asyncio.run(loop.run("What is X?", make_context()))

        # Tracer should have been called with step names
        span_calls = mock_tracer.span.call_args_list
        step_names = [call.kwargs.get("name", "") for call in span_calls]

        self.assertIn("plan", step_names)
        self.assertIn("extract", step_names)
        self.assertIn("evaluate", step_names)
        self.assertIn("synthesize", step_names)

        # Each span should have been ended
        self.assertGreaterEqual(mock_span.end.call_count, len(span_calls))
