"""
Integration tests — Skill → Config → Loop → Artifact pipeline.

Tests the full flow from SKILL.md parsing through config extraction
and into the research loop (with mocks for LLM and search).
"""
from django.test import TestCase

from apps.skills.parser import parse_skill_md, validate_skill_md
from apps.agents.research_config import ResearchConfig


GENERAL_RESEARCH_SKILL_MD = """\
---
name: General Research
description: Thorough multi-step research on any topic
domain: general
episteme:
  applies_to_agents:
    - research
  research_config:
    search:
      decomposition: simple
      max_iterations: 5
      budget:
        max_sources: 20
    evaluate:
      mode: corroborative
      quality_rubric: Prefer authoritative sources.
    completeness:
      min_sources: 3
      done_when: At least 2 independent perspectives.
    output:
      format: report
      sections:
        - Executive Summary
        - Key Findings
        - Sources
      citation_style: inline
      target_length: standard
---

You are a thorough research assistant.
"""

LEGAL_RESEARCH_SKILL_MD = """\
---
name: Legal Research
description: Legal research with court opinions and statutory analysis
domain: legal
episteme:
  applies_to_agents:
    - research
    - critique
  research_config:
    sources:
      primary:
        - type: court_opinions
          description: Federal and state case law
          domains:
            - courtlistener.com
            - law.justia.com
      trusted_publishers:
        - domain: supremecourt.gov
          trust: primary
    search:
      decomposition: issue_spotting
      follow_citations: true
      citation_depth: 2
    extract:
      fields:
        - name: holding
          description: Court holding or ruling
          type: text
          required: true
        - name: favorable
          description: Whether the case supports our position
          type: boolean
    evaluate:
      mode: hierarchical
      criteria:
        - name: Binding Authority
          importance: critical
          guidance: Weight binding courts higher than persuasive
        - name: Recency
          importance: high
          guidance: Prefer recent decisions
    completeness:
      min_sources: 5
      max_sources: 30
      require_contrary_check: true
      done_when: At least 3 binding precedents found.
    output:
      format: memo
      citation_style: bluebook
      target_length: detailed
---

When researching legal questions:
1. Always identify the controlling jurisdiction
2. Start with binding authority before persuasive authority
"""


class SkillMdToConfigTest(TestCase):
    """Test parsing SKILL.md into ResearchConfig."""

    def test_general_skill_parses_and_validates(self):
        is_valid, errors = validate_skill_md(GENERAL_RESEARCH_SKILL_MD)
        self.assertTrue(is_valid, f"Should be valid: {errors}")

    def test_legal_skill_parses_and_validates(self):
        is_valid, errors = validate_skill_md(LEGAL_RESEARCH_SKILL_MD)
        self.assertTrue(is_valid, f"Should be valid: {errors}")

    def test_general_config_extraction(self):
        parsed = parse_skill_md(GENERAL_RESEARCH_SKILL_MD)
        episteme = parsed["metadata"]["episteme"]
        config = ResearchConfig.from_dict(episteme["research_config"])

        self.assertEqual(config.search.decomposition, "simple")
        self.assertEqual(config.search.max_iterations, 5)
        self.assertEqual(config.evaluate.mode, "corroborative")
        self.assertIn("authoritative", config.evaluate.quality_rubric)
        self.assertEqual(config.completeness.min_sources, 3)
        self.assertEqual(config.output.format, "report")

    def test_legal_config_extraction(self):
        parsed = parse_skill_md(LEGAL_RESEARCH_SKILL_MD)
        episteme = parsed["metadata"]["episteme"]
        config = ResearchConfig.from_dict(episteme["research_config"])

        self.assertEqual(config.search.decomposition, "issue_spotting")
        self.assertTrue(config.search.follow_citations)
        self.assertEqual(config.search.citation_depth, 2)
        self.assertEqual(len(config.sources.primary), 1)
        self.assertEqual(config.sources.primary[0].type, "court_opinions")
        self.assertEqual(config.evaluate.mode, "hierarchical")
        self.assertEqual(len(config.evaluate.criteria), 2)
        self.assertEqual(config.extract.fields[0].name, "holding")
        self.assertTrue(config.completeness.require_contrary_check)
        self.assertEqual(config.output.citation_style, "bluebook")

    def test_body_extracted_as_prompt_extension(self):
        parsed = parse_skill_md(LEGAL_RESEARCH_SKILL_MD)
        body = parsed["body"]
        self.assertIn("controlling jurisdiction", body)
        self.assertIn("binding authority", body)


class InvalidSkillConfigTest(TestCase):
    """Test validation catches bad research_config in SKILL.md."""

    def test_invalid_decomposition_in_skill(self):
        content = """\
---
name: Bad Skill
description: Has invalid decomposition
domain: test
episteme:
  applies_to_agents:
    - research
  research_config:
    search:
      decomposition: magic_eight_ball
---

Body text.
"""
        is_valid, errors = validate_skill_md(content)
        self.assertFalse(is_valid)
        self.assertTrue(any("decomposition" in e for e in errors))

    def test_invalid_eval_mode_in_skill(self):
        content = """\
---
name: Bad Eval
description: Has invalid eval mode
domain: test
episteme:
  applies_to_agents:
    - research
  research_config:
    evaluate:
      mode: vibes
---

Body.
"""
        is_valid, errors = validate_skill_md(content)
        self.assertFalse(is_valid)
        self.assertTrue(any("mode" in e for e in errors))


class ConfigMergeTest(TestCase):
    """Test merging research configs from multiple skills."""

    def test_merge_two_configs(self):
        from apps.skills.injection import _merge_research_configs
        from apps.agents.research_config import (
            ResearchConfig, SourcesConfig, SourceEntry, SearchConfig,
            EvaluateConfig, EvaluationCriterion, ExtractConfig, ExtractionField,
            OutputConfig,
        )

        base = ResearchConfig(
            sources=SourcesConfig(primary=[SourceEntry(type="web")]),
            search=SearchConfig(decomposition="simple"),
            evaluate=EvaluateConfig(
                mode="corroborative",
                criteria=[EvaluationCriterion(name="Relevance")],
            ),
            extract=ExtractConfig(
                fields=[ExtractionField(name="key_claim")],
            ),
            output=OutputConfig(format="report"),
        )

        override = ResearchConfig(
            sources=SourcesConfig(
                primary=[SourceEntry(type="court_opinions")],
                excluded_domains=["reddit.com"],
            ),
            search=SearchConfig(decomposition="issue_spotting"),
            evaluate=EvaluateConfig(
                criteria=[EvaluationCriterion(name="Authority", importance="critical")],
            ),
            extract=ExtractConfig(
                fields=[ExtractionField(name="holding", type="text")],
            ),
            output=OutputConfig(citation_style="bluebook"),
        )

        merged = _merge_research_configs(base, override)

        # Sources: union of primary types
        primary_types = [s.type for s in merged.sources.primary]
        self.assertIn("web", primary_types)
        self.assertIn("court_opinions", primary_types)
        self.assertIn("reddit.com", merged.sources.excluded_domains)

        # Search: override wins
        self.assertEqual(merged.search.decomposition, "issue_spotting")

        # Evaluate: criteria merged
        crit_names = [c.name for c in merged.evaluate.criteria]
        self.assertIn("Relevance", crit_names)
        self.assertIn("Authority", crit_names)

        # Extract: fields merged
        field_names = [f.name for f in merged.extract.fields]
        self.assertIn("key_claim", field_names)
        self.assertIn("holding", field_names)

        # Output: override wins for changed fields
        self.assertEqual(merged.output.citation_style, "bluebook")
        # Format stays from base since override is default
        self.assertEqual(merged.output.format, "report")

    def test_merge_preserves_base_when_override_is_default(self):
        """If override has default values, base should win."""
        from apps.skills.injection import _merge_research_configs
        from apps.agents.research_config import (
            ResearchConfig, SearchConfig, EvaluateConfig,
        )

        base = ResearchConfig(
            search=SearchConfig(decomposition="hypothesis_driven", max_iterations=10),
            evaluate=EvaluateConfig(quality_rubric="Custom rubric"),
        )
        override = ResearchConfig()  # All defaults

        merged = _merge_research_configs(base, override)

        self.assertEqual(merged.search.decomposition, "hypothesis_driven")
        self.assertEqual(merged.search.max_iterations, 10)
        self.assertEqual(merged.evaluate.quality_rubric, "Custom rubric")
