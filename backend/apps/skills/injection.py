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
            'artifact_template': dict        # Artifact structure template
        }
    """
    context = {
        'system_prompt_extension': '',
        'custom_signal_types': [],
        'evidence_standards': {},
        'artifact_template': None
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
            logger.warning(f"Failed to parse skill '{skill.name}': {e}")
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
        
        # Artifact template (last skill wins)
        if 'artifact_template' in episteme:
            context['artifact_template'] = episteme['artifact_template']
    
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
    
    # Add artifact template if any
    if skill_context['artifact_template']:
        enhanced_prompt += "\n\n# Artifact Structure Template\n"
        template = skill_context['artifact_template']
        
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
