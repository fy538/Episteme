"""
Tests for the lens-based orientation system.

Covers:
- Prompt builders (lens detection, orientation synthesis, exploration angle)
- OrientationService parsing helpers (no DB required)
- Lens selection logic (no DB required)
- Supersession logic description (documents behavior)

Run locally (no DB required):
    DJANGO_SETTINGS_MODULE=config.settings.test pytest apps/graph/tests_orientation.py -v --no-cov
"""

import unittest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

# ── Django setup for imports ──────────────────────────────────────
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
django.setup()

from apps.intelligence.orientation_prompts import (
    build_lens_detection_prompt,
    build_orientation_synthesis_prompt,
    build_exploration_angle_prompt,
    LENS_DEFINITIONS,
)
from apps.graph.orientation_service import OrientationService


# ═══════════════════════════════════════════════════════════════
# Prompt Builder Tests
# ═══════════════════════════════════════════════════════════════


class LensDetectionPromptTests(unittest.TestCase):
    """Tests for build_lens_detection_prompt."""

    def _make_themes(self, count=3):
        return [
            {
                'id': f'theme_{i}',
                'label': f'Theme {i}',
                'summary': f'This is the summary for theme {i}.',
                'coverage_pct': round(100 / count, 1),
            }
            for i in range(count)
        ]

    def test_includes_all_themes(self):
        """All theme summaries should appear in the prompt."""
        themes = self._make_themes(4)
        system_prompt, user_prompt = build_lens_detection_prompt(themes)
        for theme in themes:
            self.assertIn(theme['label'], user_prompt)
            self.assertIn(theme['summary'], user_prompt)

    def test_includes_all_lens_types(self):
        """System prompt should reference all 6 lens types."""
        themes = self._make_themes(2)
        system_prompt, user_prompt = build_lens_detection_prompt(themes)
        for lens_type in LENS_DEFINITIONS:
            self.assertIn(lens_type, system_prompt)

    def test_output_format_instruction(self):
        """System prompt should include XML output format."""
        themes = self._make_themes(2)
        system_prompt, _ = build_lens_detection_prompt(themes)
        self.assertIn('<lens_scores>', system_prompt)
        self.assertIn('score=', system_prompt)


class OrientationSynthesisPromptTests(unittest.TestCase):
    """Tests for build_orientation_synthesis_prompt."""

    def _make_themes(self, count=3):
        return [
            {
                'id': f'theme_{i}',
                'label': f'Theme {i}',
                'summary': f'Summary {i}',
                'coverage_pct': round(100 / count, 1),
                'document_ids': [f'doc_{i}'],
            }
            for i in range(count)
        ]

    def test_includes_lens_instructions(self):
        """Prompt should include lens-specific label in the system prompt."""
        themes = self._make_themes(3)
        for lens_type, definition in LENS_DEFINITIONS.items():
            system_prompt, user_prompt = build_orientation_synthesis_prompt(
                lens_type, themes,
            )
            # The human-readable lens label should appear in the system prompt
            self.assertIn(
                definition['label'], system_prompt,
                f"Lens label '{definition['label']}' not found for {lens_type}",
            )

    def test_includes_theme_summaries(self):
        """All themes should appear in the user prompt."""
        themes = self._make_themes(3)
        _, user_prompt = build_orientation_synthesis_prompt(
            'positions_and_tensions', themes,
        )
        for theme in themes:
            self.assertIn(theme['label'], user_prompt)

    def test_case_context_included(self):
        """Active cases should be included when provided."""
        themes = self._make_themes(2)
        cases = [
            {'title': 'Market Entry', 'decision_question': 'Should we enter market X?'},
        ]
        _, user_prompt = build_orientation_synthesis_prompt(
            'positions_and_tensions', themes, case_context=cases,
        )
        self.assertIn('Market Entry', user_prompt)
        self.assertIn('Should we enter market X?', user_prompt)

    def test_xml_output_format(self):
        """System prompt should specify XML output structure."""
        themes = self._make_themes(2)
        system_prompt, _ = build_orientation_synthesis_prompt(
            'positions_and_tensions', themes,
        )
        self.assertIn('<orientation>', system_prompt)
        self.assertIn('<finding', system_prompt)
        self.assertIn('<angle', system_prompt)


class ExplorationAnglePromptTests(unittest.TestCase):
    """Tests for build_exploration_angle_prompt."""

    def test_includes_angle_title(self):
        """The angle title should appear in the prompt."""
        themes = [{'id': 't1', 'label': 'Theme 1', 'summary': 'Summary', 'coverage_pct': 100}]
        system_prompt, user_prompt = build_exploration_angle_prompt(
            'What are the key risks?', themes, 'positions_and_tensions',
        )
        self.assertIn('What are the key risks?', user_prompt)

    def test_includes_theme_context(self):
        """Theme summaries should appear in the prompt."""
        themes = [
            {'id': 't1', 'label': 'Market Analysis', 'summary': 'Market overview', 'coverage_pct': 60},
            {'id': 't2', 'label': 'Risk Assessment', 'summary': 'Risk factors', 'coverage_pct': 40},
        ]
        _, user_prompt = build_exploration_angle_prompt(
            'Explore risks', themes, 'positions_and_tensions',
        )
        self.assertIn('Market Analysis', user_prompt)
        self.assertIn('Risk Assessment', user_prompt)


# ═══════════════════════════════════════════════════════════════
# OrientationService Parsing Tests
# ═══════════════════════════════════════════════════════════════


class ParseLensScoresTests(unittest.TestCase):
    """Tests for OrientationService._parse_lens_scores."""

    def test_valid_xml(self):
        """Parse well-formed lens scores XML."""
        response = '''
        <lens_scores>
            <lens type="positions_and_tensions" score="0.85" />
            <lens type="structure_and_dependencies" score="0.45" />
            <lens type="perspectives_and_sentiment" score="0.30" />
        </lens_scores>
        '''
        scores = OrientationService._parse_lens_scores(response)
        self.assertEqual(len(scores), 3)
        self.assertAlmostEqual(scores['positions_and_tensions'], 0.85)
        self.assertAlmostEqual(scores['structure_and_dependencies'], 0.45)

    def test_malformed_returns_empty(self):
        """Malformed response should return empty dict."""
        scores = OrientationService._parse_lens_scores('no xml here')
        self.assertEqual(scores, {})

    def test_out_of_range_scores_filtered(self):
        """Scores outside 0.0-1.0 should be filtered out."""
        response = '''
        <lens type="positions_and_tensions" score="1.5" />
        <lens type="structure_and_dependencies" score="-0.1" />
        <lens type="perspectives_and_sentiment" score="0.7" />
        '''
        scores = OrientationService._parse_lens_scores(response)
        self.assertEqual(len(scores), 1)
        self.assertIn('perspectives_and_sentiment', scores)

    def test_non_numeric_score_skipped(self):
        """Non-numeric scores should be skipped gracefully."""
        response = '<lens type="foo" score="high" />'
        scores = OrientationService._parse_lens_scores(response)
        self.assertEqual(scores, {})


class SelectLensesTests(unittest.TestCase):
    """Tests for OrientationService._select_lenses."""

    def test_primary_only(self):
        """When gap > 0.25, no secondary lens."""
        scores = {
            'positions_and_tensions': 0.9,
            'structure_and_dependencies': 0.3,
        }
        primary, secondary, confidence = OrientationService._select_lenses(scores)
        self.assertEqual(primary, 'positions_and_tensions')
        self.assertIsNone(secondary)
        self.assertAlmostEqual(confidence, 0.9)

    def test_with_secondary(self):
        """When gap < 0.25 and second > 0.5, surface secondary."""
        scores = {
            'positions_and_tensions': 0.8,
            'perspectives_and_sentiment': 0.7,
        }
        primary, secondary, confidence = OrientationService._select_lenses(scores)
        self.assertEqual(primary, 'positions_and_tensions')
        self.assertEqual(secondary, 'perspectives_and_sentiment')

    def test_no_secondary_when_low_score(self):
        """No secondary when second score is < 0.5."""
        scores = {
            'positions_and_tensions': 0.8,
            'structure_and_dependencies': 0.4,
        }
        primary, secondary, confidence = OrientationService._select_lenses(scores)
        self.assertEqual(primary, 'positions_and_tensions')
        self.assertIsNone(secondary)

    def test_empty_scores_fallback(self):
        """Empty scores should fall back to positions_and_tensions."""
        primary, secondary, confidence = OrientationService._select_lenses({})
        self.assertEqual(primary, 'positions_and_tensions')
        self.assertIsNone(secondary)
        self.assertAlmostEqual(confidence, 0.5)


class ParseOrientationTests(unittest.TestCase):
    """Tests for OrientationService._parse_orientation."""

    def test_full_orientation_xml(self):
        """Parse a complete orientation XML response."""
        response = '''
        <orientation>
            <lead>Your documents reveal a strong consensus on market direction with notable tensions around timing.</lead>
            <findings>
                <finding type="consensus">
                    <heading>Market growth trajectory is widely agreed</heading>
                    <body>All sources point to 15-20% annual growth in the target market. The evidence base is strong with 4 independent sources.</body>
                    <source_themes>theme_1,theme_2</source_themes>
                    <action>none</action>
                </finding>
                <finding type="tension">
                    <heading>Timing of market entry is contested</heading>
                    <body>Two camps emerge: early movers cite first-mover advantage while cautious voices point to regulatory uncertainty.</body>
                    <source_themes>theme_2,theme_3</source_themes>
                    <action>discuss</action>
                </finding>
                <finding type="gap">
                    <heading>Missing competitive analysis from Asian markets</heading>
                    <body>Your documents focus heavily on US and EU markets but contain almost no data on Asian competitors.</body>
                    <source_themes>theme_1</source_themes>
                    <action>research</action>
                </finding>
            </findings>
            <angles>
                <angle type="discuss">What would change if we delayed entry by 12 months?</angle>
                <angle type="read">How do regulatory timelines compare across regions?</angle>
            </angles>
            <secondary_lens type="obligations_and_constraints" reason="Your documents contain significant regulatory and compliance discussion." />
        </orientation>
        '''
        result = OrientationService._parse_orientation(response)
        self.assertIsNotNone(result)
        self.assertIn('lead', result)
        self.assertIn('consensus', result['lead'].lower())
        self.assertEqual(len(result['findings']), 3)
        self.assertEqual(result['findings'][0]['type'], 'consensus')
        self.assertEqual(result['findings'][1]['type'], 'tension')
        self.assertEqual(result['findings'][2]['type'], 'gap')
        self.assertEqual(result['findings'][1]['action'], 'discuss')
        self.assertEqual(result['findings'][2]['action'], 'research')
        self.assertEqual(len(result['angles']), 2)
        self.assertEqual(result['angles'][0]['type'], 'discuss')
        self.assertIsNotNone(result['secondary_lens'])
        self.assertEqual(result['secondary_lens']['type'], 'obligations_and_constraints')

    def test_empty_response_returns_none(self):
        """Empty or unparseable response should return None."""
        result = OrientationService._parse_orientation('no xml here')
        self.assertIsNone(result)

    def test_lead_only(self):
        """Response with only a lead (no findings) should still parse."""
        response = '<lead>Your documents are preliminary.</lead>'
        result = OrientationService._parse_orientation(response)
        self.assertIsNotNone(result)
        self.assertEqual(result['lead'], 'Your documents are preliminary.')
        self.assertEqual(len(result['findings']), 0)

    def test_findings_without_secondary(self):
        """Findings without secondary_lens should parse correctly."""
        response = '''
        <orientation>
            <lead>Analysis lead.</lead>
            <findings>
                <finding type="pattern">
                    <heading>Recurring theme</heading>
                    <body>Description of pattern.</body>
                    <source_themes>t1</source_themes>
                    <action>none</action>
                </finding>
            </findings>
        </orientation>
        '''
        result = OrientationService._parse_orientation(response)
        self.assertIsNotNone(result)
        self.assertEqual(len(result['findings']), 1)
        self.assertIsNone(result['secondary_lens'])


class ExtractThemeSummariesTests(unittest.TestCase):
    """Tests for OrientationService._extract_theme_summaries."""

    def test_extract_level_2_themes(self):
        """Extract Level 2 themes from a standard hierarchy tree."""
        tree = {
            'id': 'root',
            'level': 3,
            'label': 'Root',
            'children': [
                {
                    'id': 'theme_1',
                    'level': 2,
                    'label': 'Market Analysis',
                    'summary': 'Analysis of market trends',
                    'coverage_pct': 60,
                    'document_ids': ['doc_1'],
                    'children': [],
                },
                {
                    'id': 'theme_2',
                    'level': 2,
                    'label': 'Risk Assessment',
                    'summary': 'Assessment of risks',
                    'coverage_pct': 40,
                    'document_ids': ['doc_2'],
                    'children': [],
                },
            ],
        }
        themes = OrientationService._extract_theme_summaries(tree)
        self.assertEqual(len(themes), 2)
        self.assertEqual(themes[0]['label'], 'Market Analysis')
        self.assertEqual(themes[1]['label'], 'Risk Assessment')

    def test_fallback_to_level_1(self):
        """When no Level 2 nodes exist, treat Level 1 as themes."""
        tree = {
            'id': 'root',
            'level': 2,
            'label': 'Root',
            'children': [
                {
                    'id': 'topic_1',
                    'level': 1,
                    'label': 'Small Topic',
                    'summary': 'A small topic',
                    'coverage_pct': 100,
                    'document_ids': ['doc_1'],
                    'children': [],
                },
            ],
        }
        themes = OrientationService._extract_theme_summaries(tree)
        self.assertEqual(len(themes), 1)
        self.assertEqual(themes[0]['label'], 'Small Topic')

    def test_empty_tree(self):
        """Empty tree should return empty list."""
        self.assertEqual(OrientationService._extract_theme_summaries({}), [])
        self.assertEqual(OrientationService._extract_theme_summaries({'children': []}), [])


if __name__ == '__main__':
    unittest.main()
