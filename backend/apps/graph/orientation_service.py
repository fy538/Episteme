"""
OrientationService — generates lens-based orientations from hierarchical
clustering results.

Orchestrates the two-step pipeline:
1. Lens detection: scores 6 lens types against theme summaries (1 LLM call)
2. Orientation synthesis: generates findings + angles through the chosen lens (1 LLM call)

Creates ProjectInsight records for each finding and exploration angle,
linked back to a ProjectOrientation metadata record.
"""
import copy
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from asgiref.sync import sync_to_async
from django.db import transaction

logger = logging.getLogger(__name__)


class OrientationService:
    """Generates lens-based orientations from hierarchical clustering results."""

    @staticmethod
    async def generate_orientation(
        project_id: uuid.UUID,
        hierarchy_id: uuid.UUID,
    ):
        """
        Full orientation pipeline.

        1. Load hierarchy tree → extract Level 2 theme summaries
        2. Load active cases for context
        3. Lens detection (1 LLM call)
        4. Select primary + optional secondary lens
        5. Create ProjectOrientation(status=GENERATING)
        6. Orientation synthesis (1 LLM call)
        7. Supersede old orientation insights
        8. Create ProjectInsight records (one at a time for SSE streaming)
        9. Mark orientation status=READY

        Returns:
            ProjectOrientation instance.
        """
        from apps.common.llm_providers.factory import get_llm_provider
        from apps.intelligence.orientation_prompts import (
            build_lens_detection_prompt,
            build_orientation_synthesis_prompt,
        )
        from .models import (
            ClusterHierarchy, HierarchyStatus,
            ProjectOrientation, OrientationStatus,
            ProjectInsight, InsightType, InsightSource, InsightStatus,
        )

        start_time = time.time()

        # ── 1. Load hierarchy and extract themes ─────────────────
        hierarchy = await sync_to_async(
            ClusterHierarchy.objects.filter(
                id=hierarchy_id,
                status=HierarchyStatus.READY,
            ).first
        )()

        if not hierarchy or not hierarchy.tree:
            raise ValueError(f"Hierarchy {hierarchy_id} not found or has no tree")

        themes = OrientationService._extract_theme_summaries(hierarchy.tree)

        if not themes:
            raise ValueError(f"No themes found in hierarchy {hierarchy_id}")

        # ── 2. Load active cases for context ─────────────────────
        case_context = await OrientationService._load_case_context(project_id)

        # ── 3. Lens detection ────────────────────────────────────
        provider = get_llm_provider('fast')

        system_prompt, user_prompt = build_lens_detection_prompt(themes)
        detection_response = await provider.generate(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            max_tokens=200,
            temperature=0.2,
        )

        lens_scores = OrientationService._parse_lens_scores(detection_response)

        if not lens_scores:
            # Fallback: default to positions_and_tensions
            lens_scores = {'positions_and_tensions': 0.7}
            logger.warning(
                "lens_detection_parse_failed_using_default",
                extra={'project_id': str(project_id)},
            )

        # ── 4. Select lenses ─────────────────────────────────────
        primary_lens, secondary_lens, primary_confidence = (
            OrientationService._select_lenses(lens_scores)
        )

        # ── 5. Create orientation record (GENERATING) ────────────
        # Mark old orientations as not current
        await sync_to_async(
            lambda: ProjectOrientation.objects.filter(
                project_id=project_id, is_current=True,
            ).update(is_current=False)
        )()

        orientation = await sync_to_async(ProjectOrientation.objects.create)(
            project_id=project_id,
            hierarchy=hierarchy,
            status=OrientationStatus.GENERATING,
            lens_type=primary_lens,
            lens_scores=lens_scores,
            is_current=True,
        )

        try:
            # ── 6. Orientation synthesis ─────────────────────────
            system_prompt, user_prompt = build_orientation_synthesis_prompt(
                lens_type=primary_lens,
                theme_summaries=themes,
                case_context=case_context if case_context else None,
            )

            synthesis_response = await provider.generate(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
                max_tokens=1200,
                temperature=0.3,
            )

            parsed = OrientationService._parse_orientation(synthesis_response)

            if not parsed:
                raise ValueError("Failed to parse orientation synthesis response")

            # Update lead text and secondary lens
            orientation.lead_text = parsed.get('lead', '')

            if parsed.get('secondary_lens'):
                orientation.secondary_lens = parsed['secondary_lens'].get('type', '')
                orientation.secondary_lens_reason = parsed['secondary_lens'].get('reason', '')
            elif secondary_lens:
                orientation.secondary_lens = secondary_lens
                orientation.secondary_lens_reason = (
                    f"Your documents also score well for the "
                    f"{secondary_lens.replace('_', ' ')} lens."
                )

            # ── 7. Supersede old orientation insights ────────────
            await OrientationService._supersede_old_insights(
                project_id, orientation.id,
            )

            # ── 8. Create insights one at a time (for SSE) ──────
            display_order = 0

            for finding in parsed.get('findings', []):
                finding_type = finding.get('type', 'pattern')
                # Map to InsightType values
                type_map = {
                    'consensus': InsightType.CONSENSUS,
                    'tension': InsightType.TENSION,
                    'gap': InsightType.GAP,
                    'weak_evidence': InsightType.WEAK_EVIDENCE,
                    'pattern': InsightType.PATTERN,
                }
                insight_type = type_map.get(finding_type, InsightType.PATTERN)

                action = finding.get('action', 'none')
                action_type = action if action in ('discuss', 'research') else ''

                source_ids = [
                    s.strip()
                    for s in finding.get('source_themes', '').split(',')
                    if s.strip()
                ]

                await sync_to_async(ProjectInsight.objects.create)(
                    project_id=project_id,
                    orientation=orientation,
                    insight_type=insight_type,
                    title=finding.get('heading', ''),
                    content=finding.get('body', ''),
                    source_type=InsightSource.ORIENTATION,
                    source_cluster_ids=source_ids,
                    status=InsightStatus.ACTIVE,
                    confidence=primary_confidence,
                    display_order=display_order,
                    action_type=action_type,
                )
                display_order += 1

            # Create exploration angles
            for angle in parsed.get('angles', []):
                angle_type = angle.get('type', 'discuss')
                await sync_to_async(ProjectInsight.objects.create)(
                    project_id=project_id,
                    orientation=orientation,
                    insight_type=InsightType.EXPLORATION_ANGLE,
                    title=angle.get('title', ''),
                    content='',  # Generated on demand when clicked
                    source_type=InsightSource.ORIENTATION,
                    source_cluster_ids=[],
                    status=InsightStatus.ACTIVE,
                    confidence=0.0,
                    display_order=display_order,
                    action_type=angle_type if angle_type in ('discuss', 'read') else 'discuss',
                )
                display_order += 1

            # ── 9. Mark orientation as READY ─────────────────────
            elapsed_ms = int((time.time() - start_time) * 1000)
            orientation.status = OrientationStatus.READY
            orientation.generation_metadata = {
                'duration_ms': elapsed_ms,
                'finding_count': len(parsed.get('findings', [])),
                'angle_count': len(parsed.get('angles', [])),
                'primary_lens_confidence': primary_confidence,
            }
            await sync_to_async(orientation.save)(
                update_fields=[
                    'status', 'lead_text', 'lens_scores',
                    'secondary_lens', 'secondary_lens_reason',
                    'generation_metadata', 'updated_at',
                ],
            )

            logger.info(
                "orientation_generated",
                extra={
                    'project_id': str(project_id),
                    'lens_type': primary_lens,
                    'confidence': primary_confidence,
                    'findings': len(parsed.get('findings', [])),
                    'angles': len(parsed.get('angles', [])),
                    'duration_ms': elapsed_ms,
                },
            )

            return orientation

        except Exception:
            # Mark orientation as failed
            orientation.status = OrientationStatus.FAILED
            await sync_to_async(orientation.save)(
                update_fields=['status', 'updated_at'],
            )
            raise

    @staticmethod
    async def generate_exploration_content(insight_id: uuid.UUID) -> str:
        """
        On-demand generation for a clicked exploration angle.

        Loads the angle's parent orientation + hierarchy themes,
        runs a single LLM call, stores result in insight.content.

        Returns:
            Generated content string.
        """
        from apps.common.llm_providers.factory import get_llm_provider
        from apps.intelligence.orientation_prompts import build_exploration_angle_prompt
        from .models import ProjectInsight, ClusterHierarchy, HierarchyStatus

        insight = await sync_to_async(
            ProjectInsight.objects.select_related('orientation', 'orientation__hierarchy').get
        )(id=insight_id)

        if not insight.orientation or not insight.orientation.hierarchy:
            raise ValueError(f"Insight {insight_id} has no linked orientation/hierarchy")

        hierarchy = insight.orientation.hierarchy
        themes = OrientationService._extract_theme_summaries(hierarchy.tree)
        lens_type = insight.orientation.lens_type

        provider = get_llm_provider('fast')
        system_prompt, user_prompt = build_exploration_angle_prompt(
            angle_title=insight.title,
            theme_summaries=themes,
            lens_type=lens_type,
        )

        content = await provider.generate(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            max_tokens=300,
            temperature=0.3,
        )

        # Store generated content
        insight.content = content.strip()
        await sync_to_async(insight.save)(update_fields=['content', 'updated_at'])

        return insight.content

    # ── Conversational editing (diff merge + apply) ────────────

    @staticmethod
    def merge_orientation_diff(
        current_findings: list,
        current_angles: list,
        current_lead: str,
        current_lens: str,
        diff_data: dict,
    ) -> dict:
        """
        Merge an LLM-generated diff into the current orientation state.

        Pure function — no DB access, no side effects.
        Same pattern as PlanService.merge_plan_diff.

        Returns:
            { lead_text, lens_type, findings: [...], angles: [...] }
        """
        findings = copy.deepcopy(current_findings)
        angles = copy.deepcopy(current_angles)
        lead_text = current_lead
        lens_type = current_lens

        # Lead text update
        if diff_data.get('update_lead'):
            lead_text = diff_data['update_lead']

        # Lens change suggestion
        if diff_data.get('suggest_lens_change'):
            lens_type = diff_data['suggest_lens_change']

        # Update existing findings
        finding_map = {str(f.get('id', '')): f for f in findings if f.get('id')}
        for update in diff_data.get('updated_findings', []):
            fid = str(update.get('id', ''))
            if fid and fid in finding_map:
                f = finding_map[fid]
                if 'title' in update:
                    f['title'] = update['title']
                if 'content' in update:
                    f['content'] = update['content']
                if 'status' in update:
                    f['status'] = update['status']

        # Remove findings
        removed_ids = set(str(rid) for rid in diff_data.get('removed_finding_ids', []))
        if removed_ids:
            findings = [f for f in findings if str(f.get('id', '')) not in removed_ids]

        # Add new findings
        for new_f in diff_data.get('added_findings', []):
            findings.append({
                'id': str(uuid.uuid4()),
                'insight_type': new_f.get('type', 'pattern'),
                'title': new_f.get('title', ''),
                'content': new_f.get('content', ''),
                'status': 'active',
                'confidence': 0.7,
                'action_type': new_f.get('action_type', ''),
            })

        # Remove angles
        removed_angle_ids = set(str(rid) for rid in diff_data.get('removed_angle_ids', []))
        if removed_angle_ids:
            angles = [a for a in angles if str(a.get('id', '')) not in removed_angle_ids]

        # Add new angles
        for new_a in diff_data.get('added_angles', []):
            angles.append({
                'id': str(uuid.uuid4()),
                'title': new_a.get('title', ''),
            })

        return {
            'lead_text': lead_text,
            'lens_type': lens_type,
            'findings': findings,
            'angles': angles,
        }

    @staticmethod
    @transaction.atomic
    def apply_orientation_edits(
        project_id,
        orientation_id,
        proposed_state: dict,
        diff_summary: str,
        diff_data: dict,
        user_id,
    ):
        """
        Persist a proposed orientation state to the database.

        Called when the user accepts an orientation diff from the chat card.

        Operations:
        - Update ProjectOrientation lead_text and lens_type if changed
        - Update existing findings (title, content, status)
        - Create new findings
        - Set removed findings to DISMISSED status
        - Same for angles

        Returns:
            ProjectOrientation instance
        """
        from .models import (
            ProjectOrientation, ProjectInsight,
            InsightType, InsightSource, InsightStatus,
        )

        orientation = ProjectOrientation.objects.get(
            id=orientation_id, project_id=project_id,
        )

        update_fields = ['updated_at']

        # Update lead text
        new_lead = proposed_state.get('lead_text')
        if new_lead and new_lead != orientation.lead_text:
            orientation.lead_text = new_lead
            update_fields.append('lead_text')

        # Update lens type
        new_lens = proposed_state.get('lens_type')
        if new_lens and new_lens != orientation.lens_type:
            orientation.lens_type = new_lens
            update_fields.append('lens_type')

        orientation.save(update_fields=update_fields)

        # Process findings
        existing_insights = {
            str(i.id): i
            for i in ProjectInsight.objects.filter(
                orientation=orientation,
            ).exclude(insight_type=InsightType.EXPLORATION_ANGLE)
        }

        # Dismiss removed findings
        removed_ids = set(str(rid) for rid in diff_data.get('removed_finding_ids', []))
        for rid in removed_ids:
            if rid in existing_insights:
                insight = existing_insights[rid]
                insight.status = InsightStatus.DISMISSED
                insight.save(update_fields=['status', 'updated_at'])

        # Update existing findings
        for update in diff_data.get('updated_findings', []):
            fid = str(update.get('id', ''))
            if fid in existing_insights:
                insight = existing_insights[fid]
                fields = ['updated_at']
                if 'title' in update:
                    insight.title = update['title']
                    fields.append('title')
                if 'content' in update:
                    insight.content = update['content']
                    fields.append('content')
                if 'status' in update:
                    insight.status = update['status']
                    fields.append('status')
                insight.save(update_fields=fields)

        # Add new findings
        type_map = {
            'consensus': InsightType.CONSENSUS,
            'tension': InsightType.TENSION,
            'gap': InsightType.GAP,
            'weak_evidence': InsightType.WEAK_EVIDENCE,
            'pattern': InsightType.PATTERN,
        }
        max_order = max(
            (i.display_order for i in existing_insights.values()),
            default=-1,
        )
        for new_f in diff_data.get('added_findings', []):
            max_order += 1
            insight_type = type_map.get(new_f.get('type', 'pattern'), InsightType.PATTERN)
            action = new_f.get('action_type', '')
            ProjectInsight.objects.create(
                project_id=project_id,
                orientation=orientation,
                insight_type=insight_type,
                title=new_f.get('title', ''),
                content=new_f.get('content', ''),
                source_type=InsightSource.ORIENTATION,
                status=InsightStatus.ACTIVE,
                confidence=0.7,
                display_order=max_order,
                action_type=action if action in ('discuss', 'research') else '',
            )

        # Process angles
        existing_angles = {
            str(a.id): a
            for a in ProjectInsight.objects.filter(
                orientation=orientation,
                insight_type=InsightType.EXPLORATION_ANGLE,
            )
        }

        # Dismiss removed angles
        removed_angle_ids = set(str(rid) for rid in diff_data.get('removed_angle_ids', []))
        for rid in removed_angle_ids:
            if rid in existing_angles:
                angle = existing_angles[rid]
                angle.status = InsightStatus.DISMISSED
                angle.save(update_fields=['status', 'updated_at'])

        # Add new angles
        angle_order = max(
            (a.display_order for a in existing_angles.values()),
            default=max_order,
        )
        for new_a in diff_data.get('added_angles', []):
            angle_order += 1
            ProjectInsight.objects.create(
                project_id=project_id,
                orientation=orientation,
                insight_type=InsightType.EXPLORATION_ANGLE,
                title=new_a.get('title', ''),
                content='',
                source_type=InsightSource.ORIENTATION,
                status=InsightStatus.ACTIVE,
                confidence=0.0,
                display_order=angle_order,
                action_type='discuss',
            )

        orientation.refresh_from_db()
        return orientation

    # ── Internal helpers ─────────────────────────────────────────

    @staticmethod
    def _extract_theme_summaries(tree: dict) -> List[Dict[str, Any]]:
        """
        Extract Level 2 theme nodes from the hierarchy tree.

        Handles cases where root has Level 1 children directly (few clusters).
        Returns list of dicts with id, label, summary, coverage_pct, document_ids.
        """
        if not tree or not tree.get('children'):
            return []

        themes = []
        for child in tree['children']:
            level = child.get('level', 0)
            if level >= 2 or (level == 1 and not any(
                c.get('level', 0) >= 2 for c in tree['children']
            )):
                themes.append({
                    'id': child.get('id', ''),
                    'label': child.get('label', 'Unknown'),
                    'summary': child.get('summary', ''),
                    'coverage_pct': child.get('coverage_pct', 0),
                    'document_ids': child.get('document_ids', []),
                })

        return themes

    @staticmethod
    async def _load_case_context(
        project_id: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        """Load active cases for context injection into orientation synthesis."""
        from apps.cases.models import Case

        cases = await sync_to_async(list)(
            Case.objects.filter(
                project_id=project_id,
                status__in=['draft', 'active'],
            ).values('title', 'decision_question')[:5]
        )
        return [
            {
                'title': c['title'],
                'decision_question': c.get('decision_question', ''),
            }
            for c in cases
            if c.get('decision_question')
        ]

    @staticmethod
    def _parse_lens_scores(response: str) -> Dict[str, float]:
        """
        Parse <lens_scores> XML from LLM response.

        Returns dict of {lens_type: score} or empty dict on failure.
        """
        scores = {}
        pattern = r'<lens\s+type="([^"]+)"\s+score="([^"]+)"\s*/>'
        matches = re.findall(pattern, response)

        for lens_type, score_str in matches:
            try:
                score = float(score_str)
                if 0.0 <= score <= 1.0:
                    scores[lens_type] = score
            except (ValueError, TypeError):
                continue

        return scores

    @staticmethod
    def _select_lenses(
        scores: Dict[str, float],
    ) -> Tuple[str, Optional[str], float]:
        """
        Select primary and optional secondary lens from scores.

        Returns:
            (primary_lens, secondary_lens_or_None, primary_confidence)
        """
        if not scores:
            return 'positions_and_tensions', None, 0.5

        sorted_lenses = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary_lens = sorted_lenses[0][0]
        primary_confidence = sorted_lenses[0][1]

        secondary_lens = None
        if len(sorted_lenses) > 1:
            second = sorted_lenses[1]
            gap = primary_confidence - second[1]
            # Surface secondary if it scores above 0.5 and gap is < 0.25
            if second[1] > 0.5 and gap < 0.25:
                secondary_lens = second[0]

        return primary_lens, secondary_lens, primary_confidence

    @staticmethod
    def _parse_orientation(response: str) -> Optional[Dict[str, Any]]:
        """
        Parse <orientation> XML into structured dict.

        Returns:
            {
                'lead': str,
                'findings': [{type, heading, body, source_themes, action}],
                'angles': [{title, type}],
                'secondary_lens': {type, reason} or None,
            }
            or None on failure.
        """
        result: Dict[str, Any] = {
            'lead': '',
            'findings': [],
            'angles': [],
            'secondary_lens': None,
        }

        # Extract lead
        lead_match = re.search(r'<lead>(.*?)</lead>', response, re.DOTALL)
        if lead_match:
            result['lead'] = lead_match.group(1).strip()

        # Extract findings
        finding_pattern = re.compile(
            r'<finding\s+type="([^"]+)">\s*'
            r'<heading>(.*?)</heading>\s*'
            r'<body>(.*?)</body>\s*'
            r'<source_themes>(.*?)</source_themes>\s*'
            r'<action>(.*?)</action>\s*'
            r'</finding>',
            re.DOTALL,
        )
        for match in finding_pattern.finditer(response):
            result['findings'].append({
                'type': match.group(1).strip(),
                'heading': match.group(2).strip(),
                'body': match.group(3).strip(),
                'source_themes': match.group(4).strip(),
                'action': match.group(5).strip(),
            })

        # Extract angles
        angle_pattern = re.compile(
            r'<angle\s+type="([^"]+)">(.*?)</angle>',
            re.DOTALL,
        )
        for match in angle_pattern.finditer(response):
            result['angles'].append({
                'type': match.group(1).strip(),
                'title': match.group(2).strip(),
            })

        # Extract secondary lens (optional)
        secondary_pattern = re.compile(
            r'<secondary_lens\s+type="([^"]+)"\s+reason="([^"]+)"\s*/?>',
        )
        secondary_match = secondary_pattern.search(response)
        if secondary_match:
            result['secondary_lens'] = {
                'type': secondary_match.group(1).strip(),
                'reason': secondary_match.group(2).strip(),
            }

        # Validate: must have at least a lead or findings
        if not result['lead'] and not result['findings']:
            logger.warning(
                "orientation_parse_empty",
                extra={'response_length': len(response)},
            )
            return None

        return result

    @staticmethod
    async def _supersede_old_insights(
        project_id: uuid.UUID,
        new_orientation_id: uuid.UUID,
    ):
        """
        Mark previous orientation insights as superseded — unless user engaged.

        Engaged = status in (acknowledged, researching, resolved).
        Those are preserved so the user doesn't lose their work.
        """
        from .models import ProjectInsight, InsightSource, InsightStatus

        await sync_to_async(
            lambda: ProjectInsight.objects.filter(
                project_id=project_id,
                source_type=InsightSource.ORIENTATION,
                status=InsightStatus.ACTIVE,
            ).exclude(
                orientation_id=new_orientation_id,
            ).update(
                status=InsightStatus.SUPERSEDED,
            )
        )()
