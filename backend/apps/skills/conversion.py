"""
Case-Skill conversion service

Handles bi-directional conversion between Cases and Skills.
"""
import copy
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
            case.save(update_fields=['became_skill', 'is_skill_template', 'template_scope', 'updated_at'])
            
            return skill
    
    @staticmethod
    def skill_to_case(
        skill: Skill,
        case_title: str,
        user,
        **case_kwargs
    ) -> Case:
        """
        Spawn a new case from a skill.

        If the skill defines artifact_template.brief.sections, those sections
        are used to scaffold the brief instead of the default 3-section structure.

        Args:
            skill: Skill to use as template
            case_title: Title for new case
            user: User creating the case
            **case_kwargs: Additional case fields (position, stakes, project_id, thread_id)

        Returns:
            Created Case instance
        """
        from apps.cases.scaffold_service import CaseScaffoldService
        from apps.skills.injection import extract_brief_sections_from_skill
        from apps.events.services import EventService
        from apps.events.models import EventType, ActorType

        # Extract skill brief sections (if defined)
        skill_sections = extract_brief_sections_from_skill(skill)

        with transaction.atomic():
            # Create case via scaffold_minimal (creates brief + BriefSection records)
            result = CaseScaffoldService.scaffold_minimal(
                title=case_title,
                user=user,
                project_id=case_kwargs.get('project_id'),
                decision_question=case_kwargs.get('position', ''),
                thread_id=case_kwargs.get('thread_id'),
                skill_sections=skill_sections,
            )

            case = result['case']

            # Link to skill
            case.based_on_skill = skill
            case.save(update_fields=['based_on_skill', 'updated_at'])

            # Auto-activate the skill (using through model)
            from apps.cases.models import CaseActiveSkill
            CaseActiveSkill.objects.get_or_create(
                case=case,
                skill=skill,
                defaults={'order': 0}
            )

        # Emit provenance event (outside transaction — non-critical)
        EventService.append(
            event_type=EventType.CASE_CREATED,
            payload={
                'source': 'skill',
                'skill_id': str(skill.id),
                'skill_name': skill.name,
                'skill_sections_count': len(skill_sections) if skill_sections else 0,
            },
            actor_type=ActorType.USER,
            actor_id=user.id,
            case_id=case.id,
            thread_id=case_kwargs.get('thread_id'),
        )

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

        if new_scope == 'team' and not skill.team:
            raise ValueError("Team must be specified for team-scoped skills")

        with transaction.atomic():
            # Update scope
            skill.scope = new_scope

            # Update organization if promoting to org/team
            if new_scope in ['organization', 'team']:
                from apps.skills.preview import _get_org_for_scope
                skill.organization = _get_org_for_scope(user, new_scope)

            # Create a new version to mark the promotion
            latest_version = skill.versions.filter(version=skill.current_version).first()
            if latest_version:
                SkillVersion.objects.create(
                    skill=skill,
                    version=skill.current_version + 1,
                    skill_md_content=latest_version.skill_md_content,
                    resources=copy.deepcopy(latest_version.resources),
                    created_by=user,
                    changelog=f"Promoted from {scope_hierarchy[current_idx]} to {new_scope}"
                )
                skill.current_version += 1

            # Single save with all changes
            save_fields = ['scope', 'updated_at']
            if new_scope in ['organization', 'team']:
                save_fields.append('organization')
            if latest_version:
                save_fields.append('current_version')
            skill.save(update_fields=save_fields)

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

        with transaction.atomic():
            # Create forked skill — use copy.deepcopy for nested dicts/lists
            forked_skill = Skill.objects.create(
                name=new_name,
                description=f"Forked from: {original_skill.name}",
                domain=original_skill.domain,
                scope=scope,
                owner=user,
                organization=None if scope == 'personal' else original_skill.organization,
                team=None,  # User can set team later
                forked_from=original_skill,
                applies_to_agents=copy.deepcopy(original_skill.applies_to_agents),
                episteme_config=copy.deepcopy(original_skill.episteme_config),
                status='draft',  # Forked skills start as draft
                created_by=user
            )

            # Copy current version
            SkillVersion.objects.create(
                skill=forked_skill,
                version=1,
                skill_md_content=current_version.skill_md_content,
                resources=copy.deepcopy(current_version.resources),
                created_by=user,
                changelog=f"Forked from {original_skill.name} v{original_skill.current_version}"
            )

        return forked_skill
