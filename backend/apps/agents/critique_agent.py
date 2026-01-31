"""
Critique Agent - Devil's advocate analysis.

Challenges positions to strengthen reasoning through constructive criticism.
"""
from django.conf import settings
import openai


class CritiqueAgent:
    """
    Generate rigorous critiques of positions.
    
    Acts as devil's advocate to surface assumptions, gaps, and logical issues.
    Helps strengthen reasoning through constructive challenges.
    """
    
    def __init__(self):
        self.model = "gpt-4o"
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
    
    def generate_critique(
        self,
        target_position: str,
        inquiry_context: str = "",
        case_context: str = ""
    ) -> dict:
        """
        Generate rigorous critique of a position.
        
        Args:
            target_position: Position to critique (from brief or inquiry)
            inquiry_context: Inquiry details
            case_context: Case background
        
        Returns:
            {
                "content": "markdown critique",
                "structure": {
                    "unexamined_assumptions": [...],
                    "evidence_gaps": [...],
                    "logical_issues": [...],
                    "recommendations": [...]
                }
            }
        """
        prompt = self._build_critique_prompt(target_position, inquiry_context, case_context)
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_critique_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,  # Focused but thoughtful
                max_tokens=3000
            )
            
            content = response.choices[0].message.content
            structure = self._extract_critique_structure(content)
            
            return {
                "content": content,
                "structure": structure
            }
        except Exception as e:
            return {
                "content": f"# Critique Generation Failed\n\nError: {str(e)}",
                "structure": {"error": str(e)}
            }
    
    def _get_critique_system_prompt(self) -> str:
        """System prompt for critique agent"""
        return """You are a rigorous critic analyzing reasoning quality.

Your role:
- Challenge unexamined assumptions
- Identify evidence gaps
- Detect logical fallacies
- Surface blind spots
- Strengthen arguments through criticism

Be tough but constructive. The goal is to improve reasoning, not to be contrarian.
Point out real weaknesses that could undermine the position."""
    
    def _build_critique_prompt(
        self,
        target_position: str,
        inquiry_context: str,
        case_context: str
    ) -> str:
        """Build critique prompt"""
        
        context_section = ""
        if case_context:
            context_section += f"Case: {case_context}\n"
        if inquiry_context:
            context_section += f"Inquiry: {inquiry_context}\n"
        
        return f"""Act as a rigorous devil's advocate.

{context_section}

Target position to critique:
{target_position}

Analyze this position for:

1. **Unexamined Assumptions**
   - What is taken as given without proof?
   - What implicit assumptions underlie the reasoning?
   - Which assumptions are critical vs. minor?

2. **Evidence Gaps**
   - What claims lack supporting evidence?
   - What evidence would strengthen or weaken this position?
   - Are sources credible and relevant?

3. **Logical Issues**
   - Any circular reasoning?
   - Any motivated reasoning (conclusion-first)?
   - Any false dichotomies or strawmen?
   - Any scope limitations?

4. **Missing Considerations**
   - What perspectives or alternatives aren't considered?
   - What could go wrong that isn't addressed?
   - What trade-offs are ignored?

5. **Recommendations**
   - Concrete actions to strengthen this position
   - Evidence needed to validate assumptions
   - Considerations to address

Be constructively critical. Format as markdown with clear sections."""
    
    def _extract_critique_structure(self, content: str) -> dict:
        """Extract assumptions, gaps, issues from critique markdown"""
        
        structure = {
            "unexamined_assumptions": [],
            "evidence_gaps": [],
            "logical_issues": [],
            "missing_considerations": [],
            "recommendations": []
        }
        
        # Parse sections
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line_stripped = line.strip()
            
            # Detect sections
            if '## Unexamined Assumptions' in line or '### Unexamined Assumptions' in line:
                current_section = 'unexamined_assumptions'
            elif '## Evidence Gaps' in line or '### Evidence Gaps' in line:
                current_section = 'evidence_gaps'
            elif '## Logical Issues' in line or '### Logical Issues' in line:
                current_section = 'logical_issues'
            elif '## Missing Considerations' in line or '### Missing Considerations' in line:
                current_section = 'missing_considerations'
            elif '## Recommendations' in line or '### Recommendations' in line:
                current_section = 'recommendations'
            # Extract list items
            elif current_section and line_stripped.startswith(('1.', '2.', '3.', '4.', '5.', '-', '•', '*')):
                item = line_stripped.lstrip('123456789.-•*').strip()
                if item and current_section in structure:
                    # Try to parse assumption/gap/issue structure
                    if ':' in item:
                        parts = item.split(':', 1)
                        structure[current_section].append({
                            'title': parts[0].strip(),
                            'description': parts[1].strip(),
                            'severity': 'medium'  # Default
                        })
                    else:
                        structure[current_section].append({
                            'title': item,
                            'description': '',
                            'severity': 'medium'
                        })
        
        return structure
