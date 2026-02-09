"""
Skill context injection for agents

Builds skill context to inject into agent system prompts.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)
from .models import Skill
from .parser import parse_skill_md


def build_skill_context(skills: List[Skill], agent_type: str) -> Dict[str, Any]:
    """
    Build context to inject into an agent based on active skills

    Args:
        skills: List of Skill objects to inject
        agent_type: Type of agent ('research', 'critique', 'brief', 'extract')

    Returns:
        {
            'system_prompt_extension': str,  # Additional content for system prompt
            'custom_signal_types': list,     # Custom signal type definitions
            'evidence_standards': dict,      # Evidence credibility standards
            'document_template': dict,       # Document structure template
            'research_config': ResearchConfig | None,  # Parsed research config (if any)
        }
    """
    context = {
        'system_prompt_extension': '',
        'custom_signal_types': [],
        'evidence_standards': {},
        'document_template': None,
        'research_config': None,
    }

    for skill in skills:
        # Filter by agent type
        if agent_type not in skill.applies_to_agents:
            continue

        # Get current version
        version = skill.versions.filter(version=skill.current_version).first()
        if not version:
            continue

        # Parse SKILL.md
        try:
            parsed = parse_skill_md(version.skill_md_content)
        except Exception as e:
            # Skip skills with parsing errors
            logger.warning("skill_md_parse_failed", extra={"skill": skill.name, "error": str(e)})
            continue

        # Add markdown body to system prompt
        if parsed['body']:
            context['system_prompt_extension'] += f"\n\n## {parsed['metadata'].get('name', skill.name)}\n"
            context['system_prompt_extension'] += parsed['body']

        # Add Episteme-specific extensions
        episteme = skill.episteme_config

        # Custom signal types
        if 'signal_types' in episteme:
            context['custom_signal_types'].extend(episteme['signal_types'])

        # Evidence standards
        if 'evidence_standards' in episteme:
            # Merge evidence standards (later skills override earlier ones)
            context['evidence_standards'].update(episteme['evidence_standards'])

        # Document template (last skill wins; accepts old 'artifact_template' key too)
        if 'document_template' in episteme:
            context['document_template'] = episteme['document_template']
        elif 'artifact_template' in episteme:
            context['document_template'] = episteme['artifact_template']

        # Research config (merge across skills — last skill wins for each section)
        if 'research_config' in episteme:
            try:
                from apps.agents.research_config import ResearchConfig
                skill_rc = ResearchConfig.from_dict(episteme['research_config'])
                if context['research_config'] is None:
                    context['research_config'] = skill_rc
                else:
                    context['research_config'] = _merge_research_configs(
                        context['research_config'], skill_rc
                    )
            except Exception as e:
                logger.warning("skill_research_config_parse_failed", extra={"skill": skill.name, "error": str(e)})

    return context


def format_system_prompt_with_skills(
    base_prompt: str,
    skill_context: Dict[str, Any]
) -> str:
    """
    Format a system prompt with skill context
    
    Args:
        base_prompt: Base system instruction for the agent
        skill_context: Context returned by build_skill_context()
    
    Returns:
        Enhanced system prompt with skill knowledge
    """
    enhanced_prompt = base_prompt
    
    # Add skill extensions
    if skill_context['system_prompt_extension']:
        enhanced_prompt += "\n\n# Additional Domain Knowledge\n"
        enhanced_prompt += skill_context['system_prompt_extension']
    
    # Add custom signal types if any
    if skill_context['custom_signal_types']:
        enhanced_prompt += "\n\n# Custom Signal Types\n"
        enhanced_prompt += "In addition to standard signal types, you may use these domain-specific types:\n\n"
        for signal_type in skill_context['custom_signal_types']:
            name = signal_type.get('name', 'Unknown')
            inherits = signal_type.get('inherits_from', '')
            desc = signal_type.get('description', '')
            enhanced_prompt += f"- **{name}**"
            if inherits:
                enhanced_prompt += f" (extends {inherits})"
            if desc:
                enhanced_prompt += f": {desc}"
            enhanced_prompt += "\n"
    
    # Add evidence standards if any
    if skill_context['evidence_standards']:
        enhanced_prompt += "\n\n# Evidence Standards\n"
        standards = skill_context['evidence_standards']
        
        if 'preferred_sources' in standards:
            enhanced_prompt += "Preferred sources:\n"
            for source in standards['preferred_sources']:
                enhanced_prompt += f"- {source}\n"
        
        if 'minimum_credibility' in standards:
            enhanced_prompt += f"\nMinimum credibility threshold: {standards['minimum_credibility']}\n"
        
        if 'requires_citation' in standards:
            enhanced_prompt += f"\nAll claims must be cited: {standards['requires_citation']}\n"
    
    # Add document template if any
    if skill_context['document_template']:
        enhanced_prompt += "\n\n# Document Structure Template\n"
        template = skill_context['document_template']
        
        # Handle different template formats
        if isinstance(template, dict):
            for key, value in template.items():
                enhanced_prompt += f"\n**{key}**:\n"
                if isinstance(value, list):
                    for item in value:
                        enhanced_prompt += f"- {item}\n"
                else:
                    enhanced_prompt += f"{value}\n"
        elif isinstance(template, str):
            enhanced_prompt += template + "\n"
    
    return enhanced_prompt


def extract_brief_sections_from_skill(skill: Skill) -> list[dict] | None:
    """
    Extract brief section definitions from a skill's document_template.

    Supports two formats:
    1. Simple string list: ["Legal Summary", "Risk Assessment"]
    2. Rich dict list: [{"heading": "Legal Summary", "type": "custom", "locked": false}]

    Returns:
        List of section dicts with {heading, type, is_locked, lock_reason},
        or None if no document_template or no brief sections defined.
    """
    from apps.cases.brief_models import SectionType

    template = skill.episteme_config.get('document_template') or skill.episteme_config.get('artifact_template', {})
    if not isinstance(template, dict):
        return None

    brief_config = template.get('brief', {})
    if not isinstance(brief_config, dict):
        return None

    raw_sections = brief_config.get('sections', [])
    if not raw_sections or not isinstance(raw_sections, list):
        return None

    valid_types = {choice.value for choice in SectionType}
    sections = []

    for item in raw_sections:
        if isinstance(item, str):
            sections.append({
                'heading': item,
                'type': SectionType.CUSTOM,
                'is_locked': False,
                'lock_reason': '',
            })
        elif isinstance(item, dict):
            raw_type = item.get('type', 'custom')
            section_type = SectionType(raw_type) if raw_type in valid_types else SectionType.CUSTOM
            sections.append({
                'heading': item.get('heading', item.get('name', 'Untitled')),
                'type': section_type,
                'is_locked': item.get('locked', False),
                'lock_reason': item.get('lock_reason', ''),
            })

    return sections if sections else None


async def get_active_skills_for_case(case) -> List[Skill]:
    """
    Get active skills for a case (async)
    
    Args:
        case: Case object
    
    Returns:
        List of active Skill objects
    """
    skills = []
    async for skill in case.active_skills.filter(status='active'):
        skills.append(skill)
    return skills


def get_active_skills_for_case_sync(case) -> List[Skill]:
    """
    Get active skills for a case (sync)

    Args:
        case: Case object

    Returns:
        List of active Skill objects
    """
    return list(case.active_skills.filter(status='active'))


def _merge_research_configs(base: 'ResearchConfig', override: 'ResearchConfig') -> 'ResearchConfig':
    """
    Merge two ResearchConfig instances. Non-default fields from *override*
    win over *base*. This allows multiple skills to contribute config pieces
    (e.g. one skill defines sources, another defines output format).

    Args:
        base: Existing ResearchConfig
        override: New ResearchConfig to merge in

    Returns:
        Merged ResearchConfig
    """
    from apps.agents.research_config import (
        ResearchConfig, SourcesConfig, SearchConfig, ExtractConfig,
        EvaluateConfig, CompletenessConfig, OutputConfig, BudgetConfig,
    )

    def pick(base_val, override_val, default_val):
        """Return override if it differs from default, else base."""
        return override_val if override_val != default_val else base_val

    default = ResearchConfig()

    # Sources: merge lists (union)
    merged_sources = SourcesConfig(
        primary=base.sources.primary + [
            s for s in override.sources.primary
            if s.type not in {x.type for x in base.sources.primary}
        ],
        supplementary=base.sources.supplementary + [
            s for s in override.sources.supplementary
            if s.type not in {x.type for x in base.sources.supplementary}
        ],
        trusted_publishers=base.sources.trusted_publishers + [
            p for p in override.sources.trusted_publishers
            if p.domain not in {x.domain for x in base.sources.trusted_publishers}
        ],
        excluded_domains=list(set(base.sources.excluded_domains + override.sources.excluded_domains)),
    )

    # Search: override wins for scalar fields
    merged_search = SearchConfig(
        decomposition=pick(base.search.decomposition, override.search.decomposition, default.search.decomposition),
        parallel_branches=pick(base.search.parallel_branches, override.search.parallel_branches, default.search.parallel_branches),
        max_iterations=pick(base.search.max_iterations, override.search.max_iterations, default.search.max_iterations),
        budget=BudgetConfig(
            max_sources=pick(base.search.budget.max_sources, override.search.budget.max_sources, default.search.budget.max_sources),
            max_search_rounds=pick(base.search.budget.max_search_rounds, override.search.budget.max_search_rounds, default.search.budget.max_search_rounds),
        ),
        follow_citations=base.search.follow_citations or override.search.follow_citations,
        citation_depth=max(base.search.citation_depth, override.search.citation_depth),
    )

    # Extract: merge field lists
    existing_field_names = {f.name for f in base.extract.fields}
    merged_extract = ExtractConfig(
        fields=base.extract.fields + [
            f for f in override.extract.fields if f.name not in existing_field_names
        ],
        relationships=list(set(base.extract.relationships + override.extract.relationships)),
    )

    # Evaluate: override wins for scalars, merge criteria lists
    existing_criteria = {c.name for c in base.evaluate.criteria}
    merged_evaluate = EvaluateConfig(
        mode=pick(base.evaluate.mode, override.evaluate.mode, default.evaluate.mode),
        quality_rubric=override.evaluate.quality_rubric or base.evaluate.quality_rubric,
        criteria=base.evaluate.criteria + [
            c for c in override.evaluate.criteria if c.name not in existing_criteria
        ],
    )

    # Completeness: override wins for scalars
    merged_completeness = CompletenessConfig(
        min_sources=pick(base.completeness.min_sources, override.completeness.min_sources, default.completeness.min_sources),
        max_sources=pick(base.completeness.max_sources, override.completeness.max_sources, default.completeness.max_sources),
        require_contrary_check=base.completeness.require_contrary_check or override.completeness.require_contrary_check,
        require_source_diversity=base.completeness.require_source_diversity or override.completeness.require_source_diversity,
        done_when=override.completeness.done_when or base.completeness.done_when,
    )

    # Output: override wins
    merged_output = OutputConfig(
        format=pick(base.output.format, override.output.format, default.output.format),
        sections=override.output.sections or base.output.sections,
        citation_style=pick(base.output.citation_style, override.output.citation_style, default.output.citation_style),
        target_length=pick(base.output.target_length, override.output.target_length, default.output.target_length),
    )

    return ResearchConfig(
        sources=merged_sources,
        search=merged_search,
        extract=merged_extract,
        evaluate=merged_evaluate,
        completeness=merged_completeness,
        output=merged_output,
    )
