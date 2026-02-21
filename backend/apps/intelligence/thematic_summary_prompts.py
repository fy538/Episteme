"""
Thematic summary prompt builders — generates a fast thematic overview
from document chunk clusters.

Follows the pattern of summary_prompts.py: stateless, no I/O, returns strings.

Unlike the full summary prompt, this operates on raw document passages
(not extracted graph nodes). It produces a lighter summary with theme labels,
coverage percentages, and gap detection.
"""
from typing import Any, Dict, List, Optional


def build_thematic_summary_system_prompt() -> str:
    """
    System prompt for thematic summary generation.

    Instructs the LLM to label themes, write a brief overview,
    and identify coverage gaps from clustered document passages.
    """
    return """You are a document analyst. You are given clusters of passages from documents uploaded to a project. Your task is to:

1. Label each cluster with a concise theme name (2-5 words)
2. Write a brief narrative for each theme (1-2 sentences) describing what the passages reveal
3. Write a project overview (40-60 words)
4. Identify coverage gaps — themes that seem underexplored or missing

## Output Format

You MUST structure your response using these XML tags:

<thematic_summary>
<overview>
40-60 word overview of what the documents cover, their breadth, and general focus.
</overview>

<themes>
<theme label="Theme Name" coverage_pct="35.2" doc_count="4">
1-2 sentence narrative about what the passages in this cluster reveal. Synthesize, don't enumerate.
</theme>
<theme label="Another Theme" coverage_pct="28.0" doc_count="3">
1-2 sentence narrative.
</theme>
</themes>

<coverage_gaps>
1-2 sentences about what appears to be missing, underexplored, or relies on only a single source. Be specific.
</coverage_gaps>
</thematic_summary>

## Rules

- Theme labels: 2-5 words, specific and descriptive (not "Miscellaneous" or "Other Topics")
- Narratives: synthesize the key insight, don't just list what topics appear
- Do NOT invent information not present in the passages
- coverage_pct and doc_count attributes should match the values provided in the context
- Be honest about gaps — single-source themes and absent topics are worth flagging
- Total output should be under 300 words
- Tone: third-person analytical, concise and scannable"""


def build_thematic_summary_user_prompt(
    project_title: str,
    project_description: str,
    clusters: List[Dict[str, Any]],
    orphan_count: int,
    total_chunks: int,
    total_documents: int,
    existing_themes: Optional[List[str]] = None,
) -> str:
    """
    Build user prompt from chunk clustering results.

    Args:
        project_title: Project name.
        project_description: Project description.
        clusters: From ChunkClusteringService.cluster_project_chunks().
        orphan_count: Number of unclustered chunks.
        total_chunks: Total chunks across all documents.
        total_documents: Total document count.
        existing_themes: Theme labels from a prior summary to maintain
                         label continuity across regenerations.
    """
    parts = []

    # ── Project metadata ──
    parts.append(f"# Project: {project_title}")
    if project_description:
        parts.append(f"Description: {project_description}")
    parts.append(
        f"\nTotal: {total_chunks} passages across "
        f"{total_documents} document{'s' if total_documents != 1 else ''}"
    )
    parts.append("")

    # ── Previous theme labels for continuity ──
    if existing_themes:
        parts.append("## Previous Theme Labels (maintain where relevant)")
        for t in existing_themes:
            parts.append(f"  - {t}")
        parts.append("")

    # ── Passage clusters ──
    parts.append("## Passage Clusters")

    for i, cluster in enumerate(clusters):
        coverage = cluster.get('coverage_pct', 0)
        doc_dist = cluster.get('document_distribution', {})
        doc_count = len(doc_dist)
        chunk_count = cluster.get('chunk_count', 0)

        parts.append(
            f"\n### Cluster {i + 1} "
            f"({chunk_count} passages, {coverage}% of total, "
            f"{doc_count} doc{'s' if doc_count != 1 else ''})"
        )

        # Document sources
        if doc_dist:
            doc_parts = [
                f'"{title}" ({count} passages)'
                for title, count in sorted(
                    doc_dist.items(), key=lambda x: -x[1]
                )
            ]
            parts.append(f"  Sources: {', '.join(doc_parts)}")

        # Representative passages
        for rep in cluster.get('representative_chunks', []):
            title = rep.get('document_title', 'Unknown')
            text = rep.get('text', '')
            parts.append(f'  [from "{title}"] {text}')

    if orphan_count > 0:
        parts.append(
            f"\n{orphan_count} passage{'s' if orphan_count != 1 else ''} "
            f"did not cluster (diverse or isolated content)."
        )

    parts.append(
        "\nGenerate the thematic summary following "
        "the XML format specified in the system prompt."
    )

    return "\n".join(parts)
