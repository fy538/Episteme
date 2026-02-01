"""
Case-Skill conversion service

Handles bi-directional conversion between Cases and Skills.
"""
from typing import Dict, Any, Optional
from django.db import transaction, models
from apps.cases.models import Case
from apps.skills.models import Skill, SkillVersion


class CaseSkillConverter:
    """Convert between Cases and Skills"""
    
    @staticmethod
    def case_to_skill(
        case: Case,
        skill_name: str,
        scope: str = 'personal',
        user = None,
        custom_description: Optional[str] = None
    ) -> Skill:
        """
        Convert a case to a skill
        
        Args:
            case: Case to convert
            skill_name: Name for the new skill
            scope: 'personal', 'team', or 'organization'
            user: User creating the skill (defaults to case owner)
            custom_description: Optional custom description
        
        Returns:
            Created Skill instance
        """
        from apps.skills.preview import (
            _extract_domain,
            _get_org_for_scope,
            _build_episteme_config,
            _generate_skill_md_from_case
        )
        
        user = user or case.user
        
        with transaction.atomic():
            # Create skill
            skill = Skill.objects.create(
                name=skill_name,
                description=custom_description or f"Template from: {case.title}",
                domain=_extract_domain(case),
                scope=scope,
                owner=user,
                organization=_get_org_for_scope(user, scope),
                team=case.project if scope == 'team' else None,
                source_case=case,
                applies_to_agents=['research', 'critique', 'brief'],
                episteme_config=_build_episteme_config(case),
                status='active',
                created_by=user
            )
            
            # Generate SKILL.md content from case
            skill_md = _generate_skill_md_from_case(case, skill_name)
            
            # Create initial version
            SkillVersion.objects.create(
                skill=skill,
                version=1,
                skill_md_content=skill_md,
                created_by=user,
                changelog=f"Created from case: {case.title}"
            )
            
            # Link back to case
            case.became_skill = skill
            case.is_skill_template = True
            case.template_scope = scope
            case.save()
            
            return skill
    
    @staticmethod
    def skill_to_case(
        skill: Skill,
        case_title: str,
        user,
        **case_kwargs
    ) -> Case:
        """
        Spawn a new case from a skill
        
        Args:
            skill: Skill to use as template
            case_title: Title for new case
            user: User creating the case
            **case_kwargs: Additional case fields (position, stakes, project_id, thread_id)
        
        Returns:
            Created Case instance
        """
        from apps.cases.services import CaseService
        from apps.events.models import Event
        
        # Create event for provenance
        event = Event.objects.create(
            user=user,
            event_type='case_from_skill',
            metadata={'skill_id': str(skill.id), 'skill_name': skill.name}
        )
        
        # Create case
        case, brief = CaseService.create_case(
            user=user,
            title=case_title,
            position=case_kwargs.get('position', ''),
            stakes=case_kwargs.get('stakes', 'medium'),
            thread_id=case_kwargs.get('thread_id'),
            project_id=case_kwargs.get('project_id'),
            event=event
        )
        
        # Link to skill
        case.based_on_skill = skill
        case.save()
        
        # Auto-activate the skill
        case.active_skills.add(skill)
        
        return case
    
    @staticmethod
    def promote_skill(skill: Skill, new_scope: str, user) -> Skill:
        """
        Promote a skill to a higher scope level
        
        personal → team → organization → public
        
        Args:
            skill: Skill to promote
            new_scope: Target scope ('team', 'organization', or 'public')
            user: User requesting promotion
        
        Returns:
            Updated Skill instance
        
        Raises:
            ValueError: If promotion is invalid
        """
        scope_hierarchy = ['personal', 'team', 'organization', 'public']
        current_idx = scope_hierarchy.index(skill.scope)
        new_idx = scope_hierarchy.index(new_scope)
        
        if new_idx <= current_idx:
            raise ValueError(f"Cannot promote from {skill.scope} to {new_scope}")
        
        # Check permissions
        if skill.owner != user:
            raise ValueError("Only skill owner can promote")
        
        # Update scope
        skill.scope = new_scope
        
        # Update organization if promoting to org/team
        if new_scope in ['organization', 'team']:
            from apps.skills.preview import _get_org_for_scope
            skill.organization = _get_org_for_scope(user, new_scope)
        
        if new_scope == 'team' and not skill.team:
            raise ValueError("Team must be specified for team-scoped skills")
        
        skill.save()
        
        # Create a new version to mark the promotion
        latest_version = skill.versions.filter(version=skill.current_version).first()
        if latest_version:
            SkillVersion.objects.create(
                skill=skill,
                version=skill.current_version + 1,
                skill_md_content=latest_version.skill_md_content,
                resources=latest_version.resources,
                created_by=user,
                changelog=f"Promoted from {scope_hierarchy[current_idx]} to {new_scope}"
            )
            skill.current_version += 1
            skill.save()
        
        return skill
    
    @staticmethod
    def fork_skill(
        original_skill: Skill,
        new_name: str,
        user,
        scope: str = 'personal'
    ) -> Skill:
        """
        Fork a skill to create a customizable copy
        
        Args:
            original_skill: Skill to fork
            new_name: Name for forked skill
            user: User forking the skill
            scope: Scope for forked skill (defaults to 'personal')
        
        Returns:
            Forked Skill instance
        """
        # Get current version
        current_version = original_skill.versions.filter(
            version=original_skill.current_version
        ).first()
        
        if not current_version:
            raise ValueError("Original skill has no versions")
        
        # Create forked skill
        forked_skill = Skill.objects.create(
            name=new_name,
            description=f"Forked from: {original_skill.name}",
            domain=original_skill.domain,
            scope=scope,
            owner=user,
            organization=None if scope == 'personal' else original_skill.organization,
            team=None,  # User can set team later
            forked_from=original_skill,
            applies_to_agents=original_skill.applies_to_agents.copy(),
            episteme_config=dict(original_skill.episteme_config),  # Deep copy
            status='draft',  # Forked skills start as draft
            created_by=user
        )
        
        # Copy current version
        SkillVersion.objects.create(
            skill=forked_skill,
            version=1,
            skill_md_content=current_version.skill_md_content,
            resources=dict(current_version.resources),  # Deep copy
            created_by=user,
            changelog=f"Forked from {original_skill.name} v{original_skill.current_version}"
        )
        
        return forked_skill
