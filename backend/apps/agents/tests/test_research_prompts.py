"""
Tests for research_prompts — prompt building and template correctness.
"""
from django.test import TestCase

from apps.agents.research_config import (
    ExtractConfig,
    ExtractionField,
    EvaluateConfig,
    EvaluationCriterion,
    OutputConfig,
    SourcesConfig,
    SourceEntry,
)
from apps.agents import research_prompts as prompts


class PlanPromptTest(TestCase):
    """Test build_plan_prompt()."""

    def test_includes_question(self):
        prompt = prompts.build_plan_prompt(
            question="What are the risks of AI?",
            decomposition="simple",
            sources=SourcesConfig(),
            context={},
            skill_instructions="",
        )
        self.assertIn("What are the risks of AI?", prompt)

    def test_includes_decomposition_guidance(self):
        prompt = prompts.build_plan_prompt(
            question="Test",
            decomposition="issue_spotting",
            sources=SourcesConfig(),
            context={},
            skill_instructions="",
        )
        self.assertIn("issue_spotting", prompt.lower().replace("_", " ").replace("-", " ") or prompt)

    def test_includes_source_types(self):
        sources = SourcesConfig(
            primary=[SourceEntry(type="court_opinions", description="Case law")],
            supplementary=[SourceEntry(type="news")],
        )
        prompt = prompts.build_plan_prompt(
            question="Test",
            decomposition="simple",
            sources=sources,
            context={},
            skill_instructions="",
        )
        self.assertIn("court_opinions", prompt)

    def test_includes_skill_instructions(self):
        prompt = prompts.build_plan_prompt(
            question="Test",
            decomposition="simple",
            sources=SourcesConfig(),
            context={},
            skill_instructions="Always prefer peer-reviewed sources.",
        )
        self.assertIn("Always prefer peer-reviewed sources", prompt)

    def test_includes_context(self):
        prompt = prompts.build_plan_prompt(
            question="Test",
            decomposition="simple",
            sources=SourcesConfig(),
            context={"case_title": "FDA Analysis", "case_position": "Approve drug X"},
            skill_instructions="",
        )
        self.assertIn("FDA Analysis", prompt)


class ExtractPromptTest(TestCase):
    """Test build_extract_prompt()."""

    def test_includes_results(self):
        results = [
            {"title": "Test Article", "url": "https://example.com", "snippet": "Test snippet"},
        ]
        prompt = prompts.build_extract_prompt(
            results=results,
            extract_config=ExtractConfig(),
            skill_instructions="",
        )
        self.assertIn("Test Article", prompt)

    def test_includes_field_schema(self):
        config = ExtractConfig(
            fields=[
                ExtractionField(name="holding", description="Court holding", type="text"),
                ExtractionField(name="favorable", type="boolean"),
            ]
        )
        prompt = prompts.build_extract_prompt(
            results=[{"title": "Test", "url": "x", "snippet": "s"}],
            extract_config=config,
            skill_instructions="",
        )
        self.assertIn("holding", prompt)
        self.assertIn("favorable", prompt)

    def test_generic_extraction_without_fields(self):
        prompt = prompts.build_extract_prompt(
            results=[{"title": "Test", "url": "x", "snippet": "s"}],
            extract_config=ExtractConfig(),
            skill_instructions="",
        )
        # Should still produce a valid prompt for generic extraction
        self.assertTrue(len(prompt) > 50)


class EvaluatePromptTest(TestCase):
    """Test build_evaluate_prompt()."""

    def test_includes_findings(self):
        findings = [
            {"source_title": "Article A", "source_url": "x", "extracted_fields": {"claim": "foo"}},
        ]
        prompt = prompts.build_evaluate_prompt(
            findings=findings,
            evaluate_config=EvaluateConfig(),
            skill_instructions="",
        )
        self.assertIn("Article A", prompt)

    def test_includes_rubric(self):
        config = EvaluateConfig(quality_rubric="Prefer authoritative sources.")
        prompt = prompts.build_evaluate_prompt(
            findings=[{"source_title": "A", "source_url": "x", "extracted_fields": {}}],
            evaluate_config=config,
            skill_instructions="",
        )
        self.assertIn("authoritative", prompt)

    def test_includes_criteria(self):
        config = EvaluateConfig(
            criteria=[
                EvaluationCriterion(name="Authority", importance="critical", guidance="Weight courts higher"),
            ]
        )
        prompt = prompts.build_evaluate_prompt(
            findings=[{"source_title": "A", "source_url": "x", "extracted_fields": {}}],
            evaluate_config=config,
            skill_instructions="",
        )
        self.assertIn("Authority", prompt)
        self.assertIn("critical", prompt)


class CompletenessPromptTest(TestCase):
    """Test build_completeness_prompt()."""

    def test_includes_done_when(self):
        prompt = prompts.build_completeness_prompt(
            findings_summary=[{"source_title": "A"}],
            done_when="At least 3 binding precedents.",
            original_question="Is X legal?",
        )
        self.assertIn("binding precedents", prompt)
        self.assertIn("Is X legal?", prompt)


class SynthesizePromptTest(TestCase):
    """Test build_synthesize_prompt()."""

    def test_includes_output_config(self):
        config = OutputConfig(
            format="memo",
            sections=["Summary", "Analysis"],
            citation_style="bluebook",
            target_length="detailed",
        )
        prompt = prompts.build_synthesize_prompt(
            findings=[{"source_title": "A", "source_url": "x"}],
            plan={"strategy_notes": "Focus on risks"},
            output_config=config,
            original_question="What about X?",
            skill_instructions="",
        )
        self.assertIn("memo", prompt)
        # Citation style may be rendered as "Bluebook" with capitalization
        prompt_lower = prompt.lower()
        self.assertIn("bluebook", prompt_lower)
        self.assertIn("Summary", prompt)

    def test_includes_skill_instructions(self):
        prompt = prompts.build_synthesize_prompt(
            findings=[],
            plan={},
            output_config=OutputConfig(),
            original_question="Q?",
            skill_instructions="Be concise and cite everything.",
        )
        self.assertIn("Be concise", prompt)


class ContraryPromptTest(TestCase):
    """Test build_contrary_prompt()."""

    def test_includes_findings_summary(self):
        prompt = prompts.build_contrary_prompt(
            findings_summary=[{"source_title": "Pro-X Article", "extracted_fields": {"claim": "X is good"}}],
            original_question="Is X good?",
        )
        self.assertIn("Pro-X Article", prompt)
        self.assertIn("Is X good?", prompt)


class SystemPromptsTest(TestCase):
    """Test that system prompts are non-empty and well-formed."""

    def test_system_prompts_exist(self):
        self.assertTrue(len(prompts.PLAN_SYSTEM) > 50)
        self.assertTrue(len(prompts.EXTRACT_SYSTEM) > 50)
        self.assertTrue(len(prompts.EVALUATE_SYSTEM) > 50)
        self.assertTrue(len(prompts.COMPLETENESS_SYSTEM) > 50)
        self.assertTrue(len(prompts.SYNTHESIZE_SYSTEM) > 50)
        self.assertTrue(len(prompts.CONTRARY_SYSTEM) > 50)

    def test_system_prompts_mention_json_where_needed(self):
        """Steps that need structured output should mention JSON."""
        self.assertIn("JSON", prompts.PLAN_SYSTEM)
        self.assertIn("JSON", prompts.EXTRACT_SYSTEM)
        self.assertIn("JSON", prompts.EVALUATE_SYSTEM)
        self.assertIn("JSON", prompts.COMPLETENESS_SYSTEM)
        self.assertIn("JSON", prompts.COMPACT_SYSTEM)


class CompactPromptTest(TestCase):
    """Test build_compact_prompt()."""

    def test_includes_findings_count(self):
        prompt = prompts.build_compact_prompt(
            dropped_findings=[
                {"quality_score": 0.3, "source_title": "Low source A", "extracted_fields": {"claim": "A"}},
                {"quality_score": 0.2, "source_title": "Low source B", "extracted_fields": {"claim": "B"}},
            ],
            kept_count=15,
        )
        self.assertIn("15", prompt)
        self.assertIn("2", prompt)
        self.assertIn("Low source A", prompt)

    def test_includes_kept_count(self):
        prompt = prompts.build_compact_prompt(
            dropped_findings=[{"quality_score": 0.1, "source_title": "X", "extracted_fields": {}}],
            kept_count=10,
        )
        self.assertIn("10 high-scoring findings", prompt)

    def test_compact_system_prompt_exists(self):
        self.assertTrue(len(prompts.COMPACT_SYSTEM) > 20)
