---
name: Market Entry Assessment
description: Evaluate U.S. market entry strategy for international companies with regulatory, competitive, and go-to-market analysis
domain: consulting
episteme:
  applies_to_agents:
    - research
    - critique
    - brief
  signal_types:
    - name: RegulatoryBarrier
      inherits_from: Constraint
      description: Regulatory hurdle for market entry (CFIUS, SEC, FDA, state licensing, etc.)
    - name: MarketOpportunity
      inherits_from: Goal
      description: Identified market opportunity, segment advantage, or unmet demand
    - name: CompetitiveThreat
      inherits_from: Risk
      description: Competitive dynamic that threatens market entry success
  evidence_standards:
    preferred_sources:
      - Industry reports (IBISWorld, Statista, Grand View Research)
      - Government databases (SEC EDGAR, USPTO, Census Bureau, BLS)
      - Regulatory filings and guidance documents
      - Trade association publications
      - Company 10-K/10-Q filings
    minimum_credibility: 0.80
    requires_citation: true
  artifact_template:
    brief:
      sections:
        - heading: Regulatory Landscape
          type: custom
        - heading: Market Sizing & Segmentation
          type: custom
        - heading: Competitive Analysis
          type: custom
        - heading: Go-to-Market Strategy
          type: custom
        - heading: Risk Matrix
          type: custom
---

## Overview

This skill provides a structured framework for evaluating U.S. market entry decisions, particularly for international companies entering the American market. When generating research, critiques, or briefs, apply this domain expertise.

## Market Entry Analysis Framework

1. **Regulatory Assessment**: Identify all federal, state, and local regulatory requirements. For foreign-owned entities, assess CFIUS (Committee on Foreign Investment) implications, export control restrictions, and sector-specific licensing.
2. **Market Sizing**: Quantify the total addressable market (TAM), serviceable addressable market (SAM), and serviceable obtainable market (SOM). Use top-down and bottom-up approaches for triangulation.
3. **Competitive Landscape**: Map direct competitors, indirect alternatives, and potential substitutes. Identify barriers to entry and switching costs.
4. **Go-to-Market**: Define entry mode (direct, partnership, acquisition), pricing strategy, distribution channels, and initial target segments.
5. **Risk Assessment**: Evaluate regulatory, operational, financial, and reputational risks. Build a risk matrix with likelihood and impact dimensions.

## Cross-Border Considerations

When analyzing market entry for Chinese or other international companies:
- CFIUS review is mandatory for acquisitions in critical technology, infrastructure, or data sectors
- Entity List and sanctions compliance must be verified before any partnership discussions
- State-level regulations may impose additional requirements (e.g., California CCPA, New York DFS)
- Corporate structure matters: wholly foreign-owned enterprise vs. JV vs. U.S. subsidiary
- Intellectual property strategy should address both U.S. patent/trademark filing and trade secret protection

## Evidence Evaluation

When assessing market entry evidence:
- **Market size claims** require at least 2 independent data sources with reconcilable methodologies
- **Regulatory guidance** should come from primary sources (Federal Register, agency websites), not secondary summaries
- **Competitive data** from company filings (10-K, proxy statements) is preferred over analyst estimates
- **Industry reports** should be from the last 3 years unless analyzing structural trends
- Flag any source with potential promotional bias (vendor whitepapers, sponsored research)

## Signal Types

### RegulatoryBarrier
A regulatory hurdle that constrains market entry options. Examples:
- "CFIUS review required for acquisition of U.S. target in semiconductor sector"
- "FDA 510(k) clearance needed before marketing medical device"
- "State-level money transmitter license required in each operating state"

### MarketOpportunity
An identified market opening or competitive advantage. Examples:
- "Underserved mid-market segment with no dominant provider"
- "Regulatory tailwind from new infrastructure spending bill"

### CompetitiveThreat
A competitive dynamic that could undermine market entry. Examples:
- "Incumbent has exclusive distribution agreements with top 3 channel partners"
- "Price war among existing players compressing margins below 15%"
