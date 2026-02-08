"""
Case serializers
"""
from rest_framework import serializers
from .models import (
    Case, WorkingView, CaseStatus, StakesLevel, ReadinessChecklistItem,
    InvestigationPlan, PlanVersion, CaseStage,
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
            # "What would change your mind" resurface response
            'what_changed_mind_response',
            'what_changed_mind_response_at',
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
        ]
        read_only_fields = ['id', 'created_from_event_id', 'created_at', 'updated_at', 'user_confidence_updated_at', 'what_changed_mind_response_at', 'premortem_at']

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


class WorkingViewSerializer(serializers.ModelSerializer):
    """Serializer for WorkingView model"""
    
    class Meta:
        model = WorkingView
        fields = [
            'id',
            'case',
            'summary_json',
            'based_on_event_id',
            'created_at',
        ]
        read_only_fields = fields


class CreateCaseSerializer(serializers.Serializer):
    """Serializer for creating a new case"""
    
    title = serializers.CharField(max_length=500)
    position = serializers.CharField(required=False, allow_blank=True, default="")
    stakes = serializers.ChoiceField(
        choices=StakesLevel.choices,
        default=StakesLevel.MEDIUM
    )
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


class ReadinessChecklistItemSerializer(serializers.ModelSerializer):
    """Serializer for readiness checklist items"""

    children = serializers.SerializerMethodField()
    blocked_by_ids = serializers.SerializerMethodField()

    class Meta:
        model = ReadinessChecklistItem
        fields = [
            'id',
            'description',
            'is_required',
            'is_complete',
            'completed_at',
            'linked_inquiry',
            'linked_assumption_signal',
            'order',
            'why_important',
            'created_by_ai',
            'completion_note',
            # Phase 2: Hierarchical fields
            'parent',
            'item_type',
            'children',
            'blocked_by_ids',
            # Timestamps
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'completed_at', 'created_at', 'updated_at', 'children', 'blocked_by_ids']

    def get_children(self, obj):
        """Get child items (for hierarchical display)"""
        # Only include children in list views, not detail
        if 'request' in self.context and self.context.get('include_children', True):
            return ReadinessChecklistItemSerializer(
                obj.children.all(),
                many=True,
                context={'include_children': True}
            ).data
        return []

    def get_blocked_by_ids(self, obj):
        """Get IDs of items blocking this one"""
        return [str(item.id) for item in obj.blocked_by.all()]


class CreateChecklistItemSerializer(serializers.Serializer):
    """Serializer for creating a checklist item"""

    description = serializers.CharField()
    is_required = serializers.BooleanField(default=True)
    linked_inquiry = serializers.UUIDField(required=False, allow_null=True)
    linked_assumption_signal = serializers.UUIDField(required=False, allow_null=True)
    # Phase 2
    parent = serializers.UUIDField(required=False, allow_null=True)
    item_type = serializers.ChoiceField(
        choices=['validation', 'investigation', 'analysis', 'stakeholder', 'alternative', 'criteria', 'custom'],
        default='custom',
        required=False
    )


class UpdateChecklistItemSerializer(serializers.Serializer):
    """Serializer for updating a checklist item"""

    description = serializers.CharField(required=False)
    is_required = serializers.BooleanField(required=False)
    is_complete = serializers.BooleanField(required=False)
    order = serializers.IntegerField(required=False)
    # Phase 2
    parent = serializers.UUIDField(required=False, allow_null=True)
    item_type = serializers.ChoiceField(
        choices=['validation', 'investigation', 'analysis', 'stakeholder', 'alternative', 'criteria', 'custom'],
        required=False
    )


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


class AssumptionStatusSerializer(serializers.Serializer):
    """Serializer for updating an assumption's status"""

    status = serializers.ChoiceField(
        choices=['untested', 'confirmed', 'challenged', 'refuted']
    )
    evidence_summary = serializers.CharField(required=False, default='')


class CriterionStatusSerializer(serializers.Serializer):
    """Serializer for updating a decision criterion"""

    is_met = serializers.BooleanField()
