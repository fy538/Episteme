"""
Research Agent - Generate comprehensive research reports.

Uses the LLM provider abstraction to research topics deeply and
create structured reports.
"""
from asgiref.sync import async_to_sync

from apps.common.llm_providers import get_llm_provider


class ResearchAgent:
    """
    Generate comprehensive research reports.

    Uses the configured LLM provider to research topics deeply,
    synthesize findings, and create structured, professional reports.
    """

    def generate_research(
        self,
        topic: str,
        case_context: str = "",
        inquiry_context: str = "",
        sources: list = None,
        graph_context: str = "",
    ) -> dict:
        """
        Generate comprehensive research on a topic.

        Args:
            topic: What to research
            case_context: Context from case
            inquiry_context: Context from inquiry (if specific)
            sources: Optional list of existing documents to reference

        Returns:
            {
                "content": "markdown research report",
                "structure": {
                    "executive_summary": "...",
                    "key_findings": [...],
                    "recommendations": [...],
                    "sources": [...],
                    "caveats": [...]
                }
            }
        """
        prompt = self._build_research_prompt(topic, case_context, inquiry_context, sources, graph_context)

        try:
            provider = get_llm_provider('chat')

            async def _call():
                return await provider.generate(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt=self._get_research_system_prompt(),
                    temperature=0.3,  # Some creativity but mostly factual
                    max_tokens=4000,  # Long-form research
                )

            content = async_to_sync(_call)()

            # Extract structure from markdown
            structure = self._extract_research_structure(content)

            return {
                "content": content,
                "structure": structure
            }
        except Exception as e:
            # Return error structure
            return {
                "content": f"# Research Generation Failed\n\nError: {str(e)}",
                "structure": {"error": str(e)}
            }
    
    def _get_research_system_prompt(self) -> str:
        """System prompt for research agent"""
        return """You are a research assistant helping with high-stakes decisions.

Your role:
- Conduct comprehensive research on topics
- Synthesize findings from multiple perspectives
- Provide evidence-based analysis
- Identify limitations and caveats
- Structure findings clearly

Output format: Markdown report with clear sections.
Be thorough, rigorous, and balanced. Don't make up facts - focus on logical analysis and frameworks."""
    
    def _build_research_prompt(
        self,
        topic: str,
        case_context: str,
        inquiry_context: str,
        sources: list,
        graph_context: str = "",
    ) -> str:
        """Build complete research prompt with context"""

        context_section = ""
        if case_context:
            context_section += f"Case context: {case_context}\n\n"
        if inquiry_context:
            context_section += f"Inquiry context: {inquiry_context}\n\n"
        if graph_context:
            context_section += (
                "The case's current knowledge graph contains these claims, "
                "evidence, assumptions, and tensions. Build on this existing "
                "knowledge and avoid redundant research:\n\n"
                f"{graph_context}\n\n"
            )

        sources_section = ""
        if sources:
            sources_section = "Existing sources to consider:\n"
            for source in sources:
                sources_section += f"- {source['title']} ({source.get('type', 'document')})\n"
            sources_section += "\n"

        return f"""{context_section}{sources_section}Research topic: {topic}

Provide comprehensive research including:

1. **Executive Summary**
   - High-level findings and key takeaways

2. **Key Findings**
   - Detailed findings organized by subtopic
   - Evidence and reasoning for each finding
   - Strength of evidence where applicable

3. **Different Perspectives**
   - Multiple viewpoints on the topic
   - Trade-offs and considerations

4. **Limitations and Caveats**
   - What this research doesn't cover
   - Assumptions made
   - Areas of uncertainty

5. **Recommendations**
   - Actionable recommendations based on findings
   - Next steps for further investigation

6. **Sources**
   - List key sources/references (can be general categories)

Format as professional research report in markdown with clear section headers."""
    
    def _extract_research_structure(self, markdown_content: str) -> dict:
        """
        Extract structured data from research markdown.
        
        Parses markdown to extract findings, recommendations, etc.
        """
        structure = {
            "executive_summary": "",
            "findings": [],
            "recommendations": [],
            "sources": [],
            "caveats": []
        }
        
        # Parse sections
        lines = markdown_content.split('\n')
        current_section = None
        current_subsection = None
        
        for line in lines:
            line_stripped = line.strip()
            
            # Detect main sections
            if '## Executive Summary' in line:
                current_section = 'executive_summary'
                current_subsection = None
            elif '## Key Findings' in line:
                current_section = 'findings'
                current_subsection = None
            elif '## Recommendations' in line:
                current_section = 'recommendations'
                current_subsection = None
            elif '## Sources' in line:
                current_section = 'sources'
                current_subsection = None
            elif '## Limitations' in line or '## Caveats' in line:
                current_section = 'caveats'
                current_subsection = None
            # Detect subsections (findings)
            elif line_stripped.startswith('### ') and current_section == 'findings':
                # New finding subsection
                finding_topic = line_stripped.replace('### ', '').strip()
                structure['findings'].append({
                    'topic': finding_topic,
                    'content': '',
                    'strength': 0.7  # Default
                })
                current_subsection = len(structure['findings']) - 1
            # Collect content
            elif current_section == 'executive_summary' and line_stripped and not line_stripped.startswith('#'):
                structure['executive_summary'] += line_stripped + ' '
            elif current_section == 'findings' and current_subsection is not None:
                if line_stripped and not line_stripped.startswith('#'):
                    structure['findings'][current_subsection]['content'] += line_stripped + ' '
            elif current_section == 'recommendations' and line_stripped.startswith('-'):
                structure['recommendations'].append(line_stripped[1:].strip())
            elif current_section == 'caveats' and line_stripped.startswith('-'):
                structure['caveats'].append(line_stripped[1:].strip())
        
        # Clean up
        structure['executive_summary'] = structure['executive_summary'].strip()
        for finding in structure['findings']:
            finding['content'] = finding['content'].strip()
        
        return structure
