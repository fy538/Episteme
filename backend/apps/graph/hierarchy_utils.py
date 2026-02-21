"""
Shared utilities for the hierarchical clustering feature.

Used by both HierarchicalSummaryService and InsightDiscoveryAgent.
"""
from typing import Dict, List


def detect_coverage_gaps(
    themes: List[dict],
    total_chunks: int = 0,
) -> List[str]:
    """
    Detect coverage gap descriptions from the hierarchy tree.

    Returns human-readable gap descriptions (strings).
    Used by HierarchicalSummaryService for summary sections and
    by InsightDiscoveryAgent for heuristic gap detection.

    Args:
        themes: Level 2 theme nodes from the hierarchy tree.
        total_chunks: Total chunks in the project (for thin-coverage threshold).
    """
    gap_parts: List[str] = []

    for theme in themes:
        for topic in theme.get('children', []):
            doc_ids = topic.get('document_ids', [])
            chunk_count = topic.get('chunk_count', 0)
            label = topic.get('label', 'Unknown')

            # Gap: single-document topic with substantive content
            if len(doc_ids) == 1 and chunk_count >= 2:
                gap_parts.append(
                    f'"{label}" relies on a single source'
                )
            # Gap: very thin topic (< 3 chunks) within a larger project
            elif chunk_count < 3 and total_chunks > 20:
                gap_parts.append(
                    f'"{label}" has thin coverage ({chunk_count} passages)'
                )

    return gap_parts


def detect_gap_insights(
    project_id,
    tree: dict,
    themes: List[dict],
) -> list:
    """
    Build ProjectInsight objects for coverage gaps.

    Returns unsaved ProjectInsight instances (for bulk_create).
    Used by InsightDiscoveryAgent.
    """
    from .models import ProjectInsight, InsightType, InsightSource, InsightStatus

    insights = []
    total_chunks = tree.get('chunk_count', 0)

    for theme in themes:
        topics = theme.get('children', [])
        for topic in topics:
            chunk_count = topic.get('chunk_count', 0)
            doc_ids = topic.get('document_ids', [])
            label = topic.get('label', 'Unknown topic')

            # Gap: single-document topic
            if len(doc_ids) == 1 and chunk_count >= 2:
                insight = ProjectInsight(
                    project_id=project_id,
                    insight_type=InsightType.BLIND_SPOT,
                    title=f'Single-source coverage: {label}',
                    content=(
                        f'The topic "{label}" under theme '
                        f'"{theme.get("label", "Unknown")}" is covered by only one document. '
                        f'This could indicate a blind spot \u2014 consider seeking additional '
                        f'perspectives on this topic.'
                    ),
                    source_type=InsightSource.AGENT_DISCOVERY,
                    source_cluster_ids=[topic.get('id', '')],
                    status=InsightStatus.ACTIVE,
                    confidence=0.6,
                    metadata={'gap_type': 'single_source'},
                )
                insights.append(insight)

            # Gap: very thin topic (< 3 chunks) within a large project
            if chunk_count < 3 and total_chunks > 20:
                insight = ProjectInsight(
                    project_id=project_id,
                    insight_type=InsightType.BLIND_SPOT,
                    title=f'Thin coverage: {label}',
                    content=(
                        f'The topic "{label}" has only '
                        f'{chunk_count} passage(s), which may indicate the topic is '
                        f'underexplored in the current documents.'
                    ),
                    source_type=InsightSource.AGENT_DISCOVERY,
                    source_cluster_ids=[topic.get('id', '')],
                    status=InsightStatus.ACTIVE,
                    confidence=0.5,
                    metadata={'gap_type': 'thin_coverage', 'chunk_count': chunk_count},
                )
                insights.append(insight)

    return insights
