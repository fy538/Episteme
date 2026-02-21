"""
InsightDiscoveryAgent — discovers tensions, blind spots, and patterns
from a project's hierarchical cluster tree.

Runs after hierarchy building completes. Creates ProjectInsight records
for observations that surface cross-cluster contradictions, coverage gaps,
and recurring patterns.
"""
import asyncio
import logging
import re
import uuid
from typing import List

logger = logging.getLogger(__name__)

# Maximum theme pairs to check for tensions (nC2 can grow fast)
MAX_TENSION_PAIRS = 15
MAX_CONCURRENT_LLM = 5


class InsightDiscoveryAgent:
    """Discover insights from project hierarchy."""

    async def run(self, project_id: uuid.UUID, hierarchy_diff=None) -> list:
        """
        Main entry point. Loads hierarchy, detects insights, stores them.

        When hierarchy_diff is provided (Plan 6):
        - Only check tension pairs involving NEW or EXPANDED themes
        - Generate "theme emerged" insights for genuinely new themes
        - Generate "theme merged" insights for merged themes

        Without hierarchy_diff (first build):
        - Full tension detection across all theme pairs (existing behavior)

        Args:
            project_id: Project UUID.
            hierarchy_diff: Optional HierarchyDiff instance from Plan 6
                hierarchy change detection.

        Returns:
            List of created ProjectInsight instances.
        """
        from .models import (
            ClusterHierarchy, HierarchyStatus, ProjectInsight,
            InsightType, InsightSource, InsightStatus,
        )

        hierarchy = (
            ClusterHierarchy.objects
            .filter(project_id=project_id, is_current=True, status=HierarchyStatus.READY)
            .first()
        )

        if not hierarchy or not hierarchy.tree:
            return []

        tree = hierarchy.tree
        themes = self._extract_themes(tree)

        if not themes:
            return []

        # Dismiss stale insights from previous hierarchy versions that reference
        # cluster IDs no longer present in the current tree
        self._dismiss_stale_insights(project_id, tree)

        insights = []

        # 1. Detect cross-cluster tensions — scoped to changed themes if diff available
        if hierarchy_diff and hierarchy_diff.has_changes:
            changed_labels = set()
            for t in hierarchy_diff.new_themes:
                changed_labels.add(t['label'])
            for t in hierarchy_diff.expanded_themes:
                changed_labels.add(t['label'])

            # Only check pairs involving at least one changed theme
            tension_insights = await self._detect_tensions(
                project_id, themes,
                filter_labels=changed_labels if changed_labels else None,
            )
        else:
            tension_insights = await self._detect_tensions(project_id, themes)

        insights.extend(tension_insights)

        # 2. Theme emergence and merge insights (Plan 6)
        if hierarchy_diff and hierarchy_diff.has_changes:
            for new_theme in hierarchy_diff.new_themes:
                summary_text = new_theme.get('summary', '')
                summary_preview = (summary_text[:150] + '...') if len(summary_text) > 150 else summary_text
                insights.append(ProjectInsight(
                    project_id=project_id,
                    insight_type=InsightType.PATTERN,
                    title=f"New theme emerged: {new_theme['label']}",
                    content=(
                        f"A new topic area appeared in your project: \"{new_theme['label']}\""
                        + (f" ({summary_preview})" if summary_preview else "")
                        + f". This covers {new_theme['chunk_count']} passages."
                    ),
                    source_type=InsightSource.AGENT_DISCOVERY,
                    status=InsightStatus.ACTIVE,
                    confidence=0.8,
                    metadata={'source': 'hierarchy_diff', 'change_type': 'new_theme'},
                ))

            for merged in hierarchy_diff.merged_themes:
                insights.append(ProjectInsight(
                    project_id=project_id,
                    insight_type=InsightType.CONNECTION,
                    title=f"Themes merged: \"{merged['old_label']}\" \u2192 \"{merged['merged_into']}\"",
                    content=(
                        f"The theme \"{merged['old_label']}\" has been absorbed into "
                        f"\"{merged['merged_into']}\", suggesting these topics are more "
                        f"closely related than initially apparent."
                    ),
                    source_type=InsightSource.AGENT_DISCOVERY,
                    status=InsightStatus.ACTIVE,
                    confidence=0.7,
                    metadata={'source': 'hierarchy_diff', 'change_type': 'merged_theme'},
                ))

        # 3. Detect coverage gaps (heuristic, no LLM)
        # Skip single-source gaps if project has ≤1 document (noisy and obvious)
        total_documents = len(set(tree.get('document_ids', [])))
        if total_documents > 1:
            from .hierarchy_utils import detect_gap_insights
            gap_insights = detect_gap_insights(project_id, tree, themes)
            insights.extend(gap_insights)

        # 4. Deduplicate against existing active insights
        new_insights = self._deduplicate(project_id, insights)

        # 5. Bulk create
        if new_insights:
            created = ProjectInsight.objects.bulk_create(new_insights)
            logger.info(
                "insights_created",
                extra={
                    'project_id': str(project_id),
                    'count': len(created),
                    'types': [i.insight_type for i in created],
                    'diff_aware': hierarchy_diff is not None,
                },
            )
            return created

        return []

    def _extract_themes(self, tree: dict) -> List[dict]:
        """Extract Level 2 theme nodes from the tree."""
        if not tree.get('children'):
            return []

        themes = []
        for child in tree['children']:
            if child.get('level', 0) >= 2:
                themes.append(child)
            elif child.get('level', 0) == 1:
                # If root has Level 1 children directly (few clusters),
                # treat them as themes
                themes.append(child)

        return themes

    async def _detect_tensions(
        self,
        project_id: uuid.UUID,
        themes: List[dict],
        filter_labels: set = None,
    ) -> list:
        """Detect cross-cluster tensions by comparing theme pairs via LLM (parallel).

        Args:
            project_id: Project UUID.
            themes: List of theme dicts from the hierarchy tree.
            filter_labels: If provided, only check pairs where at least one
                theme's label is in this set. Saves LLM calls on re-builds
                by skipping stable theme pairs (Plan 6).
        """
        from apps.common.llm_providers.factory import get_llm_provider
        from apps.intelligence.insight_prompts import build_tension_detection_prompt
        from .models import ProjectInsight, InsightType, InsightSource, InsightStatus

        if len(themes) < 2:
            return []

        # Generate pairs (limit to avoid excessive LLM calls)
        pairs = []
        for i in range(len(themes)):
            for j in range(i + 1, len(themes)):
                if filter_labels:
                    label_a = themes[i].get('label', '')
                    label_b = themes[j].get('label', '')
                    if label_a not in filter_labels and label_b not in filter_labels:
                        continue  # Skip — neither theme changed
                pairs.append((themes[i], themes[j]))

        if len(pairs) > MAX_TENSION_PAIRS:
            # Prioritize pairs with highest combined coverage
            pairs.sort(
                key=lambda p: p[0].get('coverage_pct', 0) + p[1].get('coverage_pct', 0),
                reverse=True,
            )
            pairs = pairs[:MAX_TENSION_PAIRS]

        provider = get_llm_provider('fast')
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_LLM)

        async def _check_pair(theme_a: dict, theme_b: dict):
            """Check a single theme pair for tensions."""
            async with semaphore:
                try:
                    system_prompt, user_prompt = build_tension_detection_prompt(theme_a, theme_b)
                    response = await provider.generate(
                        messages=[{"role": "user", "content": user_prompt}],
                        system_prompt=system_prompt,
                        max_tokens=256,
                        temperature=0.2,
                    )

                    if '<no_tension' in response:
                        return None

                    # Parse tension
                    title_match = re.search(r'<title>(.*?)</title>', response, re.DOTALL)
                    explanation_match = re.search(r'<explanation>(.*?)</explanation>', response, re.DOTALL)
                    confidence_match = re.search(r'<confidence>(.*?)</confidence>', response, re.DOTALL)

                    if title_match and explanation_match:
                        confidence = 0.7
                        if confidence_match:
                            try:
                                confidence = float(confidence_match.group(1).strip())
                            except ValueError:
                                pass

                        return ProjectInsight(
                            project_id=project_id,
                            insight_type=InsightType.TENSION,
                            title=title_match.group(1).strip()[:200],
                            content=explanation_match.group(1).strip(),
                            source_type=InsightSource.AGENT_DISCOVERY,
                            source_cluster_ids=[
                                theme_a.get('id', ''),
                                theme_b.get('id', ''),
                            ],
                            status=InsightStatus.ACTIVE,
                            confidence=min(max(confidence, 0.0), 1.0),
                            metadata={'model': 'fast'},
                        )

                except Exception:
                    logger.warning(
                        "tension_detection_failed",
                        extra={
                            'theme_a': theme_a.get('label'),
                            'theme_b': theme_b.get('label'),
                        },
                        exc_info=True,
                    )
                return None

        # Run all pairs in parallel with semaphore-bounded concurrency
        results = await asyncio.gather(*[_check_pair(a, b) for a, b in pairs])
        return [r for r in results if r is not None]

    def _dismiss_stale_insights(
        self,
        project_id: uuid.UUID,
        tree: dict,
    ):
        """Auto-dismiss insights that reference cluster IDs from previous versions."""
        from .models import ProjectInsight, InsightStatus

        # Collect all current cluster IDs from the tree
        current_ids = set()
        self._collect_cluster_ids(tree, current_ids)

        # Find active insights with source_cluster_ids that don't exist in current tree
        active_insights = ProjectInsight.objects.filter(
            project_id=project_id,
            status=InsightStatus.ACTIVE,
        ).exclude(source_cluster_ids=[])

        stale_ids = []
        for insight in active_insights:
            if insight.source_cluster_ids:
                # If none of the referenced clusters exist in current tree, it's stale
                if not any(cid in current_ids for cid in insight.source_cluster_ids):
                    stale_ids.append(insight.id)

        if stale_ids:
            count = ProjectInsight.objects.filter(id__in=stale_ids).update(
                status=InsightStatus.DISMISSED,
            )
            logger.info(
                "stale_insights_dismissed",
                extra={'project_id': str(project_id), 'count': count},
            )

    @staticmethod
    def _collect_cluster_ids(node: dict, ids: set):
        """Recursively collect all cluster IDs from a tree."""
        if node.get('id'):
            ids.add(node['id'])
        for child in node.get('children', []):
            InsightDiscoveryAgent._collect_cluster_ids(child, ids)

    def _deduplicate(
        self,
        project_id: uuid.UUID,
        candidates: list,
    ) -> list:
        """Remove insights that duplicate existing active ones (by title similarity)."""
        from .models import ProjectInsight, InsightStatus

        existing = list(
            ProjectInsight.objects
            .filter(project_id=project_id, status=InsightStatus.ACTIVE)
            .values_list('title', flat=True)
        )

        if not existing:
            return candidates

        existing_titles = set(t.lower() for t in existing)
        unique = []

        for candidate in candidates:
            # Simple title-based dedup (exact match after lowercasing)
            if candidate.title.lower() not in existing_titles:
                unique.append(candidate)
                existing_titles.add(candidate.title.lower())

        return unique
