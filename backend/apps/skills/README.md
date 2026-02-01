# Skills System

Organization-level AI agent customization following the Anthropic Agent Skills specification with Episteme-specific extensions.

## Overview

Skills enable organizations to customize how Episteme's AI agents (Research, Critique, Brief) process cases, signals, and artifacts. Skills provide:

- **Domain-specific knowledge** (Legal, Medical, Product, etc.)
- **Procedural workflows** (How to analyze, what to extract)
- **Evidence standards** (What sources to trust, credibility thresholds)
- **Custom signal types** (Domain-specific signal categories)

## Architecture

### Models

- **`Skill`**: Organization-level skill definition with metadata
- **`SkillVersion`**: Version-controlled SKILL.md content
- **`Case.active_skills`**: Many-to-many relationship tracking active skills
- **`Artifact.skills_used`**: Many-to-many relationship tracking skills used in generation

### SKILL.md Format

Skills use a hybrid format: Anthropic's Agent Skills spec + Episteme extensions

```yaml
---
name: Legal Decision Analysis
description: Apply legal reasoning framework to decision-making
domain: legal
episteme:
  applies_to_agents:
    - research
    - critique
    - brief
  signal_types:
    - name: LegalConstraint
      inherits_from: Constraint
      description: Legal or regulatory constraints
  evidence_standards:
    preferred_sources:
      - Legal statutes
      - Case law
    minimum_credibility: 0.85
  artifact_template:
    brief:
      sections:
        - Legal Summary
        - Compliance Requirements
---

## Overview

Markdown content here...
```

### Progressive Disclosure

Skills are only loaded when:
1. A case has active skills
2. An agent is generating an artifact
3. Only skills matching the agent type are loaded

This prevents context window bloat.

## Usage

### Creating a Skill

```python
from apps.skills.models import Skill, SkillVersion

skill = Skill.objects.create(
    organization=org,
    name='Legal Decision Analysis',
    description='Apply legal reasoning framework',
    domain='legal',
    applies_to_agents=['research', 'critique', 'brief'],
    episteme_config={...},
    created_by=user
)

SkillVersion.objects.create(
    skill=skill,
    version=1,
    skill_md_content=skill_md_content,
    created_by=user,
    changelog="Initial version"
)
```

### Activating Skills for a Case

```python
# Via API
POST /api/cases/{case_id}/activate_skills/
{
    "skill_ids": ["uuid1", "uuid2"]
}

# Via code
case.active_skills.set([skill1, skill2])
```

### Skill Injection in Workflows

Skills are automatically injected when generating artifacts:

```python
# In workflows.py
active_skills = await get_active_skills_for_case(case)
skill_context = build_skill_context(active_skills, agent_type='research')

# Enhance agent system prompt
enhanced_prompt = format_system_prompt_with_skills(
    base_prompt,
    skill_context
)
agent.agent.system_instruction = enhanced_prompt
```

## API Endpoints

### Skills

- `GET /api/skills/` - List all skills for user's organization
- `POST /api/skills/` - Create new skill
- `GET /api/skills/{id}/` - Get skill details with current version
- `PUT /api/skills/{id}/` - Update skill metadata
- `DELETE /api/skills/{id}/` - Delete skill
- `POST /api/skills/{id}/create_version/` - Create new version
- `GET /api/skills/{id}/versions/` - List all versions
- `POST /api/skills/suggest_for_case/` - Suggest skills for a case

### Case Skills

- `POST /api/cases/{id}/activate_skills/` - Activate skills for a case
- `GET /api/cases/{id}/active_skills/` - Get active skills for a case

## Testing

Run tests:

```bash
python manage.py test apps.skills
```

Test coverage includes:
- SKILL.md parsing and validation
- Skill context building and injection
- Model creation and versioning
- API endpoints

## Example Skills

See `examples/` directory:
- `legal_decision_analysis.md` - Legal reasoning framework
- `product_decision_framework.md` - Product management best practices

## Validation Rules

- **Name**: Required, max 64 chars
- **Description**: Required, max 200 chars
- **SKILL.md**: Max 50KB
- **Resources**: Max 5MB total, 2MB per file
- **Agent types**: Must be one of: research, critique, brief, extract

## Future Enhancements

1. **Skill Marketplace**: Share skills across organizations
2. **Skill Analytics**: Track which skills improve artifact quality
3. **Skill Recommendations**: Use embeddings to auto-suggest skills
4. **Skill Composition**: Allow skills to reference other skills
5. **User-Level Skills**: Extend to support personal preferences

## References

- [Anthropic Agent Skills Specification](https://agentskills.io)
- [Skill System Integration Plan](../../../docs/SKILL_SYSTEM_PLAN.md)
