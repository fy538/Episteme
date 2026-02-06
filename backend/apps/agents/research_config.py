"""
Research Config — Declarative configuration for the multi-step research agent.

Lives inside a Skill's episteme_config as 'research_config'. Parsed at runtime
into typed dataclasses. Every field has sensible defaults — an empty config
produces a working generic research agent.

Design decisions (evidence-backed):
- quality_rubric string > complex scoring (Snorkel: 37% → 94% alignment)
- importance levels > numeric weights (DeepResearch Bench, Google Vertex)
- Named fields with descriptions for extraction (Instructor 3M+ downloads, Elicit 99.4%)
- done_when prose + min_sources floor (Deep Research survey 2025)
- Budget ceilings as safety valve (CLEAR framework, METR research)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ─── Source Configuration ───────────────────────────────────────────────────

@dataclass
class SourceEntry:
    """A type of source to search (semantic label, not an API name)."""
    type: str                           # e.g. "court_opinions", "sec_filings", "web"
    description: str = ""
    domains: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict | str) -> SourceEntry:
        if isinstance(data, str):
            return cls(type=data)
        return cls(
            type=data.get("type", ""),
            description=data.get("description", ""),
            domains=data.get("domains", []),
        )


@dataclass
class TrustedPublisher:
    """Domain-level trust signal (cross-cutting, applies regardless of source type)."""
    domain: str
    trust: str = "secondary"            # primary | secondary | supplementary

    @classmethod
    def from_dict(cls, data: dict | str) -> TrustedPublisher:
        if isinstance(data, str):
            return cls(domain=data)
        return cls(
            domain=data.get("domain", ""),
            trust=data.get("trust", "secondary"),
        )


@dataclass
class SourcesConfig:
    primary: list[SourceEntry] = field(default_factory=list)
    supplementary: list[SourceEntry] = field(default_factory=list)
    trusted_publishers: list[TrustedPublisher] = field(default_factory=list)
    excluded_domains: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> SourcesConfig:
        return cls(
            primary=[SourceEntry.from_dict(s) for s in data.get("primary", [])],
            supplementary=[SourceEntry.from_dict(s) for s in data.get("supplementary", [])],
            trusted_publishers=[TrustedPublisher.from_dict(p) for p in data.get("trusted_publishers", [])],
            excluded_domains=data.get("excluded_domains", []),
        )


# ─── Search Configuration ──────────────────────────────────────────────────

VALID_DECOMPOSITIONS = frozenset({
    "simple",
    "issue_spotting",
    "hypothesis_driven",
    "entity_pivot",
    "systematic",
    "stakeholder",
})


@dataclass
class BudgetConfig:
    """Safety ceiling to prevent runaway token consumption."""
    max_sources: int = 25
    max_search_rounds: int = 8

    @classmethod
    def from_dict(cls, data: dict) -> BudgetConfig:
        return cls(
            max_sources=data.get("max_sources", 25),
            max_search_rounds=data.get("max_search_rounds", 8),
        )


@dataclass
class SearchConfig:
    decomposition: str = "simple"
    parallel_branches: int = 3
    max_iterations: int = 5
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    follow_citations: bool = False
    citation_depth: int = 2

    @classmethod
    def from_dict(cls, data: dict) -> SearchConfig:
        budget_data = data.get("budget", {})
        return cls(
            decomposition=data.get("decomposition", "simple"),
            parallel_branches=data.get("parallel_branches", 3),
            max_iterations=data.get("max_iterations", 5),
            budget=BudgetConfig.from_dict(budget_data) if isinstance(budget_data, dict) else BudgetConfig(),
            follow_citations=data.get("follow_citations", False),
            citation_depth=data.get("citation_depth", 2),
        )


# ─── Extraction Configuration ──────────────────────────────────────────────

VALID_FIELD_TYPES = frozenset({"text", "boolean", "choice", "numeric"})


@dataclass
class ExtractionField:
    """A named field to extract from each source."""
    name: str
    description: str = ""
    type: str = "text"                  # text | boolean | choice | numeric
    required: bool = False

    @classmethod
    def from_dict(cls, data: dict | str) -> ExtractionField:
        if isinstance(data, str):
            return cls(name=data)
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            type=data.get("type", "text"),
            required=data.get("required", False),
        )


@dataclass
class ExtractConfig:
    fields: list[ExtractionField] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> ExtractConfig:
        return cls(
            fields=[ExtractionField.from_dict(f) for f in data.get("fields", [])],
            relationships=data.get("relationships", []),
        )


# ─── Evaluation Configuration ──────────────────────────────────────────────

VALID_EVAL_MODES = frozenset({"hierarchical", "corroborative", "hybrid"})
VALID_IMPORTANCE_LEVELS = frozenset({"critical", "high", "medium", "low"})


@dataclass
class EvaluationCriterion:
    """A named criterion for evaluating source quality."""
    name: str
    importance: str = "medium"          # critical | high | medium | low
    guidance: str = ""

    @classmethod
    def from_dict(cls, data: dict | str) -> EvaluationCriterion:
        if isinstance(data, str):
            return cls(name=data)
        return cls(
            name=data.get("name", ""),
            importance=data.get("importance", "medium"),
            guidance=data.get("guidance", ""),
        )


@dataclass
class EvaluateConfig:
    mode: str = "corroborative"
    quality_rubric: str = ""
    criteria: list[EvaluationCriterion] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> EvaluateConfig:
        return cls(
            mode=data.get("mode", "corroborative"),
            quality_rubric=data.get("quality_rubric", ""),
            criteria=[EvaluationCriterion.from_dict(c) for c in data.get("criteria", [])],
        )


# ─── Completeness Configuration ────────────────────────────────────────────

@dataclass
class CompletenessConfig:
    min_sources: int = 3
    max_sources: int = 25
    require_contrary_check: bool = False
    require_source_diversity: bool = True
    done_when: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> CompletenessConfig:
        return cls(
            min_sources=data.get("min_sources", 3),
            max_sources=data.get("max_sources", 25),
            require_contrary_check=data.get("require_contrary_check", False),
            require_source_diversity=data.get("require_source_diversity", True),
            done_when=data.get("done_when", ""),
        )


# ─── Output Configuration ──────────────────────────────────────────────────

VALID_OUTPUT_FORMATS = frozenset({
    "memo", "brief", "report", "table", "annotated_bibliography",
})
VALID_CITATION_STYLES = frozenset({
    "inline", "footnote", "bluebook", "apa", "chicago", "mla",
})
VALID_TARGET_LENGTHS = frozenset({"brief", "standard", "detailed"})


@dataclass
class OutputConfig:
    format: str = "report"
    sections: list[str] = field(default_factory=list)
    citation_style: str = "inline"
    target_length: str = "standard"

    @classmethod
    def from_dict(cls, data: dict) -> OutputConfig:
        return cls(
            format=data.get("format", "report"),
            sections=data.get("sections", []),
            citation_style=data.get("citation_style", "inline"),
            target_length=data.get("target_length", "standard"),
        )


# ─── Top-Level Research Config ──────────────────────────────────────────────

DEFAULT_QUALITY_RUBRIC = (
    "Prefer authoritative sources (official sites, peer-reviewed, established publications). "
    "Check recency — prefer content from the last 2 years unless the topic requires historical context. "
    "Cross-reference claims across multiple independent sources. "
    "Flag any source with obvious bias or conflicts of interest."
)

DEFAULT_SECTIONS = [
    "Executive Summary",
    "Key Findings",
    "Supporting Evidence",
    "Contrary Views",
    "Limitations",
    "Sources",
]


@dataclass
class ResearchConfig:
    """
    Top-level config for a research agent loop.

    Parsed from a Skill's ``episteme_config.research_config`` dict.
    Every field is optional — missing values get sensible defaults.
    """
    suggest_defaults: bool = True
    sources: SourcesConfig = field(default_factory=SourcesConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    extract: ExtractConfig = field(default_factory=ExtractConfig)
    evaluate: EvaluateConfig = field(default_factory=EvaluateConfig)
    completeness: CompletenessConfig = field(default_factory=CompletenessConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    # ── Constructors ────────────────────────────────────────────────────

    @classmethod
    def from_dict(cls, data: dict | None) -> ResearchConfig:
        """
        Parse from a raw dict (e.g. from JSON/YAML).
        Missing keys get defaults. Handles ``None`` gracefully.
        """
        if not data:
            return cls.default()

        return cls(
            suggest_defaults=data.get("suggest_defaults", True),
            sources=SourcesConfig.from_dict(data["sources"]) if "sources" in data else SourcesConfig(),
            search=SearchConfig.from_dict(data["search"]) if "search" in data else SearchConfig(),
            extract=ExtractConfig.from_dict(data["extract"]) if "extract" in data else ExtractConfig(),
            evaluate=EvaluateConfig.from_dict(data["evaluate"]) if "evaluate" in data else EvaluateConfig(),
            completeness=CompletenessConfig.from_dict(data["completeness"]) if "completeness" in data else CompletenessConfig(),
            output=OutputConfig.from_dict(data["output"]) if "output" in data else OutputConfig(),
        )

    @classmethod
    def default(cls) -> ResearchConfig:
        """Sensible defaults for generic research (no vertical)."""
        return cls(
            suggest_defaults=True,
            search=SearchConfig(
                decomposition="simple",
                max_iterations=5,
                budget=BudgetConfig(max_sources=20, max_search_rounds=8),
            ),
            evaluate=EvaluateConfig(
                mode="corroborative",
                quality_rubric=DEFAULT_QUALITY_RUBRIC,
            ),
            completeness=CompletenessConfig(
                min_sources=3,
                max_sources=20,
                require_source_diversity=True,
                done_when=(
                    "Research is complete when the core question is answered from "
                    "at least 2 independent perspectives with supporting evidence."
                ),
            ),
            output=OutputConfig(
                format="report",
                sections=list(DEFAULT_SECTIONS),
                citation_style="inline",
                target_length="standard",
            ),
        )

    # ── Validation ──────────────────────────────────────────────────────

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate the config. Returns ``(is_valid, errors)``.

        Rules are intentionally permissive — we warn on unknown values
        rather than rejecting outright, so users can extend without friction.
        """
        errors: list[str] = []

        # Search
        if self.search.max_iterations < 1 or self.search.max_iterations > 20:
            errors.append(
                f"search.max_iterations must be 1-20, got {self.search.max_iterations}"
            )
        if self.search.parallel_branches < 1 or self.search.parallel_branches > 10:
            errors.append(
                f"search.parallel_branches must be 1-10, got {self.search.parallel_branches}"
            )
        if self.search.decomposition not in VALID_DECOMPOSITIONS:
            errors.append(
                f"search.decomposition '{self.search.decomposition}' not recognized. "
                f"Valid: {', '.join(sorted(VALID_DECOMPOSITIONS))}"
            )
        if self.search.citation_depth < 0 or self.search.citation_depth > 5:
            errors.append(
                f"search.citation_depth must be 0-5, got {self.search.citation_depth}"
            )

        # Budget
        if self.search.budget.max_sources < 1:
            errors.append("search.budget.max_sources must be >= 1")
        if self.search.budget.max_search_rounds < 1:
            errors.append("search.budget.max_search_rounds must be >= 1")

        # Extraction fields
        for i, f in enumerate(self.extract.fields):
            if not f.name:
                errors.append(f"extract.fields[{i}].name is required")
            if f.type not in VALID_FIELD_TYPES:
                errors.append(
                    f"extract.fields[{i}].type '{f.type}' not recognized. "
                    f"Valid: {', '.join(sorted(VALID_FIELD_TYPES))}"
                )

        # Evaluation
        if self.evaluate.mode not in VALID_EVAL_MODES:
            errors.append(
                f"evaluate.mode '{self.evaluate.mode}' not recognized. "
                f"Valid: {', '.join(sorted(VALID_EVAL_MODES))}"
            )
        for i, c in enumerate(self.evaluate.criteria):
            if not c.name:
                errors.append(f"evaluate.criteria[{i}].name is required")
            if c.importance not in VALID_IMPORTANCE_LEVELS:
                errors.append(
                    f"evaluate.criteria[{i}].importance '{c.importance}' not recognized. "
                    f"Valid: {', '.join(sorted(VALID_IMPORTANCE_LEVELS))}"
                )

        # Completeness
        if self.completeness.min_sources < 1:
            errors.append("completeness.min_sources must be >= 1")
        if self.completeness.max_sources < self.completeness.min_sources:
            errors.append(
                f"completeness.max_sources ({self.completeness.max_sources}) "
                f"must be >= completeness.min_sources ({self.completeness.min_sources})"
            )
        if self.search.budget.max_sources < self.completeness.min_sources:
            errors.append(
                f"search.budget.max_sources ({self.search.budget.max_sources}) "
                f"must be >= completeness.min_sources ({self.completeness.min_sources})"
            )

        # Output
        if self.output.format not in VALID_OUTPUT_FORMATS:
            errors.append(
                f"output.format '{self.output.format}' not recognized. "
                f"Valid: {', '.join(sorted(VALID_OUTPUT_FORMATS))}"
            )
        if self.output.citation_style not in VALID_CITATION_STYLES:
            errors.append(
                f"output.citation_style '{self.output.citation_style}' not recognized. "
                f"Valid: {', '.join(sorted(VALID_CITATION_STYLES))}"
            )
        if self.output.target_length not in VALID_TARGET_LENGTHS:
            errors.append(
                f"output.target_length '{self.output.target_length}' not recognized. "
                f"Valid: {', '.join(sorted(VALID_TARGET_LENGTHS))}"
            )

        # Trusted publishers
        for i, pub in enumerate(self.sources.trusted_publishers):
            if not pub.domain:
                errors.append(f"sources.trusted_publishers[{i}].domain is required")
            if pub.trust not in ("primary", "secondary", "supplementary"):
                errors.append(
                    f"sources.trusted_publishers[{i}].trust '{pub.trust}' not recognized. "
                    f"Valid: primary, secondary, supplementary"
                )

        return len(errors) == 0, errors

    # ── Utility ─────────────────────────────────────────────────────────

    def get_effective_rubric(self) -> str:
        """Return the evaluation rubric, falling back to default if none set."""
        if self.evaluate.quality_rubric:
            return self.evaluate.quality_rubric
        if self.evaluate.criteria:
            # Build rubric from structured criteria
            lines = []
            for c in self.evaluate.criteria:
                prefix = f"[{c.importance.upper()}]" if c.importance != "medium" else ""
                lines.append(f"{prefix} {c.name}: {c.guidance}".strip())
            return "\n".join(lines)
        return DEFAULT_QUALITY_RUBRIC

    def get_effective_sections(self) -> list[str]:
        """Return output sections, falling back to defaults if none set."""
        return self.output.sections if self.output.sections else list(DEFAULT_SECTIONS)

    def to_dict(self) -> dict[str, Any]:
        """Serialize back to a plain dict (for storage in JSON fields)."""
        import dataclasses
        return dataclasses.asdict(self)
