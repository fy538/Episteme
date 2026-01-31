"""
Debate Agent - Generate multi-perspective debates.

Simulates stakeholder perspectives to help users see all sides.
"""
import json
from django.conf import settings
import openai


class DebateAgent:
    """
    Generate debates between different personas/stakeholders.
    
    Simulates multiple perspectives to help users consider all viewpoints.
    Each perspective is presented in its strongest form (steel-man).
    """
    
    def __init__(self):
        self.model = "gpt-4o"
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
    
    def generate_debate(
        self,
        topic: str,
        personas: list,
        case_context: str = ""
    ) -> dict:
        """
        Generate debate between personas.
        
        Args:
            topic: Debate topic
            personas: List of personas like [{"name": "Tech Lead", "role": "Cost-focused"}]
            case_context: Case background
        
        Returns:
            {
                "content": "markdown debate",
                "structure": {
                    "personas": [
                        {
                            "name": "...",
                            "position": "...",
                            "arguments": [...],
                        }
                    ],
                    "synthesis": "..."
                }
            }
        """
        prompt = self._build_debate_prompt(topic, personas, case_context)
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_debate_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,  # More creative for different perspectives
                max_tokens=3000
            )
            
            content = response.choices[0].message.content
            structure = self._extract_debate_structure(content, personas)
            
            return {
                "content": content,
                "structure": structure
            }
        except Exception as e:
            return {
                "content": f"# Debate Generation Failed\n\nError: {str(e)}",
                "structure": {"error": str(e)}
            }
    
    def _get_debate_system_prompt(self) -> str:
        """System prompt for debate generation"""
        return """You simulate rigorous debates between different stakeholders.

Your role:
- Present each perspective in its strongest form (steel-man, not straw-man)
- Provide evidence for each position
- Be fair and balanced
- Show where positions conflict and where they agree
- Help users see all sides of an issue

Output: Structured debate in markdown with clear sections for each persona."""
    
    def _build_debate_prompt(
        self,
        topic: str,
        personas: list,
        case_context: str
    ) -> str:
        """Build debate prompt"""
        
        context_section = ""
        if case_context:
            context_section = f"Decision context: {case_context}\n\n"
        
        personas_section = "Personas to simulate:\n"
        for persona in personas:
            personas_section += f"- {persona['name']}: {persona.get('role', 'stakeholder')}\n"
        
        return f"""{context_section}{personas_section}

Debate topic: {topic}

For each persona:
1. State their position clearly
2. Provide 3-5 strong arguments with supporting reasoning
3. Present counter-arguments to other positions
4. Be charitable and fair - present each view in its strongest form

End with a synthesis showing:
- What all positions agree on (common ground)
- Where they fundamentally disagree (key trade-offs)
- What the decision depends on

Format as markdown with clear sections for each persona, then synthesis."""
    
    def _extract_debate_structure(self, content: str, personas: list) -> dict:
        """Extract positions and arguments from debate markdown"""
        
        structure = {
            "personas": [
                {
                    "name": p["name"],
                    "role": p.get("role", ""),
                    "position": "",
                    "arguments": []
                }
                for p in personas
            ],
            "common_ground": [],
            "key_disagreements": [],
            "synthesis": ""
        }
        
        # Simple parsing - look for persona names in headings
        lines = content.split('\n')
        current_persona_idx = None
        in_synthesis = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Detect persona sections
            for idx, persona in enumerate(personas):
                if persona['name'] in line and line.startswith('##'):
                    current_persona_idx = idx
                    in_synthesis = False
                    break
            
            # Detect synthesis section
            if '## Synthesis' in line or '## Common Ground' in line:
                in_synthesis = True
                current_persona_idx = None
            
            # Extract position statements (first paragraph under persona)
            if current_persona_idx is not None and line_stripped and not line_stripped.startswith('#'):
                if not structure['personas'][current_persona_idx]['position']:
                    structure['personas'][current_persona_idx]['position'] = line_stripped
            
            # Extract arguments (numbered or bulleted lists)
            if current_persona_idx is not None:
                if line_stripped.startswith(('1.', '2.', '3.', '4.', '5.', '-', '•')):
                    argument = line_stripped.lstrip('123456789.-•').strip()
                    if argument:
                        structure['personas'][current_persona_idx]['arguments'].append(argument)
            
            # Extract synthesis content
            if in_synthesis and line_stripped and not line_stripped.startswith('#'):
                structure['synthesis'] += line_stripped + ' '
        
        structure['synthesis'] = structure['synthesis'].strip()
        
        return structure
