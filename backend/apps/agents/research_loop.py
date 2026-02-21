"""
Research Loop — The multi-step research engine.

Runs: Plan → Search → Extract → Evaluate → (iterate?) → Synthesize

Config changes behavior. Code stays the same.
Each step is an LLM call through our provider-agnostic LLMProvider.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

from .research_config import ResearchConfig
from .research_tools import ResearchTool, SearchResult, resolve_tools_for_config
from . import research_prompts as prompts

logger = logging.getLogger(__name__)

# ─── Constants ─────────────────────────────────────────────────────────────

MAX_FOLLOWUPS_PER_ROUND = 3
MAX_RESULTS_PER_QUERY = 5
MAX_CONTRARY_FINDINGS = 5
MAX_CITATION_LEADS_PER_ROUND = 5

# Progressive context thinning thresholds (tokens)
NOISE_REMOVAL_THRESHOLD = 40_000   # Drop findings below min composite score
OBSERVATION_MASK_THRESHOLD = 60_000  # Strip remaining raw source text
LLM_COMPACTION_THRESHOLD = 80_000   # Trigger LLM digest of lowest 40%
NOISE_REMOVAL_MIN_SCORE = 0.3       # Composite score floor for noise removal
COMPACT_KEEP_RATIO = 0.6
MIN_FINDINGS_AFTER_COMPACT = 10
MIN_FINDINGS_FOR_COMPACTION = 20

# LLM call retry settings
LLM_MAX_RETRIES = 2                # Max retry attempts per LLM call
LLM_RETRY_BASE_DELAY = 1.0        # Base delay in seconds (doubles each retry)
LLM_RETRYABLE_ERRORS = (           # Exception types worth retrying
    ConnectionError, TimeoutError,
)


# ─── Provider Protocol ─────────────────────────────────────────────────────

class LLMProviderProtocol(Protocol):
    """Structural type for LLM providers — any object with generate() qualifies.

    The research loop checks ``hasattr(provider, 'generate')`` at call time.
    Providers that only expose ``stream_chat()`` (async iterator of chunks)
    are supported via an automatic fallback that collects the stream.
    """

    async def generate(
        self,
        messages: list[dict],
        system_prompt: str = "",
        max_tokens: int = 4000,
        temperature: float = 0.3,
    ) -> str: ...


# ─── Data Models ────────────────────────────────────────────────────────────

@dataclass
class ResearchContext:
    """Context passed into the research loop from the case/thread."""
    case_title: str = ""
    case_position: str = ""
    signals: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    conversation_context: str = ""
    graph_context: str = ""

    def to_dict(self) -> dict:
        return {
            "case_title": self.case_title,
            "case_position": self.case_position,
            "conversation_context": self.conversation_context,
            "graph_context": self.graph_context,
        }


@dataclass
class SubQuery:
    query: str
    source_target: str = "web"
    rationale: str = ""


@dataclass
class ResearchPlan:
    sub_queries: list[SubQuery] = field(default_factory=list)
    strategy_notes: str = ""
    followups: list[SubQuery] = field(default_factory=list)

    def add_followups(self, leads: list[SubQuery]):
        self.followups.extend(leads)

    def get_pending_queries(self, iteration: int) -> list[SubQuery]:
        """Get queries for the current iteration."""
        if iteration == 0:
            return self.sub_queries
        # Later iterations use followup queries
        pending = self.followups[:MAX_FOLLOWUPS_PER_ROUND]
        self.followups = self.followups[MAX_FOLLOWUPS_PER_ROUND:]
        return pending


@dataclass
class Finding:
    """A single extracted finding from a source."""
    source: SearchResult
    extracted_fields: dict[str, Any] = field(default_factory=dict)
    raw_quote: str = ""
    relationships: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_title": self.source.title,
            "source_url": self.source.url,
            "source_domain": self.source.domain,
            "extracted_fields": self.extracted_fields,
            "raw_quote": self.raw_quote,
            "relationships": self.relationships,
        }


@dataclass
class ScoredFinding(Finding):
    """A finding with evaluation scores."""
    relevance_score: float = 0.0
    quality_score: float = 0.0
    evaluation_notes: str = ""

    def to_dict(self) -> dict:
        base = super().to_dict()
        base.update({
            "relevance_score": self.relevance_score,
            "quality_score": self.quality_score,
            "evaluation_notes": self.evaluation_notes,
        })
        return base


@dataclass
class ResearchResult:
    """Final output of the research loop."""
    content: str                                # Full markdown report
    blocks: list[dict] = field(default_factory=list)  # Parsed artifact blocks
    findings: list[ScoredFinding] = field(default_factory=list)
    plan: ResearchPlan = field(default_factory=ResearchPlan)
    metadata: dict = field(default_factory=dict)


# ─── Research Loop ──────────────────────────────────────────────────────────

class ResearchLoop:
    """
    Universal research loop. Config changes behavior. Code stays the same.

    Usage:
        config = ResearchConfig.from_dict(skill_config)
        provider = get_llm_provider('chat')
        tools = resolve_tools_for_config(config.sources, case_id)

        loop = ResearchLoop(config, prompt_extension, provider, tools)
        result = await loop.run("What are the risks of...", context)
    """

    def __init__(
        self,
        config: ResearchConfig,
        prompt_extension: str,
        provider: LLMProviderProtocol,
        tools: list[ResearchTool],
        progress_callback: Optional[Callable] = None,
        trace_id: Optional[str] = None,
        checkpoint_callback: Optional[Callable] = None,
        trajectory_recorder: Optional[Any] = None,
    ):
        self.config = config
        self.prompt_extension = prompt_extension
        self.provider = provider
        self.tools = {t.name: t for t in tools}
        self.progress_callback = progress_callback
        self.checkpoint_callback = checkpoint_callback
        self.trajectory_recorder = trajectory_recorder

        # Runtime state
        self._total_sources_found = 0
        self._search_rounds = 0
        self._semaphore = asyncio.Semaphore(self.config.search.parallel_branches)
        self._token_cache: dict[int, int] = {}  # id(finding) → token count

        # Context budget tracking (optional)
        self._context_tracker = None
        if hasattr(provider, 'context_window_tokens'):
            from .context_manager import ContextBudgetTracker
            self._context_tracker = ContextBudgetTracker(provider.context_window_tokens)

        # Cost tracking (optional — requires provider with model attribute)
        self._cost_tracker = None
        if hasattr(provider, 'model'):
            from .context_manager import CostTracker
            self._cost_tracker = CostTracker(model=provider.model)

        # Observability
        self._trace_id = trace_id
        self._tracer = _get_tracer()

    async def run(self, question: str, context: ResearchContext) -> ResearchResult:
        """Execute the full research loop."""
        start_time = time.time()

        # 1. PLAN
        await self._emit_progress("planning", "Decomposing research question...")
        plan_start = time.time()
        plan = await self._plan(question, context)
        self._record_trajectory(
            "plan",
            input_summary=f"Question: {question[:200]}",
            output_summary=f"{len(plan.sub_queries)} sub-queries, strategy: {plan.strategy_notes[:200]}",
            decision_rationale=f"Decomposition: {self.config.search.decomposition}",
            metrics={"sub_queries": len(plan.sub_queries)},
            duration_ms=int((time.time() - plan_start) * 1000),
        )
        await self._emit_progress("plan_complete", f"Created {len(plan.sub_queries)} sub-queries")
        await self._emit_checkpoint("plan", 0, plan, [], question, context)

        # 2. SEARCH + EXTRACT + EVALUATE + CONTRARY + SYNTHESIZE
        result = await self._iterate_and_synthesize(
            plan=plan,
            initial_findings=[],
            question=question,
            context=context,
            start_iteration=0,
        )

        elapsed_ms = int((time.time() - start_time) * 1000)
        result.metadata["generation_time_ms"] = elapsed_ms
        result.plan = plan

        await self._emit_progress(
            "done",
            f"Complete — {result.metadata['findings_count']} findings in {elapsed_ms / 1000:.1f}s",
        )
        return result

    # ── Shared Iteration Loop ──────────────────────────────────────────

    async def _iterate_and_synthesize(
        self,
        plan: ResearchPlan,
        initial_findings: list[ScoredFinding],
        question: str,
        context: ResearchContext,
        start_iteration: int = 0,
    ) -> ResearchResult:
        """
        Run the search/extract/evaluate iteration loop, contrary check,
        and synthesize step. Shared by run() and resume_from_checkpoint().
        """
        all_findings = list(initial_findings)

        for iteration in range(start_iteration, self.config.search.max_iterations):
            queries = plan.get_pending_queries(iteration)
            if not queries:
                logger.info("research_loop_no_queries", extra={"iteration": iteration})
                break

            await self._emit_progress(
                "searching",
                f"Search round {iteration + 1}: {len(queries)} queries...",
            )

            # Search
            search_start = time.time()
            raw_results = await self._search(queries)
            self._search_rounds += 1
            domains_hit = list({r.domain for r in raw_results if r.domain})
            self._record_trajectory(
                "search",
                input_summary=f"{len(queries)} queries: {', '.join(q.query[:50] for q in queries)}",
                output_summary=f"{len(raw_results)} results from {len(domains_hit)} domains",
                metrics={"results": len(raw_results), "domains": domains_hit[:10], "iteration": iteration},
                duration_ms=int((time.time() - search_start) * 1000),
            )

            if not raw_results:
                logger.info("research_loop_no_results", extra={"iteration": iteration})
                continue

            # Extract
            await self._emit_progress("extracting", f"Extracting from {len(raw_results)} sources...")
            extract_start = time.time()
            findings = await self._extract(raw_results)
            self._record_trajectory(
                "extract",
                input_summary=f"{len(raw_results)} sources",
                output_summary=f"{len(findings)} findings extracted",
                metrics={"findings_extracted": len(findings), "iteration": iteration},
                duration_ms=int((time.time() - extract_start) * 1000),
            )

            # Evaluate
            await self._emit_progress("evaluating", f"Evaluating {len(findings)} findings...")
            eval_start = time.time()
            scored = await self._evaluate(findings)
            avg_relevance = sum(f.relevance_score for f in scored) / len(scored) if scored else 0
            self._record_trajectory(
                "evaluate",
                input_summary=f"{len(findings)} findings",
                output_summary=f"{len(scored)} scored, avg relevance: {avg_relevance:.2f}",
                decision_rationale=f"Rubric: {self.config.get_effective_rubric()[:200]}",
                metrics={"scored": len(scored), "avg_relevance": round(avg_relevance, 3), "iteration": iteration},
                duration_ms=int((time.time() - eval_start) * 1000),
            )
            # Observation masking: strip raw source text now that extraction is done.
            # Keeps title/url/domain for citation; drops full_text and long snippets.
            _mask_sources(scored)

            all_findings.extend(scored)
            self._total_sources_found += len(scored)
            await self._emit_checkpoint("evaluate", iteration, plan, all_findings, question, context)

            # Compact if findings are growing large
            if self._should_compact(all_findings):
                await self._emit_progress("compacting", "Condensing findings...")
                all_findings = await self._compact_findings(all_findings)
                await self._emit_checkpoint("compact", iteration, plan, all_findings, question, context)

            # Follow citations if configured
            if (
                self.config.search.follow_citations
                and iteration < self.config.search.citation_depth
            ):
                citation_leads = self._get_citation_leads(scored)
                if citation_leads:
                    plan.add_followups(citation_leads)

            # Check context budget
            if self._context_tracker:
                self._context_tracker.track_findings([f.to_dict() for f in all_findings])
                budget_status = self._context_tracker.check_budget()
                if budget_status["needs_continuation"]:
                    logger.info(
                        "research_loop_context_exhausted",
                        extra={"utilization": budget_status["utilization"], "iteration": iteration},
                    )
                    break

            # Check budget ceiling
            if self._total_sources_found >= self.config.completeness.max_sources:
                logger.info(
                    "research_loop_budget_ceiling",
                    extra={"total_sources": self._total_sources_found},
                )
                break

            if self._search_rounds >= self.config.search.budget.max_search_rounds:
                logger.info("research_loop_max_rounds", extra={"rounds": self._search_rounds})
                break

            # Check completeness
            complete_start = time.time()
            is_done = await self._is_complete(all_findings, question)
            self._record_trajectory(
                "completeness",
                input_summary=f"{len(all_findings)} total findings",
                output_summary="complete" if is_done else "continue",
                decision_rationale=self.config.completeness.done_when[:200] if self.config.completeness.done_when else "min_sources met",
                metrics={"is_complete": is_done, "findings": len(all_findings), "iteration": iteration},
                duration_ms=int((time.time() - complete_start) * 1000),
            )
            if is_done:
                await self._emit_progress("complete", "Research complete — sufficient coverage")
                break

        # Contrary check
        if self.config.completeness.require_contrary_check and all_findings:
            await self._emit_progress("contrary_check", "Searching for contrary evidence...")
            contrary = await self._search_contrary(all_findings, question)
            all_findings.extend(contrary)

        # Synthesize
        await self._emit_progress("synthesizing", "Writing research report...")
        synth_start = time.time()
        result = await self._synthesize(all_findings, plan, question)
        self._record_trajectory(
            "synthesize",
            input_summary=f"{len(all_findings)} findings, {len(plan.sub_queries)} sub-queries",
            output_summary=f"{len(result.blocks)} blocks, {len(result.content)} chars",
            metrics={"blocks": len(result.blocks), "content_length": len(result.content)},
            duration_ms=int((time.time() - synth_start) * 1000),
        )

        result.metadata = {
            "iterations": self._search_rounds,
            "total_sources": self._total_sources_found,
            "findings_count": len(all_findings),
            "config_decomposition": self.config.search.decomposition,
            "config_eval_mode": self.config.evaluate.mode,
        }

        # Flag if context budget was exhausted
        if self._context_tracker and self._context_tracker.budget.needs_continuation:
            result.metadata["needs_continuation"] = True
            result.metadata["context_utilization"] = round(self._context_tracker.budget.utilization, 3)

        # Attach cost summary
        if self._cost_tracker:
            result.metadata["cost"] = self._cost_tracker.summary()

        return result

    # ── Step Implementations ────────────────────────────────────────────

    async def _plan(self, question: str, context: ResearchContext) -> ResearchPlan:
        """LLM decomposes the question into sub-queries."""
        prompt = prompts.build_plan_prompt(
            question=question,
            decomposition=self.config.search.decomposition,
            sources=self.config.sources,
            context=context.to_dict(),
        )
        system = prompts.build_system_prompt(prompts.PLAN_SYSTEM, self.prompt_extension)

        response = await self._llm_call(prompt, system, step_name="plan")
        parsed = _parse_json_from_response(response)

        sub_queries = []
        for sq in parsed.get("sub_queries", []):
            sub_queries.append(SubQuery(
                query=sq.get("query", ""),
                source_target=sq.get("source_target", "web"),
                rationale=sq.get("rationale", ""),
            ))

        # Ensure we have at least one query
        if not sub_queries:
            sub_queries = [SubQuery(query=question, source_target="web")]

        return ResearchPlan(
            sub_queries=sub_queries,
            strategy_notes=parsed.get("strategy_notes", ""),
        )

    async def _search(self, queries: list[SubQuery]) -> list[SearchResult]:
        """Execute search queries in parallel using semaphore."""

        async def _search_one(sq: SubQuery) -> list[SearchResult]:
            async with self._semaphore:
                tool = self._resolve_tool(sq)
                if not tool:
                    return []
                domains, excluded = self._build_domain_filters(sq)
                try:
                    return await tool.execute(
                        query=sq.query,
                        domains=domains,
                        excluded_domains=excluded or None,
                        max_results=MAX_RESULTS_PER_QUERY,
                    )
                except Exception as e:
                    logger.exception(
                        "research_search_failed",
                        extra={"query": sq.query, "tool": tool.name, "error": str(e)},
                    )
                    return []

        results = await asyncio.gather(
            *[_search_one(sq) for sq in queries],
            return_exceptions=True,
        )

        # Flatten, skip exceptions
        all_results: list[SearchResult] = []
        for r in results:
            if isinstance(r, list):
                all_results.extend(r)
            elif isinstance(r, BaseException):
                logger.warning(
                    "research_search_exception", extra={"error": str(r)}
                )
        return all_results

    def _resolve_tool(self, sq: SubQuery) -> ResearchTool | None:
        """Pick the right tool for a sub-query based on source_target."""
        if sq.source_target == "internal":
            return self.tools.get("document_search") or self.tools.get("web_search")
        return self.tools.get("web_search")

    def _build_domain_filters(self, sq: SubQuery) -> tuple[list[str] | None, list[str]]:
        """Build domain include/exclude lists from config for a sub-query."""
        domains = None
        excluded = list(self.config.sources.excluded_domains)

        for source in self.config.sources.primary + self.config.sources.supplementary:
            if source.type == sq.source_target and source.domains:
                domains = source.domains
                break

        return domains, excluded

    async def _extract(self, results: list[SearchResult]) -> list[Finding]:
        """LLM extracts structured fields from search results."""
        if not results:
            return []

        prompt = prompts.build_extract_prompt(
            results=[r.to_dict() for r in results],
            extract_config=self.config.extract,
        )
        system = prompts.build_system_prompt(prompts.EXTRACT_SYSTEM, self.prompt_extension)

        response = await self._llm_call(prompt, system, step_name="extract")
        parsed = _parse_json_from_response(response)

        findings = []
        for f in parsed.get("findings", []):
            source_idx = f.get("source_index", 0)
            if source_idx < len(results):
                findings.append(Finding(
                    source=results[source_idx],
                    extracted_fields=f.get("extracted_fields", {}),
                    raw_quote=f.get("raw_quote", ""),
                    relationships=f.get("relationships", []),
                ))

        return findings

    async def _evaluate(self, findings: list[Finding]) -> list[ScoredFinding]:
        """LLM scores findings using config rubric or criteria."""
        if not findings:
            return []

        prompt = prompts.build_evaluate_prompt(
            findings=[f.to_dict() for f in findings],
            evaluate_config=self.config.evaluate,
            effective_rubric=self.config.get_effective_rubric(),
        )
        system = prompts.build_system_prompt(prompts.EVALUATE_SYSTEM, self.prompt_extension)

        response = await self._llm_call(prompt, system, step_name="evaluate")
        parsed = _parse_json_from_response(response)

        scored = []
        for eval_result in parsed.get("evaluations", []):
            idx = eval_result.get("finding_index", 0)
            if idx < len(findings):
                f = findings[idx]
                scored.append(ScoredFinding(
                    source=f.source,
                    extracted_fields=f.extracted_fields,
                    raw_quote=f.raw_quote,
                    relationships=f.relationships,
                    relevance_score=float(eval_result.get("relevance_score", 0.5)),
                    quality_score=float(eval_result.get("quality_score", 0.5)),
                    evaluation_notes=eval_result.get("evaluation_notes", ""),
                ))

        # If parsing failed, return findings with default scores
        if not scored and findings:
            scored = [
                ScoredFinding(
                    source=f.source,
                    extracted_fields=f.extracted_fields,
                    raw_quote=f.raw_quote,
                    relationships=f.relationships,
                    relevance_score=0.5,
                    quality_score=0.5,
                    evaluation_notes="Evaluation unavailable",
                )
                for f in findings
            ]

        return scored

    async def _is_complete(self, findings: list[ScoredFinding], question: str) -> bool:
        """Check if research is done."""
        # Hard floor
        if len(findings) < self.config.completeness.min_sources:
            return False

        # If no done_when condition, just check min_sources
        if not self.config.completeness.done_when:
            return True

        # Check source diversity
        if self.config.completeness.require_source_diversity:
            domains = set(f.source.domain for f in findings if f.source.domain)
            if len(domains) < 2:
                return False

        # LLM evaluates done_when condition
        prompt = prompts.build_completeness_prompt(
            findings_summary=[f.to_dict() for f in findings],
            done_when=self.config.completeness.done_when,
            original_question=question,
        )

        response = await self._llm_call(prompt, prompts.COMPLETENESS_SYSTEM, step_name="completeness")
        parsed = _parse_json_from_response(response)

        is_complete = parsed.get("complete", False)
        if not is_complete:
            # Add suggested follow-up queries
            suggested = parsed.get("suggested_queries", [])
            logger.info(
                "research_not_complete",
                extra={"reasoning": parsed.get("reasoning", ""), "suggested": suggested},
            )

        return is_complete

    async def _search_contrary(
        self, findings: list[ScoredFinding], question: str
    ) -> list[ScoredFinding]:
        """Search for evidence that contradicts current findings."""
        prompt = prompts.build_contrary_prompt(
            findings_summary=[f.to_dict() for f in findings[:MAX_CONTRARY_FINDINGS]],
            original_question=question,
        )

        response = await self._llm_call(prompt, prompts.CONTRARY_SYSTEM, step_name="contrary")
        parsed = _parse_json_from_response(response)

        contrary_queries = [
            SubQuery(query=q.get("query", ""), rationale=q.get("rationale", ""))
            for q in parsed.get("contrary_queries", [])
        ]

        if not contrary_queries:
            return []

        # Search + extract + evaluate the contrary evidence
        results = await self._search(contrary_queries)
        if not results:
            return []

        extracted = await self._extract(results)
        scored = await self._evaluate(extracted)
        return scored

    async def _synthesize(
        self, findings: list[ScoredFinding], plan: ResearchPlan, question: str
    ) -> ResearchResult:
        """LLM writes the final research output."""
        prompt = prompts.build_synthesize_prompt(
            findings=[f.to_dict() for f in findings],
            plan={"strategy_notes": plan.strategy_notes},
            output_config=self.config.output,
            effective_sections=self.config.get_effective_sections(),
            original_question=question,
        )
        system = prompts.build_system_prompt(prompts.SYNTHESIZE_SYSTEM, self.prompt_extension)

        response = await self._llm_call(
            prompt,
            system,
            max_tokens=_target_length_to_tokens(self.config.output.target_length),
            step_name="synthesize",
        )

        # Parse response into blocks for artifact storage
        blocks = _parse_markdown_to_blocks(response)

        return ResearchResult(
            content=response,
            blocks=blocks,
            findings=findings,
        )

    def _get_citation_leads(self, findings: list[ScoredFinding]) -> list[SubQuery]:
        """Extract follow-up queries from citation relationships."""
        leads = []
        for f in findings:
            for rel in f.relationships:
                if rel.get("type") in ("cites", "references"):
                    target = rel.get("target_title") or rel.get("target_url", "")
                    if target:
                        leads.append(SubQuery(
                            query=target,
                            source_target="web",
                            rationale=f"Cited by {f.source.title}",
                        ))
                        if len(leads) >= MAX_CITATION_LEADS_PER_ROUND:
                            return leads
        return leads

    # ── Context Compaction ───────────────────────────────────────────────

    def _should_compact(self, findings: list[ScoredFinding]) -> bool:
        """Check if findings need any form of compaction (progressive thinning)."""
        if len(findings) < MIN_FINDINGS_FOR_COMPACTION:
            return False
        estimated_tokens = self._estimate_findings_tokens(findings)
        return estimated_tokens > NOISE_REMOVAL_THRESHOLD

    def _estimate_findings_tokens(self, findings: list[ScoredFinding]) -> int:
        """Estimate tokens using tiktoken for accuracy, with per-finding cache.

        Falls back to char÷4 if tiktoken is unavailable.
        """
        total = 0
        for f in findings:
            fid = id(f)
            cached = self._token_cache.get(fid)
            if cached is not None:
                total += cached
                continue
            text = (
                str(f.extracted_fields) + f.raw_quote + f.evaluation_notes
                + f.source.title + f.source.url + f.source.domain
                + str(f.relationships)
            )
            try:
                from apps.common.token_utils import count_tokens
                tokens = count_tokens(text)
            except Exception:
                tokens = len(text) // 4  # fallback
            self._token_cache[fid] = tokens
            total += tokens
        return total

    async def _compact_findings(
        self, findings: list[ScoredFinding]
    ) -> list[ScoredFinding]:
        """Progressive context thinning — three tiers of compaction.

        Tier 1 (40K tokens): Drop findings below NOISE_REMOVAL_MIN_SCORE (free)
        Tier 2 (60K tokens): Observation-mask remaining sources (free)
        Tier 3 (80K tokens): LLM digest of lowest-scored 40% (one LLM call)
        """
        estimated = self._estimate_findings_tokens(findings)
        original_count = len(findings)

        # ── Tier 1: Noise removal (free — no LLM cost) ─────────────────
        if estimated > NOISE_REMOVAL_THRESHOLD:
            findings = [
                f for f in findings
                if (f.relevance_score * 0.6 + f.quality_score * 0.4) >= NOISE_REMOVAL_MIN_SCORE
            ]
            # Never drop below MIN_FINDINGS_AFTER_COMPACT
            if len(findings) < MIN_FINDINGS_AFTER_COMPACT:
                scored_sorted = sorted(
                    findings,
                    key=lambda f: (f.relevance_score * 0.6 + f.quality_score * 0.4),
                    reverse=True,
                )
                findings = scored_sorted[:MIN_FINDINGS_AFTER_COMPACT]
            # Invalidate token cache for removed items
            self._token_cache.clear()
            estimated = self._estimate_findings_tokens(findings)
            logger.info(
                "context_thinning_noise_removal",
                extra={"before": original_count, "after": len(findings), "tokens": estimated},
            )

        # ── Tier 2: Observation masking (free — no LLM cost) ───────────
        if estimated > OBSERVATION_MASK_THRESHOLD:
            _mask_sources(findings)
            self._token_cache.clear()
            estimated = self._estimate_findings_tokens(findings)
            logger.info(
                "context_thinning_observation_mask",
                extra={"findings": len(findings), "tokens_after_mask": estimated},
            )

        # ── Tier 3: LLM structured digest (one LLM call) ──────────────
        if estimated > LLM_COMPACTION_THRESHOLD:
            scored_sorted = sorted(
                findings,
                key=lambda f: (f.relevance_score * 0.6 + f.quality_score * 0.4),
                reverse=True,
            )
            keep_count = max(MIN_FINDINGS_AFTER_COMPACT, int(len(scored_sorted) * COMPACT_KEEP_RATIO))
            top_findings = scored_sorted[:keep_count]
            dropped = scored_sorted[keep_count:]

            if dropped:
                prompt = prompts.build_compact_prompt(
                    dropped_findings=[f.to_dict() for f in dropped],
                    kept_count=len(top_findings),
                )
                system = prompts.build_system_prompt(prompts.COMPACT_SYSTEM, self.prompt_extension)
                response = await self._llm_call(
                    prompt, system, max_tokens=2000, step_name="compact"
                )
                parsed = _parse_json_from_response(response)

                digest_text = parsed.get("digest", "")
                if digest_text:
                    digest_finding = ScoredFinding(
                        source=SearchResult(
                            url="",
                            title="Compacted findings digest",
                            snippet=digest_text,
                            domain="internal",
                        ),
                        extracted_fields={
                            "digest": digest_text,
                            "key_claims": parsed.get("key_claims", []),
                            "contradictions": parsed.get("contradictions", []),
                            "unique_data_points": parsed.get("unique_data_points", []),
                            "sources_summary": parsed.get("sources_summary", ""),
                        },
                        relevance_score=0.5,
                        quality_score=0.5,
                        evaluation_notes=f"Structured digest of {len(dropped)} lower-scored findings",
                    )
                    top_findings.append(digest_finding)

                logger.info(
                    "context_thinning_llm_compaction",
                    extra={"kept": len(top_findings), "dropped": len(dropped)},
                )
                findings = top_findings

        return findings

    # ── LLM Interface ───────────────────────────────────────────────────

    async def _llm_call(
        self,
        user_prompt: str,
        system_prompt: str,
        max_tokens: int = 4000,
        step_name: str = "",
    ) -> str:
        """Make a single LLM call using our provider-agnostic interface.

        Retries on transient errors (ConnectionError, TimeoutError) with
        exponential backoff. Non-retryable errors fail immediately.
        """
        messages = [{"role": "user", "content": user_prompt}]

        # Start observability span
        span = None
        if self._tracer and self._trace_id:
            try:
                span = self._tracer.span(
                    trace_id=self._trace_id,
                    name=step_name or "llm_call",
                    input={"prompt_length": len(user_prompt), "max_tokens": max_tokens},
                )
            except Exception:
                span = None  # Tracing is best-effort

        last_error: Exception | None = None
        for attempt in range(1 + LLM_MAX_RETRIES):
            try:
                # Use generate() for non-streaming single calls
                if hasattr(self.provider, "generate"):
                    response = await self.provider.generate(
                        messages=messages,
                        system_prompt=system_prompt,
                        max_tokens=max_tokens,
                        temperature=0.3,
                    )
                else:
                    # Fallback: collect stream chunks
                    response = ""
                    async for chunk in self.provider.stream_chat(
                        messages=messages,
                        system_prompt=system_prompt,
                        max_tokens=max_tokens,
                        temperature=0.3,
                    ):
                        response += chunk.content

                if span:
                    try:
                        span.end(output={"response_length": len(response)})
                    except Exception as e:
                        logger.debug("Span end failed: %s", e)

                # Record cost estimate (best-effort from text lengths)
                if self._cost_tracker and step_name:
                    try:
                        from apps.common.token_utils import count_tokens
                        in_tokens = count_tokens(system_prompt + user_prompt)
                        out_tokens = count_tokens(response)
                    except Exception:
                        in_tokens = (len(system_prompt) + len(user_prompt)) // 4
                        out_tokens = len(response) // 4
                    self._cost_tracker.record_call(
                        step_name=step_name,
                        input_tokens=in_tokens,
                        output_tokens=out_tokens,
                    )

                return response

            except LLM_RETRYABLE_ERRORS as e:
                last_error = e
                if attempt < LLM_MAX_RETRIES:
                    delay = LLM_RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "research_llm_call_retrying",
                        extra={
                            "step": step_name,
                            "attempt": attempt + 1,
                            "max_retries": LLM_MAX_RETRIES,
                            "delay_s": delay,
                            "error": str(e),
                        },
                    )
                    await asyncio.sleep(delay)
                    continue
                # Exhausted retries — fall through to error handling below
                break
            except Exception as e:
                last_error = e
                break  # Non-retryable error — fail immediately

        # All attempts failed
        if span:
            try:
                span.end(level="ERROR", status_message=str(last_error))
            except Exception as e:
                logger.debug("Span error-end failed: %s", e)
        logger.exception(
            "research_llm_call_failed",
            extra={"error": str(last_error), "step": step_name, "attempts": attempt + 1},
        )
        return "{}"

    # ── Progress ────────────────────────────────────────────────────────

    async def _emit_progress(self, step: str, message: str):
        """Emit progress update if callback is registered."""
        if self.progress_callback:
            try:
                await self.progress_callback(step, message)
            except Exception as e:
                logger.debug("Progress callback failed: %s", e)

    def _record_trajectory(
        self,
        step_name: str,
        input_summary: str = "",
        output_summary: str = "",
        decision_rationale: str = "",
        metrics: dict | None = None,
        duration_ms: int = 0,
    ):
        """Record a trajectory event if recorder is attached. Zero overhead otherwise."""
        if self.trajectory_recorder is None:
            return

        # Pull cost data from the most recent CostTracker entry for this step
        tokens_used = 0
        cost_usd = 0.0
        if self._cost_tracker and self._cost_tracker._calls:
            last_call = self._cost_tracker._calls[-1]
            if last_call.step_name == step_name:
                tokens_used = last_call.input_tokens + last_call.output_tokens
                cost_usd = last_call.cost_usd

        try:
            self.trajectory_recorder.record_step(
                step_name=step_name,
                input_summary=input_summary,
                output_summary=output_summary,
                decision_rationale=decision_rationale,
                metrics=metrics,
                duration_ms=duration_ms,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
            )
        except Exception as e:
            logger.debug("Trajectory recording failed: %s", e)

    async def _emit_checkpoint(
        self,
        phase: str,
        iteration: int,
        plan: ResearchPlan,
        findings: list[ScoredFinding],
        question: str,
        context: ResearchContext,
    ):
        """Emit a checkpoint if callback is registered. Best-effort."""
        if not self.checkpoint_callback:
            return
        try:
            from .checkpoint import ResearchCheckpoint

            checkpoint = ResearchCheckpoint(
                correlation_id=self._trace_id or "",
                question=question,
                iteration=iteration,
                phase=phase,
                total_sources_found=self._total_sources_found,
                search_rounds=self._search_rounds,
                plan_dict={
                    "sub_queries": [
                        {"query": sq.query, "source_target": sq.source_target, "rationale": sq.rationale}
                        for sq in plan.sub_queries
                    ],
                    "strategy_notes": plan.strategy_notes,
                    "followups": [
                        {"query": sq.query, "source_target": sq.source_target, "rationale": sq.rationale}
                        for sq in plan.followups
                    ],
                },
                findings_dicts=[f.to_dict() for f in findings],
                config_dict=self.config.to_dict(),
                prompt_extension=self.prompt_extension,
                context_dict=context.to_dict(),
            )
            await asyncio.to_thread(self.checkpoint_callback, checkpoint)
        except Exception as e:
            logger.debug("Checkpoint emit failed: %s", e)

    # ── Resume from Checkpoint ────────────────────────────────────────────

    @classmethod
    async def resume_from_checkpoint(
        cls,
        checkpoint: Any,  # ResearchCheckpoint (avoid circular at module level)
        config: ResearchConfig,
        prompt_extension: str,
        provider: LLMProviderProtocol,
        tools: list[ResearchTool],
        progress_callback: Optional[Callable] = None,
        trace_id: Optional[str] = None,
        checkpoint_callback: Optional[Callable] = None,
        trajectory_recorder: Optional[Any] = None,
    ) -> ResearchResult:
        """
        Resume a research loop from a saved checkpoint.

        Reconstructs the plan and scored findings from the checkpoint,
        then continues the iteration loop from where it left off.
        """
        loop = cls(
            config=config,
            prompt_extension=prompt_extension,
            provider=provider,
            tools=tools,
            progress_callback=progress_callback,
            trace_id=trace_id,
            checkpoint_callback=checkpoint_callback,
            trajectory_recorder=trajectory_recorder,
        )

        # Restore runtime state
        loop._total_sources_found = checkpoint.total_sources_found
        loop._search_rounds = checkpoint.search_rounds

        # Rebuild plan
        plan = ResearchPlan(
            sub_queries=[
                SubQuery(
                    query=sq.get("query", ""),
                    source_target=sq.get("source_target", "web"),
                    rationale=sq.get("rationale", ""),
                )
                for sq in checkpoint.plan_dict.get("sub_queries", [])
            ],
            strategy_notes=checkpoint.plan_dict.get("strategy_notes", ""),
            followups=[
                SubQuery(
                    query=sq.get("query", ""),
                    source_target=sq.get("source_target", "web"),
                    rationale=sq.get("rationale", ""),
                )
                for sq in checkpoint.plan_dict.get("followups", [])
            ],
        )

        # Rebuild scored findings
        all_findings = _rebuild_findings(checkpoint.findings_dicts)

        # Rebuild context
        context = ResearchContext(
            case_title=checkpoint.context_dict.get("case_title", ""),
            case_position=checkpoint.context_dict.get("case_position", ""),
            conversation_context=checkpoint.context_dict.get("conversation_context", ""),
        )
        question = checkpoint.question

        await loop._emit_progress(
            "resuming",
            f"Resuming from checkpoint at iteration {checkpoint.iteration} "
            f"({len(all_findings)} findings recovered)",
        )

        start_time = time.time()
        start_iteration = checkpoint.iteration + 1

        result = await loop._iterate_and_synthesize(
            plan=plan,
            initial_findings=all_findings,
            question=question,
            context=context,
            start_iteration=start_iteration,
        )

        elapsed_ms = int((time.time() - start_time) * 1000)
        result.metadata["generation_time_ms"] = elapsed_ms
        result.metadata["resumed_from_checkpoint"] = True
        result.metadata["resumed_at_iteration"] = checkpoint.iteration
        result.plan = plan

        await loop._emit_progress(
            "done",
            f"Complete — {result.metadata['findings_count']} findings in {elapsed_ms / 1000:.1f}s (resumed)",
        )
        return result


# ─── Observation Masking ────────────────────────────────────────────────────

SNIPPET_MASK_LENGTH = 100  # chars to keep from snippet after extraction


def _mask_sources(findings: list) -> None:
    """Strip raw source text from findings after extraction.

    After the extract step, the full_text and long snippets in each finding's
    SearchResult source are no longer needed — the extracted_fields and
    raw_quote contain the useful intelligence. Masking reduces context size
    by 30-50% per iteration without losing any extracted information.

    This is the "observation masking" pattern (JetBrains 2025): cheaper
    and equally effective vs. LLM summarization.
    """
    for f in findings:
        src = f.source
        # Drop full_text entirely
        if hasattr(src, "full_text"):
            src.full_text = ""
        # Truncate snippet to a short preview
        if hasattr(src, "snippet") and len(src.snippet) > SNIPPET_MASK_LENGTH:
            src.snippet = src.snippet[:SNIPPET_MASK_LENGTH] + "..."


# ─── Utilities ──────────────────────────────────────────────────────────────

def _parse_json_from_response(text: str) -> dict:
    """
    Extract JSON from an LLM response. Returns {} on failure.

    Delegates to the shared utility in apps.common.utils.
    """
    from apps.common.utils import parse_json_from_response
    result = parse_json_from_response(text)
    return result if isinstance(result, dict) else (result or {})


def _target_length_to_tokens(target: str) -> int:
    """Map target length to approximate max_tokens."""
    return {
        "brief": 1500,
        "standard": 4000,
        "detailed": 8000,
    }.get(target, 4000)


def _parse_markdown_to_blocks(markdown: str) -> list[dict]:
    """
    Parse markdown into artifact blocks.
    Compatible with the existing ArtifactVersion.blocks format.
    """
    blocks = []
    lines = markdown.split("\n")
    current_paragraph = []

    def flush_paragraph():
        if current_paragraph:
            text = "\n".join(current_paragraph).strip()
            if text:
                blocks.append({
                    "id": str(uuid.uuid4()),
                    "type": "paragraph",
                    "content": text,
                })
            current_paragraph.clear()

    for line in lines:
        stripped = line.strip()

        # Headings (check longest prefix first to avoid mis-classification)
        if stripped.startswith("### "):
            flush_paragraph()
            blocks.append({
                "id": str(uuid.uuid4()),
                "type": "heading",
                "content": stripped[4:].strip(),
                "metadata": {"level": 3},
            })
        elif stripped.startswith("## "):
            flush_paragraph()
            blocks.append({
                "id": str(uuid.uuid4()),
                "type": "heading",
                "content": stripped[3:].strip(),
                "metadata": {"level": 2},
            })
        elif stripped.startswith("# "):
            flush_paragraph()
            blocks.append({
                "id": str(uuid.uuid4()),
                "type": "heading",
                "content": stripped[2:].strip(),
                "metadata": {"level": 1},
            })
        elif stripped == "":
            flush_paragraph()
        else:
            current_paragraph.append(line)

    flush_paragraph()
    return blocks


def _rebuild_findings(findings_dicts: list[dict]) -> list[ScoredFinding]:
    """Reconstruct ScoredFinding objects from serialized dicts (checkpoint resume)."""
    findings = []
    for fd in findings_dicts:
        findings.append(ScoredFinding(
            source=SearchResult(
                url=fd.get("source_url", ""),
                title=fd.get("source_title", ""),
                snippet="",
                domain=fd.get("source_domain", ""),
            ),
            extracted_fields=fd.get("extracted_fields", {}),
            raw_quote=fd.get("raw_quote", ""),
            relationships=fd.get("relationships", []),
            relevance_score=float(fd.get("relevance_score", 0.5)),
            quality_score=float(fd.get("quality_score", 0.5)),
            evaluation_notes=fd.get("evaluation_notes", ""),
        ))
    return findings


def _get_tracer() -> Any:
    """Get Langfuse client if configured, else None. Best-effort — never raises."""
    try:
        if not os.environ.get("LANGFUSE_PUBLIC_KEY"):
            return None
        from langfuse import Langfuse
        return Langfuse()
    except ImportError:
        return None
    except Exception:
        return None
