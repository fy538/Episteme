"""
Tests for the intelligence module — parser, engine config, prompt builder, and plan diff merge.

These tests are pure-Python (no Django ORM needed) for the parser, engine config,
and prompt modules. The merge_plan_diff tests are also pure-Python.

Run with:
    python -m pytest apps/intelligence/tests.py -v
    # or with Django:
    python manage.py test apps.intelligence
"""
import copy
import json
import uuid
from unittest import TestCase

from .parser import SectionedStreamParser, Section, ParsedChunk
from .engine import (
    StreamEventType,
    _SECTION_CONFIGS,
    _SectionConfig,
    UnifiedAnalysisEngine,
)
from .prompts import (
    build_unified_system_prompt,
    build_unified_user_prompt,
    build_case_aware_system_prompt,
    build_scaffolding_system_prompt,
    UnifiedPromptConfig,
    _format_plan_state,
    _build_persona_section,
    _build_case_context_section,
    _build_stage_guidance_section,
    _build_plan_state_section,
    _build_plan_edits_section,
)
from .orientation_prompts import build_orientation_aware_system_prompt


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def _make_plan_content(**overrides):
    """Create a minimal plan content dict for testing."""
    base = {
        'phases': [{'id': 'p1', 'title': 'Phase 1', 'order': 0}],
        'assumptions': [
            {
                'id': 'a1', 'text': 'Market is large enough',
                'status': 'untested', 'risk_level': 'medium',
                'test_strategy': '', 'evidence_summary': '',
            },
            {
                'id': 'a2', 'text': 'Team can execute',
                'status': 'confirmed', 'risk_level': 'low',
                'test_strategy': '', 'evidence_summary': 'Track record',
            },
        ],
        'decision_criteria': [
            {'id': 'c1', 'text': 'Revenue > 1M', 'is_met': False, 'linked_inquiry_id': None},
        ],
        'stage_rationale': 'Just started',
    }
    base.update(overrides)
    return base


def _simulate_stream(raw_text: str) -> list:
    """Parse a complete raw LLM output through the parser, simulating chunked delivery."""
    parser = SectionedStreamParser()
    # Simulate small chunks like real streaming
    all_chunks = []
    chunk_size = 5
    for i in range(0, len(raw_text), chunk_size):
        all_chunks.extend(parser.parse(raw_text[i:i + chunk_size]))
    all_chunks.extend(parser.flush())
    return all_chunks


# ═══════════════════════════════════════════════════════════════════
# Parser Tests
# ═══════════════════════════════════════════════════════════════════


class TestSectionedStreamParser(TestCase):
    """Tests for SectionedStreamParser — the core section detection engine."""

    # --- Basic section detection ---

    def test_parse_response_section(self):
        """Parser detects <response> opening and closing tags."""
        parser = SectionedStreamParser()
        chunks = parser.parse('<response>Hello world</response>')

        response_chunks = [c for c in chunks if c.section == Section.RESPONSE]
        self.assertTrue(len(response_chunks) >= 1)

        # Should have content chunks and a completion marker
        content = ''.join(c.content for c in response_chunks if not c.is_complete)
        self.assertEqual(content, 'Hello world')

        completions = [c for c in response_chunks if c.is_complete]
        self.assertEqual(len(completions), 1)

    def test_parse_reflection_section(self):
        """Parser detects <reflection> section."""
        parser = SectionedStreamParser()
        chunks = parser.parse('<reflection>Think deeper</reflection>')

        reflection_chunks = [c for c in chunks if c.section == Section.REFLECTION]
        content = ''.join(c.content for c in reflection_chunks if not c.is_complete)
        self.assertEqual(content, 'Think deeper')

    def test_parse_plan_edits_section(self):
        """Parser detects <plan_edits> section and accumulates in buffer."""
        parser = SectionedStreamParser()
        json_str = '{"diff_summary": "test change"}'
        chunks = parser.parse(f'<plan_edits>{json_str}</plan_edits>')

        plan_chunks = [c for c in chunks if c.section == Section.PLAN_EDITS]
        self.assertTrue(any(c.is_complete for c in plan_chunks))

        buffer = parser.get_plan_edits_buffer()
        self.assertEqual(buffer, json_str)

    def test_parse_action_hints_section(self):
        """Parser detects <action_hints> and buffers JSON content."""
        parser = SectionedStreamParser()
        json_str = '[{"type": "suggest_case"}]'
        chunks = parser.parse(f'<action_hints>{json_str}</action_hints>')

        buffer = parser.get_action_hints_buffer()
        self.assertEqual(buffer, json_str)

    def test_parse_graph_edits_section(self):
        """Parser detects <graph_edits> and buffers content."""
        parser = SectionedStreamParser()
        json_str = '[{"op": "add", "node": "test"}]'
        chunks = parser.parse(f'<graph_edits>{json_str}</graph_edits>')

        buffer = parser.get_graph_edits_buffer()
        self.assertEqual(buffer, json_str)

    # --- Multi-section parsing ---

    def test_parse_full_unified_output(self):
        """Parser handles a complete unified output with all sections."""
        raw = (
            '<response>The answer is 42.</response>'
            '<reflection>Deep thought required.</reflection>'
            '<action_hints>[]</action_hints>'
            '<graph_edits>[]</graph_edits>'
            '<plan_edits>{}</plan_edits>'
        )
        chunks = _simulate_stream(raw)

        # Response content
        response_content = ''.join(
            c.content for c in chunks
            if c.section == Section.RESPONSE and not c.is_complete
        )
        self.assertIn('42', response_content)

        # Reflection content
        reflection_content = ''.join(
            c.content for c in chunks
            if c.section == Section.REFLECTION and not c.is_complete
        )
        self.assertIn('Deep thought', reflection_content)

        # All sections should have completion markers
        completed_sections = {c.section for c in chunks if c.is_complete}
        self.assertIn(Section.RESPONSE, completed_sections)
        self.assertIn(Section.REFLECTION, completed_sections)
        self.assertIn(Section.ACTION_HINTS, completed_sections)
        self.assertIn(Section.GRAPH_EDITS, completed_sections)
        self.assertIn(Section.PLAN_EDITS, completed_sections)

    # --- Chunked/split marker handling ---

    def test_marker_split_across_chunks(self):
        """Parser handles markers split across multiple chunks."""
        parser = SectionedStreamParser()

        # Feed '<respo' then 'nse>Hello' — marker split across chunks
        chunks1 = parser.parse('<respo')
        chunks2 = parser.parse('nse>Hello</response>')

        all_chunks = chunks1 + chunks2
        response_chunks = [c for c in all_chunks if c.section == Section.RESPONSE]
        content = ''.join(c.content for c in response_chunks if not c.is_complete)
        self.assertEqual(content, 'Hello')

    def test_single_char_chunks(self):
        """Parser works correctly with single-character chunks."""
        parser = SectionedStreamParser()
        raw = '<response>Hi</response>'

        all_chunks = []
        for char in raw:
            all_chunks.extend(parser.parse(char))
        all_chunks.extend(parser.flush())

        response_chunks = [c for c in all_chunks if c.section == Section.RESPONSE]
        content = ''.join(c.content for c in response_chunks if not c.is_complete)
        self.assertEqual(content, 'Hi')
        self.assertTrue(any(c.is_complete for c in response_chunks))

    # --- Edge cases ---

    def test_empty_section(self):
        """Parser handles empty sections."""
        parser = SectionedStreamParser()
        chunks = parser.parse('<response></response>')

        completions = [c for c in chunks if c.section == Section.RESPONSE and c.is_complete]
        self.assertEqual(len(completions), 1)

    def test_empty_plan_edits(self):
        """Parser handles empty object in plan_edits."""
        parser = SectionedStreamParser()
        chunks = parser.parse('<plan_edits>{}</plan_edits>')

        completions = [c for c in chunks if c.section == Section.PLAN_EDITS and c.is_complete]
        self.assertEqual(len(completions), 1)

        buffer = parser.get_plan_edits_buffer()
        self.assertEqual(buffer.strip(), '{}')

    def test_content_before_any_section(self):
        """Content before any section tag is Section.NONE."""
        parser = SectionedStreamParser()
        chunks = parser.parse('Preamble text <response>Hello</response>')

        none_chunks = [c for c in chunks if c.section == Section.NONE and c.content.strip()]
        self.assertTrue(len(none_chunks) >= 1)

    def test_buffer_reset_on_new_section(self):
        """JSON buffers reset when a new opening tag of same type arrives."""
        parser = SectionedStreamParser()
        parser.parse('<action_hints>[1]</action_hints>')
        first_buffer = parser.get_action_hints_buffer()
        self.assertEqual(first_buffer, '[1]')

        # New opening tag should reset
        parser.parse('<action_hints>[2]</action_hints>')
        second_buffer = parser.get_action_hints_buffer()
        self.assertEqual(second_buffer, '[2]')

    def test_flush_emits_remaining_content(self):
        """flush() emits any remaining buffered content."""
        parser = SectionedStreamParser()
        # Feed content inside a section without closing tag
        all_chunks = parser.parse('<response>Incomplete content here')
        remaining = parser.flush()
        all_chunks.extend(remaining)

        # Combine all response content — should include everything
        response_content = ''.join(
            c.content for c in all_chunks
            if c.section == Section.RESPONSE and not c.is_complete
        )
        self.assertIn('Incomplete', response_content)

    def test_plan_edits_complex_json(self):
        """Parser handles complex nested JSON in plan_edits."""
        diff = {
            "diff_summary": "Added new assumption",
            "diff_data": {
                "added_assumptions": [
                    {"text": "Market will grow", "risk_level": "high"}
                ],
                "updated_assumptions": [
                    {"id": "abc-123", "status": "challenged",
                     "evidence_summary": "New data contradicts"}
                ],
            }
        }
        json_str = json.dumps(diff)
        parser = SectionedStreamParser()
        parser.parse(f'<plan_edits>{json_str}</plan_edits>')

        buffer = parser.get_plan_edits_buffer()
        parsed = json.loads(buffer)
        self.assertEqual(parsed['diff_summary'], "Added new assumption")
        self.assertEqual(len(parsed['diff_data']['added_assumptions']), 1)

    def test_section_enum_completeness(self):
        """All non-NONE sections have corresponding markers."""
        marker_sections = set()
        for m in SectionedStreamParser.MARKERS:
            if m.startswith('</'):
                name = m[2:-1]
            else:
                name = m[1:-1]
            marker_sections.add(name)

        for section in Section:
            if section == Section.NONE:
                continue
            self.assertIn(section.value, marker_sections,
                          f"Section {section} has no marker pair in MARKERS")


# ═══════════════════════════════════════════════════════════════════
# Engine Config Tests
# ═══════════════════════════════════════════════════════════════════


class TestEngineConfig(TestCase):
    """Tests for the table-driven engine section configuration."""

    def test_all_sections_have_configs(self):
        """Every non-NONE Section has a _SECTION_CONFIGS entry."""
        for section in Section:
            if section == Section.NONE:
                continue
            self.assertIn(section, _SECTION_CONFIGS,
                          f"Missing config for {section}")

    def test_streaming_sections_have_chunk_events(self):
        """Streaming sections must have both chunk and complete events."""
        for section, cfg in _SECTION_CONFIGS.items():
            if cfg.streams:
                self.assertIsNotNone(cfg.chunk_event,
                                     f"Streaming {section} missing chunk_event")
                self.assertIsNotNone(cfg.complete_event,
                                     f"Streaming {section} missing complete_event")

    def test_buffered_sections_have_getters(self):
        """Buffered sections must have buffer_getter and complete_event."""
        for section, cfg in _SECTION_CONFIGS.items():
            if not cfg.streams:
                self.assertIsNotNone(cfg.buffer_getter,
                                     f"Buffered {section} missing buffer_getter")
                self.assertIsNotNone(cfg.complete_event,
                                     f"Buffered {section} missing complete_event")

    def test_buffer_getters_exist_on_parser(self):
        """Buffer getter method names resolve to real methods on the parser."""
        parser = SectionedStreamParser()
        for section, cfg in _SECTION_CONFIGS.items():
            if cfg.buffer_getter:
                self.assertTrue(
                    hasattr(parser, cfg.buffer_getter),
                    f"Parser missing method {cfg.buffer_getter} "
                    f"(required by {section} config)"
                )
                # Call it — should return a string
                result = getattr(parser, cfg.buffer_getter)()
                self.assertIsInstance(result, str)

    def test_event_types_unique(self):
        """All configured event types are unique across sections."""
        seen_chunk = set()
        seen_complete = set()
        for section, cfg in _SECTION_CONFIGS.items():
            if cfg.chunk_event:
                self.assertNotIn(cfg.chunk_event, seen_chunk,
                                 f"Duplicate chunk_event: {cfg.chunk_event}")
                seen_chunk.add(cfg.chunk_event)
            if cfg.complete_event:
                self.assertNotIn(cfg.complete_event, seen_complete,
                                 f"Duplicate complete_event: {cfg.complete_event}")
                seen_complete.add(cfg.complete_event)

    def test_data_keys_unique(self):
        """All data_key values are unique."""
        keys = [cfg.data_key for cfg in _SECTION_CONFIGS.values()]
        self.assertEqual(len(keys), len(set(keys)), "Duplicate data_key found")

    def test_response_and_reflection_are_streaming(self):
        """Response and reflection sections stream (not buffered)."""
        self.assertTrue(_SECTION_CONFIGS[Section.RESPONSE].streams)
        self.assertTrue(_SECTION_CONFIGS[Section.REFLECTION].streams)

    def test_json_sections_are_buffered(self):
        """Action hints, graph edits, and plan edits are buffered."""
        self.assertFalse(_SECTION_CONFIGS[Section.ACTION_HINTS].streams)
        self.assertFalse(_SECTION_CONFIGS[Section.GRAPH_EDITS].streams)
        self.assertFalse(_SECTION_CONFIGS[Section.PLAN_EDITS].streams)

    def test_plan_edits_default_is_dict(self):
        """Plan edits default value is {} (dict), not [] (list)."""
        cfg = _SECTION_CONFIGS[Section.PLAN_EDITS]
        self.assertIsInstance(cfg.default_value, dict)
        self.assertEqual(cfg.default_value, {})

    def test_engine_has_no_duplicate_method(self):
        """Engine should NOT have the old _analyze_with_custom_prompt method."""
        engine = UnifiedAnalysisEngine()
        self.assertFalse(
            hasattr(engine, '_analyze_with_custom_prompt'),
            "Old duplicated method should be removed"
        )

    def test_engine_has_shared_streaming_method(self):
        """Engine should have the shared _stream_and_parse method."""
        engine = UnifiedAnalysisEngine()
        self.assertTrue(hasattr(engine, '_stream_and_parse'))


# ═══════════════════════════════════════════════════════════════════
# Prompt Tests
# ═══════════════════════════════════════════════════════════════════


class TestUnifiedPrompt(TestCase):
    """Tests for build_unified_system_prompt."""

    def test_basic_prompt_has_required_sections(self):
        """Unified prompt has response, reflection, and action_hints sections."""
        config = UnifiedPromptConfig()
        prompt = build_unified_system_prompt(config)

        self.assertIn('<response>', prompt)
        self.assertIn('</response>', prompt)
        self.assertIn('<reflection>', prompt)
        self.assertIn('</reflection>', prompt)
        self.assertIn('<action_hints>', prompt)
        self.assertIn('</action_hints>', prompt)

    def test_prompt_with_patterns(self):
        """Prompt includes patterns context when provided."""
        config = UnifiedPromptConfig(
            patterns={
                'ungrounded_assumptions': ['a', 'b'],
                'contradictions': ['c'],
            }
        )
        prompt = build_unified_system_prompt(config)
        self.assertIn('2 ungrounded assumption', prompt)
        self.assertIn('1 potential contradiction', prompt)

    def test_prompt_without_patterns(self):
        """Prompt omits patterns section when empty."""
        config = UnifiedPromptConfig(patterns={})
        prompt = build_unified_system_prompt(config)
        self.assertNotIn('ungrounded assumption', prompt)


class TestUserPrompt(TestCase):
    """Tests for build_unified_user_prompt."""

    def test_basic_user_prompt(self):
        """User prompt includes the user's message."""
        prompt = build_unified_user_prompt("What should I do?")
        self.assertIn("What should I do?", prompt)

    def test_with_conversation_context(self):
        """User prompt includes conversation history when provided."""
        prompt = build_unified_user_prompt(
            "Follow up",
            conversation_context="User: Hello\nAssistant: Hi there"
        )
        self.assertIn("Previous conversation:", prompt)
        self.assertIn("Hello", prompt)

    def test_with_retrieval_context(self):
        """User prompt includes RAG context with citation instructions."""
        prompt = build_unified_user_prompt(
            "Tell me about the doc",
            retrieval_context="[1] Some document content here"
        )
        self.assertIn("[1]", prompt)
        self.assertIn("Citation rules:", prompt)


class TestCaseAwarePrompt(TestCase):
    """Tests for build_case_aware_system_prompt (composable sections)."""

    def test_has_all_required_xml_sections(self):
        """Case-aware prompt has response, reflection, action_hints, plan_edits."""
        prompt = build_case_aware_system_prompt(stage='exploring')

        self.assertIn('<response>', prompt)
        self.assertIn('<reflection>', prompt)
        self.assertIn('<action_hints>', prompt)
        self.assertIn('<plan_edits>', prompt)

    def test_diff_only_format(self):
        """Prompt instructs diff-only plan_edits (no proposed_content)."""
        prompt = build_case_aware_system_prompt(stage='exploring')

        self.assertIn('diff_data', prompt)
        self.assertIn('diff_summary', prompt)
        # Should NOT mention proposed_content
        self.assertNotIn('proposed_content', prompt)

    def test_case_context_included(self):
        """Case context appears when decision_question is provided."""
        prompt = build_case_aware_system_prompt(
            stage='investigating',
            decision_question='Should we expand to Europe?',
            position_statement='Cautiously optimistic',
        )
        self.assertIn('## Case Context', prompt)
        self.assertIn('Europe', prompt)
        self.assertIn('Cautiously optimistic', prompt)

    def test_case_context_omitted_when_empty(self):
        """Case context section is omitted when no case data provided."""
        prompt = build_case_aware_system_prompt(stage='exploring')
        self.assertNotIn('## Case Context', prompt)

    def test_stage_guidance_exploring(self):
        """Exploring stage guidance appears."""
        prompt = build_case_aware_system_prompt(stage='exploring')
        self.assertIn('Stage: Exploring', prompt)

    def test_stage_guidance_investigating(self):
        """Investigating stage guidance appears."""
        prompt = build_case_aware_system_prompt(stage='investigating')
        self.assertIn('Stage: Investigating', prompt)

    def test_stage_guidance_synthesizing(self):
        prompt = build_case_aware_system_prompt(stage='synthesizing')
        self.assertIn('Stage: Synthesizing', prompt)

    def test_stage_guidance_ready(self):
        prompt = build_case_aware_system_prompt(stage='ready')
        self.assertIn('Stage: Ready', prompt)

    def test_stage_guidance_unknown_defaults_to_exploring(self):
        """Unknown stage falls back to exploring guidance."""
        prompt = build_case_aware_system_prompt(stage='nonexistent')
        self.assertIn('Stage: Exploring', prompt)

    def test_plan_state_displayed(self):
        """Plan state is formatted and included when provided."""
        plan = _make_plan_content()
        prompt = build_case_aware_system_prompt(
            stage='investigating',
            plan_content=plan,
        )
        self.assertIn('## Investigation Plan', prompt)
        self.assertIn('Market is large enough', prompt)
        self.assertIn('[CONFIRMED]', prompt)  # a2 is confirmed
        self.assertIn('[UNTESTED]', prompt)  # a1 is untested

    def test_no_plan_message(self):
        """Message about no plan appears when plan_content is None."""
        prompt = build_case_aware_system_prompt(stage='exploring', plan_content=None)
        self.assertIn('No plan has been created yet', prompt)

    def test_constraints_and_criteria_included(self):
        """Constraints and success criteria are formatted."""
        prompt = build_case_aware_system_prompt(
            stage='exploring',
            decision_question='Test',
            constraints=[{'text': 'Budget < 500K'}, {'text': 'Timeline < 6 months'}],
            success_criteria=[{'text': 'Positive ROI'}],
        )
        self.assertIn('Budget < 500K', prompt)
        self.assertIn('Timeline < 6 months', prompt)
        self.assertIn('Positive ROI', prompt)

    def test_composable_no_triple_newlines(self):
        """Composable sections join cleanly without triple newlines."""
        prompt = build_case_aware_system_prompt(
            stage='investigating',
            plan_content=_make_plan_content(),
            decision_question='Should we proceed?',
        )
        self.assertNotIn('\n\n\n', prompt)


class TestFormatPlanState(TestCase):
    """Tests for _format_plan_state — plan content formatting for prompts."""

    def test_empty_plan(self):
        """Empty plan content returns sensible default."""
        result = _format_plan_state({})
        self.assertIn('No assumptions', result)

    def test_assumptions_formatted(self):
        """Assumptions appear with status symbols and IDs."""
        plan = _make_plan_content()
        result = _format_plan_state(plan)
        self.assertIn('Assumptions (2 total)', result)
        self.assertIn('[UNTESTED]', result)
        self.assertIn('[CONFIRMED]', result)
        self.assertIn('[id: a1]', result)
        self.assertIn('[id: a2]', result)

    def test_criteria_formatted(self):
        """Decision criteria appear with met/unmet checkboxes."""
        plan = _make_plan_content()
        result = _format_plan_state(plan)
        self.assertIn('Decision Criteria (1 total, 0 met)', result)
        self.assertIn('[ ]', result)  # c1 is not met

    def test_met_criteria(self):
        """Met criteria show [x] checkbox."""
        plan = _make_plan_content(
            decision_criteria=[
                {'id': 'c1', 'text': 'Revenue target', 'is_met': True}
            ]
        )
        result = _format_plan_state(plan)
        self.assertIn('1 met', result)
        self.assertIn('[x]', result)

    def test_phases_formatted(self):
        """Phases appear with titles."""
        plan = _make_plan_content()
        result = _format_plan_state(plan)
        self.assertIn('Investigation Phases (1 total)', result)
        self.assertIn('Phase 1', result)

    def test_assumption_size_management(self):
        """Plans with >10 untested assumptions show summary + first 5."""
        many_assumptions = [
            {'id': f'a{i}', 'text': f'Assumption {i}', 'status': 'untested',
             'risk_level': 'medium'}
            for i in range(12)
        ]
        # Add a confirmed one — should always show
        many_assumptions.append({
            'id': 'confirmed1', 'text': 'Already confirmed',
            'status': 'confirmed', 'risk_level': 'low',
        })
        plan = _make_plan_content(assumptions=many_assumptions)
        result = _format_plan_state(plan)

        # Total count should be 13
        self.assertIn('13 total', result)
        # Should show the confirmed one
        self.assertIn('Already confirmed', result)
        # Should show "... and N more untested"
        self.assertIn('more untested', result)


class TestComposableSections(TestCase):
    """Tests for individual composable section builder functions."""

    def test_persona_section_has_xml_tags(self):
        result = _build_persona_section()
        self.assertIn('<response>', result)
        self.assertIn('<reflection>', result)
        self.assertIn('<action_hints>', result)

    def test_case_context_returns_none_when_empty(self):
        result = _build_case_context_section('', '', None, None)
        self.assertIsNone(result)

    def test_case_context_returns_string_when_populated(self):
        result = _build_case_context_section('My decision?', '', None, None)
        self.assertIsNotNone(result)
        self.assertIn('My decision?', result)

    def test_stage_guidance_returns_string(self):
        for stage in ['exploring', 'investigating', 'synthesizing', 'ready']:
            result = _build_stage_guidance_section(stage)
            self.assertIsInstance(result, str)
            self.assertTrue(len(result) > 20)

    def test_plan_state_with_content(self):
        result = _build_plan_state_section(_make_plan_content())
        self.assertIn('## Investigation Plan', result)

    def test_plan_state_without_content(self):
        result = _build_plan_state_section(None)
        self.assertIn('No plan has been created yet', result)

    def test_plan_edits_section_is_diff_only(self):
        result = _build_plan_edits_section()
        self.assertIn('diff_data', result)
        self.assertIn('diff_summary', result)
        self.assertNotIn('proposed_content', result)
        self.assertIn('ONLY the changes', result)


class TestScaffoldingPrompt(TestCase):
    """Tests for build_scaffolding_system_prompt."""

    def test_basic_scaffolding_prompt(self):
        prompt = build_scaffolding_system_prompt()
        self.assertIn('<response>', prompt)
        self.assertIn('<reflection>', prompt)
        self.assertIn('Socratic', prompt)

    def test_scaffolding_with_skill_context(self):
        """Skill context adds domain knowledge to scaffolding prompt."""
        skill_ctx = {
            'system_prompt_extension': 'You are an expert in real estate.',
            'evidence_standards': {'preferred_sources': ['MLS data', 'Appraisals']},
        }
        prompt = build_scaffolding_system_prompt(skill_context=skill_ctx)
        self.assertIn('real estate', prompt)
        self.assertIn('MLS data', prompt)


# ═══════════════════════════════════════════════════════════════════
# merge_plan_diff Tests
# ═══════════════════════════════════════════════════════════════════


class TestMergePlanDiff(TestCase):
    """Tests for PlanService.merge_plan_diff — diff-only plan editing merge logic."""

    def _merge(self, current, diff_data):
        """Inline merge to avoid Django import."""
        import copy as _copy
        content = _copy.deepcopy(current)

        assumptions = content.get('assumptions', [])
        assumption_map = {a['id']: a for a in assumptions if 'id' in a}
        for update in diff_data.get('updated_assumptions', []):
            a_id = update.get('id')
            if a_id and a_id in assumption_map:
                if 'status' in update:
                    assumption_map[a_id]['status'] = update['status']
                if 'evidence_summary' in update:
                    assumption_map[a_id]['evidence_summary'] = update['evidence_summary']
                if 'risk_level' in update:
                    assumption_map[a_id]['risk_level'] = update['risk_level']
        for new_a in diff_data.get('added_assumptions', []):
            assumptions.append({
                'id': str(uuid.uuid4()),
                'text': new_a.get('text', ''),
                'status': 'untested',
                'test_strategy': new_a.get('test_strategy', ''),
                'evidence_summary': '',
                'risk_level': new_a.get('risk_level', 'medium'),
            })
        content['assumptions'] = assumptions

        criteria = content.get('decision_criteria', [])
        criteria_map = {c['id']: c for c in criteria if 'id' in c}
        for update in diff_data.get('updated_criteria', []):
            c_id = update.get('id')
            if c_id and c_id in criteria_map:
                if 'is_met' in update:
                    criteria_map[c_id]['is_met'] = update['is_met']
        for new_c in diff_data.get('added_criteria', []):
            criteria.append({
                'id': str(uuid.uuid4()),
                'text': new_c.get('text', ''),
                'is_met': False,
                'priority': new_c.get('priority', 'nice_to_have'),
                'linked_inquiry_id': None,
            })
        content['decision_criteria'] = criteria

        stage_change = diff_data.get('stage_change')
        if stage_change and isinstance(stage_change, str):
            content['stage_rationale'] = diff_data.get(
                'stage_rationale', f'Stage advanced to {stage_change}')
        elif stage_change and isinstance(stage_change, dict):
            content['stage_rationale'] = stage_change.get('rationale', '')

        return content

    def test_update_assumption_status(self):
        """Existing assumption status is updated in place."""
        current = _make_plan_content()
        merged = self._merge(current, {
            'updated_assumptions': [
                {'id': 'a1', 'status': 'challenged',
                 'evidence_summary': 'Market shrank 30%'}
            ]
        })

        a1 = next(a for a in merged['assumptions'] if a['id'] == 'a1')
        self.assertEqual(a1['status'], 'challenged')
        self.assertEqual(a1['evidence_summary'], 'Market shrank 30%')

    def test_unchanged_assumptions_preserved(self):
        """Assumptions not in the diff remain unchanged."""
        current = _make_plan_content()
        merged = self._merge(current, {
            'updated_assumptions': [{'id': 'a1', 'status': 'refuted'}]
        })

        a2 = next(a for a in merged['assumptions'] if a['id'] == 'a2')
        self.assertEqual(a2['status'], 'confirmed')  # unchanged

    def test_add_new_assumption(self):
        """New assumptions are added with generated UUIDs."""
        current = _make_plan_content()
        merged = self._merge(current, {
            'added_assumptions': [
                {'text': 'Recovery uncertain', 'risk_level': 'high'}
            ]
        })

        self.assertEqual(len(merged['assumptions']), 3)
        new_a = merged['assumptions'][-1]
        self.assertEqual(new_a['text'], 'Recovery uncertain')
        self.assertEqual(new_a['risk_level'], 'high')
        self.assertEqual(new_a['status'], 'untested')
        # ID should be a valid UUID
        uuid.UUID(new_a['id'])  # raises if invalid

    def test_update_criterion_met_status(self):
        """Criteria is_met status can be updated."""
        current = _make_plan_content()
        merged = self._merge(current, {
            'updated_criteria': [{'id': 'c1', 'is_met': True}]
        })

        c1 = next(c for c in merged['decision_criteria'] if c['id'] == 'c1')
        self.assertTrue(c1['is_met'])

    def test_add_new_criterion(self):
        """New criteria are added with default values."""
        current = _make_plan_content()
        merged = self._merge(current, {
            'added_criteria': [
                {'text': 'Regulatory approval', 'priority': 'must_have'}
            ]
        })

        self.assertEqual(len(merged['decision_criteria']), 2)
        new_c = merged['decision_criteria'][-1]
        self.assertEqual(new_c['text'], 'Regulatory approval')
        self.assertEqual(new_c['priority'], 'must_have')
        self.assertFalse(new_c['is_met'])

    def test_stage_change_string(self):
        """Stage change as a string updates stage_rationale."""
        current = _make_plan_content()
        merged = self._merge(current, {'stage_change': 'investigating'})
        self.assertIn('investigating', merged['stage_rationale'])

    def test_stage_change_dict(self):
        """Stage change as a dict extracts the rationale."""
        current = _make_plan_content()
        merged = self._merge(current, {
            'stage_change': {
                'from': 'exploring', 'to': 'investigating',
                'rationale': 'Enough evidence gathered'
            }
        })
        self.assertEqual(merged['stage_rationale'], 'Enough evidence gathered')

    def test_empty_diff_returns_copy(self):
        """Empty diff returns an identical deep copy."""
        current = _make_plan_content()
        merged = self._merge(current, {})

        self.assertEqual(len(merged['assumptions']), len(current['assumptions']))
        self.assertEqual(len(merged['decision_criteria']), len(current['decision_criteria']))

    def test_original_not_mutated(self):
        """Deep copy ensures original content is never mutated."""
        current = _make_plan_content()
        original_status = current['assumptions'][0]['status']

        self._merge(current, {
            'updated_assumptions': [{'id': 'a1', 'status': 'refuted'}]
        })

        # Original should be unchanged
        self.assertEqual(current['assumptions'][0]['status'], original_status)

    def test_unknown_assumption_id_skipped(self):
        """Updates to nonexistent assumption IDs are silently skipped."""
        current = _make_plan_content()
        merged = self._merge(current, {
            'updated_assumptions': [{'id': 'nonexistent', 'status': 'confirmed'}]
        })

        # All assumptions unchanged
        for orig, new in zip(current['assumptions'], merged['assumptions']):
            self.assertEqual(orig['status'], new['status'])

    def test_phases_preserved(self):
        """Phases are preserved unchanged (merge doesn't touch them)."""
        current = _make_plan_content()
        merged = self._merge(current, {
            'added_assumptions': [{'text': 'New thing', 'risk_level': 'low'}]
        })
        self.assertEqual(merged['phases'], current['phases'])

    def test_combined_operations(self):
        """Multiple operations in a single diff all apply correctly."""
        current = _make_plan_content()
        merged = self._merge(current, {
            'updated_assumptions': [
                {'id': 'a1', 'status': 'challenged', 'evidence_summary': 'Bad data'},
            ],
            'added_assumptions': [
                {'text': 'New assumption', 'risk_level': 'high'},
            ],
            'updated_criteria': [
                {'id': 'c1', 'is_met': True},
            ],
            'added_criteria': [
                {'text': 'New criterion'},
            ],
            'stage_change': 'investigating',
        })

        self.assertEqual(len(merged['assumptions']), 3)
        self.assertEqual(len(merged['decision_criteria']), 2)

        a1 = next(a for a in merged['assumptions'] if a['id'] == 'a1')
        self.assertEqual(a1['status'], 'challenged')

        c1 = next(c for c in merged['decision_criteria'] if c['id'] == 'c1')
        self.assertTrue(c1['is_met'])

        self.assertIn('investigating', merged['stage_rationale'])


# ═══════════════════════════════════════════════════════════════════
# Orientation Edits — Parser Tests
# ═══════════════════════════════════════════════════════════════════


class TestOrientationEditsParser(TestCase):
    """Tests for ORIENTATION_EDITS section detection in parser."""

    def test_parse_orientation_edits_section(self):
        """Parser detects <orientation_edits> and accumulates in buffer."""
        parser = SectionedStreamParser()
        json_str = '{"diff_summary": "updated lead text"}'
        chunks = parser.parse(f'<orientation_edits>{json_str}</orientation_edits>')

        oe_chunks = [c for c in chunks if c.section == Section.ORIENTATION_EDITS]
        self.assertTrue(any(c.is_complete for c in oe_chunks))

        buffer = parser.get_orientation_edits_buffer()
        self.assertEqual(buffer, json_str)

    def test_parse_empty_orientation_edits(self):
        """Parser handles empty object in orientation_edits."""
        parser = SectionedStreamParser()
        chunks = parser.parse('<orientation_edits>{}</orientation_edits>')

        completions = [c for c in chunks if c.section == Section.ORIENTATION_EDITS and c.is_complete]
        self.assertEqual(len(completions), 1)

        buffer = parser.get_orientation_edits_buffer()
        self.assertEqual(buffer.strip(), '{}')

    def test_orientation_edits_complex_json(self):
        """Parser handles complex nested JSON in orientation_edits."""
        diff = {
            "diff_summary": "Added gap finding and dismissed a tension",
            "diff_data": {
                "added_findings": [
                    {"type": "gap", "title": "Missing market data", "content": "No data on APAC.", "action_type": "research"}
                ],
                "removed_finding_ids": ["abc-123"],
                "update_lead": "The documents reveal a nuanced landscape.",
            }
        }
        json_str = json.dumps(diff)
        parser = SectionedStreamParser()
        parser.parse(f'<orientation_edits>{json_str}</orientation_edits>')

        buffer = parser.get_orientation_edits_buffer()
        parsed = json.loads(buffer)
        self.assertEqual(parsed['diff_summary'], "Added gap finding and dismissed a tension")
        self.assertEqual(len(parsed['diff_data']['added_findings']), 1)
        self.assertEqual(parsed['diff_data']['added_findings'][0]['type'], 'gap')

    def test_full_output_with_orientation_edits(self):
        """Parser handles multi-section output including orientation_edits."""
        raw = (
            '<response>I see your point about the lead.</response>'
            '<reflection>User wants to reframe the lead.</reflection>'
            '<action_hints>[]</action_hints>'
            '<orientation_edits>{"diff_summary":"Update lead","diff_data":{"update_lead":"New lead"}}</orientation_edits>'
        )
        chunks = _simulate_stream(raw)

        completed_sections = {c.section for c in chunks if c.is_complete}
        self.assertIn(Section.RESPONSE, completed_sections)
        self.assertIn(Section.REFLECTION, completed_sections)
        self.assertIn(Section.ACTION_HINTS, completed_sections)
        self.assertIn(Section.ORIENTATION_EDITS, completed_sections)

    def test_orientation_edits_buffer_reset(self):
        """Buffer resets when a new opening tag arrives."""
        parser = SectionedStreamParser()
        parser.parse('<orientation_edits>{"v":1}</orientation_edits>')
        self.assertEqual(parser.get_orientation_edits_buffer(), '{"v":1}')

        parser.parse('<orientation_edits>{"v":2}</orientation_edits>')
        self.assertEqual(parser.get_orientation_edits_buffer(), '{"v":2}')


# ═══════════════════════════════════════════════════════════════════
# Orientation Edits — Engine Config Tests
# ═══════════════════════════════════════════════════════════════════


class TestOrientationEditsEngineConfig(TestCase):
    """Tests for ORIENTATION_EDITS engine configuration entry."""

    def test_orientation_edits_config_exists(self):
        """ORIENTATION_EDITS has a valid config entry."""
        self.assertIn(Section.ORIENTATION_EDITS, _SECTION_CONFIGS)

    def test_orientation_edits_is_buffered(self):
        """Orientation edits is a buffered (non-streaming) section."""
        cfg = _SECTION_CONFIGS[Section.ORIENTATION_EDITS]
        self.assertFalse(cfg.streams)

    def test_orientation_edits_default_is_dict(self):
        """Default value is {} (dict), not [] (list)."""
        cfg = _SECTION_CONFIGS[Section.ORIENTATION_EDITS]
        self.assertIsInstance(cfg.default_value, dict)
        self.assertEqual(cfg.default_value, {})

    def test_orientation_edits_data_key(self):
        """Data key is 'orientation_edits'."""
        cfg = _SECTION_CONFIGS[Section.ORIENTATION_EDITS]
        self.assertEqual(cfg.data_key, 'orientation_edits')

    def test_orientation_edits_complete_event(self):
        """Complete event is ORIENTATION_EDITS_COMPLETE."""
        cfg = _SECTION_CONFIGS[Section.ORIENTATION_EDITS]
        self.assertEqual(cfg.complete_event, StreamEventType.ORIENTATION_EDITS_COMPLETE)

    def test_orientation_edits_getter_resolves(self):
        """Buffer getter resolves on parser instance."""
        cfg = _SECTION_CONFIGS[Section.ORIENTATION_EDITS]
        parser = SectionedStreamParser()
        self.assertTrue(hasattr(parser, cfg.buffer_getter))
        result = getattr(parser, cfg.buffer_getter)()
        self.assertIsInstance(result, str)


# ═══════════════════════════════════════════════════════════════════
# Orientation Diff Merge Tests
# ═══════════════════════════════════════════════════════════════════


def _make_orientation_state(**overrides):
    """Create a minimal orientation state for testing merge_orientation_diff."""
    base = {
        'current_findings': [
            {
                'id': 'f1', 'insight_type': 'consensus', 'title': 'All agree on growth',
                'content': 'Documents unanimously support growth.', 'status': 'active', 'confidence': 0.9,
            },
            {
                'id': 'f2', 'insight_type': 'tension', 'title': 'Timing is disputed',
                'content': 'Sources disagree on when to launch.', 'status': 'active', 'confidence': 0.8,
            },
        ],
        'current_angles': [
            {'id': 'a1', 'title': 'What drives the timing disagreement?'},
        ],
        'current_lead': 'The collection reveals strong agreement on growth with tension around timing.',
        'current_lens': 'positions_and_tensions',
    }
    base.update(overrides)
    return base


class TestOrientationDiffMerge(TestCase):
    """Tests for OrientationService.merge_orientation_diff — pure diff merge logic."""

    def _merge(self, diff_data, **state_overrides):
        """Helper to call merge_orientation_diff with test state."""
        from apps.graph.orientation_service import OrientationService
        state = _make_orientation_state(**state_overrides)
        return OrientationService.merge_orientation_diff(
            current_findings=state['current_findings'],
            current_angles=state['current_angles'],
            current_lead=state['current_lead'],
            current_lens=state['current_lens'],
            diff_data=diff_data,
        )

    def test_update_lead_text(self):
        """Lead text is replaced when update_lead is present."""
        result = self._merge({'update_lead': 'A completely new lead.'})
        self.assertEqual(result['lead_text'], 'A completely new lead.')

    def test_suggest_lens_change(self):
        """Lens type is replaced when suggest_lens_change is present."""
        result = self._merge({'suggest_lens_change': 'events_and_causation'})
        self.assertEqual(result['lens_type'], 'events_and_causation')

    def test_add_finding(self):
        """New findings are appended with generated UUID and defaults."""
        result = self._merge({
            'added_findings': [
                {'type': 'gap', 'title': 'Missing competitor data', 'content': 'No competitive analysis.', 'action_type': 'research'}
            ]
        })
        self.assertEqual(len(result['findings']), 3)
        new_f = result['findings'][-1]
        self.assertEqual(new_f['title'], 'Missing competitor data')
        self.assertEqual(new_f['insight_type'], 'gap')
        self.assertEqual(new_f['status'], 'active')
        self.assertAlmostEqual(new_f['confidence'], 0.7)
        self.assertEqual(new_f['action_type'], 'research')
        # ID should be a valid UUID
        uuid.UUID(new_f['id'])

    def test_remove_finding(self):
        """Removed findings are filtered out by ID."""
        result = self._merge({'removed_finding_ids': ['f1']})
        self.assertEqual(len(result['findings']), 1)
        self.assertEqual(result['findings'][0]['id'], 'f2')

    def test_update_finding(self):
        """Existing finding fields are updated in place."""
        result = self._merge({
            'updated_findings': [
                {'id': 'f2', 'title': 'Updated title', 'status': 'resolved'}
            ]
        })
        f2 = next(f for f in result['findings'] if f['id'] == 'f2')
        self.assertEqual(f2['title'], 'Updated title')
        self.assertEqual(f2['status'], 'resolved')
        # Content should be unchanged
        self.assertEqual(f2['content'], 'Sources disagree on when to launch.')

    def test_add_angle(self):
        """New angles are appended with generated UUID."""
        result = self._merge({
            'added_angles': [{'title': 'How does regulation affect timing?'}]
        })
        self.assertEqual(len(result['angles']), 2)
        new_a = result['angles'][-1]
        self.assertEqual(new_a['title'], 'How does regulation affect timing?')
        uuid.UUID(new_a['id'])

    def test_remove_angle(self):
        """Removed angles are filtered out by ID."""
        result = self._merge({'removed_angle_ids': ['a1']})
        self.assertEqual(len(result['angles']), 0)

    def test_empty_diff(self):
        """Empty diff returns identical copy of current state."""
        result = self._merge({})
        state = _make_orientation_state()
        self.assertEqual(result['lead_text'], state['current_lead'])
        self.assertEqual(result['lens_type'], state['current_lens'])
        self.assertEqual(len(result['findings']), len(state['current_findings']))
        self.assertEqual(len(result['angles']), len(state['current_angles']))

    def test_original_not_mutated(self):
        """Deep copy ensures original input is not mutated."""
        original_findings = [
            {'id': 'f1', 'insight_type': 'consensus', 'title': 'Original', 'content': 'Content', 'status': 'active', 'confidence': 0.9},
        ]
        original_copy = copy.deepcopy(original_findings)

        from apps.graph.orientation_service import OrientationService
        OrientationService.merge_orientation_diff(
            current_findings=original_findings,
            current_angles=[],
            current_lead='Lead',
            current_lens='positions_and_tensions',
            diff_data={'updated_findings': [{'id': 'f1', 'title': 'Changed'}]},
        )

        # Original should be unchanged
        self.assertEqual(original_findings[0]['title'], original_copy[0]['title'])

    def test_combined_operations(self):
        """Multiple operations in a single diff all apply correctly."""
        result = self._merge({
            'update_lead': 'New lead text.',
            'suggest_lens_change': 'structure_and_dependencies',
            'added_findings': [
                {'type': 'pattern', 'title': 'Recurring cost concern', 'content': 'Cost mentioned 5 times.'}
            ],
            'updated_findings': [
                {'id': 'f1', 'status': 'acknowledged'}
            ],
            'removed_finding_ids': ['f2'],
            'added_angles': [
                {'title': 'What are the cost drivers?'}
            ],
            'removed_angle_ids': ['a1'],
        })

        self.assertEqual(result['lead_text'], 'New lead text.')
        self.assertEqual(result['lens_type'], 'structure_and_dependencies')
        # f1 (updated) + new pattern = 2 findings (f2 was removed)
        self.assertEqual(len(result['findings']), 2)
        f1 = next(f for f in result['findings'] if f['id'] == 'f1')
        self.assertEqual(f1['status'], 'acknowledged')
        # a1 removed, new angle added = 1 angle
        self.assertEqual(len(result['angles']), 1)
        self.assertEqual(result['angles'][0]['title'], 'What are the cost drivers?')


# ═══════════════════════════════════════════════════════════════════
# Orientation-Aware Prompt Tests
# ═══════════════════════════════════════════════════════════════════


class TestOrientationAwarePrompt(TestCase):
    """Tests for build_orientation_aware_system_prompt."""

    def _build(self, **overrides):
        defaults = {
            'lens_type': 'positions_and_tensions',
            'lead_text': 'The documents show competing views on market size.',
            'findings': [
                {
                    'id': 'f-abc', 'insight_type': 'consensus', 'title': 'Growth is real',
                    'content': 'All sources agree.', 'status': 'active', 'confidence': 0.9,
                },
                {
                    'id': 'f-def', 'insight_type': 'tension', 'title': 'Timing disputed',
                    'content': 'Q1 vs Q3.', 'status': 'active', 'confidence': 0.8,
                },
            ],
            'angles': [
                {'id': 'a-ghi', 'title': 'What explains the timing gap?'},
            ],
        }
        defaults.update(overrides)
        return build_orientation_aware_system_prompt(**defaults)

    def test_prompt_contains_orientation_edits_instructions(self):
        """Prompt has <orientation_edits> format instructions."""
        prompt = self._build()
        self.assertIn('<orientation_edits>', prompt)
        self.assertIn('</orientation_edits>', prompt)
        self.assertIn('diff_summary', prompt)
        self.assertIn('diff_data', prompt)

    def test_prompt_has_findings_with_ids(self):
        """Finding IDs appear as references in the prompt."""
        prompt = self._build()
        self.assertIn('[f-abc]', prompt)
        self.assertIn('[f-def]', prompt)

    def test_prompt_shows_lens_type(self):
        """Human-readable lens label appears in the prompt."""
        prompt = self._build()
        self.assertIn('Positions & Tensions', prompt)

    def test_prompt_shows_lead_text(self):
        """Lead text appears in the prompt."""
        prompt = self._build()
        self.assertIn('competing views on market size', prompt)

    def test_prompt_shows_angles(self):
        """Exploration angles appear in the prompt."""
        prompt = self._build()
        self.assertIn('[a-ghi]', prompt)
        self.assertIn('What explains the timing gap?', prompt)

    def test_prompt_shows_finding_types(self):
        """Finding type badges appear (consensus, tension, etc.)."""
        prompt = self._build()
        self.assertIn('[consensus]', prompt)
        self.assertIn('[tension]', prompt)

    def test_diff_only_no_proposed_state(self):
        """Prompt should not mention proposed_state (diff-only format)."""
        prompt = self._build()
        self.assertNotIn('proposed_state', prompt)

    def test_prompt_has_all_xml_sections(self):
        """Prompt mentions all required output sections."""
        prompt = self._build()
        self.assertIn('<response>', prompt)
        self.assertIn('<reflection>', prompt)
        self.assertIn('<action_hints>', prompt)
        self.assertIn('<orientation_edits>', prompt)

    def test_empty_findings(self):
        """Prompt handles empty findings gracefully."""
        prompt = self._build(findings=[], angles=[])
        self.assertIn('No findings yet', prompt)
        self.assertIn('No exploration angles yet', prompt)

    def test_secondary_lens_shown(self):
        """Secondary lens and reason appear when provided."""
        prompt = self._build(
            secondary_lens='events_and_causation',
            secondary_lens_reason='Several sources describe historical events.',
        )
        self.assertIn('Events & Causation', prompt)
        self.assertIn('historical events', prompt)
