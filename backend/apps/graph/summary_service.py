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
    def mark_stale(project_id: uuid.UUID):
        """
        Mark the current summary as stale. Called on graph delta events.
        Uses update() for efficiency — no object fetching.
        """
        ProjectSummary.objects.filter(
            project_id=project_id,
            is_stale=False,
        ).exclude(
            status__in=[SummaryStatus.NONE, SummaryStatus.FAILED, SummaryStatus.GENERATING]
        ).update(
            is_stale=True,
            stale_since=timezone.now(),
        )

    @staticmethod
    def should_generate(project_id: uuid.UUID) -> Tuple[bool, str]:
        """
        Determine if summary generation should proceed.

        Returns:
            (should_generate, reason)
        """
        node_count = Node.objects.filter(project_id=project_id).count()
        if node_count == 0:
            return False, 'no_nodes'

        current = ProjectSummaryService.get_current_summary(project_id)
        if current is None:
            return True, 'no_summary'
        if current.is_stale:
            return True, 'stale'

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
        overview = (
            f"This project has a small knowledge graph with {', '.join(type_parts)}. "
            f"Add more documents to generate a full AI summary."
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

        Steps:
        1. Check if generation is needed
        2. Determine tier: seed (<5 nodes) vs full (5+ nodes)
        3. For seed: store template
        4. For full: cluster → label → prompt → LLM → parse → store
        """
        from apps.common.llm_providers.anthropic_provider import AnthropicProvider
        from apps.intelligence.summary_prompts import (
            build_summary_system_prompt,
            build_summary_user_prompt,
        )

        node_count = Node.objects.filter(project_id=project_id).count()
        if node_count == 0:
            raise ValueError("Cannot generate summary for project with no nodes")

        # Determine version number
        latest = ProjectSummary.objects.filter(project_id=project_id).order_by('-version').first()
        next_version = (latest.version + 1) if latest else 1

        # Get previous summary for diffing
        previous = ProjectSummaryService.get_current_summary(project_id)
        previous_sections = previous.sections if previous else None
        previous_clusters = previous.clusters if previous else None

        # Create placeholder row (status=generating)
        summary = ProjectSummary.objects.create(
            project_id=project_id,
            status=SummaryStatus.GENERATING,
            version=next_version,
        )

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

            # Step 2: Cluster nodes
            clusters = ClusteringService.cluster_project_nodes(project_id)

            # Step 3: Label clusters (LLM call)
            nodes_by_id = {
                n.id: n
                for n in Node.objects.filter(project_id=project_id)
                    .select_related('source_document')
            }
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
            )

            # Step 8: Call LLM
            provider = AnthropicProvider()
            response = await provider.generate(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
                max_tokens=2048,
                temperature=0.4,
            )

            # Step 9: Parse XML response
            sections = ProjectSummaryService._parse_summary_xml(response)

            # Step 10: Get latest delta for reference
            latest_delta = deltas[0] if deltas else None

            # Step 11: Store result
            duration_ms = int((time.time() - start_time) * 1000)

            # Strip node_contents from clusters before storing (only needed for prompt)
            stored_clusters = [
                {
                    'label': c.get('label', ''),
                    'node_ids': c.get('node_ids', []),
                    'centroid_node_id': c.get('centroid_node_id', ''),
                }
                for c in clusters
            ]

            # Compute cluster quality metrics
            graph = GraphService.get_project_graph(project_id)
            cluster_quality = ClusteringService.compute_cluster_quality(
                clusters, graph['edges'],
            )

            summary.status = SummaryStatus.FULL
            summary.sections = sections
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
