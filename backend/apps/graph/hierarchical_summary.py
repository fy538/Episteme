"""
HierarchicalSummaryService — generates project summaries from the
hierarchical cluster tree.

Replaces the node-based full summary pipeline with hierarchy-based
synthesis. Uses the existing ProjectSummary model for storage.
"""
import logging
import time
from typing import Dict, List

logger = logging.getLogger(__name__)


class HierarchicalSummaryService:
    """Generate project summaries from hierarchical cluster trees."""

    async def generate_project_overview(
        self,
        project_id,
        hierarchy,
    ):
        """
        Generate a ProjectSummary from a ClusterHierarchy tree.

        Extracts themes from the hierarchy, synthesizes them into
        the standard ProjectSummary sections format, and stores
        the result.

        Args:
            project_id: UUID of the project.
            hierarchy: ClusterHierarchy instance with status='ready'.

        Returns:
            ProjectSummary instance.
        """
        from .models import ProjectSummary, SummaryStatus, ClusterHierarchy
        from .models import ProjectInsight, InsightStatus

        start_time = time.time()
        tree = hierarchy.tree

        if not tree:
            return None

        # Extract themes (Level 2) and root overview
        root_summary = tree.get('summary', '')
        root_label = tree.get('label', '')
        themes = tree.get('children', [])

        # Build sections
        sections = {
            'overview': root_summary,
            'key_findings': [],
            'emerging_picture': '',
            'attention_needed': '',
            'what_changed': '',
            'coverage_gaps': '',
        }

        # Key findings from themes
        for theme in themes:
            finding = {
                'theme_label': theme.get('label', 'Unknown'),
                'narrative': theme.get('summary', ''),
                'coverage_pct': theme.get('coverage_pct', 0),
                'chunk_count': theme.get('chunk_count', 0),
                'document_count': len(theme.get('document_ids', [])),
                'topic_count': len(theme.get('children', [])),
            }
            sections['key_findings'].append(finding)

        # Attention needed from active insights
        active_insights = list(
            ProjectInsight.objects
            .filter(project_id=project_id, status=InsightStatus.ACTIVE)
            .order_by('-confidence')[:5]
        )

        if active_insights:
            attention_parts = []
            for insight in active_insights:
                attention_parts.append(
                    f"**{insight.title}**: {insight.content}"
                )
            sections['attention_needed'] = '\n\n'.join(attention_parts)

        # Coverage gaps: use shared utility (also used by InsightDiscoveryAgent)
        from .hierarchy_utils import detect_coverage_gaps
        gap_parts = detect_coverage_gaps(themes)
        if gap_parts:
            sections['coverage_gaps'] = '. '.join(gap_parts[:5]) + '.'

        # What changed: diff with previous hierarchy version
        previous = (
            ClusterHierarchy.objects
            .filter(project_id=project_id, is_current=False)
            .exclude(id=hierarchy.id)
            .order_by('-version')
            .first()
        )

        if previous and previous.tree:
            sections['what_changed'] = self._compute_diff(
                previous.tree, hierarchy.tree,
            )

        # Store clusters for frontend reference
        stored_clusters = []
        for theme in themes:
            stored_clusters.append({
                'label': theme.get('label', ''),
                'cluster_id': theme.get('id', ''),
                'chunk_ids': theme.get('chunk_ids', []),
                'coverage_pct': theme.get('coverage_pct', 0),
                'chunk_count': theme.get('chunk_count', 0),
                'summary': theme.get('summary', ''),
            })

        # Create ProjectSummary with atomic version increment
        from django.db import transaction

        duration_ms = int((time.time() - start_time) * 1000)

        with transaction.atomic():
            latest_version = (
                ProjectSummary.objects
                .filter(project_id=project_id)
                .select_for_update()
                .order_by('-version')
                .values_list('version', flat=True)
                .first()
            ) or 0

            summary = ProjectSummary.objects.create(
                project_id=project_id,
                status=SummaryStatus.FULL,
                sections=sections,
                version=latest_version + 1,
                clusters=stored_clusters,
                is_stale=False,
                generation_metadata={
                    'tier': 'hierarchy',
                    'duration_ms': duration_ms,
                    'hierarchy_version': hierarchy.version,
                    'theme_count': len(themes),
                    'total_chunks': tree.get('chunk_count', 0),
                },
            )

        logger.info(
            "hierarchy_summary_generated",
            extra={
                'project_id': str(project_id),
                'version': summary.version,
                'duration_ms': duration_ms,
            },
        )

        return summary

    @staticmethod
    def _compute_diff(old_tree: dict, new_tree: dict) -> str:
        """Compute a human-readable diff between two hierarchy versions."""
        old_themes = {
            c.get('label', ''): c
            for c in old_tree.get('children', [])
        }
        new_themes = {
            c.get('label', ''): c
            for c in new_tree.get('children', [])
        }

        old_labels = set(old_themes.keys())
        new_labels = set(new_themes.keys())

        added = new_labels - old_labels
        removed = old_labels - new_labels
        kept = old_labels & new_labels

        parts = []

        if added:
            parts.append(f"New themes: {', '.join(sorted(added))}")

        if removed:
            parts.append(f"Removed themes: {', '.join(sorted(removed))}")

        # Check for significant coverage changes in kept themes
        for label in sorted(kept):
            old_cov = old_themes[label].get('coverage_pct', 0)
            new_cov = new_themes[label].get('coverage_pct', 0)
            diff = new_cov - old_cov
            if abs(diff) > 5:
                direction = 'grew' if diff > 0 else 'shrank'
                parts.append(f'"{label}" {direction} ({old_cov:.0f}% -> {new_cov:.0f}%)')

        if not parts:
            return 'No significant changes from previous version.'

        return ' '.join(parts)
