"""
Insight discovery prompt builders — generates LLM prompts for detecting
cross-cluster tensions, coverage gaps, and patterns.

Follows the pattern of thematic_summary_prompts.py: stateless, no I/O, returns strings.
"""
from typing import Any, Dict


def build_tension_detection_prompt(
    theme_a: Dict[str, Any],
    theme_b: Dict[str, Any],
) -> tuple[str, str]:
    """
    Build prompts for detecting contradictions between two theme clusters.

    Args:
        theme_a: Dict with 'label', 'summary', 'coverage_pct'.
        theme_b: Dict with 'label', 'summary', 'coverage_pct'.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    system_prompt = """You are an analytical reviewer examining two thematic clusters from a document collection. Your task is to determine whether these clusters contain contradictory claims, conflicting evidence, or unresolved tensions.

## Output Format

If you find a tension:
<tension>
<title>Brief title of the contradiction (5-10 words)</title>
<explanation>2-3 sentences explaining the contradiction and why it matters.</explanation>
<confidence>0.0-1.0 confidence that this is a genuine tension</confidence>
</tension>

If there is no meaningful tension:
<no_tension />

## Rules

- Only flag genuine contradictions or conflicts, not mere differences in focus
- A tension exists when two themes make incompatible claims or present conflicting evidence
- Confidence should reflect how clear and significant the contradiction is
- Do NOT invent tensions that aren't supported by the summaries"""

    user_prompt = f"""## Theme A: {theme_a.get('label', 'Unknown')} ({theme_a.get('coverage_pct', 0):.0f}% of content)
{theme_a.get('summary', '')}

## Theme B: {theme_b.get('label', 'Unknown')} ({theme_b.get('coverage_pct', 0):.0f}% of content)
{theme_b.get('summary', '')}

Do these themes contain contradictions, conflicting claims, or unresolved tensions?"""

    return system_prompt, user_prompt
