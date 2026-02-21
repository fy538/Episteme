"""
Summary prompt builders — pure functions for project summary generation.

Follows the pattern of graph_prompts.py: stateless, no I/O, returns strings.
The generated prompt instructs the LLM to produce an XML-structured project
summary with node citations.
"""
from typing import Any, Dict, List, Optional


def build_summary_system_prompt() -> str:
    """
    System prompt for project summary generation.

    Instructs the LLM to produce a structured summary with XML tags and
    node citations in [nodeId:UUID] format.
    """
    return """You are a project intelligence analyst. Your job is to generate a concise, insightful narrative summary of a project's knowledge graph.

## Output Format

You MUST structure your response using these XML tags:

<project_summary>
<overview>
50-80 word overview of the project: what it's about, how many documents/cases, overall state.
</overview>

<key_findings>
<theme label="Theme Name">
1-2 sentences summarizing this theme. Reference specific nodes using [nodeId:UUID] format. Focus on what the evidence shows, not just what topics exist.
</theme>
<theme label="Another Theme">
1-2 sentences with [nodeId:UUID] citations.
</theme>
</key_findings>

<emerging_picture>
50-100 words synthesizing across cases and themes. Where is evidence converging? Where is it diverging? What patterns are becoming clear?
</emerging_picture>

<attention_needed>
50-100 words on gaps, tensions, and weak spots. Unresolved contradictions, untested assumptions, evidence deserts. Be specific — name the nodes involved using [nodeId:UUID].
</attention_needed>

<what_changed>
30-50 words on what changed since the last summary. Reference specific deltas. If this is the first summary, say "This is the first project summary."
</what_changed>
</project_summary>

## Citation Rules

- Use [nodeId:UUID] to reference specific graph nodes (the UUID is provided in the context)
- Only cite nodes that are relevant to the point you're making
- Prefer citing evidence and claims over assumptions
- Do not cite every node — be selective and meaningful

## Tone

- Third-person analytical: "The evidence suggests..." not "You should..."
- Concise and scannable — total should be 300-500 words
- Focus on insight, not enumeration — don't just list what exists, explain what it means
- Be honest about uncertainty and gaps"""


def build_summary_user_prompt(
    project_title: str,
    project_description: str,
    graph_health: Dict[str, Any],
    clusters: List[Dict[str, Any]],
    case_summaries: List[Dict[str, Any]],
    recent_deltas: List[Dict[str, Any]],
    previous_summary: Optional[Dict[str, Any]],
    attention_patterns: Dict[str, Any],
    thematic_labels: Optional[List[str]] = None,
) -> str:
    """
    Build the user prompt with all context for summary generation.

    Args:
        project_title: Project name
        project_description: Project description
        graph_health: From GraphService.compute_graph_health()
        clusters: Labeled clusters with node contents
        case_summaries: [{title, stage, position, key_inquiries, assumptions_summary}]
        recent_deltas: From GraphDeltaService.get_project_deltas()
        previous_summary: Previous sections JSON for "what changed" comparison
        attention_patterns: Tensions, gaps, untested assumptions
        thematic_labels: Theme labels from a prior thematic summary,
                         to maintain naming continuity across tiers
    """
    parts = []

    # ── Project metadata ──
    parts.append(f"# Project: {project_title}")
    if project_description:
        parts.append(f"Description: {project_description}")
    parts.append("")

    # ── Graph health ──
    parts.append("## Graph Overview")
    parts.append(_format_graph_health(graph_health))
    parts.append("")

    # ── Clustered nodes ──
    parts.append("## Knowledge Clusters")
    if not clusters:
        parts.append("No clusters formed yet.")
    else:
        for cluster in clusters:
            label = cluster.get('label', 'Unlabeled')
            node_count = len(cluster.get('node_ids', []))
            edge_count = cluster.get('edge_count', 0)
            parts.append(f"\n### {label} ({node_count} nodes, {edge_count} internal edges)")

            # Include node contents for the LLM to reference
            for node_data in cluster.get('node_contents', []):
                nid = node_data.get('id', '')
                ntype = node_data.get('type', '')
                status = node_data.get('status', '')
                content = node_data.get('content', '')
                source = node_data.get('source', '')
                source_tag = f" (from: {source})" if source else ""
                parts.append(f"  [nodeId:{nid}] [{ntype}][{status}] {content}{source_tag}")
    parts.append("")

    # ── Thematic labels (for continuity from thematic tier) ──
    if thematic_labels:
        parts.append("## Thematic Labels (from initial analysis, maintain where appropriate)")
        for tl in thematic_labels:
            parts.append(f"  - {tl}")
        parts.append("")

    # ── Case summaries ──
    if case_summaries:
        parts.append("## Cases")
        for cs in case_summaries:
            parts.append(f"\n### {cs.get('title', 'Untitled Case')}")
            parts.append(f"Stage: {cs.get('stage', 'unknown')}")
            if cs.get('position'):
                parts.append(f"Position: {cs['position']}")
            if cs.get('key_inquiries'):
                parts.append("Key inquiries:")
                for inq in cs['key_inquiries']:
                    status = inq.get('status', '')
                    title = inq.get('title', '')
                    conclusion = inq.get('conclusion', '')
                    conclusion_tag = f" → {conclusion}" if conclusion else ""
                    parts.append(f"  - [{status}] {title}{conclusion_tag}")
            if cs.get('assumptions_summary'):
                a = cs['assumptions_summary']
                parts.append(
                    f"Assumptions: {a.get('untested', 0)} untested, "
                    f"{a.get('confirmed', 0)} confirmed, "
                    f"{a.get('challenged', 0)} challenged"
                )
        parts.append("")

    # ── Attention patterns ──
    if attention_patterns:
        parts.append("## Attention Patterns")
        if attention_patterns.get('unresolved_tensions'):
            parts.append(f"Unresolved tensions: {attention_patterns['unresolved_tensions']}")
        if attention_patterns.get('untested_assumptions'):
            parts.append(f"Untested assumptions: {attention_patterns['untested_assumptions']}")
        if attention_patterns.get('unsubstantiated_claims'):
            parts.append(f"Unsubstantiated claims: {attention_patterns['unsubstantiated_claims']}")
        if attention_patterns.get('evidence_deserts'):
            parts.append("Evidence deserts (areas with few evidence nodes):")
            for desert in attention_patterns['evidence_deserts'][:5]:
                parts.append(f"  - {desert}")
        parts.append("")

    # ── Recent deltas ──
    if recent_deltas:
        parts.append("## Recent Changes")
        for delta in recent_deltas[:5]:
            trigger = delta.get('trigger', '')
            narrative = delta.get('narrative', '')
            parts.append(f"  - [{trigger}] {narrative}")
        parts.append("")

    # ── Previous summary (for delta comparison) ──
    if previous_summary:
        parts.append("## Previous Summary (for comparison)")
        overview = previous_summary.get('overview', '')
        if overview:
            parts.append(f"Previous overview: {overview[:300]}")
        parts.append("(Generate a 'what_changed' section describing meaningful differences.)")
        parts.append("")
    else:
        parts.append("## Note: This is the FIRST summary for this project.")
        parts.append("(Set what_changed to: 'This is the first project summary.')")
        parts.append("")

    parts.append("Now generate the project summary following the XML format specified in the system prompt.")
    return "\n".join(parts)


def _format_graph_health(health: Dict[str, Any]) -> str:
    """Format graph health stats into a concise summary."""
    if not health or health.get('total_nodes', 0) == 0:
        return "The knowledge graph is empty."

    parts = []
    parts.append(f"{health.get('total_nodes', 0)} nodes, {health.get('total_edges', 0)} edges")

    by_type = health.get('nodes_by_type', {})
    type_parts = []
    for ntype in ['claim', 'evidence', 'assumption', 'tension']:
        count = by_type.get(ntype, 0)
        if count > 0:
            type_parts.append(f"{count} {ntype}s")
    if type_parts:
        parts.append(", ".join(type_parts))

    parts.append(f"Across {health.get('total_documents', 0)} documents")

    return " · ".join(parts)
