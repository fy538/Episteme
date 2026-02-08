---
name: Consulting Research Standards
description: Rigorous research methodology for management consulting with triangulated evidence and structured evaluation
domain: consulting
episteme:
  applies_to_agents:
    - research
  research_config:
    sources:
      primary:
        - type: industry_reports
          description: Market research from established firms (IBISWorld, Gartner, McKinsey)
        - type: regulatory_filings
          description: Government and regulatory documents (SEC, Federal Register)
        - type: financial_data
          description: Company filings, annual reports, earnings transcripts
      supplementary:
        - type: trade_publications
          description: Industry magazines, trade press, association reports
        - type: expert_commentary
          description: Analyst reports, expert opinions, conference proceedings
    search:
      decomposition: systematic
      max_iterations: 8
      budget:
        max_sources: 30
        max_search_rounds: 12
    evaluate:
      mode: corroborative
      quality_rubric: >
        Prioritize authoritative sources: government databases,
        established research firms, and peer-reviewed publications.
        Cross-reference market sizing with at least 2 independent sources.
        Flag any source with potential bias toward the client's interests.
        Recency matters — prefer data from last 3 years unless historical
        trend analysis requires older data. Distinguish between primary
        data (surveys, filings) and secondary analysis.
      criteria:
        - name: source_triangulation
          description: Key claims verified across 3+ independent sources
          importance: critical
        - name: data_recency
          description: Market data from last 3 years
          importance: high
    completeness:
      min_sources: 5
      max_sources: 30
      require_contrary_check: true
      require_source_diversity: true
      done_when: >
        Research complete when the core question is answered with
        triangulated evidence from at least 3 independent source types,
        contrary evidence has been actively sought and addressed,
        and data recency requirements are met.
    output:
      format: report
      sections:
        - Executive Summary
        - Key Findings
        - Supporting Data
        - Contrary Evidence & Risks
        - Methodology Notes
        - Sources
      citation_style: inline
      target_length: detailed
  evidence_standards:
    preferred_sources:
      - Industry research firms
      - Government databases
      - Financial filings
      - Peer-reviewed publications
    minimum_credibility: 0.80
---

## Consulting-Grade Research Methodology

Apply these principles when conducting research for consulting engagements:

1. **Triangulate everything** — No single source is sufficient for a key claim. Cross-reference market data, competitive intelligence, and regulatory findings across at least 3 independent sources before treating them as reliable.

2. **Source hierarchy matters** — Primary sources (government filings, company 10-Ks, raw survey data) outrank secondary analysis (analyst reports, news articles). When they conflict, primary sources win.

3. **Actively seek disconfirming evidence** — Consulting engagements are vulnerable to confirmation bias toward the client's preferred outcome. Deliberately search for evidence that challenges the emerging thesis.

4. **Document methodology** — Every research output should include a brief methodology note explaining what was searched, what sources were consulted, and what limitations exist. This is non-negotiable for client-facing deliverables.

5. **Recency and relevance** — Market data older than 3 years should be flagged. Industry dynamics can shift rapidly; what was true in 2022 may not hold in 2025. Always note the data vintage.

6. **Distinguish fact from inference** — Clearly label what is established data, what is expert consensus, and what is your analytical inference. Clients rely on this distinction for their own decision-making.
