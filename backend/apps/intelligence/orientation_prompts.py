"""
Orientation prompt builders — generates LLM prompts for lens detection
and lens-based orientation synthesis.

Follows the pattern of thematic_summary_prompts.py: stateless, no I/O, returns strings.

The orientation pipeline has two steps:
1. Lens detection: scores 6 lens types against the theme summaries
2. Orientation synthesis: generates findings + exploration angles through the chosen lens
"""
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════
# Lens definitions
# ═══════════════════════════════════════════════════════════════════

LENS_DEFINITIONS = {
    'positions_and_tensions': {
        'label': 'Positions & Tensions',
        'short': 'Competing claims, arguments, evidence for and against',
        'detection_hint': (
            'Material contains debatable claims, competing positions, '
            'evidence that supports or contradicts assertions, or sources '
            'that disagree on key points.'
        ),
        'synthesis_instructions': (
            'Focus on: What claims are being made? Where do sources agree strongly? '
            'Where do they disagree? What is asserted without evidence? What is '
            'conspicuously absent? Rate the evidential strength of each finding.'
        ),
    },
    'structure_and_dependencies': {
        'label': 'Structure & Dependencies',
        'short': 'Systems, components, processes with relationships',
        'detection_hint': (
            'Material describes systems, components, processes, or architectures '
            'with explicit relationships, dependencies, interfaces, or constraints '
            'between parts.'
        ),
        'synthesis_instructions': (
            'Focus on: What components or systems exist? How do they relate to each '
            'other? What dependencies are critical? What interfaces or boundaries are '
            'defined? What single points of failure or coupling risks exist?'
        ),
    },
    'perspectives_and_sentiment': {
        'label': 'Perspectives & Sentiment',
        'short': 'Different human viewpoints, stakeholder opinions',
        'detection_hint': (
            'Material contains distinct human viewpoints, stakeholder opinions, '
            'interview responses, qualitative feedback, or personal perspectives '
            'on shared topics.'
        ),
        'synthesis_instructions': (
            'Focus on: What distinct viewpoints or stakeholder perspectives exist? '
            'Where do perspectives align or diverge? What is the emotional or strategic '
            'stance of each group? Whose voice is missing from the conversation?'
        ),
    },
    'obligations_and_constraints': {
        'label': 'Obligations & Constraints',
        'short': 'Rules, requirements, boundaries, compliance',
        'detection_hint': (
            'Material defines rules, legal requirements, compliance obligations, '
            'contractual terms, policies, or regulatory constraints that must be '
            'followed or considered.'
        ),
        'synthesis_instructions': (
            'Focus on: What rules or obligations are defined? Where do requirements '
            'conflict or overlap? What is ambiguous or open to interpretation? What '
            'jurisdictional or contextual variations exist? What obligations may be missing?'
        ),
    },
    'events_and_causation': {
        'label': 'Events & Causation',
        'short': 'What happened, why, and what patterns emerge',
        'detection_hint': (
            'Material narrates events, incidents, case studies, or historical sequences '
            'with causal explanations, timelines, outcomes, and lessons learned.'
        ),
        'synthesis_instructions': (
            'Focus on: What events occurred and in what sequence? What were the causes '
            'and effects? What patterns recur across events? What turning points or '
            'decision moments were critical? What lessons emerge?'
        ),
    },
    'concepts_and_progression': {
        'label': 'Concepts & Progression',
        'short': 'Ideas that build on each other, learning material',
        'detection_hint': (
            'Material explains concepts, theories, or domain knowledge with '
            'prerequisite relationships, progressive complexity, or foundational '
            'ideas that more advanced content builds upon.'
        ),
        'synthesis_instructions': (
            'Focus on: What foundational concepts exist? How do ideas build on each '
            'other? What prerequisite knowledge is assumed? What concept dependencies '
            'exist? What areas have the deepest vs. shallowest coverage?'
        ),
    },
}

LENS_TYPES = list(LENS_DEFINITIONS.keys())


# ═══════════════════════════════════════════════════════════════════
# Lens detection
# ═══════════════════════════════════════════════════════════════════

def build_lens_detection_prompt(
    theme_summaries: List[Dict[str, Any]],
) -> tuple[str, str]:
    """
    Build prompts for detecting which orientation lens best fits the content.

    Args:
        theme_summaries: List of dicts with 'id', 'label', 'summary', 'coverage_pct'.
            Extracted from Level 2 of the cluster hierarchy.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    lens_descriptions = "\n".join(
        f"- **{key}**: {defn['detection_hint']}"
        for key, defn in LENS_DEFINITIONS.items()
    )

    system_prompt = f"""You are a document collection analyst. Given theme summaries from a document collection, determine which orientation lens would be most useful for understanding this material.

## Available Lenses

{lens_descriptions}

## Output Format

Score each lens from 0.0 to 1.0 based on how well it fits the content. A score of 0.8+ means the lens is an excellent fit. A score below 0.3 means the lens is not applicable.

<lens_scores>
<lens type="positions_and_tensions" score="0.85" />
<lens type="structure_and_dependencies" score="0.20" />
<lens type="perspectives_and_sentiment" score="0.45" />
<lens type="obligations_and_constraints" score="0.10" />
<lens type="events_and_causation" score="0.15" />
<lens type="concepts_and_progression" score="0.30" />
</lens_scores>

## Rules

- Score based on the actual content of the summaries, not assumptions about the domain
- Multiple lenses can score highly if the content genuinely fits multiple modes
- At least one lens should score above 0.5
- Do not explain your scoring — just output the XML"""

    # Build the user prompt with theme summaries
    themes_text = "\n\n".join(
        f"### {t.get('label', 'Unknown')} ({t.get('coverage_pct', 0):.0f}% of content)\n"
        f"{t.get('summary', '')}"
        for t in theme_summaries
    )

    user_prompt = f"""## Document Collection Themes

{themes_text}

Score each lens for this collection."""

    return system_prompt, user_prompt


# ═══════════════════════════════════════════════════════════════════
# Orientation synthesis
# ═══════════════════════════════════════════════════════════════════

def build_orientation_synthesis_prompt(
    lens_type: str,
    theme_summaries: List[Dict[str, Any]],
    case_context: Optional[List[Dict[str, Any]]] = None,
) -> tuple[str, str]:
    """
    Build prompts for generating a lens-based orientation from theme summaries.

    Args:
        lens_type: The chosen lens key (e.g. 'positions_and_tensions').
        theme_summaries: List of dicts with 'id', 'label', 'summary', 'coverage_pct'.
        case_context: Optional list of active cases with 'title', 'decision_question'.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    lens = LENS_DEFINITIONS.get(lens_type, LENS_DEFINITIONS['positions_and_tensions'])

    system_prompt = f"""You are a document analysis expert generating an orientation briefing. You are viewing a collection of documents through the lens of: **{lens['label']}**.

## Your Lens

{lens['synthesis_instructions']}

## Output Format

Produce a structured orientation using this XML format:

<orientation>
<lead>
2-3 sentence lead paragraph. State the most important headline about this collection viewed through this lens. Be specific and substantive, not generic.
</lead>

<findings>
<finding type="consensus|tension|gap|weak_evidence|pattern">
<heading>Meaningful heading in 5-12 words — a sentence fragment that carries meaning, not a label</heading>
<body>2-3 sentences of substance. Explain what was found, cite which themes contribute, and why it matters. Write in a way that someone reading just this finding learns something concrete.</body>
<source_themes>comma-separated theme IDs that contribute to this finding</source_themes>
<action>discuss|research|none</action>
</finding>
<!-- Include 3-7 findings. Order: consensus first, then tensions, then gaps. -->
</findings>

<angles>
<angle type="discuss|read">A provocative question or comparison that would deepen understanding (title only, 8-15 words)</angle>
<!-- Include 2-4 exploration angles. -->
</angles>

<secondary_lens type="lens_type_key" reason="1 sentence explaining why" />
<!-- Include only if the material has significant secondary character not captured by the primary lens. Omit if not applicable. -->
</orientation>

## Finding Types

- **consensus**: Sources agree strongly on this point. Heading should convey what they agree on.
- **tension**: Sources disagree or contradict each other. Heading should convey the split.
- **gap**: Something important is absent or unaddressed. Heading should convey what is missing.
- **weak_evidence**: A claim rests on thin or questionable evidence. Heading should convey the weakness.
- **pattern**: A recurring theme or notable observation. Heading should convey the pattern.

## Action Rules

- **Maximum 2 findings** may have action != "none". Choose the most consequential.
- Tensions naturally invite "discuss" — they need deliberation.
- Gaps naturally invite "research" — they need investigation.
- Consensus, weak_evidence, and patterns usually have action="none".

## Rules

- Headings must carry meaning — "Market size is well-grounded" not "Market Sizing"
- Body text must be substantive — tell the reader something they learn from reading it
- Do NOT invent information not supported by the theme summaries
- Reference theme labels in the body text naturally (e.g. "the Market Sizing theme shows...")
- source_themes should list the IDs of themes that contribute to each finding
- Tone: third-person analytical, direct and concise
- Total output should be under 600 words"""

    # Build user prompt
    themes_text = "\n\n".join(
        f"### Theme [{t.get('id', '')}]: {t.get('label', 'Unknown')} "
        f"({t.get('coverage_pct', 0):.0f}% of content)\n"
        f"{t.get('summary', '')}"
        for t in theme_summaries
    )

    case_section = ""
    if case_context:
        cases_text = "\n".join(
            f"- **{c.get('title', 'Untitled')}**: {c.get('decision_question', 'No question set')}"
            for c in case_context
        )
        case_section = f"""

## Active Investigations

The user is currently investigating these decisions:
{cases_text}

Consider surfacing exploration angles related to these investigations if the material supports it."""

    user_prompt = f"""## Document Collection Themes

{themes_text}{case_section}

Generate the orientation briefing through the **{lens['label']}** lens."""

    return system_prompt, user_prompt


# ═══════════════════════════════════════════════════════════════════
# Exploration angle on-demand generation
# ═══════════════════════════════════════════════════════════════════

def build_exploration_angle_prompt(
    angle_title: str,
    theme_summaries: List[Dict[str, Any]],
    lens_type: str,
) -> tuple[str, str]:
    """
    Build prompts for on-demand generation when a user clicks an exploration angle.

    Args:
        angle_title: The exploration angle title (e.g. "Why do your sources disagree on timing?")
        theme_summaries: List of dicts with 'id', 'label', 'summary', 'coverage_pct'.
        lens_type: The orientation's lens type for context.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    lens = LENS_DEFINITIONS.get(lens_type, LENS_DEFINITIONS['positions_and_tensions'])

    system_prompt = f"""You are a document analyst providing a brief exploration of a specific angle on a document collection. The collection was analyzed through the **{lens['label']}** lens.

## Output Format

Write 3-5 sentences that explore this angle, grounded in the theme summaries provided. Be specific, cite themes by name, and provide genuine analytical insight. Do not be vague or generic.

Output your response as plain text (no XML tags). Keep it under 100 words."""

    themes_text = "\n\n".join(
        f"### {t.get('label', 'Unknown')} ({t.get('coverage_pct', 0):.0f}%)\n"
        f"{t.get('summary', '')}"
        for t in theme_summaries
    )

    user_prompt = f"""## Exploration Angle

"{angle_title}"

## Available Theme Summaries

{themes_text}

Explore this angle using the theme summaries above."""

    return system_prompt, user_prompt


# ═══════════════════════════════════════════════════════════════════
# Orientation-aware chat prompt (for conversational editing)
# ═══════════════════════════════════════════════════════════════════

def _build_orientation_persona_section() -> str:
    return (
        "You are the Episteme orientation assistant. "
        "You help the user refine their project's orientation — the interpretive "
        "layer that explains what their documents mean, not just what topics they cover.\n\n"
        "## Output Format\n\n"
        "Always wrap your output in these sections:\n"
        "- `<response>` ... `</response>` — Your conversational reply to the user\n"
        "- `<reflection>` ... `</reflection>` — Brief private reflection on what you learned\n"
        "- `<action_hints>[]</action_hints>` — Empty JSON array (no actions needed)\n"
        "- `<orientation_edits>` ... `</orientation_edits>` — JSON diff if proposing changes (or `{}` if not)"
    )


def _build_orientation_state_section(
    lens_type: str,
    lead_text: str,
    findings: list,
    angles: list,
    secondary_lens: str = '',
    secondary_lens_reason: str = '',
) -> str:
    lens_label = LENS_DEFINITIONS.get(lens_type, {}).get('label', lens_type)
    lines = [
        "## Current Orientation State",
        f"**Lens:** {lens_label} (`{lens_type}`)",
    ]
    if secondary_lens:
        sec_label = LENS_DEFINITIONS.get(secondary_lens, {}).get('label', secondary_lens)
        lines.append(f"**Secondary lens:** {sec_label} — {secondary_lens_reason}")
    lines.append(f"\n**Lead text:**\n{lead_text}")

    if findings:
        lines.append("\n### Findings")
        for i, f in enumerate(findings):
            status_badge = f.get('status', 'active')
            ftype = f.get('insight_type', f.get('type', ''))
            fid = f.get('id', '')
            lines.append(
                f"{i+1}. [{fid}] **[{ftype}]** {f.get('title', '')} "
                f"(status: {status_badge}, confidence: {f.get('confidence', 0.7):.1f})\n"
                f"   {f.get('content', '')}"
            )
    else:
        lines.append("\n*No findings yet.*")

    if angles:
        lines.append("\n### Exploration Angles")
        for a in angles:
            lines.append(f"- [{a.get('id', '')}] {a.get('title', '')}")
    else:
        lines.append("\n*No exploration angles yet.*")

    return "\n".join(lines)


def _build_orientation_edits_section() -> str:
    return """## Orientation Edits

When the user's message warrants a change to the orientation, emit a JSON diff inside `<orientation_edits>`. Emit only the fields that change.

```json
{
  "diff_summary": "Human-readable summary of proposed changes",
  "diff_data": {
    "update_lead": "New lead text (only if changing)",
    "suggest_lens_change": "new_lens_type (only if suggesting)",
    "added_findings": [
      {"type": "gap|tension|consensus|pattern|weak_evidence", "title": "...", "content": "...", "action_type": "discuss|research|none"}
    ],
    "updated_findings": [
      {"id": "existing-finding-uuid", "title": "...", "content": "...", "status": "active|acknowledged|resolved|dismissed"}
    ],
    "removed_finding_ids": ["uuid-of-finding-to-dismiss"],
    "added_angles": [{"title": "..."}],
    "removed_angle_ids": ["uuid-of-angle-to-remove"]
  }
}
```

**When to propose edits:**
- User disagrees with a finding or wants to reframe it
- User identifies a new tension, gap, or pattern
- User wants to rewrite the lead text
- User suggests a different lens would be more appropriate
- User wants to dismiss or refine a specific finding
- User provides new information that changes the orientation

**When NOT to propose edits:**
- Casual conversation or general questions about the orientation
- User is asking what a finding means (explain instead)
- No new information or perspective has been offered

If no changes are warranted, emit `<orientation_edits>{}</orientation_edits>` (empty object)."""


def build_orientation_aware_system_prompt(
    lens_type: str,
    lead_text: str,
    findings: list,
    angles: list,
    secondary_lens: str = '',
    secondary_lens_reason: str = '',
) -> str:
    """
    Build a system prompt for orientation-mode chat.

    The LLM sees the current orientation state and can propose
    diff-only edits via the <orientation_edits> section.

    Args:
        lens_type: Current lens type key
        lead_text: Current lead text
        findings: List of finding dicts with id, insight_type/type, title, content, status, confidence
        angles: List of angle dicts with id, title
        secondary_lens: Optional secondary lens type key
        secondary_lens_reason: Why the secondary lens is relevant
    """
    sections = [
        _build_orientation_persona_section(),
        _build_orientation_state_section(
            lens_type=lens_type,
            lead_text=lead_text,
            findings=findings,
            angles=angles,
            secondary_lens=secondary_lens,
            secondary_lens_reason=secondary_lens_reason,
        ),
        _build_orientation_edits_section(),
    ]
    return "\n\n".join(sections)
