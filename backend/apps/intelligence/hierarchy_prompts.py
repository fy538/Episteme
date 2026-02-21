"""
Hierarchy prompt builders — generates LLM prompts for hierarchical
cluster summarization at each level of the tree.

Follows the pattern of thematic_summary_prompts.py: stateless, no I/O, returns strings.

Output format uses XML tags for easy parsing:
    <label>2-5 word label</label>
    <summary>Summary text</summary>
"""
from typing import Any, Dict, List


def build_topic_summary_prompt(
    chunk_texts: List[str],
    doc_titles: List[str],
) -> tuple[str, str]:
    """
    Build prompts for Level 1 (topic) summarization.

    Takes representative chunk texts from a single cluster and asks
    for a concise label and 1-3 sentence summary.

    Args:
        chunk_texts: Representative passage texts from the cluster.
        doc_titles: Document titles that contributed to this cluster.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    system_prompt = """You are a document analyst. You are given passages from one thematic cluster of documents. Your task is to:

1. Create a concise label (2-5 words) that captures the core topic
2. Write a brief summary (1-3 sentences) synthesizing the key insight

## Output Format

<label>2-5 word topic label</label>
<summary>1-3 sentence synthesis of what these passages reveal.</summary>

## Rules

- Label: specific and descriptive, not generic (avoid "Miscellaneous" or "General Topics")
- Summary: synthesize the insight, don't enumerate topics
- Do NOT invent information not present in the passages
- Total output under 60 words"""

    parts = []
    if doc_titles:
        unique_titles = sorted(set(doc_titles))
        parts.append(f"Sources: {', '.join(unique_titles)}")
        parts.append("")

    parts.append("## Passages")
    for i, text in enumerate(chunk_texts):
        parts.append(f"\n[{i + 1}] {text}")

    parts.append(
        "\n\nGenerate a topic label and summary using the XML format "
        "specified in the system prompt."
    )

    user_prompt = "\n".join(parts)
    return system_prompt, user_prompt


def build_theme_synthesis_prompt(
    topic_summaries: List[Dict[str, Any]],
) -> tuple[str, str]:
    """
    Build prompts for Level 2 (theme) synthesis.

    Takes topic labels and summaries from Level 1 clusters and asks
    for a higher-level theme label and 2-4 sentence synthesis.

    Args:
        topic_summaries: List of dicts with 'label', 'summary', 'chunk_count'.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    system_prompt = """You are a document analyst. You are given topic summaries from related clusters of document passages. Your task is to:

1. Create a concise theme label (2-5 words) that captures the overarching theme
2. Write a synthesis (2-4 sentences) that connects the topics and draws out the higher-level insight

## Output Format

<label>2-5 word theme label</label>
<summary>2-4 sentence synthesis connecting the topics and their implications.</summary>

## Rules

- The theme should be more abstract than any individual topic
- Identify connections and tensions between topics
- Do NOT just concatenate topic summaries — synthesize
- Total output under 100 words"""

    parts = ["## Topics in this Theme"]
    for i, topic in enumerate(topic_summaries):
        label = topic.get('label', f'Topic {i + 1}')
        summary = topic.get('summary', '')
        chunk_count = topic.get('chunk_count', 0)
        parts.append(f"\n### {label} ({chunk_count} passages)")
        parts.append(summary)

    parts.append(
        "\n\nSynthesize these topics into a theme label and summary "
        "using the XML format specified in the system prompt."
    )

    user_prompt = "\n".join(parts)
    return system_prompt, user_prompt


def build_project_overview_prompt(
    theme_summaries: List[Dict[str, Any]],
    project_title: str,
    project_description: str = '',
) -> tuple[str, str]:
    """
    Build prompts for Level 3 (root) project overview.

    Takes theme labels and syntheses from Level 2 and asks for a
    project-level narrative overview.

    Args:
        theme_summaries: List of dicts with 'label', 'summary', 'coverage_pct'.
        project_title: The project's title.
        project_description: Optional project description.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    system_prompt = """You are a document analyst. You are given the major themes identified across a project's documents. Your task is to:

1. Create a concise label (3-7 words) that captures the project's knowledge landscape
2. Write a project overview (3-5 sentences) that synthesizes the themes into a coherent narrative

## Output Format

<label>3-7 word project landscape label</label>
<summary>3-5 sentence overview synthesizing the project's knowledge themes, their relationships, and the overall picture they paint.</summary>

## Rules

- The overview should help someone quickly understand what this project's documents are about
- Identify how themes relate to each other (tensions, dependencies, complementary perspectives)
- Mention coverage distribution if notable (e.g., heavily focused on one area)
- Do NOT just list themes — weave them into a narrative
- Total output under 150 words"""

    parts = [f"# Project: {project_title}"]
    if project_description:
        parts.append(f"Description: {project_description}")
    parts.append("")

    parts.append("## Themes")
    for i, theme in enumerate(theme_summaries):
        label = theme.get('label', f'Theme {i + 1}')
        summary = theme.get('summary', '')
        coverage = theme.get('coverage_pct', 0)
        parts.append(f"\n### {label} ({coverage:.0f}% of content)")
        parts.append(summary)

    parts.append(
        "\n\nSynthesize these themes into a project overview using "
        "the XML format specified in the system prompt."
    )

    user_prompt = "\n".join(parts)
    return system_prompt, user_prompt
