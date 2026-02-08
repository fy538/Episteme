"""
Case scaffold service.

Transforms a scaffolding chat transcript (or minimal input) into a
fully structured case with brief sections, inquiries, signals, and
readiness checklist.
"""
import json
import logging
import uuid
from typing import Optional

from django.contrib.auth.models import User
from django.db import transaction

from apps.cases.models import Case, CaseDocument, CaseStatus, StakesLevel, DocumentType, EditFriction
from apps.cases.brief_models import BriefSection, SectionType, SectionCreator, GroundingStatus
from apps.cases.services import CaseService
from apps.cases.document_service import CaseDocumentService
from apps.cases.scaffold_schemas import ScaffoldExtraction
from apps.common.llm_providers import get_llm_provider
from apps.events.services import EventService
from apps.events.models import EventType, ActorType

logger = logging.getLogger(__name__)


SCAFFOLD_EXTRACTION_PROMPT = """You are analyzing a conversation to extract the structure of a decision the user needs to make.

**CONVERSATION:**
{transcript}

**YOUR TASK:**
Extract the decision structure from this conversation. Be specific to what was actually discussed.

Return a JSON object with these fields:
{{
  "decision_question": "The core question in clear, specific terms",
  "key_uncertainties": [
    {{
      "title": "Question form, e.g. 'What is the ROI of option A?'",
      "description": "Brief elaboration",
      "why_important": "Why this matters"
    }}
  ],
  "initial_position": "The user's current thesis, or null if not stated",
  "assumptions": ["List of assumptions detected in the conversation"],
  "constraints": [
    {{"type": "timeline|budget|regulatory|technical|other", "description": "..."}}
  ],
  "stakeholders": [
    {{"name": "Role or name", "interest": "What they care about", "influence": "low|medium|high"}}
  ],
  "suggested_research": ["Topics that would benefit from research"],
  "stakes_level": "low|medium|high",
  "background_summary": "2-3 sentence summary of the decision context"
}}

**RULES:**
- Extract 2-5 key uncertainties (these become investigation threads)
- Only include assumptions that were actually stated or implied
- If something wasn't discussed, use empty lists or null
- Keep descriptions concise
- Return ONLY valid JSON, no markdown, no explanation"""


class CaseScaffoldService:
    """
    Transforms scaffolding input into a fully structured case.

    Supports three modes:
    - scaffold_from_chat: Full extraction from conversation transcript
    - scaffold_minimal: Blank case with Decision Frame only
    - evolve_scaffold: Recompute grounding (delegates to BriefGroundingEngine)
    """

    @classmethod
    async def scaffold_from_chat(
        cls,
        transcript: list[dict],
        user: User,
        project_id: uuid.UUID,
        thread_id: Optional[uuid.UUID] = None,
        skill_context: Optional[dict] = None,
    ) -> dict:
        """
        Extract structure from scaffolding chat and create full case.

        Args:
            transcript: List of {role, content} message dicts
            user: User creating the case
            project_id: Project to create case in
            thread_id: Optional thread ID for provenance
            skill_context: Optional skill context dict from build_skill_context()
                          (enhances LLM extraction with domain knowledge)

        Returns:
            Dict with: case, brief, inquiries, sections, signals
        """
        # 1. Extract structure via LLM (skill-aware if context provided)
        extraction = await cls._extract_structure(transcript, skill_context=skill_context)

        # 1b. Generate a concise case title (keep extraction.decision_question intact)
        case_title = extraction.decision_question[:200] if extraction.decision_question else "Untitled Case"
        if extraction.decision_question and len(extraction.decision_question) > 60:
            from apps.intelligence.title_generator import generate_case_title
            short_title = await generate_case_title(
                signals=[],
                conversation_summary=extraction.decision_question,
                max_length=60,
            )
            if short_title:
                case_title = short_title

        # 2. Create case and all related objects
        result = cls._create_scaffolded_case(
            extraction=extraction,
            user=user,
            project_id=project_id,
            thread_id=thread_id,
            case_title=case_title,
        )

        # 3. Emit scaffolding event
        EventService.append(
            event_type=EventType.CASE_SCAFFOLDED,
            payload={
                'case_id': str(result['case'].id),
                'extraction': extraction.model_dump(),
                'inquiries_created': len(result['inquiries']),
                'sections_created': len(result['sections']),
                'signals_created': len(result['signals']),
            },
            actor_type=ActorType.SYSTEM,
            case_id=result['case'].id,
            thread_id=thread_id,
        )

        return result

    @classmethod
    def scaffold_minimal(
        cls,
        title: str,
        user: User,
        project_id: uuid.UUID,
        decision_question: Optional[str] = None,
        thread_id: Optional[uuid.UUID] = None,
        skill_sections: Optional[list[dict]] = None,
    ) -> dict:
        """
        Create a blank case with minimal structure.

        Creates: Case + brief with Decision Frame + empty suggested sections.
        User can add/modify sections freely.

        Args:
            title: Case title
            user: User creating the case
            project_id: Project ID
            decision_question: Optional decision question
            thread_id: Optional thread for provenance

        Returns:
            Dict with: case, brief, inquiries (empty), sections
        """
        with transaction.atomic():
            # Create case
            case, brief = CaseDocumentService.create_case_with_brief(
                user=user,
                title=title,
                project_id=project_id,
                decision_question=decision_question or '',
            )

            # Generate minimal brief markdown with section markers
            sections_data = cls._generate_minimal_sections(title, decision_question, skill_sections=skill_sections)
            brief_markdown = cls._build_brief_markdown(title, sections_data)

            # Update brief content
            brief.content_markdown = brief_markdown
            brief.save(update_fields=['content_markdown', 'updated_at'])

            # Create BriefSection records
            sections = []
            for i, section_data in enumerate(sections_data):
                section = BriefSection.objects.create(
                    brief=brief,
                    section_id=section_data['section_id'],
                    heading=section_data['heading'],
                    order=i,
                    section_type=section_data['type'],
                    created_by=SectionCreator.SYSTEM,
                    is_locked=section_data.get('is_locked', False),
                    lock_reason=section_data.get('lock_reason', ''),
                )
                sections.append(section)

            # Bootstrap investigation plan (minimal — no assumptions or criteria)
            try:
                from apps.cases.plan_service import PlanService
                PlanService.create_initial_plan(
                    case=case,
                    analysis={
                        'assumptions': [],
                        'decision_criteria': [],
                        'position_draft': '',
                    },
                    inquiries=[],
                )
            except Exception as e:
                logger.warning(f"Could not auto-create plan for case {case.id}: {e}")

            return {
                'case': case,
                'brief': brief,
                'inquiries': [],
                'sections': sections,
                'signals': [],
            }

    @classmethod
    async def _extract_structure(
        cls,
        transcript: list[dict],
        skill_context: Optional[dict] = None,
    ) -> ScaffoldExtraction:
        """
        Use LLM to extract decision structure from chat transcript.

        When skill_context is provided, domain knowledge is injected into
        the system prompt so the LLM can extract more relevant uncertainties,
        assumptions, and domain-specific constraints.
        """
        provider = get_llm_provider('fast')

        # Format transcript
        formatted = "\n".join(
            f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
            for msg in transcript
        )

        prompt = SCAFFOLD_EXTRACTION_PROMPT.format(transcript=formatted)

        # Build system prompt — optionally enhanced with domain knowledge
        system_prompt = "You extract decision structures from conversations. Return only valid JSON."
        if skill_context and skill_context.get('system_prompt_extension'):
            system_prompt += (
                "\n\nYou have domain expertise that should inform your extraction. "
                "Use this knowledge to identify domain-specific uncertainties, "
                "constraints, and assumptions that a generalist might miss.\n"
                + skill_context['system_prompt_extension']
            )

        # Call LLM
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=system_prompt
        ):
            full_response += chunk.content

        # Parse response
        try:
            text = full_response.strip()
            if text.startswith("```"):
                parts = text.split("```")
                if len(parts) >= 2:
                    text = parts[1]
                    if text.startswith("json"):
                        text = text[4:]
                    text = text.strip()

            data = json.loads(text)
            return ScaffoldExtraction(**data)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to parse scaffold extraction: {e}")
            # Return minimal extraction
            return ScaffoldExtraction(
                decision_question="Decision question to be defined",
                background_summary="Created from conversation",
            )

    @classmethod
    @transaction.atomic
    def _create_scaffolded_case(
        cls,
        extraction: ScaffoldExtraction,
        user: User,
        project_id: uuid.UUID,
        thread_id: Optional[uuid.UUID] = None,
        case_title: Optional[str] = None,
    ) -> dict:
        """
        Create the full case from extracted structure.
        """
        from apps.inquiries.models import ElevationReason
        from apps.signals.models import Signal, SignalType, SignalSourceType
        from apps.events.models import Event

        # Map stakes
        stakes_map = {
            'low': StakesLevel.LOW,
            'medium': StakesLevel.MEDIUM,
            'high': StakesLevel.HIGH,
        }

        # 1. Create case
        case, brief = CaseService.create_case(
            user=user,
            title=case_title or extraction.decision_question[:200],
            position=extraction.initial_position or '',
            stakes=stakes_map.get(extraction.stakes_level, StakesLevel.MEDIUM),
            thread_id=thread_id,
            project_id=project_id,
        )

        # Update decision frame fields
        case.decision_question = extraction.decision_question
        case.constraints = [c.model_dump() for c in extraction.constraints]
        case.stakeholders = [s.model_dump() for s in extraction.stakeholders]
        case.save(update_fields=[
            'decision_question', 'constraints', 'stakeholders', 'updated_at'
        ])

        # 2. Create inquiries
        inquiries = []
        for uncertainty in extraction.key_uncertainties:
            inquiry, _ = CaseDocumentService.create_inquiry_with_brief(
                case=case,
                title=uncertainty.title,
                user=user,
                elevation_reason=ElevationReason.USER_CREATED,
            )
            if uncertainty.description:
                inquiry.description = uncertainty.description
                inquiry.save(update_fields=['description'])
            inquiries.append(inquiry)

        # 3. Generate brief markdown with section markers
        sections_data = cls._generate_scaffolded_sections(extraction, inquiries)
        brief_markdown = cls._build_scaffolded_brief_markdown(extraction, sections_data, inquiries)

        brief.content_markdown = brief_markdown
        brief.save(update_fields=['content_markdown', 'updated_at'])

        # 4. Create BriefSection records
        sections = []
        for i, section_data in enumerate(sections_data):
            inquiry_link = None
            if section_data.get('inquiry_index') is not None:
                idx = section_data['inquiry_index']
                if idx < len(inquiries):
                    inquiry_link = inquiries[idx]

            section = BriefSection.objects.create(
                brief=brief,
                section_id=section_data['section_id'],
                heading=section_data['heading'],
                order=i,
                section_type=section_data['type'],
                inquiry=inquiry_link,
                created_by=SectionCreator.SYSTEM,
                is_linked=bool(inquiry_link),
                is_locked=section_data.get('is_locked', False),
                lock_reason=section_data.get('lock_reason', ''),
            )
            sections.append(section)

        # 5. Create signals for assumptions
        signals = []
        # Get or create event for signal extraction
        event = EventService.append(
            event_type=EventType.SIGNAL_EXTRACTED,
            payload={
                'source': 'scaffolding',
                'count': len(extraction.assumptions),
            },
            actor_type=ActorType.SYSTEM,
            case_id=case.id,
            thread_id=thread_id,
        )

        for assumption_text in extraction.assumptions:
            signal = Signal.objects.create(
                event=event,
                source_type=SignalSourceType.ANALYSIS,
                type=SignalType.ASSUMPTION,
                text=assumption_text,
                normalized_text=assumption_text.lower().strip(),
                confidence=0.7,
                case=case,
                thread_id=thread_id,
            )
            signals.append(signal)

        # 6. Bootstrap investigation plan
        try:
            from apps.cases.plan_service import PlanService
            PlanService.create_initial_plan(
                case=case,
                analysis={
                    'assumptions': list(extraction.assumptions) if extraction.assumptions else [],
                    'decision_criteria': [],
                    'position_draft': extraction.initial_position or '',
                },
                inquiries=inquiries,
            )
        except Exception as e:
            logger.warning(f"Could not auto-create plan for case {case.id}: {e}")

        return {
            'case': case,
            'brief': brief,
            'inquiries': inquiries,
            'sections': sections,
            'signals': signals,
        }

    @staticmethod
    def _generate_minimal_sections(
        title: str,
        decision_question: Optional[str],
        skill_sections: Optional[list[dict]] = None,
    ) -> list[dict]:
        """
        Generate section data for a minimal/blank case.

        If skill_sections are provided (from a Skill's artifact_template),
        they are inserted between the Decision Frame and the synthesis sections
        (Trade-offs, Recommendation).
        """
        sections = [
            {
                'section_id': BriefSection.generate_section_id(),
                'heading': 'Decision Frame',
                'type': SectionType.DECISION_FRAME,
            },
        ]

        # Insert skill-defined sections between Decision Frame and synthesis sections
        if skill_sections:
            for skill_sec in skill_sections:
                sections.append({
                    'section_id': BriefSection.generate_section_id(),
                    'heading': skill_sec['heading'],
                    'type': skill_sec.get('type', SectionType.CUSTOM),
                    'is_locked': skill_sec.get('is_locked', False),
                    'lock_reason': skill_sec.get('lock_reason', ''),
                })

        sections.extend([
            {
                'section_id': BriefSection.generate_section_id(),
                'heading': 'Trade-offs & Considerations',
                'type': SectionType.TRADE_OFFS,
                'is_locked': True,
                'lock_reason': 'Gather evidence in at least one inquiry to unlock',
            },
            {
                'section_id': BriefSection.generate_section_id(),
                'heading': 'Recommendation',
                'type': SectionType.RECOMMENDATION,
                'is_locked': True,
                'lock_reason': 'Complete your analysis to build toward a recommendation',
            },
        ])
        return sections

    @staticmethod
    def _generate_scaffolded_sections(extraction: ScaffoldExtraction, inquiries) -> list[dict]:
        """Generate section data from full extraction."""
        sections = [
            {
                'section_id': BriefSection.generate_section_id(),
                'heading': 'Decision Frame',
                'type': SectionType.DECISION_FRAME,
            },
        ]

        # One section per inquiry
        for i, inquiry in enumerate(inquiries):
            sections.append({
                'section_id': BriefSection.generate_section_id(),
                'heading': inquiry.title,
                'type': SectionType.INQUIRY_BRIEF,
                'inquiry_index': i,
            })

        # Synthesis sections
        sections.extend([
            {
                'section_id': BriefSection.generate_section_id(),
                'heading': 'Trade-offs & Considerations',
                'type': SectionType.TRADE_OFFS,
                'is_locked': True,
                'lock_reason': 'Gather evidence in at least one inquiry to unlock',
            },
            {
                'section_id': BriefSection.generate_section_id(),
                'heading': 'Recommendation',
                'type': SectionType.RECOMMENDATION,
                'is_locked': True,
                'lock_reason': 'Complete your analysis to build toward a recommendation',
            },
        ])

        return sections

    @staticmethod
    def _build_brief_markdown(title: str, sections_data: list[dict]) -> str:
        """Build markdown for a minimal brief."""
        lines = [f'# {title}\n']
        for section in sections_data:
            lines.append(f'<!-- section:{section["section_id"]} -->')
            lines.append(f'## {section["heading"]}')
            if section['type'] == SectionType.DECISION_FRAME:
                lines.append('[Describe the decision you need to make]\n')
            elif section['type'] == SectionType.TRADE_OFFS:
                lines.append('*Suggested — unlocks as inquiries resolve*\n')
            elif section['type'] == SectionType.RECOMMENDATION:
                lines.append('*Suggested — builds from your inquiry conclusions*\n')
            else:
                lines.append(f'[Analyze: {section["heading"]}]\n')
        lines.append('---')
        lines.append('*Edit freely — this is YOUR brief.*')
        return '\n'.join(lines)

    @staticmethod
    def _build_scaffolded_brief_markdown(
        extraction: ScaffoldExtraction,
        sections_data: list[dict],
        inquiries,
    ) -> str:
        """Build markdown for a fully scaffolded brief."""
        lines = [f'# {extraction.decision_question[:200]}\n']

        for section in sections_data:
            lines.append(f'<!-- section:{section["section_id"]} -->')
            lines.append(f'## {section["heading"]}')

            if section['type'] == SectionType.DECISION_FRAME:
                lines.append(f'{extraction.background_summary}\n')
                if extraction.constraints:
                    lines.append('**Constraints:**')
                    for c in extraction.constraints:
                        lines.append(f'- {c.type}: {c.description}')
                    lines.append('')
                if extraction.stakeholders:
                    lines.append('**Key stakeholders:**')
                    for s in extraction.stakeholders:
                        lines.append(f'- {s.name} ({s.influence} influence): {s.interest}')
                    lines.append('')

            elif section['type'] == SectionType.INQUIRY_BRIEF:
                idx = section.get('inquiry_index')
                if idx is not None and idx < len(extraction.key_uncertainties):
                    uncertainty = extraction.key_uncertainties[idx]
                    lines.append(f'*Linked to inquiry: {uncertainty.title}*\n')
                    if uncertainty.description:
                        lines.append(f'{uncertainty.description}\n')
                    if uncertainty.why_important:
                        lines.append(f'**Why this matters:** {uncertainty.why_important}\n')
                    lines.append('**Current position:** [Not yet explored]\n')
                else:
                    lines.append('[Not yet explored]\n')

            elif section['type'] == SectionType.TRADE_OFFS:
                lines.append('*Suggested — unlocks as inquiries resolve*\n')

            elif section['type'] == SectionType.RECOMMENDATION:
                lines.append('*Suggested — builds from your inquiry conclusions*\n')

            else:
                lines.append('\n')

        # Add assumptions section if any
        if extraction.assumptions:
            lines.append('---')
            lines.append('### Detected Assumptions')
            lines.append('*These assumptions were detected in your conversation and should be validated:*\n')
            for assumption in extraction.assumptions:
                lines.append(f'- ⚠️ {assumption}')
            lines.append('')

        lines.append('---')
        lines.append('*AI-scaffolded from your conversation. Edit freely.*')
        return '\n'.join(lines)

    @classmethod
    async def evolve_scaffold(cls, case_id: uuid.UUID) -> dict:
        """
        Recompute grounding for all BriefSections in a case.
        Delegates to BriefGroundingEngine.
        """
        from apps.cases.brief_grounding import BriefGroundingEngine
        return BriefGroundingEngine.evolve_brief(case_id)
