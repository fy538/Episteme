"""
ProjectSummaryService — generates, stores, and manages project summaries.

Orchestrates clustering, prompt building, LLM generation, XML parsing,
and staleness tracking for AI-generated project summaries.
"""
import asyncio
import logging
import re
import time
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree

from django.db import transaction
from django.utils import timezone

from .clustering import ClusteringService
from .models import (
    GraphDelta, Node, ProjectSummary, SummaryStatus,
)
from .services import GraphService

logger = logging.getLogger(__name__)


class ProjectSummaryService:
    """Generates, stores, and manages project summaries."""

    @staticmethod
    def validate_sections(sections: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize summary sections JSON.

        Ensures the expected shape is present, fills missing keys with
        defaults, and strips malformed key_findings entries. Called before
        storing sections to the database.

        Returns:
            Sanitized sections dict.
        """
        defaults = {
            'overview': '',
            'key_findings': [],
            'emerging_picture': '',
            'attention_needed': '',
            'what_changed': '',
            'coverage_gaps': '',
        }

        if not isinstance(sections, dict):
            logger.warning("sections is not a dict, returning defaults")
            return defaults

        result = {}
        for key, default in defaults.items():
            val = sections.get(key, default)
            if key == 'key_findings':
                if not isinstance(val, list):
                    val = []
                # Validate each finding entry
                clean_findings = []
                for f in val:
                    if not isinstance(f, dict):
                        continue
                    clean_findings.append({
                        'theme_label': str(f.get('theme_label', 'Unlabeled')),
                        'narrative': str(f.get('narrative', '')),
                        'cited_nodes': (
                            f.get('cited_nodes', [])
                            if isinstance(f.get('cited_nodes'), list)
                            else []
                        ),
                        # Optional thematic fields
                        **({k: f[k] for k in ('coverage_pct', 'doc_count', 'chunk_count') if k in f}),
                    })
                val = clean_findings
            else:
                val = str(val) if val else ''
            result[key] = val

        return result

    @staticmethod
    def get_current_summary(project_id: uuid.UUID) -> Optional[ProjectSummary]:
        """
        Get the most recent non-failed, non-generating summary for a project.
        Returns None if no summary exists.
        """
        return (
            ProjectSummary.objects
            .filter(project_id=project_id)
            .exclude(status__in=[SummaryStatus.FAILED, SummaryStatus.GENERATING])
            .order_by('-created_at')
            .first()
        )

    @staticmethod
    def mark_stale(project_id: uuid.UUID, auto_regenerate: bool = True):
        """
        Mark the current summary as stale. Called on graph delta events.
        Uses update() for efficiency — no object fetching.

        If auto_regenerate is True (default), schedules a debounced
        regeneration task so stale summaries refresh within ~30s of
        the last document upload, rather than waiting for the daily cron.
        """
        updated = ProjectSummary.objects.filter(
            project_id=project_id,
            is_stale=False,
        ).exclude(
            status__in=[SummaryStatus.NONE, SummaryStatus.FAILED, SummaryStatus.GENERATING]
        ).update(
            is_stale=True,
            stale_since=timezone.now(),
        )

        # Debounced auto-regeneration: cache key prevents duplicate dispatches
        # within the cooldown window (batch uploads produce many stale events).
        if auto_regenerate and updated > 0:
            try:
                from django.core.cache import cache
                lock_key = f'summary_auto_regen:{project_id}'
                if cache.add(lock_key, '1', timeout=30):
                    from .tasks import generate_project_summary
                    generate_project_summary.apply_async(
                        args=[str(project_id)],
                        kwargs={'force': True},
                        countdown=30,  # 30s debounce
                    )
                    logger.info(
                        "summary_auto_regeneration_scheduled",
                        extra={'project_id': str(project_id)},
                    )
            except Exception:
                logger.debug("Auto-regeneration dispatch failed", exc_info=True)

    @staticmethod
    def should_generate(project_id: uuid.UUID) -> Tuple[bool, str]:
        """
        Determine if full summary generation should proceed.

        Returns:
            (should_generate, reason)
        """
        from .models import ClusterHierarchy, HierarchyStatus

        # Check if a ready hierarchy exists (new primary path)
        has_hierarchy = ClusterHierarchy.objects.filter(
            project_id=project_id,
            is_current=True,
            status=HierarchyStatus.READY,
        ).exists()

        node_count = Node.objects.filter(project_id=project_id).count()

        if not has_hierarchy and node_count == 0:
            return False, 'no_data'

        current = ProjectSummaryService.get_current_summary(project_id)
        if current is None:
            if has_hierarchy:
                return True, 'hierarchy_ready'
            return True, 'no_summary'
        if current.is_stale:
            return True, 'stale'

        # Thematic summaries should be upgraded to full when hierarchy is ready
        if current.status == SummaryStatus.THEMATIC:
            if has_hierarchy:
                return True, 'thematic_to_hierarchy'
            if node_count >= 5:
                return True, 'thematic_upgrade'
            return False, 'thematic_insufficient_data'

        # Seed summaries are templates — upgrade to full once enough data exists
        if current.status == SummaryStatus.SEED:
            if has_hierarchy:
                return True, 'seed_to_hierarchy'
            if node_count >= 5:
                return True, 'seed_upgrade'
            return False, 'seed_insufficient_nodes'

        # Check if currently generating
        generating = ProjectSummary.objects.filter(
            project_id=project_id,
            status=SummaryStatus.GENERATING,
        ).exists()
        if generating:
            return False, 'already_generating'

        return False, 'up_to_date'

    @staticmethod
    def get_seed_summary(project_id: uuid.UUID) -> Dict[str, Any]:
        """
        Generate a template-based seed summary without LLM.
        Used when graph has <5 nodes.

        Returns dict matching sections JSON shape.
        """
        nodes = list(
            Node.objects.filter(project_id=project_id)
            .select_related('source_document')
            .order_by('node_type', '-created_at')[:10]
        )

        if not nodes:
            return {
                'overview': '',
                'key_findings': [],
                'emerging_picture': '',
                'attention_needed': '',
                'what_changed': '',
            }

        # Group by type for the overview
        type_counts: Dict[str, int] = defaultdict(int)
        for n in nodes:
            type_counts[n.node_type] += 1

        type_parts = [f"{count} {ntype}{'s' if count > 1 else ''}" for ntype, count in type_counts.items()]
        total = sum(type_counts.values())
        overview = (
            f"Episteme extracted {', '.join(type_parts)} from your documents so far — "
            f"{'a solid start' if total >= 3 else 'the beginning of your knowledge map'}. "
            f"Upload more to unlock a full AI-powered summary with argument analysis."
        )

        # List nodes as findings
        key_findings = [{
            'theme_label': 'Initial Findings',
            'narrative': '; '.join(
                f"{n.content[:100]}" for n in nodes[:5]
            ),
            'cited_nodes': [str(n.id) for n in nodes[:5]],
        }]

        return {
            'overview': overview,
            'key_findings': key_findings,
            'emerging_picture': '',
            'attention_needed': '',
            'what_changed': 'This is the first project summary.',
        }

    @staticmethod
    async def generate_summary(
        project_id: uuid.UUID,
        force: bool = False,
    ) -> ProjectSummary:
        """
        Generate a new project summary.

        Args:
            project_id: Project UUID.
            force: If True, skip the concurrent-generation guard. Used by
                   stale summary regeneration and manual regenerate API to
                   proceed even when another GENERATING row exists.

        Steps:
        1. Check if hierarchy is available → delegate to HierarchicalSummaryService
        2. Otherwise fall back to node-based generation (seed / full tier)
        """
        from .models import ClusterHierarchy, HierarchyStatus

        # ── Preferred path: hierarchy-based summary ──
        # If a ready cluster hierarchy exists, use it instead of node-based clustering
        current_hierarchy = (
            ClusterHierarchy.objects
            .filter(project_id=project_id, is_current=True, status=HierarchyStatus.READY)
            .first()
        )
        if current_hierarchy:
            from .hierarchical_summary import HierarchicalSummaryService
            service = HierarchicalSummaryService()
            summary = await service.generate_project_overview(project_id, current_hierarchy)
            if summary:
                return summary
            # Fall through to legacy path if hierarchy summary failed

        # ── Legacy fallback: node-based summary ──
        return await ProjectSummaryService._generate_node_based_summary(
            project_id, force=force,
        )

    @staticmethod
    async def _generate_node_based_summary(
        project_id: uuid.UUID,
        force: bool = False,
    ) -> ProjectSummary:
        """
        Legacy node-based summary generation.

        Used as fallback when no cluster hierarchy is available (e.g.,
        projects created before hierarchical clustering was enabled).
        """
        from apps.common.llm_providers.anthropic_provider import AnthropicProvider
        from apps.intelligence.summary_prompts import (
            build_summary_system_prompt,
            build_summary_user_prompt,
        )

        node_count = Node.objects.filter(project_id=project_id).count()
        if node_count == 0:
            raise ValueError("Cannot generate summary for project with no nodes")

        # Atomically determine version + create placeholder to prevent
        # concurrent generation attempts (should_generate checks GENERATING).
        with transaction.atomic():
            latest = (
                ProjectSummary.objects
                .filter(project_id=project_id)
                .select_for_update()
                .order_by('-version')
                .first()
            )
            next_version = (latest.version + 1) if latest else 1

            # Bail out if another generation is already in flight
            if not force and ProjectSummary.objects.filter(
                project_id=project_id,
                status=SummaryStatus.GENERATING,
            ).exists():
                raise ValueError("Summary generation already in progress")

            summary = ProjectSummary.objects.create(
                project_id=project_id,
                status=SummaryStatus.GENERATING,
                version=next_version,
            )

        # Get previous summary for diffing (outside transaction — read-only)
        previous = ProjectSummaryService.get_current_summary(project_id)
        previous_sections = previous.sections if previous else None
        previous_clusters = previous.clusters if previous else None

        start_time = time.time()

        try:
            # ── Seed tier ──
            if node_count < 5:
                sections = ProjectSummaryService.get_seed_summary(project_id)
                summary.status = SummaryStatus.SEED
                summary.sections = sections
                summary.generation_metadata = {
                    'tier': 'seed',
                    'node_count': node_count,
                    'duration_ms': int((time.time() - start_time) * 1000),
                }
                summary.is_stale = False
                summary.save()
                return summary

            # ── Full tier ──

            # Step 1: Fetch graph health
            graph_health = GraphService.compute_graph_health(project_id)

            # Step 2: Fetch graph once, then reuse for clustering/prompt/metrics
            graph = GraphService.get_project_graph(project_id)
            project_nodes = graph.get('nodes', [])
            project_edges = graph.get('edges', [])
            nodes_by_id = {n.id: n for n in project_nodes}

            # Cluster nodes using the already-loaded graph to avoid re-querying
            clusters = ClusteringService.cluster_project_nodes(
                project_id, graph=graph,
            )

            # Step 3: Label clusters (LLM call)
            # Enrich clusters with node contents for the prompt
            for cluster in clusters:
                node_contents = []
                for nid_str in cluster['node_ids']:
                    nid = uuid.UUID(nid_str)
                    node = nodes_by_id.get(nid)
                    if node:
                        node_contents.append({
                            'id': nid_str,
                            'type': node.node_type,
                            'status': node.status,
                            'content': node.content[:200],
                            'source': node.source_document.title[:40] if node.source_document else '',
                        })
                cluster['node_contents'] = node_contents

            clusters = await ClusteringService.label_clusters(
                clusters, nodes_by_id, previous_clusters,
            )

            # Step 3b: Inherit thematic labels for continuity
            thematic_labels = None
            thematic_summary = (
                ProjectSummary.objects
                .filter(project_id=project_id, status=SummaryStatus.THEMATIC)
                .order_by('-created_at')
                .first()
            )
            if thematic_summary and thematic_summary.sections.get('key_findings'):
                thematic_labels = [
                    f['theme_label']
                    for f in thematic_summary.sections['key_findings']
                    if f.get('theme_label')
                ]

            # Step 4: Build case summaries
            case_summaries = ProjectSummaryService._build_case_summaries(project_id)

            # Step 5: Get recent deltas
            from .delta_service import GraphDeltaService
            deltas = GraphDeltaService.get_project_deltas(project_id, limit=5)
            recent_deltas = [
                {
                    'trigger': d.trigger,
                    'narrative': d.narrative,
                    'nodes_created': d.nodes_created,
                    'edges_created': d.edges_created,
                    'tensions_surfaced': d.tensions_surfaced,
                }
                for d in deltas
            ]

            # Step 6: Attention patterns
            attention_patterns = {
                'unresolved_tensions': graph_health.get('unresolved_tensions', 0),
                'untested_assumptions': graph_health.get('untested_assumptions', 0),
                'unsubstantiated_claims': graph_health.get('unsubstantiated_claims', 0),
            }

            # Step 7: Build prompt
            system_prompt = build_summary_system_prompt()
            user_prompt = build_summary_user_prompt(
                project_title=summary.project.title,
                project_description=summary.project.description or '',
                graph_health=graph_health,
                clusters=clusters,
                case_summaries=case_summaries,
                recent_deltas=recent_deltas,
                previous_summary=previous_sections,
                attention_patterns=attention_patterns,
                thematic_labels=thematic_labels,
            )

            # Step 8: Call LLM
            from django.conf import settings
            full_cfg = getattr(settings, 'SUMMARY_SETTINGS', {}).get('full', {})
            llm_max_tokens = full_cfg.get('max_tokens', 2048)
            llm_temperature = full_cfg.get('temperature', 0.4)
            llm_timeout = full_cfg.get('timeout_seconds', 120)

            provider = AnthropicProvider()
            try:
                response = await asyncio.wait_for(
                    provider.generate(
                        messages=[{"role": "user", "content": user_prompt}],
                        system_prompt=system_prompt,
                        max_tokens=llm_max_tokens,
                        temperature=llm_temperature,
                    ),
                    timeout=float(llm_timeout),
                )
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"Full summary LLM call timed out after {llm_timeout}s"
                )

            # Step 9: Parse XML response
            sections = ProjectSummaryService._parse_summary_xml(response)

            # Step 10: Get latest delta for reference
            latest_delta = deltas[0] if deltas else None

            # Step 11: Store result
            duration_ms = int((time.time() - start_time) * 1000)

            # Strip node_contents from clusters before storing (only needed for prompt).
            # Attach per-cluster summaries from key_findings narratives.
            # Match by case-insensitive label; fall back to index alignment.
            key_findings = sections.get('key_findings', [])
            narrative_lookup = {
                f['theme_label'].strip().lower(): f['narrative']
                for f in key_findings
                if f.get('theme_label') and f.get('narrative')
            }
            stored_clusters = []
            for i, c in enumerate(clusters):
                label = c.get('label', '').strip()
                narrative = (
                    narrative_lookup.get(label.lower())
                    or (key_findings[i]['narrative'] if i < len(key_findings) else '')
                )
                stored_clusters.append({
                    'label': label or f'Theme {i + 1}',
                    'node_ids': c.get('node_ids', []),
                    'centroid_node_id': c.get('centroid_node_id', ''),
                    'summary': narrative.strip() if narrative else '',
                })

            # Compute cluster quality metrics using preloaded project edges.
            cluster_quality = ClusteringService.compute_cluster_quality(
                clusters, project_edges,
            )

            summary.status = SummaryStatus.FULL
            summary.sections = ProjectSummaryService.validate_sections(sections)
            summary.clusters = stored_clusters
            summary.is_stale = False
            summary.stale_since = None
            summary.latest_delta_at_generation = latest_delta
            summary.generation_metadata = {
                'tier': 'full',
                'model': provider.model,
                'node_count': node_count,
                'cluster_count': len(clusters),
                'duration_ms': duration_ms,
                'cluster_quality': cluster_quality,
            }
            summary.save()

            logger.info(
                "project_summary_generated",
                extra={
                    'project_id': str(project_id),
                    'version': next_version,
                    'node_count': node_count,
                    'cluster_count': len(clusters),
                    'duration_ms': duration_ms,
                },
            )

            return summary

        except Exception as e:
            logger.exception(
                "project_summary_generation_failed",
                extra={'project_id': str(project_id)},
            )
            summary.status = SummaryStatus.FAILED
            summary.generation_metadata = {
                'error': str(e)[:500],
                'duration_ms': int((time.time() - start_time) * 1000),
            }
            summary.save()
            raise

    # ── Thematic summary (chunk-based, pre-graph) ──────────────────

    @staticmethod
    async def generate_thematic_summary(
        project_id: uuid.UUID,
        document_ids: Optional[List[uuid.UUID]] = None,
    ) -> Optional[ProjectSummary]:
        """
        Generate a thematic summary from chunk clustering (no graph required).

        Called immediately after embeddings are generated, before graph
        extraction. Creates a ProjectSummary with status=THEMATIC.

        This is the fast first-pass summary (~3s total) that gives users
        thematic orientation while the full argumentative analysis runs.

        Args:
            project_id: Project UUID.
            document_ids: Optional subset of documents to include.
                          If None, clusters all project chunks.

        Returns:
            ProjectSummary with status=THEMATIC, or None if skipped
            (e.g., concurrency lock, too few chunks).
        """
        from django.core.cache import cache
        from apps.common.llm_providers.anthropic_provider import AnthropicProvider
        from apps.intelligence.thematic_summary_prompts import (
            build_thematic_summary_system_prompt,
            build_thematic_summary_user_prompt,
        )
        from .chunk_clustering import ChunkClusteringService

        # Concurrency guard: prevent duplicate thematic summaries
        # during batch uploads
        lock_key = f'thematic_summary_lock:{project_id}'
        if not cache.add(lock_key, '1', timeout=30):
            logger.info(
                "thematic_summary_skipped_lock",
                extra={'project_id': str(project_id)},
            )
            return None

        start_time = time.time()

        # Atomically determine version + create placeholder
        with transaction.atomic():
            latest = (
                ProjectSummary.objects
                .filter(project_id=project_id)
                .select_for_update()
                .order_by('-version')
                .first()
            )
            next_version = (latest.version + 1) if latest else 1

            summary = ProjectSummary.objects.create(
                project_id=project_id,
                status=SummaryStatus.GENERATING,
                version=next_version,
            )

        # Check for existing thematic labels to maintain continuity
        existing_themes = None
        previous = ProjectSummaryService.get_current_summary(project_id)
        if previous and previous.sections.get('key_findings'):
            existing_themes = [
                f['theme_label']
                for f in previous.sections['key_findings']
                if f.get('theme_label')
            ]

        try:
            # 1. Cluster chunks (~100ms CPU)
            cluster_result = ChunkClusteringService.cluster_project_chunks(
                project_id=project_id,
                document_ids=document_ids,
            )

            clusters = cluster_result['clusters']

            if not clusters:
                # Too few chunks / all orphans — store minimal summary
                sections = {
                    'overview': (
                        'Documents are being analyzed. '
                        'A full summary will be available shortly.'
                    ),
                    'key_findings': [],
                    'emerging_picture': '',
                    'attention_needed': '',
                    'what_changed': '',
                    'coverage_gaps': '',
                }
                summary.status = SummaryStatus.THEMATIC
                summary.sections = sections
                summary.is_stale = False
                summary.generation_metadata = {
                    'tier': 'thematic',
                    'total_chunks': cluster_result['total_chunks'],
                    'cluster_count': 0,
                    'duration_ms': int((time.time() - start_time) * 1000),
                }
                summary.save()
                return summary

            # 2. Build prompt
            project = summary.project
            system_prompt = build_thematic_summary_system_prompt()
            user_prompt = build_thematic_summary_user_prompt(
                project_title=project.title,
                project_description=project.description or '',
                clusters=clusters,
                orphan_count=len(cluster_result['orphan_chunk_ids']),
                total_chunks=cluster_result['total_chunks'],
                total_documents=cluster_result['total_documents'],
                existing_themes=existing_themes,
            )

            # 3. LLM call (~2-3s)
            from django.conf import settings as django_settings
            thematic_cfg = getattr(django_settings, 'SUMMARY_SETTINGS', {}).get('thematic', {})
            llm_max_tokens = thematic_cfg.get('max_tokens', 1024)
            llm_temperature = thematic_cfg.get('temperature', 0.3)
            llm_timeout = thematic_cfg.get('timeout_seconds', 30)

            provider = AnthropicProvider()
            try:
                response = await asyncio.wait_for(
                    provider.generate(
                        messages=[{"role": "user", "content": user_prompt}],
                        system_prompt=system_prompt,
                        max_tokens=llm_max_tokens,
                        temperature=llm_temperature,
                    ),
                    timeout=float(llm_timeout),
                )
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"Thematic summary LLM call timed out after {llm_timeout}s"
                )

            # 4. Parse response
            sections = ProjectSummaryService._parse_thematic_summary_xml(
                response, clusters,
            )

            # 5. Store clusters for potential future reference
            stored_clusters = []
            for i, c in enumerate(clusters):
                label = (
                    sections['key_findings'][i]['theme_label']
                    if i < len(sections['key_findings'])
                    else f'Theme {i + 1}'
                )
                narrative = (
                    sections['key_findings'][i]['narrative']
                    if i < len(sections['key_findings'])
                    else ''
                )
                stored_clusters.append({
                    'label': label,
                    'chunk_ids': c['chunk_ids'],
                    'coverage_pct': c['coverage_pct'],
                    'document_distribution': c['document_distribution'],
                    'chunk_count': c['chunk_count'],
                    'summary': narrative,
                })

            duration_ms = int((time.time() - start_time) * 1000)

            summary.status = SummaryStatus.THEMATIC
            summary.sections = ProjectSummaryService.validate_sections(sections)
            summary.clusters = stored_clusters
            summary.is_stale = False
            summary.stale_since = None
            summary.generation_metadata = {
                'tier': 'thematic',
                'model': provider.model,
                'total_chunks': cluster_result['total_chunks'],
                'cluster_count': len(clusters),
                'orphan_count': len(cluster_result['orphan_chunk_ids']),
                'duration_ms': duration_ms,
            }
            summary.save()

            logger.info(
                "thematic_summary_generated",
                extra={
                    'project_id': str(project_id),
                    'version': next_version,
                    'cluster_count': len(clusters),
                    'duration_ms': duration_ms,
                },
            )

            return summary

        except Exception as e:
            logger.exception(
                "thematic_summary_generation_failed",
                extra={'project_id': str(project_id)},
            )
            summary.status = SummaryStatus.FAILED
            summary.generation_metadata = {
                'tier': 'thematic',
                'error': str(e)[:500],
                'duration_ms': int((time.time() - start_time) * 1000),
            }
            summary.save()
            raise
        finally:
            cache.delete(lock_key)

    @staticmethod
    def _parse_thematic_summary_xml(
        response: str,
        clusters: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Parse LLM XML response for thematic summary.

        Returns sections dict compatible with full summary format, plus
        additional coverage data per theme (coverage_pct, doc_count,
        chunk_count).
        """
        sections: Dict[str, Any] = {
            'overview': '',
            'key_findings': [],
            'emerging_picture': '',
            'attention_needed': '',
            'what_changed': '',
            'coverage_gaps': '',
        }

        # Try XML parsing first
        try:
            xml_match = re.search(
                r'<thematic_summary>(.*?)</thematic_summary>',
                response,
                re.DOTALL,
            )
            if xml_match:
                xml_str = f"<root>{xml_match.group(1)}</root>"
                root = ElementTree.fromstring(xml_str)

                overview_el = root.find('overview')
                if overview_el is not None and overview_el.text:
                    sections['overview'] = overview_el.text.strip()

                themes_el = root.find('themes')
                if themes_el is not None:
                    for i, theme_el in enumerate(themes_el.findall('theme')):
                        label = theme_el.get('label', f'Theme {i + 1}')
                        narrative = (theme_el.text or '').strip()

                        # Get coverage data from cluster or XML attrs
                        cluster_data = clusters[i] if i < len(clusters) else {}
                        try:
                            coverage_pct = float(
                                theme_el.get('coverage_pct', '0')
                            )
                        except (ValueError, TypeError):
                            coverage_pct = 0
                        try:
                            doc_count = int(
                                theme_el.get('doc_count', '0')
                            )
                        except (ValueError, TypeError):
                            doc_count = 0

                        sections['key_findings'].append({
                            'theme_label': label,
                            'narrative': narrative,
                            'cited_nodes': [],  # No nodes yet
                            'coverage_pct': (
                                coverage_pct
                                or cluster_data.get('coverage_pct', 0)
                            ),
                            'doc_count': (
                                doc_count
                                or len(
                                    cluster_data.get(
                                        'document_distribution', {}
                                    )
                                )
                            ),
                            'chunk_count': cluster_data.get(
                                'chunk_count', 0
                            ),
                        })

                gaps_el = root.find('coverage_gaps')
                if gaps_el is not None and gaps_el.text:
                    sections['coverage_gaps'] = gaps_el.text.strip()

                return sections

        except ElementTree.ParseError:
            logger.warning(
                "XML parsing failed for thematic summary, "
                "falling back to regex"
            )

        # Regex fallback for malformed XML
        overview_match = re.search(
            r'<overview>(.*?)</overview>', response, re.DOTALL
        )
        if overview_match:
            sections['overview'] = overview_match.group(1).strip()

        theme_matches = re.finditer(
            r'<theme\s+label="([^"]*)"[^>]*>(.*?)</theme>',
            response,
            re.DOTALL,
        )
        for i, tm in enumerate(theme_matches):
            cluster_data = clusters[i] if i < len(clusters) else {}
            sections['key_findings'].append({
                'theme_label': tm.group(1),
                'narrative': tm.group(2).strip(),
                'cited_nodes': [],
                'coverage_pct': cluster_data.get('coverage_pct', 0),
                'doc_count': len(
                    cluster_data.get('document_distribution', {})
                ),
                'chunk_count': cluster_data.get('chunk_count', 0),
            })

        gaps_match = re.search(
            r'<coverage_gaps>(.*?)</coverage_gaps>', response, re.DOTALL
        )
        if gaps_match:
            sections['coverage_gaps'] = gaps_match.group(1).strip()

        return sections

    # ── Case summaries (used by full tier) ───────────────────────

    @staticmethod
    def _build_case_summaries(project_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Build case summary context for the prompt."""
        from apps.cases.models import Case, CaseStatus
        from apps.inquiries.models import Inquiry

        cases = Case.objects.filter(
            project_id=project_id,
            status__in=[CaseStatus.ACTIVE, CaseStatus.DRAFT],
        ).order_by('-updated_at')[:10]

        summaries = []
        for case in cases:
            inquiries = Inquiry.objects.filter(case=case).order_by('-updated_at')[:5]
            key_inquiries = [
                {
                    'title': inq.title,
                    'status': inq.status,
                    'conclusion': getattr(inq, 'conclusion', '') or '',
                }
                for inq in inquiries
            ]

            summaries.append({
                'title': case.title,
                'stage': getattr(case, 'stage', 'exploring'),
                'position': getattr(case, 'position', '') or '',
                'key_inquiries': key_inquiries,
            })

        return summaries

    @staticmethod
    def _parse_summary_xml(response: str) -> Dict[str, Any]:
        """
        Parse the XML-structured LLM response into sections JSON.

        Handles malformed XML gracefully with regex fallbacks.
        """
        sections = {
            'overview': '',
            'key_findings': [],
            'emerging_picture': '',
            'attention_needed': '',
            'what_changed': '',
        }

        # Try XML parsing first
        try:
            # Wrap in root if needed and clean up
            xml_match = re.search(
                r'<project_summary>(.*?)</project_summary>',
                response,
                re.DOTALL,
            )
            if xml_match:
                xml_str = f"<root>{xml_match.group(1)}</root>"
                root = ElementTree.fromstring(xml_str)

                # Overview
                overview_el = root.find('overview')
                if overview_el is not None and overview_el.text:
                    sections['overview'] = overview_el.text.strip()

                # Key findings
                findings_el = root.find('key_findings')
                if findings_el is not None:
                    for theme_el in findings_el.findall('theme'):
                        label = theme_el.get('label', 'Unlabeled')
                        narrative = (theme_el.text or '').strip()
                        # Extract cited node IDs from narrative
                        cited = re.findall(r'\[nodeId:([a-f0-9-]+)\]', narrative)
                        sections['key_findings'].append({
                            'theme_label': label,
                            'narrative': narrative,
                            'cited_nodes': cited,
                        })

                # Simple text sections
                for section_name in ['emerging_picture', 'attention_needed', 'what_changed']:
                    el = root.find(section_name)
                    if el is not None and el.text:
                        sections[section_name] = el.text.strip()

                return sections
        except ElementTree.ParseError:
            logger.warning("XML parsing failed for summary, falling back to regex")

        # Regex fallback for malformed XML
        for tag in ['overview', 'emerging_picture', 'attention_needed', 'what_changed']:
            match = re.search(rf'<{tag}>(.*?)</{tag}>', response, re.DOTALL)
            if match:
                sections[tag] = match.group(1).strip()

        # Key findings regex fallback
        findings_match = re.search(
            r'<key_findings>(.*?)</key_findings>', response, re.DOTALL
        )
        if findings_match:
            theme_matches = re.finditer(
                r'<theme\s+label="([^"]*)">(.*?)</theme>',
                findings_match.group(1),
                re.DOTALL,
            )
            for tm in theme_matches:
                narrative = tm.group(2).strip()
                cited = re.findall(r'\[nodeId:([a-f0-9-]+)\]', narrative)
                sections['key_findings'].append({
                    'theme_label': tm.group(1),
                    'narrative': narrative,
                    'cited_nodes': cited,
                })

        return sections
