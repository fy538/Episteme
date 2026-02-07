"""
Tests for ResearchConfig — parsing, defaults, and validation.
"""
from django.test import TestCase

from apps.agents.research_config import (
    ResearchConfig,
    SourcesConfig,
    SourceEntry,
    TrustedPublisher,
    SearchConfig,
    BudgetConfig,
    ExtractConfig,
    ExtractionField,
    EvaluateConfig,
    EvaluationCriterion,
    CompletenessConfig,
    OutputConfig,
    DEFAULT_QUALITY_RUBRIC,
    DEFAULT_SECTIONS,
    VALID_DECOMPOSITIONS,
)


class ResearchConfigFromDictTest(TestCase):
    """Test ResearchConfig.from_dict() with various inputs."""

    def test_empty_dict_returns_defaults(self):
        config = ResearchConfig.from_dict({})
        self.assertEqual(config.search.decomposition, "simple")
        self.assertEqual(config.search.max_iterations, 5)
        self.assertEqual(config.evaluate.mode, "corroborative")
        self.assertEqual(config.completeness.min_sources, 3)
        self.assertEqual(config.output.format, "report")

    def test_none_returns_defaults(self):
        config = ResearchConfig.from_dict(None)
        self.assertEqual(config.search.max_iterations, 5)

    def test_full_config_parses(self):
        data = {
            "sources": {
                "primary": [
                    {"type": "court_opinions", "description": "Case law", "domains": ["courtlistener.com"]},
                ],
                "supplementary": [{"type": "news"}],
                "trusted_publishers": [
                    {"domain": "supremecourt.gov", "trust": "primary"},
                ],
                "excluded_domains": ["reddit.com"],
            },
            "search": {
                "decomposition": "issue_spotting",
                "parallel_branches": 5,
                "max_iterations": 10,
                "budget": {"max_sources": 30, "max_search_rounds": 12},
                "follow_citations": True,
                "citation_depth": 3,
            },
            "extract": {
                "fields": [
                    {"name": "holding", "description": "Court holding", "type": "text", "required": True},
                    {"name": "favorable", "type": "boolean"},
                ],
                "relationships": ["cites", "overrules"],
            },
            "evaluate": {
                "mode": "hierarchical",
                "quality_rubric": "Prefer binding precedent.",
                "criteria": [
                    {"name": "Authority", "importance": "critical", "guidance": "Weight binding courts higher"},
                ],
            },
            "completeness": {
                "min_sources": 5,
                "max_sources": 30,
                "require_contrary_check": True,
                "require_source_diversity": False,
                "done_when": "At least 3 binding precedents found.",
            },
            "output": {
                "format": "memo",
                "sections": ["Summary", "Analysis", "Conclusion"],
                "citation_style": "bluebook",
                "target_length": "detailed",
            },
        }

        config = ResearchConfig.from_dict(data)

        # Sources
        self.assertEqual(len(config.sources.primary), 1)
        self.assertEqual(config.sources.primary[0].type, "court_opinions")
        self.assertEqual(config.sources.primary[0].domains, ["courtlistener.com"])
        self.assertEqual(len(config.sources.supplementary), 1)
        self.assertEqual(config.sources.trusted_publishers[0].trust, "primary")
        self.assertEqual(config.sources.excluded_domains, ["reddit.com"])

        # Search
        self.assertEqual(config.search.decomposition, "issue_spotting")
        self.assertEqual(config.search.parallel_branches, 5)
        self.assertEqual(config.search.max_iterations, 10)
        self.assertEqual(config.search.budget.max_sources, 30)
        self.assertTrue(config.search.follow_citations)
        self.assertEqual(config.search.citation_depth, 3)

        # Extract
        self.assertEqual(len(config.extract.fields), 2)
        self.assertEqual(config.extract.fields[0].name, "holding")
        self.assertTrue(config.extract.fields[0].required)
        self.assertEqual(config.extract.fields[1].type, "boolean")
        self.assertEqual(config.extract.relationships, ["cites", "overrules"])

        # Evaluate
        self.assertEqual(config.evaluate.mode, "hierarchical")
        self.assertIn("binding precedent", config.evaluate.quality_rubric)
        self.assertEqual(config.evaluate.criteria[0].importance, "critical")

        # Completeness
        self.assertEqual(config.completeness.min_sources, 5)
        self.assertTrue(config.completeness.require_contrary_check)
        self.assertFalse(config.completeness.require_source_diversity)

        # Output
        self.assertEqual(config.output.format, "memo")
        self.assertEqual(config.output.citation_style, "bluebook")
        self.assertEqual(config.output.target_length, "detailed")

    def test_partial_config_merges_defaults(self):
        """Only sources specified — everything else should be defaults."""
        data = {
            "sources": {
                "primary": [{"type": "sec_filings"}],
            }
        }
        config = ResearchConfig.from_dict(data)

        self.assertEqual(len(config.sources.primary), 1)
        self.assertEqual(config.sources.primary[0].type, "sec_filings")
        # Rest is default
        self.assertEqual(config.search.decomposition, "simple")
        self.assertEqual(config.evaluate.mode, "corroborative")
        self.assertEqual(config.output.format, "report")

    def test_source_entry_from_string(self):
        entry = SourceEntry.from_dict("web")
        self.assertEqual(entry.type, "web")
        self.assertEqual(entry.description, "")
        self.assertEqual(entry.domains, [])

    def test_trusted_publisher_from_string(self):
        pub = TrustedPublisher.from_dict("example.com")
        self.assertEqual(pub.domain, "example.com")
        self.assertEqual(pub.trust, "secondary")

    def test_extraction_field_from_string(self):
        field = ExtractionField.from_dict("key_claim")
        self.assertEqual(field.name, "key_claim")
        self.assertEqual(field.type, "text")

    def test_evaluation_criterion_from_string(self):
        crit = EvaluationCriterion.from_dict("Relevance")
        self.assertEqual(crit.name, "Relevance")
        self.assertEqual(crit.importance, "medium")


class ResearchConfigDefaultTest(TestCase):
    """Test ResearchConfig.default() factory."""

    def test_default_is_valid(self):
        config = ResearchConfig.default()
        is_valid, errors = config.validate()
        self.assertTrue(is_valid, f"Default config should be valid, got errors: {errors}")

    def test_default_has_rubric(self):
        config = ResearchConfig.default()
        self.assertEqual(config.evaluate.quality_rubric, DEFAULT_QUALITY_RUBRIC)

    def test_default_has_sections(self):
        config = ResearchConfig.default()
        self.assertEqual(config.output.sections, list(DEFAULT_SECTIONS))

    def test_default_done_when(self):
        config = ResearchConfig.default()
        self.assertIn("2 independent perspectives", config.completeness.done_when)


class ResearchConfigValidationTest(TestCase):
    """Test ResearchConfig.validate()."""

    def test_valid_config(self):
        config = ResearchConfig.default()
        is_valid, errors = config.validate()
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

    def test_invalid_decomposition(self):
        config = ResearchConfig(search=SearchConfig(decomposition="magic"))
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("decomposition" in e for e in errors))

    def test_max_iterations_too_high(self):
        config = ResearchConfig(search=SearchConfig(max_iterations=50))
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("max_iterations" in e for e in errors))

    def test_max_iterations_too_low(self):
        config = ResearchConfig(search=SearchConfig(max_iterations=0))
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)

    def test_parallel_branches_out_of_range(self):
        config = ResearchConfig(search=SearchConfig(parallel_branches=15))
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)

    def test_invalid_field_type(self):
        config = ResearchConfig(
            extract=ExtractConfig(
                fields=[ExtractionField(name="foo", type="invalid_type")]
            )
        )
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("type" in e for e in errors))

    def test_missing_field_name(self):
        config = ResearchConfig(
            extract=ExtractConfig(fields=[ExtractionField(name="")])
        )
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("name" in e for e in errors))

    def test_invalid_eval_mode(self):
        config = ResearchConfig(evaluate=EvaluateConfig(mode="fuzzy"))
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)

    def test_invalid_importance(self):
        config = ResearchConfig(
            evaluate=EvaluateConfig(
                criteria=[EvaluationCriterion(name="Relevance", importance="extreme")]
            )
        )
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)

    def test_min_sources_greater_than_max(self):
        config = ResearchConfig(
            completeness=CompletenessConfig(min_sources=10, max_sources=5)
        )
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("max_sources" in e for e in errors))

    def test_budget_less_than_min_sources(self):
        config = ResearchConfig(
            search=SearchConfig(budget=BudgetConfig(max_sources=2)),
            completeness=CompletenessConfig(min_sources=5),
        )
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)

    def test_invalid_output_format(self):
        config = ResearchConfig(output=OutputConfig(format="powerpoint"))
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)

    def test_invalid_citation_style(self):
        config = ResearchConfig(output=OutputConfig(citation_style="harvard"))
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)

    def test_invalid_target_length(self):
        config = ResearchConfig(output=OutputConfig(target_length="enormous"))
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)

    def test_invalid_trusted_publisher_trust(self):
        config = ResearchConfig(
            sources=SourcesConfig(
                trusted_publishers=[TrustedPublisher(domain="x.com", trust="ultimate")]
            )
        )
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)

    def test_empty_trusted_publisher_domain(self):
        config = ResearchConfig(
            sources=SourcesConfig(
                trusted_publishers=[TrustedPublisher(domain="")]
            )
        )
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)

    def test_citation_depth_out_of_range(self):
        config = ResearchConfig(search=SearchConfig(citation_depth=10))
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)

    def test_multiple_errors(self):
        """Multiple invalid fields should return all errors."""
        config = ResearchConfig(
            search=SearchConfig(decomposition="bad", max_iterations=100),
            evaluate=EvaluateConfig(mode="bad"),
            output=OutputConfig(format="bad"),
        )
        is_valid, errors = config.validate()
        self.assertFalse(is_valid)
        self.assertGreaterEqual(len(errors), 3)


class ResearchConfigUtilityTest(TestCase):
    """Test utility methods."""

    def test_get_effective_rubric_returns_rubric(self):
        config = ResearchConfig(
            evaluate=EvaluateConfig(quality_rubric="Custom rubric")
        )
        self.assertEqual(config.get_effective_rubric(), "Custom rubric")

    def test_get_effective_rubric_builds_from_criteria(self):
        config = ResearchConfig(
            evaluate=EvaluateConfig(
                criteria=[
                    EvaluationCriterion(name="Authority", importance="critical", guidance="Prefer courts"),
                    EvaluationCriterion(name="Recency", importance="medium", guidance="Last 2 years"),
                ]
            )
        )
        rubric = config.get_effective_rubric()
        self.assertIn("[CRITICAL]", rubric)
        self.assertIn("Authority", rubric)
        self.assertIn("Recency", rubric)
        # Medium importance should not have a prefix
        self.assertNotIn("[MEDIUM]", rubric)

    def test_get_effective_rubric_falls_back_to_default(self):
        config = ResearchConfig()
        self.assertEqual(config.get_effective_rubric(), DEFAULT_QUALITY_RUBRIC)

    def test_get_effective_sections_returns_custom(self):
        config = ResearchConfig(
            output=OutputConfig(sections=["A", "B", "C"])
        )
        self.assertEqual(config.get_effective_sections(), ["A", "B", "C"])

    def test_get_effective_sections_falls_back_to_default(self):
        config = ResearchConfig()
        self.assertEqual(config.get_effective_sections(), list(DEFAULT_SECTIONS))

    def test_to_dict_roundtrip(self):
        config = ResearchConfig.default()
        data = config.to_dict()
        self.assertIsInstance(data, dict)
        self.assertIn("search", data)
        self.assertIn("evaluate", data)
        self.assertEqual(data["search"]["decomposition"], "simple")

    def test_all_decomposition_values_valid(self):
        """Ensure all VALID_DECOMPOSITIONS actually pass validation."""
        for decomp in VALID_DECOMPOSITIONS:
            config = ResearchConfig(search=SearchConfig(decomposition=decomp))
            is_valid, errors = config.validate()
            self.assertTrue(
                is_valid,
                f"Decomposition '{decomp}' should be valid but got errors: {errors}",
            )
