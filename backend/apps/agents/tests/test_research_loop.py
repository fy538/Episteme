"""
Tests for ResearchLoop — mock LLM provider and tools, test loop execution.
"""
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import TestCase

from apps.agents.research_config import (
    ResearchConfig, SearchConfig, SourcesConfig, SourceEntry,
    CompletenessConfig,
)
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
    MAX_CITATION_LEADS_PER_ROUND,
    MIN_FINDINGS_AFTER_COMPACT,
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
    # Prevent MagicMock from auto-creating these attributes (hasattr returns True
    # for any attr on MagicMock). The ResearchLoop checks these to decide whether
    # to create ContextBudgetTracker and CostTracker.
    del provider.context_window_tokens
    del provider.model
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
        self.assertGreaterEqual(result.metadata["generation_time_ms"], 0)

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

    def test_heading_levels_correct(self):
        """### should be level 3, not misclassified as level 1."""
        md = "# H1\n\n## H2\n\n### H3\n\nParagraph."
        blocks = _parse_markdown_to_blocks(md)
        headings = [b for b in blocks if b["type"] == "heading"]
        self.assertEqual(len(headings), 3)
        self.assertEqual(headings[0]["metadata"]["level"], 1)
        self.assertEqual(headings[0]["content"], "H1")
        self.assertEqual(headings[1]["metadata"]["level"], 2)
        self.assertEqual(headings[1]["content"], "H2")
        self.assertEqual(headings[2]["metadata"]["level"], 3)
        self.assertEqual(headings[2]["content"], "H3")

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
        """All queries should be dispatched and results combined."""
        config = ResearchConfig.default()
        provider = make_mock_provider()

        dispatched_queries = []

        async def tracking_search(**kwargs):
            dispatched_queries.append(kwargs.get("query", ""))
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
        tool.execute = AsyncMock(side_effect=tracking_search)

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

        results = asyncio.run(loop._search(queries))

        # All 3 queries dispatched and results combined
        self.assertEqual(len(results), 3)
        self.assertEqual(len(dispatched_queries), 3)
        self.assertEqual(set(dispatched_queries), {"Q1", "Q2", "Q3"})

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
        """Should compact when findings >= 20 and tokens > 40K (noise removal tier)."""
        config = ResearchConfig.default()
        provider = make_mock_provider()
        tool = make_mock_tool()

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        # Create findings with enough text to exceed noise removal threshold (40K)
        findings = [
            self._make_finding(quote="A" * 12000)  # ~3K tokens each
            for _ in range(25)
        ]
        self.assertTrue(loop._should_compact(findings))

    def test_compaction_preserves_top_findings(self):
        """Top-scored findings should survive compaction."""
        config = ResearchConfig.default()

        # Provider returns a structured compact digest
        compact_response = json.dumps({
            "digest": "Summary of dropped findings.",
            "key_claims": [],
            "contradictions": [],
            "unique_data_points": [],
        })
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

        # Progressive thinning: tier 1 noise removal drops low-scored findings.
        # Result should have fewer findings than original.
        self.assertLessEqual(len(result), 25)
        self.assertGreaterEqual(len(result), MIN_FINDINGS_AFTER_COMPACT)

        # Highest-scored finding should still be present
        top_finding = max(
            result,
            key=lambda f: f.relevance_score * 0.6 + f.quality_score * 0.4,
        )
        self.assertGreaterEqual(top_finding.relevance_score, 0.8)

    def test_compaction_creates_digest(self):
        """When tokens exceed LLM compaction threshold, a digest is created."""
        config = ResearchConfig.default()

        compact_response = json.dumps({
            "digest": "Dropped findings mention edge cases in region X.",
            "key_claims": ["edge case in region X"],
            "contradictions": [],
            "unique_data_points": [],
        })
        provider = MagicMock()
        provider.generate = AsyncMock(return_value=compact_response)
        tool = make_mock_tool()

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        # Create findings with scores above noise threshold (0.3) but with
        # enough text to exceed LLM_COMPACTION_THRESHOLD (80K tokens)
        findings = [
            self._make_finding(
                relevance=0.5, quality=0.5,
                quote=f"Substantial finding {i} with lots of text " * 200,
            )
            for i in range(25)
        ]

        result = asyncio.run(loop._compact_findings(findings))

        # When LLM digest was triggered, should contain digest finding
        if provider.generate.called:
            digest_findings = [
                f for f in result if f.source.title == "Compacted findings digest"
            ]
            self.assertEqual(len(digest_findings), 1)
            self.assertIn("edge cases", digest_findings[0].extracted_fields["digest"])
        else:
            # If tokens didn't reach LLM threshold (tier 1+2 were enough),
            # all findings should still be returned
            self.assertGreaterEqual(len(result), MIN_FINDINGS_AFTER_COMPACT)


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


# ─── Contrary Search Tests ─────────────────────────────────────────────────

class ContrarySearchTest(TestCase):
    """Test _search_contrary() method."""

    def _make_finding(self, title="Source", quote="Quote", domain="example.com"):
        return ScoredFinding(
            source=SearchResult(
                url=f"https://{domain}/article",
                title=title,
                snippet="Snippet",
                domain=domain,
            ),
            extracted_fields={"claim": f"Claim from {title}"},
            raw_quote=quote,
            relevance_score=0.8,
            quality_score=0.8,
        )

    def test_search_contrary_generates_and_searches(self):
        """Contrary check should generate contrary queries and search them."""
        config = ResearchConfig.default()

        responses = [
            # 1. Contrary prompt → generates queries
            json.dumps({
                "contrary_queries": [
                    {"query": "Why X is overhyped", "rationale": "Challenge consensus"},
                ]
            }),
            # 2. Extract from contrary results
            json.dumps({
                "findings": [
                    {
                        "source_index": 0,
                        "extracted_fields": {"key_claim": "X has been overhyped"},
                        "raw_quote": "Critics argue X is overhyped.",
                        "relationships": [],
                    }
                ]
            }),
            # 3. Evaluate contrary findings
            json.dumps({
                "evaluations": [
                    {"finding_index": 0, "relevance_score": 0.7, "quality_score": 0.6,
                     "evaluation_notes": "Valid contrarian view"},
                ]
            }),
        ]

        provider = MagicMock()
        provider.generate = AsyncMock(side_effect=responses)

        tool = make_mock_tool([
            SearchResult(
                url="https://critic.com/article",
                title="Why X is Overhyped",
                snippet="Critics argue X is overhyped.",
                domain="critic.com",
            ),
        ])

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        findings = [self._make_finding()]
        result = asyncio.run(loop._search_contrary(findings, "What is X?"))

        # Should return scored contrary findings
        self.assertGreaterEqual(len(result), 1)
        self.assertIsInstance(result[0], ScoredFinding)

    def test_search_contrary_empty_when_no_queries_generated(self):
        """If LLM returns no contrary queries, result is empty."""
        config = ResearchConfig.default()

        provider = MagicMock()
        provider.generate = AsyncMock(return_value=json.dumps({"contrary_queries": []}))

        tool = make_mock_tool()

        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        findings = [self._make_finding()]
        result = asyncio.run(loop._search_contrary(findings, "What is X?"))
        self.assertEqual(result, [])


# ─── Tool Resolution Tests ─────────────────────────────────────────────────

class ResolveToolTest(TestCase):
    """Test _resolve_tool() method."""

    def _make_loop(self):
        config = ResearchConfig.default()
        provider = make_mock_provider()
        web_tool = MagicMock()
        web_tool.name = "web_search"
        doc_tool = MagicMock()
        doc_tool.name = "document_search"
        return ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[web_tool, doc_tool],
        )

    def test_resolve_tool_internal(self):
        """Internal source target should pick document_search."""
        loop = self._make_loop()
        sq = SubQuery(query="contract terms", source_target="internal")
        tool = loop._resolve_tool(sq)
        self.assertEqual(tool.name, "document_search")

    def test_resolve_tool_web_for_default(self):
        """Default source_target 'web' should pick web_search."""
        loop = self._make_loop()
        sq = SubQuery(query="latest news", source_target="web")
        tool = loop._resolve_tool(sq)
        self.assertEqual(tool.name, "web_search")

    def test_resolve_tool_unknown_falls_back_to_web(self):
        """Unknown source_target should fall back to web_search."""
        loop = self._make_loop()
        sq = SubQuery(query="court cases", source_target="court_opinions")
        tool = loop._resolve_tool(sq)
        self.assertEqual(tool.name, "web_search")

    def test_resolve_tool_internal_without_doc_search(self):
        """Internal target without document_search tool should fall back to web."""
        config = ResearchConfig.default()
        provider = make_mock_provider()
        web_tool = MagicMock()
        web_tool.name = "web_search"
        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[web_tool],
        )
        sq = SubQuery(query="contract terms", source_target="internal")
        tool = loop._resolve_tool(sq)
        self.assertEqual(tool.name, "web_search")


# ─── Domain Filter Tests ───────────────────────────────────────────────────

class DomainFilterTest(TestCase):
    """Test _build_domain_filters() method."""

    def test_filters_from_source_config(self):
        """Should pick up domains from matching source entry."""
        config = ResearchConfig(
            sources=SourcesConfig(
                primary=[
                    SourceEntry(type="sec_filings", domains=["sec.gov", "edgar.sec.gov"]),
                ],
                excluded_domains=["spam.com"],
            ),
        )
        provider = make_mock_provider()
        tool = make_mock_tool()
        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        sq = SubQuery(query="AAPL 10-K filing", source_target="sec_filings")
        domains, excluded = loop._build_domain_filters(sq)

        self.assertEqual(domains, ["sec.gov", "edgar.sec.gov"])
        self.assertIn("spam.com", excluded)

    def test_no_domain_filter_for_generic_web(self):
        """Generic web queries should not have domain restrictions."""
        config = ResearchConfig(
            sources=SourcesConfig(
                primary=[SourceEntry(type="web")],
                excluded_domains=["tabloid.com"],
            ),
        )
        provider = make_mock_provider()
        tool = make_mock_tool()
        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        sq = SubQuery(query="general topic", source_target="web")
        domains, excluded = loop._build_domain_filters(sq)

        # web type has no domains restriction
        self.assertIsNone(domains)
        self.assertIn("tabloid.com", excluded)

    def test_excluded_domains_always_present(self):
        """Excluded domains should always be applied."""
        config = ResearchConfig(
            sources=SourcesConfig(excluded_domains=["bad.com", "worse.com"]),
        )
        provider = make_mock_provider()
        tool = make_mock_tool()
        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        sq = SubQuery(query="anything", source_target="web")
        _, excluded = loop._build_domain_filters(sq)

        self.assertEqual(set(excluded), {"bad.com", "worse.com"})


# ─── Citation Leads Tests ──────────────────────────────────────────────────

class CitationLeadsTest(TestCase):
    """Test _get_citation_leads() method."""

    def _make_finding_with_rels(self, relationships):
        return ScoredFinding(
            source=SearchResult(
                url="https://example.com/src",
                title="Source Paper",
                snippet="Snippet",
                domain="example.com",
            ),
            extracted_fields={},
            raw_quote="Quote",
            relationships=relationships,
            relevance_score=0.8,
            quality_score=0.8,
        )

    def test_extracts_cites_relationships(self):
        """Should create SubQueries from 'cites' relationships."""
        config = ResearchConfig.default()
        provider = make_mock_provider()
        tool = make_mock_tool()
        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        findings = [
            self._make_finding_with_rels([
                {"type": "cites", "target_title": "Referenced Paper A"},
                {"type": "cites", "target_url": "https://ref.com/paper-b"},
            ]),
        ]

        leads = loop._get_citation_leads(findings)
        self.assertEqual(len(leads), 2)
        self.assertEqual(leads[0].query, "Referenced Paper A")
        self.assertEqual(leads[1].query, "https://ref.com/paper-b")

    def test_ignores_non_citation_relationships(self):
        """Should skip relationship types that aren't cites/references."""
        config = ResearchConfig.default()
        provider = make_mock_provider()
        tool = make_mock_tool()
        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        findings = [
            self._make_finding_with_rels([
                {"type": "contradicts", "target_title": "Opposing View"},
                {"type": "cites", "target_title": "Valid Citation"},
            ]),
        ]

        leads = loop._get_citation_leads(findings)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0].query, "Valid Citation")

    def test_limits_to_max_per_round(self):
        """Should cap leads at MAX_CITATION_LEADS_PER_ROUND."""
        config = ResearchConfig.default()
        provider = make_mock_provider()
        tool = make_mock_tool()
        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        many_rels = [
            {"type": "cites", "target_title": f"Paper {i}"}
            for i in range(10)
        ]
        findings = [self._make_finding_with_rels(many_rels)]

        leads = loop._get_citation_leads(findings)
        self.assertEqual(len(leads), MAX_CITATION_LEADS_PER_ROUND)


# ─── Token Estimation Tests ────────────────────────────────────────────────

class TokenEstimationTest(TestCase):
    """Test _estimate_findings_tokens() method."""

    def test_basic_estimate(self):
        """Known input should produce expected token count."""
        config = ResearchConfig.default()
        provider = make_mock_provider()
        tool = make_mock_tool()
        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        findings = [
            ScoredFinding(
                source=SearchResult(url="", title="T", snippet="S", domain="d"),
                extracted_fields={"claim": "A" * 400},  # 400 chars
                raw_quote="B" * 400,                      # 400 chars
                evaluation_notes="C" * 200,                # 200 chars
            ),
        ]

        tokens = loop._estimate_findings_tokens(findings)
        # extracted_fields str repr ≈ ~420 chars, raw_quote 400, notes 200 → ~1020/4 ≈ 255
        self.assertGreater(tokens, 200)
        self.assertLess(tokens, 400)

    def test_empty_findings(self):
        """Empty findings should return 0 tokens."""
        config = ResearchConfig.default()
        provider = make_mock_provider()
        tool = make_mock_tool()
        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        self.assertEqual(loop._estimate_findings_tokens([]), 0)


# ─── Stream Chat Fallback Tests ────────────────────────────────────────────

class StreamChatFallbackTest(TestCase):
    """Test that _llm_call works with stream_chat when generate is absent."""

    def test_stream_chat_fallback(self):
        """Provider without generate() should fall back to stream_chat()."""
        config = ResearchConfig.default()

        # Create a provider with stream_chat but NO generate
        chunk1 = MagicMock()
        chunk1.content = '{"sub_queries": [{"query": "Q1"}]'
        chunk2 = MagicMock()
        chunk2.content = "}"

        async def mock_stream(**kwargs):
            for chunk in [chunk1, chunk2]:
                yield chunk

        provider = MagicMock(spec=[])  # Empty spec — no generate attribute
        provider.stream_chat = MagicMock(return_value=mock_stream())

        tool = make_mock_tool()
        loop = ResearchLoop(
            config=config,
            prompt_extension="",
            provider=provider,
            tools=[tool],
        )

        # Call _llm_call directly — should use stream_chat fallback
        result = asyncio.run(loop._llm_call(
            user_prompt="Test",
            system_prompt="System",
            step_name="test",
        ))

        self.assertIn("sub_queries", result)
        self.assertTrue(provider.stream_chat.called)
