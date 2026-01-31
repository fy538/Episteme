"""
Brief template generator - AI outlines for case and inquiry briefs.

Generates helpful starting structures that users can edit freely.
"""


class BriefTemplateGenerator:
    """
    Generate AI-assisted outlines for briefs.
    
    Templates provide structure without being prescriptive.
    Users can edit/delete/customize freely.
    """
    
    @staticmethod
    def generate_case_brief_outline(case) -> str:
        """
        Generate outline for case brief.
        
        Args:
            case: Case object
        
        Returns:
            Markdown template with helpful structure
        """
        return f'''# {case.title}

## Background
[Describe the decision context, why this matters, and what's at stake]

## Key Questions
[List the main inquiries being investigated]

## Analysis
[Synthesis of inquiry findings - what did you learn?]

## Recommendation
[Your final recommendation based on the analysis]

## Trade-offs & Considerations
[What are the key trade-offs? What did you have to weigh?]

## Next Steps
[Action items, blockers, and what needs to happen]

## Confidence
[How confident are you in this recommendation? What would change your mind?]

---
*AI-generated outline. Edit freely - this is YOUR brief.*
'''
    
    @staticmethod
    def generate_inquiry_brief_outline(inquiry) -> str:
        """
        Generate outline for inquiry brief.
        
        Args:
            inquiry: Inquiry object
        
        Returns:
            Markdown template for inquiry synthesis
        """
        return f'''# {inquiry.title}

## Question
What are we trying to answer or investigate?

## Your Position
What do you currently think and why?

## Evidence
Key evidence supporting or contradicting your position:

### Supporting
[Evidence that supports your position]

### Contradicting  
[Evidence that challenges your position]

## Issues & Objections
Challenges that need to be addressed:
[List concerns, objections, or gaps in reasoning]

## Conclusion
Your assessment based on the evidence:
[What's your conclusion? How confident are you?]

## Next Steps
[What needs to happen to resolve this inquiry?]

---
*AI-generated outline based on inquiry context. Customize as needed.*
'''
    
    @staticmethod
    def generate_research_template(topic: str) -> str:
        """
        Template for AI-generated research documents.
        
        Args:
            topic: Research topic
        
        Returns:
            Markdown structure for research report
        """
        return f'''# Research: {topic}

## Executive Summary
[High-level findings and key takeaways]

## Methodology
[How this research was conducted, sources used]

## Key Findings

### Finding 1
[Detailed finding with evidence]

### Finding 2
[Detailed finding with evidence]

## Evidence Summary
[Overview of evidence strength and credibility]

## Limitations & Caveats
[What this research doesn't cover, limitations of sources]

## Recommendations
[What actions or decisions this research suggests]

## Sources
[List of sources consulted]

---
*AI-generated research. Read-only - annotate to add your thoughts.*
'''
    
    @staticmethod
    def generate_debate_template(topic: str, persona1: str, persona2: str) -> str:
        """
        Template for AI-generated debate documents.
        
        Args:
            topic: Debate topic
            persona1: First persona name
            persona2: Second persona name
        
        Returns:
            Markdown structure for debate
        """
        return f'''# Debate: {topic}

## {persona1} Position
[Position statement]

### Arguments
1. [First argument with evidence]
2. [Second argument with evidence]

### Counter to {persona2}
[Response to opposing position]

---

## {persona2} Position  
[Position statement]

### Arguments
1. [First argument with evidence]
2. [Second argument with evidence]

### Counter to {persona1}
[Response to opposing position]

---

## Synthesis
[What both positions agree on, where they differ, and what the core trade-off is]

---
*AI-generated debate. Read-only - annotate or cite in your brief.*
'''
    
    @staticmethod
    def generate_critique_template(target: str) -> str:
        """
        Template for AI-generated critique documents.
        
        Args:
            target: What's being critiqued
        
        Returns:
            Markdown structure for critique
        """
        return f'''# Critique: {target}

## Target Position
[The position being critiqued]

## Unexamined Assumptions
[Assumptions that lack evidence or validation]

1. Assumption: [Statement]
   - Gap: [What's missing]
   - Severity: [High/Medium/Low]

## Evidence Gaps
[Missing evidence that would strengthen or weaken the position]

## Logical Issues
[Problems in reasoning, circular logic, etc.]

## Recommendations
[What needs to be done to strengthen this position]

---
*AI-generated critique. Read-only - use to improve your reasoning.*
'''
