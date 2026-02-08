"""
Prompt templates for each step of the research loop.

Each function builds a user prompt that includes:
1. Step-specific instructions
2. Relevant config parameters (structured, for programmatic anchoring)
3. The SKILL.md body (natural language domain knowledge)
4. The actual data to process

The system prompt for each step is kept short and role-focused.
The heavy lifting is in the user prompt.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .research_config import (
        ResearchConfig, SourcesConfig, ExtractConfig,
        EvaluateConfig, OutputConfig, CompletenessConfig,
    )


# ─── System Prompts (short, role-focused) ──────────────────────────────────

PLAN_SYSTEM = (
    "You are a research planner. Given a research question and context, "
    "decompose it into concrete sub-queries that a search engine can answer. "
    "Think about what information is actually needed to answer the question well. "
    "Respond with JSON only."
)

EXTRACT_SYSTEM = (
    "You are a research extractor. Given source documents, extract structured "
    "information accurately. Always include a direct quote from the source "
    "to support each extraction. Never fabricate information. "
    "Respond with JSON only."
)

EVALUATE_SYSTEM = (
    "You are a source evaluator. Assess the quality and relevance of research "
    "findings. Be honest about uncertainty. Score fairly — high-quality sources "
    "with relevant findings score high, regardless of whether they confirm or "
    "contradict the hypothesis. "
    "Respond with JSON only."
)

COMPLETENESS_SYSTEM = (
    "You evaluate whether a research effort has gathered sufficient information. "
    "Be rigorous but practical — research can always continue, but there are "
    "diminishing returns. Answer with a clear YES or NO and brief reasoning. "
    "Respond with JSON only."
)

SYNTHESIZE_SYSTEM = (
    "You are a research synthesizer. Create a clear, well-structured research "
    "report from the findings. Cite every factual claim. Be explicit about "
    "conflicting evidence and areas of uncertainty. "
    "Respond in well-structured markdown."
)

CONTRARY_SYSTEM = (
    "You generate search queries designed to find evidence that contradicts "
    "or challenges the findings so far. Think like a devil's advocate — "
    "what would someone who disagrees with these conclusions search for? "
    "Respond with JSON only."
)

COMPACT_SYSTEM = (
    "You condense research findings into a dense digest that preserves "
    "key insights. Focus on unique claims not already covered by the "
    "top findings. Respond with JSON only."
)


# ─── System Prompt Composition ─────────────────────────────────────────────

def build_system_prompt(
    role_prompt: str,
    skill_instructions: str = "",
) -> str:
    """Compose the system prompt: role definition + cached domain knowledge.

    Skill instructions are placed in the system prompt (not the user prompt)
    so they benefit from Anthropic's ephemeral prompt caching. Since the
    system prompt stays stable across all calls within one research session,
    the KV-cache hit rate is maximized.

    Layout (stable prefix → dynamic suffix):
        1. Role definition (short, role-specific)
        2. Domain knowledge from skills (cached across calls)
    """
    if not skill_instructions:
        return role_prompt
    return f"{role_prompt}\n\n# Domain Knowledge\n{skill_instructions}"


# ─── Plan Prompt ────────────────────────────────────────────────────────────

def build_plan_prompt(
    question: str,
    decomposition: str,
    sources: SourcesConfig,
    context: dict,
) -> str:
    """Build the user prompt for the planning step.

    Note: skill_instructions now live in the system prompt via
    build_system_prompt() for cache efficiency.
    """

    # Decomposition strategy guidance
    strategy_guidance = _get_decomposition_guidance(decomposition)

    # Source context
    source_context = ""
    if sources.primary:
        source_types = [s.type for s in sources.primary]
        source_context += f"Primary source types available: {', '.join(source_types)}\n"
    if sources.supplementary:
        source_types = [s.type for s in sources.supplementary]
        source_context += f"Supplementary source types: {', '.join(source_types)}\n"
    if sources.excluded_domains:
        source_context += f"Excluded domains (do not search): {', '.join(sources.excluded_domains)}\n"

    # Case context
    case_context = ""
    if context.get("case_title"):
        case_context += f"Case: {context['case_title']}\n"
    if context.get("case_position"):
        case_context += f"Current position: {context['case_position']}\n"
    if context.get("conversation_context"):
        case_context += f"Recent conversation:\n{context['conversation_context']}\n"

    prompt = f"""## Research Question
{question}

## Planning Strategy
{strategy_guidance}

{f"## Available Sources{chr(10)}{source_context}" if source_context else ""}
{f"## Context{chr(10)}{case_context}" if case_context else ""}

## Your Task
Decompose this research question into 2-5 specific sub-queries that a search engine can answer.

For each sub-query, specify:
- `query`: The actual search query string
- `source_target`: Which source type to search (or "web" for general web search)
- `rationale`: Why this sub-query helps answer the main question

Also provide brief `strategy_notes` explaining your overall research approach.

Respond in JSON:
```json
{{
  "sub_queries": [
    {{"query": "...", "source_target": "...", "rationale": "..."}}
  ],
  "strategy_notes": "..."
}}
```"""
    return prompt.strip()


def _get_decomposition_guidance(strategy: str) -> str:
    """Return natural-language guidance for each decomposition strategy."""
    guidance = {
        "simple": (
            "Break the question into its component parts. "
            "Search broadly first, then narrow based on findings."
        ),
        "issue_spotting": (
            "Identify the distinct legal/analytical issues embedded in the question. "
            "For each issue, identify the applicable rules or frameworks, "
            "then search for evidence on each issue independently."
        ),
        "hypothesis_driven": (
            "Formulate a hypothesis from the question. "
            "Design sub-queries that could confirm OR disconfirm the hypothesis. "
            "Include at least one query specifically designed to find contrary evidence."
        ),
        "entity_pivot": (
            "Identify the key entities (people, organizations, products, events). "
            "Search for each entity, then pivot to relationships between entities "
            "and patterns across entities."
        ),
        "systematic": (
            "Design a systematic search strategy. "
            "Start with broad terms, then use specific terminology discovered in initial results. "
            "Track search terms used to avoid redundancy."
        ),
        "stakeholder": (
            "Identify the key stakeholders affected by this question. "
            "Search for each stakeholder's perspective, interests, and constraints. "
            "Look for areas of alignment and conflict between stakeholders."
        ),
    }
    return guidance.get(strategy, guidance["simple"])


# ─── Extract Prompt ─────────────────────────────────────────────────────────

def build_extract_prompt(
    results: list[dict],
    extract_config: ExtractConfig,
) -> str:
    """Build the user prompt for the extraction step."""

    # Format source results
    sources_text = ""
    for i, r in enumerate(results):
        sources_text += f"\n### Source {i + 1}: {r.get('title', 'Untitled')}\n"
        sources_text += f"URL: {r.get('url', 'N/A')}\n"
        if r.get("published_date"):
            sources_text += f"Date: {r['published_date']}\n"
        content = r.get("full_text") or r.get("snippet", "")
        # Truncate very long content
        if len(content) > 3000:
            content = content[:3000] + "\n...[truncated]"
        sources_text += f"\n{content}\n"

    # Extraction fields
    if extract_config.fields:
        fields_spec = "Extract these specific fields from each source:\n\n"
        for f in extract_config.fields:
            req = " (REQUIRED)" if f.required else ""
            fields_spec += f"- **{f.name}** ({f.type}){req}: {f.description}\n"
    else:
        fields_spec = (
            "Extract key claims, findings, and data points from each source. "
            "For each extraction, include a direct quote from the source."
        )

    # Relationships
    rel_spec = ""
    if extract_config.relationships:
        rel_spec = (
            f"\nAlso note any relationships between sources: "
            f"{', '.join(extract_config.relationships)}\n"
        )

    prompt = f"""## Sources to Extract From
{sources_text}

## Extraction Instructions
{fields_spec}
{rel_spec}

## Your Task
For each source, extract the requested information. Include a direct `raw_quote` from the source text to support each extraction.

Respond in JSON:
```json
{{
  "findings": [
    {{
      "source_index": 0,
      "extracted_fields": {{"field_name": "value", ...}},
      "raw_quote": "exact quote from source supporting this extraction",
      "relationships": [{{"type": "cites", "target_source_index": 1}}]
    }}
  ]
}}
```"""
    return prompt.strip()


# ─── Evaluate Prompt ────────────────────────────────────────────────────────

def build_evaluate_prompt(
    findings: list[dict],
    evaluate_config: EvaluateConfig,
    effective_rubric: str = "",
) -> str:
    """Build the user prompt for the evaluation step."""

    # Format findings
    findings_text = ""
    for i, f in enumerate(findings):
        findings_text += f"\n### Finding {i + 1}\n"
        findings_text += f"Source: {f.get('source_title', 'Unknown')} ({f.get('source_url', 'N/A')})\n"
        if f.get("source_domain"):
            findings_text += f"Domain: {f['source_domain']}\n"
        if f.get("extracted_fields"):
            findings_text += f"Extracted: {json.dumps(f['extracted_fields'], indent=2)}\n"
        if f.get("raw_quote"):
            findings_text += f'Quote: "{f["raw_quote"]}"\n'

    # Evaluation criteria
    if evaluate_config.criteria:
        criteria_spec = "Evaluate each finding against these criteria:\n\n"
        for c in evaluate_config.criteria:
            criteria_spec += f"- **{c.name}** [{c.importance.upper()}]: {c.guidance}\n"
        criteria_spec += (
            f"\nEvaluation mode: **{evaluate_config.mode}**\n"
        )
        if evaluate_config.mode == "hierarchical":
            criteria_spec += "Higher-authority sources override lower-authority sources on conflicting claims.\n"
        elif evaluate_config.mode == "corroborative":
            criteria_spec += "Multiple independent sources increase confidence. Weight by criteria importance.\n"
    elif effective_rubric:
        criteria_spec = f"Evaluation rubric:\n\n{effective_rubric}\n"
    elif evaluate_config.quality_rubric:
        criteria_spec = f"Evaluation rubric:\n\n{evaluate_config.quality_rubric}\n"
    else:
        criteria_spec = (
            "Evaluate based on: source authority, recency, relevance to the question, "
            "and whether claims are well-supported."
        )

    prompt = f"""## Findings to Evaluate
{findings_text}

## Evaluation Criteria
{criteria_spec}

## Your Task
Score each finding on relevance (0.0-1.0) and quality (0.0-1.0).
Provide brief evaluation notes explaining your scoring.

Respond in JSON:
```json
{{
  "evaluations": [
    {{
      "finding_index": 0,
      "relevance_score": 0.85,
      "quality_score": 0.9,
      "evaluation_notes": "Brief explanation of scores"
    }}
  ]
}}
```"""
    return prompt.strip()


# ─── Completeness Prompt ───────────────────────────────────────────────────

def build_completeness_prompt(
    findings_summary: list[dict],
    done_when: str,
    original_question: str = "",
) -> str:
    """Build the prompt for the completeness check."""

    # Summarize what we have
    summary = f"Total findings: {len(findings_summary)}\n"
    if findings_summary:
        avg_quality = sum(f.get("quality_score", 0) for f in findings_summary) / len(findings_summary)
        summary += f"Average quality score: {avg_quality:.2f}\n"

        # Count unique domains
        domains = set(f.get("source_domain", "") for f in findings_summary if f.get("source_domain"))
        summary += f"Unique source domains: {len(domains)}\n"

        # List top findings
        summary += "\nTop findings:\n"
        sorted_findings = sorted(findings_summary, key=lambda f: f.get("quality_score", 0), reverse=True)
        for f in sorted_findings[:5]:
            summary += f"- [{f.get('quality_score', 0):.1f}] {f.get('source_title', 'Unknown')}: "
            fields = f.get("extracted_fields", {})
            preview = str(fields)[:100] if fields else "N/A"
            summary += f"{preview}\n"

    prompt = f"""## Research Progress
{summary}

{f"## Original Question{chr(10)}{original_question}" if original_question else ""}

## Completeness Condition
{done_when}

## Your Task
Based on the findings so far and the completeness condition above, is this research complete?

Answer with exactly:
```json
{{"complete": true, "reasoning": "Brief explanation"}}
```
or
```json
{{"complete": false, "reasoning": "What's still missing", "suggested_queries": ["query1", "query2"]}}
```"""
    return prompt.strip()


# ─── Contrary Search Prompt ────────────────────────────────────────────────

def build_contrary_prompt(
    findings_summary: list[dict],
    original_question: str,
) -> str:
    """Build the prompt for generating contrary evidence search queries."""

    # Summarize the current consensus
    consensus = "Current findings suggest:\n"
    for f in findings_summary[:5]:
        fields = f.get("extracted_fields", {})
        if fields:
            consensus += f"- {json.dumps(fields)[:150]}\n"

    prompt = f"""## Original Question
{original_question}

## Current Findings (Consensus)
{consensus}

## Your Task
Generate 2-3 search queries designed to find evidence that **contradicts** or **challenges** the findings above. Think like a devil's advocate.

Respond in JSON:
```json
{{
  "contrary_queries": [
    {{"query": "...", "rationale": "What this might reveal that contradicts current findings"}}
  ]
}}
```"""
    return prompt.strip()


# ─── Synthesize Prompt ─────────────────────────────────────────────────────

def build_synthesize_prompt(
    findings: list[dict],
    plan: dict,
    output_config: OutputConfig,
    original_question: str,
    effective_sections: list[str] | None = None,
) -> str:
    """Build the user prompt for the synthesis step."""

    # Format findings by quality
    sorted_findings = sorted(findings, key=lambda f: f.get("quality_score", 0), reverse=True)

    findings_text = ""
    for i, f in enumerate(sorted_findings):
        findings_text += f"\n### Finding {i + 1} "
        findings_text += f"[quality: {f.get('quality_score', 0):.1f}, relevance: {f.get('relevance_score', 0):.1f}]\n"
        findings_text += f"Source: {f.get('source_title', 'Unknown')}\n"
        findings_text += f"URL: {f.get('source_url', 'N/A')}\n"
        if f.get("extracted_fields"):
            findings_text += f"Data: {json.dumps(f['extracted_fields'], indent=2)}\n"
        if f.get("raw_quote"):
            findings_text += f'Quote: "{f["raw_quote"]}"\n'
        if f.get("evaluation_notes"):
            findings_text += f"Notes: {f['evaluation_notes']}\n"

    # Output structure — use effective_sections if provided (includes config defaults)
    sections = effective_sections or output_config.sections or [
        "Executive Summary",
        "Key Findings",
        "Supporting Evidence",
        "Contrary Views",
        "Limitations",
        "Sources",
    ]
    sections_spec = "Structure your report with these sections:\n"
    for s in sections:
        sections_spec += f"- **{s}**\n"

    # Length guidance
    length_guidance = {
        "brief": "Keep it concise — approximately 500 words.",
        "standard": "Provide moderate detail — approximately 1500 words.",
        "detailed": "Be thorough — approximately 3000 words with detailed analysis.",
    }
    length = length_guidance.get(output_config.target_length, length_guidance["standard"])

    # Citation style
    citation_guidance = {
        "inline": "Use inline citations: [Source Title](URL) after each cited claim.",
        "footnote": "Use numbered footnote citations [1], [2], etc. List all sources at the end.",
        "bluebook": "Use Bluebook legal citation format.",
        "apa": "Use APA citation format.",
        "chicago": "Use Chicago citation format.",
        "mla": "Use MLA citation format.",
    }
    citation = citation_guidance.get(output_config.citation_style, citation_guidance["inline"])

    prompt = f"""## Original Research Question
{original_question}

## Research Strategy
{plan.get('strategy_notes', 'Standard research approach')}

## All Findings (sorted by quality)
{findings_text}

## Output Instructions
Format: **{output_config.format}**
{sections_spec}
{length}
{citation}

## Your Task
Synthesize the findings into a well-structured {output_config.format}.
- Cite every factual claim with its source
- Be explicit about conflicting evidence
- Note areas of uncertainty or insufficient evidence
- Prioritize higher-quality findings over lower-quality ones

Write the full report in markdown."""
    return prompt.strip()


# ─── Compact Prompt ───────────────────────────────────────────────────────

def build_compact_prompt(
    dropped_findings: list[dict],
    kept_count: int,
) -> str:
    """Build the user prompt for the compaction step."""

    findings_text = ""
    for f in dropped_findings:
        findings_text += f"\n- [{f.get('quality_score', 0):.1f}] {f.get('source_title', '')}: "
        fields = f.get("extracted_fields", {})
        findings_text += str(fields)[:200] + "\n"

    # Count unique domains in dropped findings
    domains = set(f.get("source_domain", "") for f in dropped_findings if f.get("source_domain"))

    prompt = f"""## Context
We have {kept_count} high-scoring findings already retained.
The following {len(dropped_findings)} lower-scoring findings from {len(domains)} domains are being compacted.

## Findings to Digest
{findings_text}

## Your Task
Produce a **structured** digest preserving maximum information density.
Focus on insights NOT likely covered by the {kept_count} retained high-scoring findings.

Respond in JSON:
```json
{{
  "key_claims": ["claim 1", "claim 2"],
  "sources_summary": "{len(dropped_findings)} sources from {len(domains)} domains",
  "contradictions": ["any claims that conflict with the consensus"],
  "unique_data_points": ["niche facts or statistics not in top findings"],
  "digest": "2-3 sentence synthesis of the above"
}}
```"""
    return prompt.strip()
