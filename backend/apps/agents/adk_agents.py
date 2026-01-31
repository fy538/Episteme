"""
Google ADK agent wrappers for Episteme

Simple agents using Google's Agent Development Kit:
- Research agent (with web search)
- Critique agent (red-team/devil's advocate)
- Brief generator (synthesize position)

Design philosophy: Keep it simple
- Basic agent calls with web search
- Parse responses into blocks
- Track provenance (signals + evidence)
"""
import logging
from typing import List, Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from google.adk import Agent
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    logger.warning(
        "google_adk_not_installed",
        extra={"install_hint": "pip install google-adk"},
    )


class ADKResearchAgent:
    """
    Research agent using Google ADK with web search.
    
    Generates comprehensive research reports on topics.
    """
    
    def __init__(self):
        if not ADK_AVAILABLE:
            raise ImportError("Google ADK not available")
        
        self.agent = Agent(
            model="gemini-2.0-flash-exp",
            system_instruction="""
            You are a research agent for Episteme.
            
            Your role:
            - Research topics thoroughly using web search
            - Focus on facts, data, and evidence
            - Generate structured reports with clear sections
            - Cite sources explicitly
            - Highlight key metrics and benchmarks
            
            Output format should be structured blocks:
            1. Executive Summary
            2. Key Findings (with evidence)
            3. Data Points (metrics, benchmarks)
            4. Recommendations
            5. Caveats/Limitations
            6. Sources
            """
        )
    
    async def generate_research(
        self,
        topic: str,
        context_signals: List[Dict[str, Any]] = None,
        context_evidence: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate research report.
        
        Args:
            topic: What to research
            context_signals: User's signals for context
            context_evidence: Existing evidence for context
        
        Returns:
            {
                "blocks": [...],
                "sources": [...],
                "generation_time_ms": int
            }
        """
        import time
        start = time.time()
        
        # Build prompt with context
        prompt = self._build_research_prompt(topic, context_signals, context_evidence)
        
        # Call ADK agent
        result = await self.agent.run(prompt)
        
        # Parse response into blocks
        blocks = self._parse_response_to_blocks(result.text)
        
        elapsed_ms = int((time.time() - start) * 1000)
        
        return {
            'blocks': blocks,
            'sources': self._extract_sources(result.text),
            'generation_time_ms': elapsed_ms,
        }
    
    def _build_research_prompt(self, topic, signals, evidence):
        """Build research prompt with context"""
        prompt = f"Research topic: {topic}\n\n"
        
        if signals:
            prompt += "User's current thinking:\n"
            for sig in signals[:5]:  # Top 5
                prompt += f"- {sig['type']}: {sig['text']}\n"
            prompt += "\n"
        
        if evidence:
            prompt += "Existing evidence:\n"
            for ev in evidence[:3]:  # Top 3
                prompt += f"- {ev['text']}\n"
            prompt += "\n"
        
        prompt += "Generate a comprehensive research report with web search."
        
        return prompt
    
    def _parse_response_to_blocks(self, text: str) -> List[Dict[str, Any]]:
        """Parse markdown response into structured blocks"""
        # Simple parser: split by headings
        import re
        import uuid
        
        blocks = []
        current_block = None
        
        lines = text.split('\n')
        
        for line in lines:
            # Check if line is a heading
            heading_match = re.match(r'^(#{1,3})\s+(.+)$', line)
            
            if heading_match:
                # Save previous block
                if current_block:
                    blocks.append(current_block)
                
                # Start new heading block
                level = len(heading_match.group(1))
                current_block = {
                    'id': str(uuid.uuid4()),
                    'type': 'heading',
                    'level': level,
                    'content': heading_match.group(2),
                    'cites': [],
                }
            elif line.strip():
                # Content line
                if current_block and current_block['type'] == 'heading':
                    # Start paragraph after heading
                    blocks.append(current_block)
                    current_block = {
                        'id': str(uuid.uuid4()),
                        'type': 'paragraph',
                        'content': line,
                        'cites': [],
                    }
                elif current_block:
                    # Add to current paragraph
                    current_block['content'] += '\n' + line
                else:
                    # Start new paragraph
                    current_block = {
                        'id': str(uuid.uuid4()),
                        'type': 'paragraph',
                        'content': line,
                        'cites': [],
                    }
        
        # Save last block
        if current_block:
            blocks.append(current_block)
        
        return blocks
    
    def _extract_sources(self, text: str) -> List[str]:
        """Extract source URLs from text"""
        import re
        
        # Find URLs
        url_pattern = r'https?://[^\s)]+'
        urls = re.findall(url_pattern, text)
        
        return list(set(urls))  # Dedupe


class ADKCritiqueAgent:
    """
    Critique agent using Google ADK.
    
    Challenges assumptions and finds counterarguments.
    """
    
    def __init__(self):
        if not ADK_AVAILABLE:
            raise ImportError("Google ADK not available")
        
        self.agent = Agent(
            model="gemini-2.0-flash-exp",
            system_instruction="""
            You are a critique agent (devil's advocate) for Episteme.
            
            Your role:
            - Challenge assumptions rigorously
            - Find logical gaps and unexamined premises
            - Surface counterarguments
            - Identify evidence gaps
            - Strengthen reasoning through critique
            
            Output structured blocks:
            1. Summary (what you're critiquing)
            2. Unexamined Assumptions
            3. Logical Issues
            4. Evidence Gaps
            5. Counterarguments
            6. Recommendations
            """
        )
    
    async def generate_critique(
        self,
        target_position: str,
        supporting_signals: List[Dict] = None,
        supporting_evidence: List[Dict] = None
    ) -> Dict[str, Any]:
        """Generate critique of a position"""
        import time
        start = time.time()
        
        prompt = f"Critique this position: {target_position}\n\n"
        
        if supporting_signals:
            prompt += "Supporting assumptions:\n"
            for sig in supporting_signals:
                prompt += f"- {sig['text']}\n"
            prompt += "\n"
        
        if supporting_evidence:
            prompt += "Supporting evidence:\n"
            for ev in supporting_evidence:
                prompt += f"- {ev['text']}\n"
            prompt += "\n"
        
        prompt += "Generate a rigorous critique. Challenge assumptions and find gaps."
        
        result = await self.agent.run(prompt)
        blocks = self._parse_response_to_blocks(result.text)
        
        return {
            'blocks': blocks,
            'generation_time_ms': int((time.time() - start) * 1000),
        }
    
    def _parse_response_to_blocks(self, text: str) -> List[Dict]:
        """Same block parsing as research agent"""
        from apps.agents.adk_agents import ADKResearchAgent
        parser = ADKResearchAgent()
        return parser._parse_response_to_blocks(text)


class ADKBriefAgent:
    """
    Brief generator using Google ADK.
    
    Synthesizes position with evidence into decision brief.
    """
    
    def __init__(self):
        if not ADK_AVAILABLE:
            raise ImportError("Google ADK not available")
        
        self.agent = Agent(
            model="gemini-2.0-flash-exp",
            system_instruction="""
            You are a brief generator for Episteme.
            
            Your role:
            - Synthesize position into clear decision brief
            - Ground claims in evidence
            - Structure for stakeholder consumption
            - Be concise but comprehensive
            
            Output structured blocks:
            1. Executive Summary
            2. Decision/Recommendation
            3. Key Assumptions
            4. Supporting Evidence
            5. Risks/Caveats
            6. Next Steps
            """
        )
    
    async def generate_brief(
        self,
        case_position: str,
        confirmed_signals: List[Dict] = None,
        high_credibility_evidence: List[Dict] = None
    ) -> Dict[str, Any]:
        """Generate decision brief"""
        import time
        start = time.time()
        
        prompt = f"Generate decision brief for: {case_position}\n\n"
        
        if confirmed_signals:
            prompt += "Confirmed assumptions/constraints:\n"
            for sig in confirmed_signals:
                prompt += f"- {sig['type']}: {sig['text']}\n"
            prompt += "\n"
        
        if high_credibility_evidence:
            prompt += "Supporting evidence:\n"
            for ev in high_credibility_evidence:
                prompt += f"- {ev['text']}\n"
            prompt += "\n"
        
        prompt += "Create a concise decision brief suitable for stakeholders."
        
        result = await self.agent.run(prompt)
        blocks = self._parse_response_to_blocks(result.text)
        
        return {
            'blocks': blocks,
            'generation_time_ms': int((time.time() - start) * 1000),
        }
    
    def _parse_response_to_blocks(self, text: str) -> List[Dict]:
        """Same block parsing"""
        from apps.agents.adk_agents import ADKResearchAgent
        parser = ADKResearchAgent()
        return parser._parse_response_to_blocks(text)


# Singleton instances
_research_agent = None
_critique_agent = None
_brief_agent = None


def get_research_agent() -> ADKResearchAgent:
    """Get or create research agent singleton"""
    global _research_agent
    if _research_agent is None:
        _research_agent = ADKResearchAgent()
    return _research_agent


def get_critique_agent() -> ADKCritiqueAgent:
    """Get or create critique agent singleton"""
    global _critique_agent
    if _critique_agent is None:
        _critique_agent = ADKCritiqueAgent()
    return _critique_agent


def get_brief_agent() -> ADKBriefAgent:
    """Get or create brief agent singleton"""
    global _brief_agent
    if _brief_agent is None:
        _brief_agent = ADKBriefAgent()
    return _brief_agent
