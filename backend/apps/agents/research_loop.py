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
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .research_config import ResearchConfig
from .research_tools import ResearchTool, SearchResult, resolve_tools_for_config
from . import research_prompts as prompts

logger = logging.getLogger(__name__)


# ─── Data Models ────────────────────────────────────────────────────────────

@dataclass
class ResearchContext:
    """Context passed into the research loop from the case/thread."""
    case_title: str = ""
    case_position: str = ""
    signals: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    conversation_context: str = ""

    def to_dict(self) -> dict:
        return {
            "case_title": self.case_title,
            "case_position": self.case_position,
            "conversation_context": self.conversation_context,
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
        pending = self.followups[:3]  # Max 3 followups per round
        self.followups = self.followups[3:]
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
        provider,  # LLMProvider instance
        tools: list[ResearchTool],
        progress_callback: Optional[Callable] = None,
        trace_id: Optional[str] = None,
    ):
        self.config = config
        self.prompt_extension = prompt_extension
        self.provider = provider
        self.tools = {t.name: t for t in tools}
        self.progress_callback = progress_callback

        # Runtime state
        self._total_sources_found = 0
        self._search_rounds = 0
        self._semaphore = asyncio.Semaphore(self.config.search.parallel_branches)

        # Observability
        self._trace_id = trace_id
        self._tracer = _get_tracer()

    async def run(self, question: str, context: ResearchContext) -> ResearchResult:
        """Execute the full research loop."""
        start_time = time.time()

        # 1. PLAN
        await self._emit_progress("planning", "Decomposing research question...")
        plan = await self._plan(question, context)
        await self._emit_progress("plan_complete", f"Created {len(plan.sub_queries)} sub-queries")

        # 2. SEARCH + EXTRACT + EVALUATE LOOP
        all_findings: list[ScoredFinding] = []

        for iteration in range(self.config.search.max_iterations):
            # Get queries for this round
            queries = plan.get_pending_queries(iteration)
            if not queries:
                logger.info("research_loop_no_queries", extra={"iteration": iteration})
                break

            await self._emit_progress(
                "searching",
                f"Search round {iteration + 1}: {len(queries)} queries..."
            )

            # Search
            raw_results = await self._search(queries)
            self._search_rounds += 1

            if not raw_results:
                logger.info("research_loop_no_results", extra={"iteration": iteration})
                continue

            # Extract
            await self._emit_progress("extracting", f"Extracting from {len(raw_results)} sources...")
            findings = await self._extract(raw_results)

            # Evaluate
            await self._emit_progress("evaluating", f"Evaluating {len(findings)} findings...")
            scored = await self._evaluate(findings)
            all_findings.extend(scored)
            self._total_sources_found += len(scored)

            # Compact if findings are growing large
            if self._should_compact(all_findings):
                await self._emit_progress("compacting", "Condensing findings...")
                all_findings = await self._compact_findings(all_findings)

            # Follow citations if configured
            if (
                self.config.search.follow_citations
                and iteration < self.config.search.citation_depth
            ):
                citation_leads = self._get_citation_leads(scored)
                if citation_leads:
                    plan.add_followups(citation_leads)

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
            if await self._is_complete(all_findings, question):
                await self._emit_progress("complete", "Research complete — sufficient coverage")
                break

        # 3. CONTRARY CHECK
        if self.config.completeness.require_contrary_check and all_findings:
            await self._emit_progress("contrary_check", "Searching for contrary evidence...")
            contrary = await self._search_contrary(all_findings, question)
            all_findings.extend(contrary)

        # 4. SYNTHESIZE
        await self._emit_progress("synthesizing", "Writing research report...")
        result = await self._synthesize(all_findings, plan, question)

        elapsed_ms = int((time.time() - start_time) * 1000)
        result.metadata = {
            "generation_time_ms": elapsed_ms,
            "iterations": self._search_rounds,
            "total_sources": self._total_sources_found,
            "findings_count": len(all_findings),
            "config_decomposition": self.config.search.decomposition,
            "config_eval_mode": self.config.evaluate.mode,
        }
        result.plan = plan

        await self._emit_progress("done", f"Complete — {len(all_findings)} findings in {elapsed_ms / 1000:.1f}s")
        return result

    # ── Step Implementations ────────────────────────────────────────────

    async def _plan(self, question: str, context: ResearchContext) -> ResearchPlan:
        """LLM decomposes the question into sub-queries."""
        prompt = prompts.build_plan_prompt(
            question=question,
            decomposition=self.config.search.decomposition,
            sources=self.config.sources,
            context=context.to_dict(),
            skill_instructions=self.prompt_extension,
        )

        response = await self._llm_call(prompt, prompts.PLAN_SYSTEM, step_name="plan")
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
                        max_results=5,
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
            skill_instructions=self.prompt_extension,
        )

        response = await self._llm_call(prompt, prompts.EXTRACT_SYSTEM, step_name="extract")
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
            skill_instructions=self.prompt_extension,
        )

        response = await self._llm_call(prompt, prompts.EVALUATE_SYSTEM, step_name="evaluate")
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
            findings_summary=[f.to_dict() for f in findings[:5]],
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
            original_question=question,
            skill_instructions=self.prompt_extension,
        )

        response = await self._llm_call(
            prompt,
            prompts.SYNTHESIZE_SYSTEM,
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
        return leads[:5]  # Limit citation leads per round

    # ── Context Compaction ───────────────────────────────────────────────

    def _should_compact(self, findings: list[ScoredFinding]) -> bool:
        """Check if findings need compaction."""
        if len(findings) < 20:
            return False
        estimated_tokens = self._estimate_findings_tokens(findings)
        return estimated_tokens > 60_000

    def _estimate_findings_tokens(self, findings: list[ScoredFinding]) -> int:
        """Rough token estimate: ~4 chars per token."""
        total_chars = sum(
            len(str(f.extracted_fields)) + len(f.raw_quote) + len(f.evaluation_notes)
            for f in findings
        )
        return total_chars // 4

    async def _compact_findings(
        self, findings: list[ScoredFinding]
    ) -> list[ScoredFinding]:
        """Two-tier compaction: score filter + LLM digest."""
        # Tier 1: Keep top findings by composite score (no LLM cost)
        scored_sorted = sorted(
            findings,
            key=lambda f: (f.relevance_score * 0.6 + f.quality_score * 0.4),
            reverse=True,
        )
        # Keep top 60%, drop bottom 40%
        keep_count = max(10, int(len(scored_sorted) * 0.6))
        top_findings = scored_sorted[:keep_count]
        dropped = scored_sorted[keep_count:]

        if not dropped:
            return top_findings

        # Tier 2: LLM digest of dropped findings
        prompt = prompts.build_compact_prompt(
            dropped_findings=[f.to_dict() for f in dropped],
            kept_count=len(top_findings),
        )
        response = await self._llm_call(
            prompt, prompts.COMPACT_SYSTEM, max_tokens=2000, step_name="compact"
        )
        parsed = _parse_json_from_response(response)

        # Create a synthetic "digest" finding summarizing what was dropped
        digest_text = parsed.get("digest", "")
        if digest_text:
            digest_finding = ScoredFinding(
                source=SearchResult(
                    url="",
                    title="Compacted findings digest",
                    snippet=digest_text,
                    domain="internal",
                ),
                extracted_fields={"digest": digest_text},
                relevance_score=0.5,
                quality_score=0.5,
                evaluation_notes=f"Digest of {len(dropped)} lower-scored findings",
            )
            top_findings.append(digest_finding)

        logger.info(
            "research_compacted",
            extra={"kept": len(top_findings), "dropped": len(dropped)},
        )
        return top_findings

    # ── LLM Interface ───────────────────────────────────────────────────

    async def _llm_call(
        self,
        user_prompt: str,
        system_prompt: str,
        max_tokens: int = 4000,
        step_name: str = "",
    ) -> str:
        """Make a single LLM call using our provider-agnostic interface."""
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
                except Exception:
                    pass
            return response

        except Exception as e:
            if span:
                try:
                    span.end(level="ERROR", status_message=str(e))
                except Exception:
                    pass
            logger.exception("research_llm_call_failed", extra={"error": str(e)})
            return "{}"

    # ── Progress ────────────────────────────────────────────────────────

    async def _emit_progress(self, step: str, message: str):
        """Emit progress update if callback is registered."""
        if self.progress_callback:
            try:
                await self.progress_callback(step, message)
            except Exception:
                pass  # Progress is best-effort


# ─── Utilities ──────────────────────────────────────────────────────────────

def _parse_json_from_response(text: str) -> dict:
    """
    Extract JSON from an LLM response that may contain markdown code fences.
    Robust to common LLM response patterns.
    """
    if not text:
        return {}

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from code fence
    import re
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding first { to last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace : last_brace + 1])
        except json.JSONDecodeError:
            pass

    logger.warning("json_parse_failed", extra={"text_preview": text[:200]})
    return {}


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
    import uuid

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

        # Headings
        if stripped.startswith("# "):
            flush_paragraph()
            blocks.append({
                "id": str(uuid.uuid4()),
                "type": "heading",
                "content": stripped.lstrip("# ").strip(),
                "metadata": {"level": 1},
            })
        elif stripped.startswith("## "):
            flush_paragraph()
            blocks.append({
                "id": str(uuid.uuid4()),
                "type": "heading",
                "content": stripped.lstrip("# ").strip(),
                "metadata": {"level": 2},
            })
        elif stripped.startswith("### "):
            flush_paragraph()
            blocks.append({
                "id": str(uuid.uuid4()),
                "type": "heading",
                "content": stripped.lstrip("# ").strip(),
                "metadata": {"level": 3},
            })
        elif stripped == "":
            flush_paragraph()
        else:
            current_paragraph.append(line)

    flush_paragraph()
    return blocks


def _get_tracer():
    """Get Langfuse client if configured, else None. Best-effort — never raises."""
    try:
        import os
        if not os.environ.get("LANGFUSE_PUBLIC_KEY"):
            return None
        from langfuse import Langfuse
        return Langfuse()
    except ImportError:
        return None
    except Exception:
        return None
