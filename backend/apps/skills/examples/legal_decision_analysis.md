---
name: Legal Decision Analysis
description: Apply legal reasoning framework to decision-making, focusing on liability, compliance, and risk assessment
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
    - name: LiabilityRisk
      inherits_from: Risk
      description: Potential legal liability
  evidence_standards:
    preferred_sources:
      - Legal statutes
      - Case law
      - Attorney opinions
    minimum_credibility: 0.85
  artifact_template:
    brief:
      sections:
        - Legal Summary
        - Compliance Requirements
        - Risk Assessment
        - Recommended Actions
---

## Overview

This skill provides a legal decision-making framework for analyzing cases with legal implications. When generating research, critiques, or briefs for legal decisions, apply these principles.

## Legal Analysis Framework

1. **Identify Applicable Law**: Determine which statutes, regulations, and precedents apply
2. **Compliance Check**: Verify compliance with all applicable legal requirements
3. **Risk Assessment**: Identify potential legal liabilities and their likelihood
4. **Mitigation Strategies**: Propose actions to minimize legal risk

## Evidence Standards

When citing legal authority:
- Primary sources (statutes, regulations) are preferred
- Case law should include jurisdiction and year
- Attorney opinions should be from licensed practitioners
- All legal claims must be supported by citations

## Signal Types

### LegalConstraint
Legal or regulatory requirements that constrain decisions. Examples:
- "Must comply with GDPR for EU users"
- "Requires FDA approval before marketing"

### LiabilityRisk
Potential legal exposure from a decision. Examples:
- "Potential breach of contract claim"
- "Risk of IP infringement lawsuit"

## Brief Template

When generating a legal brief, structure as:

1. **Legal Summary**: What is the legal question?
2. **Compliance Requirements**: What laws/regulations apply?
3. **Risk Assessment**: What are the legal risks?
4. **Recommended Actions**: What steps minimize risk while achieving goals?
