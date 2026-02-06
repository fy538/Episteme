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
    ) -> dict:
        """
        Extract structure from scaffolding chat and create full case.

        Args:
            transcript: List of {role, content} message dicts
            user: User creating the case
            project_id: Project to create case in
            thread_id: Optional thread ID for provenance

        Returns:
            Dict with: case, brief, inquiries, sections, signals
        """
        # 1. Extract structure via LLM
        extraction = await cls._extract_structure(transcript)

        # 2. Create case and all related objects
        result = cls._create_scaffolded_case(
            extraction=extraction,
            user=user,
            project_id=project_id,
            thread_id=thread_id,
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
            sections_data = cls._generate_minimal_sections(title, decision_question)
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

            return {
                'case': case,
                'brief': brief,
                'inquiries': [],
                'sections': sections,
                'signals': [],
            }

    @classmethod
    async def _extract_structure(cls, transcript: list[dict]) -> ScaffoldExtraction:
        """
        Use LLM to extract decision structure from chat transcript.
        """
        provider = get_llm_provider('fast')

        # Format transcript
        formatted = "\n".join(
            f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
            for msg in transcript
        )

        prompt = SCAFFOLD_EXTRACTION_PROMPT.format(transcript=formatted)

        # Call LLM
        full_response = ""
        async for chunk in provider.stream_chat(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You extract decision structures from conversations. Return only valid JSON."
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
            title=extraction.decision_question[:200],  # Title from question
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

        return {
            'case': case,
            'brief': brief,
            'inquiries': inquiries,
            'sections': sections,
            'signals': signals,
        }

    @staticmethod
    def _generate_minimal_sections(title: str, decision_question: Optional[str]) -> list[dict]:
        """Generate section data for a minimal/blank case."""
        sections = [
            {
                'section_id': BriefSection.generate_section_id(),
                'heading': 'Decision Frame',
                'type': SectionType.DECISION_FRAME,
            },
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
        ]
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
                lines.append('\n')
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
