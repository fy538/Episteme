"""
Case serializers
"""
from rest_framework import serializers
from .models import (
    Case, CaseStatus, StakesLevel,
    InvestigationPlan, PlanVersion, CaseStage,
    DecisionRecord, ResolutionType,
)


class CaseSerializer(serializers.ModelSerializer):
    """Serializer for Case model"""
    based_on_skill_name = serializers.CharField(
        source='based_on_skill.name',
        read_only=True,
        allow_null=True
    )
    became_skill_name = serializers.CharField(
        source='became_skill.name',
        read_only=True,
        allow_null=True
    )
    active_skills_summary = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = [
            'id',
            'title',
            'status',
            'stakes',
            'position',
            # User-stated epistemic confidence
            'user_confidence',
            'user_confidence_updated_at',
            'what_would_change_mind',
            # Premortem
            'premortem_text',
            'premortem_at',
            # Decision Frame fields
            'decision_question',
            'constraints',
            'success_criteria',
            'stakeholders',
            # Relationships
            'user',
            'project',
            'created_from_event_id',
            'created_at',
            'updated_at',
            # Per-case configuration
            'intelligence_config',
            'investigation_preferences',
            # Skill template fields
            'is_skill_template',
            'template_scope',
            'based_on_skill',
            'based_on_skill_name',
            'became_skill',
            'became_skill_name',
            # Active skills
            'active_skills_summary',
            # Flexible metadata (extraction status, analysis, etc.)
            'metadata',
        ]
        read_only_fields = ['id', 'created_from_event_id', 'created_at', 'updated_at', 'user_confidence_updated_at', 'premortem_at']

    def get_active_skills_summary(self, obj):
        """Return lightweight summary of active skills (up to 5).

        Uses prefetched caseactiveskill_set when available (set on
        CaseViewSet.get_queryset) to avoid N+1 queries in list views.
        """
        from apps.cases.models import CaseActiveSkill

        # Try prefetched data first
        try:
            cas_all = obj.caseactiveskill_set.all()
            active = sorted(cas_all, key=lambda a: a.order)[:5]
        except AttributeError:
            active = list(
                CaseActiveSkill.objects
                .filter(case=obj)
                .select_related('skill')
                .order_by('order')[:5]
            )
        return [
            {
                'id': str(a.skill_id),
                'name': a.skill.name,
                'domain': a.skill.domain,
            }
            for a in active
        ]


class CaseWithDecisionSerializer(CaseSerializer):
    """Extended serializer for case list views with decision lifecycle data.

    Adds plan_stage, decision_summary, and risk_indicator fields needed
    by the project Cases page to show decision lifecycle status.
    """
    plan_stage = serializers.SerializerMethodField()
    decision_summary = serializers.SerializerMethodField()
    risk_indicator = serializers.SerializerMethodField()

    class Meta(CaseSerializer.Meta):
        fields = CaseSerializer.Meta.fields + [
            'plan_stage',
            'decision_summary',
            'risk_indicator',
        ]

    def get_plan_stage(self, obj):
        """Current investigation plan stage."""
        try:
            return obj.plan.stage
        except (InvestigationPlan.DoesNotExist, AttributeError):
            return 'exploring'

    def get_decision_summary(self, obj):
        """For decided cases: resolution type, decided_at, outcome status."""
        try:
            dr = obj.decision
        except (DecisionRecord.DoesNotExist, AttributeError):
            return None

        outcome_status = 'pending'
        if dr.outcome_check_date:
            from datetime import date, timedelta
            today = date.today()
            if dr.outcome_check_date <= today:
                # Check if there's a recent outcome note
                has_recent_note = False
                if dr.outcome_notes:
                    latest = dr.outcome_notes[-1]
                    note_date_str = latest.get('date', '')
                    if note_date_str:
                        try:
                            note_date = date.fromisoformat(note_date_str[:10])
                            has_recent_note = (today - note_date) < timedelta(days=7)
                        except (ValueError, TypeError):
                            pass

                if has_recent_note:
                    sentiment = dr.outcome_notes[-1].get('sentiment', 'neutral')
                    outcome_status = sentiment
                else:
                    outcome_status = 'overdue'
            else:
                outcome_status = 'pending'

        return {
            'resolution_type': dr.resolution_type,
            'decided_at': dr.decided_at.isoformat() if dr.decided_at else None,
            'outcome_check_date': str(dr.outcome_check_date) if dr.outcome_check_date else None,
            'outcome_status': outcome_status,
        }

    def get_risk_indicator(self, obj):
        """High-risk untested assumption count from current plan version."""
        try:
            plan = obj.plan
            latest_version = (
                PlanVersion.objects
                .filter(plan=plan)
                .order_by('-version_number')
                .values_list('content', flat=True)
                .first()
            )
            if not latest_version:
                return 0

            assumptions = latest_version.get('assumptions', [])
            return sum(
                1 for a in assumptions
                if a.get('risk_level') == 'high' and a.get('status') == 'untested'
            )
        except (InvestigationPlan.DoesNotExist, AttributeError):
            return 0


class CreateCaseSerializer(serializers.Serializer):
    """Serializer for creating a new case"""

    title = serializers.CharField(max_length=500)
    position = serializers.CharField(required=False, allow_blank=True, default="")
    stakes = serializers.ChoiceField(
        choices=StakesLevel.choices,
        default=StakesLevel.MEDIUM
    )
    decision_question = serializers.CharField(required=False, allow_blank=True, default="")
    thread_id = serializers.UUIDField(required=False, allow_null=True)
    project_id = serializers.UUIDField(required=False, allow_null=True)  # Phase 2


class UpdateCaseSerializer(serializers.Serializer):
    """Serializer for updating a case"""

    title = serializers.CharField(max_length=500, required=False)
    position = serializers.CharField(required=False)
    stakes = serializers.ChoiceField(choices=StakesLevel.choices, required=False)
    status = serializers.ChoiceField(choices=CaseStatus.choices, required=False)
    # Decision Frame fields
    decision_question = serializers.CharField(required=False, allow_blank=True)
    constraints = serializers.ListField(child=serializers.DictField(), required=False)
    success_criteria = serializers.ListField(child=serializers.DictField(), required=False)
    stakeholders = serializers.ListField(child=serializers.DictField(), required=False)
    # User-stated confidence
    user_confidence = serializers.IntegerField(min_value=0, max_value=100, required=False, allow_null=True)
    what_would_change_mind = serializers.CharField(required=False, allow_blank=True)
    # Per-case configuration
    intelligence_config = serializers.DictField(required=False)
    investigation_preferences = serializers.DictField(required=False)


class CreateCaseFromAnalysisSerializer(serializers.Serializer):
    """Serializer for creating a case from conversation analysis"""

    analysis = serializers.DictField(required=True)
    correlation_id = serializers.UUIDField(required=True)
    user_edits = serializers.DictField(required=False, allow_null=True)


class CaseAnalysisResponseSerializer(serializers.Serializer):
    """Serializer for case analysis response"""

    should_suggest = serializers.BooleanField()
    suggested_title = serializers.CharField()
    suggested_question = serializers.CharField()
    signals_summary = serializers.DictField()
    position_draft = serializers.CharField(required=False)
    key_questions = serializers.ListField(child=serializers.CharField(), required=False)
    assumptions = serializers.ListField(child=serializers.CharField(), required=False)
    constraints = serializers.ListField(child=serializers.DictField(), required=False)
    success_criteria = serializers.ListField(child=serializers.DictField(), required=False)
    confidence = serializers.FloatField(required=False)


class UserConfidenceSerializer(serializers.Serializer):
    """Serializer for setting user confidence"""

    user_confidence = serializers.IntegerField(min_value=0, max_value=100)
    what_would_change_mind = serializers.CharField(required=False, allow_blank=True)


# ===== Investigation Plan Serializers =====

class PlanVersionSerializer(serializers.ModelSerializer):
    """Serializer for plan version snapshots"""

    class Meta:
        model = PlanVersion
        fields = [
            'id', 'version_number', 'content', 'diff_summary', 'diff_data',
            'created_by', 'created_at',
        ]
        read_only_fields = ['id', 'version_number', 'created_at']


class InvestigationPlanSerializer(serializers.ModelSerializer):
    """Serializer for the investigation plan with inline current content"""

    current_content = serializers.SerializerMethodField()

    class Meta:
        model = InvestigationPlan
        fields = [
            'id', 'case', 'stage', 'current_version', 'position_statement',
            'current_content', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'case', 'current_version', 'created_at', 'updated_at']

    def get_current_content(self, obj):
        """Inline the current version's content for convenience."""
        try:
            version = obj.versions.get(version_number=obj.current_version)
            return version.content
        except PlanVersion.DoesNotExist:
            return None


class PlanStageUpdateSerializer(serializers.Serializer):
    """Serializer for updating the investigation stage"""

    stage = serializers.ChoiceField(choices=CaseStage.choices)
    rationale = serializers.CharField(required=False, default='')


class PlanRestoreSerializer(serializers.Serializer):
    """Serializer for restoring a previous plan version"""

    version_number = serializers.IntegerField(min_value=1)


class PlanDiffProposalSerializer(serializers.Serializer):
    """Serializer for accepting a proposed plan diff"""

    content = serializers.DictField()
    diff_summary = serializers.CharField()
    diff_data = serializers.DictField(required=False, allow_null=True)
    trigger_type = serializers.CharField(required=False, default='ai_proposal_accepted')
    generation_context = serializers.DictField(required=False, default=dict)


class AssumptionStatusSerializer(serializers.Serializer):
    """Serializer for updating an assumption's status"""

    status = serializers.ChoiceField(
        choices=['untested', 'confirmed', 'challenged', 'refuted']
    )
    evidence_summary = serializers.CharField(required=False, default='')


class CriterionStatusSerializer(serializers.Serializer):
    """Serializer for updating a decision criterion"""

    is_met = serializers.BooleanField()


# ===== Decision Record Serializers =====

class RecordDecisionSerializer(serializers.Serializer):
    """Input serializer for recording a decision.

    All fields are optional for the new auto-resolution flow (only
    resolution_type is needed). Legacy callers that send decision_text +
    key_reasons + confidence_level still work through the legacy path.
    """

    resolution_type = serializers.ChoiceField(
        choices=ResolutionType.choices,
        default=ResolutionType.RESOLVED,
        required=False,
    )
    decision_text = serializers.CharField(
        max_length=5000, required=False, allow_blank=True
    )
    key_reasons = serializers.ListField(
        child=serializers.CharField(max_length=1000),
        required=False,
        default=list,
    )
    confidence_level = serializers.IntegerField(
        min_value=0, max_value=100, required=False
    )
    caveats = serializers.CharField(required=False, allow_blank=True, default="")
    linked_assumption_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )
    outcome_check_date = serializers.DateField(required=False, allow_null=True)


class DecisionRecordSerializer(serializers.ModelSerializer):
    """Output serializer for decision records."""

    class Meta:
        model = DecisionRecord
        fields = [
            'id', 'case', 'resolution_type', 'resolution_profile',
            'decision_text', 'key_reasons',
            'caveats', 'linked_assumption_ids',
            'decided_at', 'outcome_check_date', 'outcome_notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class UpdateResolutionSerializer(serializers.Serializer):
    """Input serializer for editing a resolution after creation."""

    decision_text = serializers.CharField(
        max_length=5000, required=False, allow_blank=True
    )
    key_reasons = serializers.ListField(
        child=serializers.CharField(max_length=1000),
        required=False,
    )
    caveats = serializers.CharField(required=False, allow_blank=True)
    outcome_check_date = serializers.DateField(required=False, allow_null=True)


class OutcomeNoteSerializer(serializers.Serializer):
    """Input serializer for adding an outcome note."""

    note = serializers.CharField(max_length=5000)
    sentiment = serializers.ChoiceField(
        choices=['positive', 'neutral', 'negative', 'mixed'],
        default='neutral',
    )