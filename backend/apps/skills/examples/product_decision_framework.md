---
name: Product Decision Framework
description: Apply product management best practices to feature prioritization and roadmap decisions
domain: product
episteme:
  applies_to_agents:
    - research
    - critique
    - brief
  signal_types:
    - name: UserNeed
      inherits_from: Goal
      description: User need or pain point
    - name: TechnicalConstraint
      inherits_from: Constraint
      description: Technical feasibility constraint
  evidence_standards:
    preferred_sources:
      - User research data
      - Analytics data
      - Customer interviews
    minimum_credibility: 0.75
---

## Product Decision Framework

Apply this framework when analyzing product decisions.

## Analysis Steps

1. **User Impact**: Who benefits? How many users?
2. **Business Value**: What's the expected ROI?
3. **Technical Feasibility**: Can we build it? Timeline?
4. **Resource Requirements**: What's the effort estimate?

## Prioritization Criteria

- User impact (1-10)
- Business value (1-10)
- Technical feasibility (1-10)
- Strategic alignment (1-10)

Use RICE scoring: (Reach × Impact × Confidence) / Effort

## Signal Types

### UserNeed
A user need or pain point that drives product decisions. Examples:
- "Users struggle to export their data"
- "Need mobile app for field workers"

### TechnicalConstraint
Technical feasibility or architectural constraints. Examples:
- "Current database can't handle real-time updates"
- "Requires migration to new API version"

## Research Guidelines

When researching product decisions, prioritize:
- Quantitative data (analytics, A/B tests)
- Qualitative insights (user interviews, support tickets)
- Competitive analysis
- Technical feasibility assessments

## Brief Structure

When generating product decision briefs:

1. **Problem Statement**: What user need are we addressing?
2. **Proposed Solution**: What are we building?
3. **Expected Impact**: User metrics, business metrics
4. **Resource Requirements**: Timeline and team needs
5. **Risks and Alternatives**: What could go wrong? What else could we do?
6. **Recommendation**: Go/No-go with rationale
