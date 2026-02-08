"""
Tests for assumption status cascade.

Covers:
- recompute_assumption_status: evidence balance -> status mapping
- cascade_from_evidence_change: full cascade (status + plan sync + grounding)
- _on_evidence_m2m_changed: Django signal handler triggering cascade
"""
import uuid
from unittest.mock import patch, MagicMock

from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User

from apps.events.models import Event, EventType, ActorType
from apps.projects.models import Project, Document, DocumentChunk, Evidence
from apps.signals.models import Signal, SignalType, SignalSourceType, AssumptionStatus
from apps.signals.assumption_cascade import (
    recompute_assumption_status,
    cascade_from_evidence_change,
    _on_evidence_m2m_changed,
)


class CascadeTestMixin:
    """Shared helpers for creating test data."""

    def _create_user(self):
        return User.objects.create_user(
            username=f'testuser-{uuid.uuid4().hex[:8]}',
            password='testpass123',
        )

    def _create_event(self, case=None, event_type=EventType.SIGNAL_EXTRACTED):
        return Event.objects.create(
            actor_type=ActorType.SYSTEM,
            type=event_type,
            payload={},
            case_id=case.id if case else None,
        )

    def _create_project(self, user):
        return Project.objects.create(title='Test Project', user=user)

    def _create_case(self, user, project):
        from apps.cases.models import Case
        event = self._create_event(event_type=EventType.CASE_CREATED)
        return Case.objects.create(
            title='Test Case',
            user=user,
            project=project,
            position='Test',
            created_from_event_id=event.id,
        )

    def _create_assumption_signal(self, case, status='untested'):
        event = self._create_event(case=case)
        return Signal.objects.create(
            type=SignalType.ASSUMPTION,
            text='Test assumption',
            normalized_text='test assumption',
            confidence=0.8,
            case=case,
            event=event,
            sequence_index=0,
            dedupe_key=uuid.uuid4().hex[:16],
            assumption_status=status,
        )

    def _create_claim_signal(self, case):
        event = self._create_event(case=case)
        return Signal.objects.create(
            type=SignalType.CLAIM,
            text='Test claim',
            normalized_text='test claim',
            confidence=0.8,
            case=case,
            event=event,
            sequence_index=0,
            dedupe_key=uuid.uuid4().hex[:16],
        )

    def _create_evidence(self, user, project):
        """Create a projects.Evidence item (with required document/chunk FKs)."""
        doc = Document.objects.create(
            title='Test Doc',
            source_type='text',
            content_text='Test content',
            project=project,
            user=user,
        )
        chunk = DocumentChunk.objects.create(
            document=doc,
            chunk_index=0,
            chunk_text='Some evidence text',
            token_count=10,
        )
        return Evidence.objects.create(
            text='Evidence text',
            type='fact',
            chunk=chunk,
            document=doc,
            extraction_confidence=0.9,
        )

    def _link_evidence_silently(self, evidence, signal, relationship='supports'):
        """
        Link evidence to signal via the M2M through table directly,
        bypassing the Django m2m_changed signal handler.
        Use this when you want to set up M2M state for a test without
        triggering the cascade.
        """
        if relationship == 'supports':
            through_model = Evidence.supports_signals.through
            through_model.objects.create(evidence_id=evidence.id, signal_id=signal.id)
        else:
            through_model = Evidence.contradicts_signals.through
            through_model.objects.create(evidence_id=evidence.id, signal_id=signal.id)


class TestRecomputeAssumptionStatus(CascadeTestMixin, TestCase):
    """Test recompute_assumption_status() evidence balance logic."""

    def setUp(self):
        self.user = self._create_user()
        self.project = self._create_project(self.user)
        self.case = self._create_case(self.user, self.project)

    def test_non_assumption_returns_none(self):
        """Non-assumption signals are skipped."""
        signal = self._create_claim_signal(self.case)
        result = recompute_assumption_status(signal)
        self.assertIsNone(result)

    def test_no_evidence_returns_untested(self):
        """Assumption with no evidence should be untested."""
        signal = self._create_assumption_signal(self.case, status='untested')
        result = recompute_assumption_status(signal)
        # Status unchanged, returns old status
        self.assertEqual(result, 'untested')

    def test_only_supporting_evidence_returns_confirmed(self):
        """Assumption with only supporting evidence should be confirmed."""
        signal = self._create_assumption_signal(self.case, status='untested')
        evidence = self._create_evidence(self.user, self.project)
        evidence.supports_signals.add(signal)

        result = recompute_assumption_status(signal)
        self.assertEqual(result, 'confirmed')
        signal.refresh_from_db()
        self.assertEqual(signal.assumption_status, 'confirmed')

    def test_only_contradicting_evidence_returns_refuted(self):
        """Assumption with only contradicting evidence should be refuted."""
        signal = self._create_assumption_signal(self.case, status='untested')
        evidence = self._create_evidence(self.user, self.project)
        evidence.contradicts_signals.add(signal)

        result = recompute_assumption_status(signal)
        self.assertEqual(result, 'refuted')
        signal.refresh_from_db()
        self.assertEqual(signal.assumption_status, 'refuted')

    def test_more_supporting_than_contradicting_returns_confirmed(self):
        """Majority supporting evidence -> confirmed."""
        signal = self._create_assumption_signal(self.case, status='untested')
        e1 = self._create_evidence(self.user, self.project)
        e2 = self._create_evidence(self.user, self.project)
        e3 = self._create_evidence(self.user, self.project)
        e1.supports_signals.add(signal)
        e2.supports_signals.add(signal)
        e3.contradicts_signals.add(signal)

        result = recompute_assumption_status(signal)
        self.assertEqual(result, 'confirmed')

    def test_more_contradicting_than_supporting_returns_challenged(self):
        """Majority contradicting evidence -> challenged."""
        signal = self._create_assumption_signal(self.case, status='untested')
        e1 = self._create_evidence(self.user, self.project)
        e2 = self._create_evidence(self.user, self.project)
        e3 = self._create_evidence(self.user, self.project)
        e1.contradicts_signals.add(signal)
        e2.contradicts_signals.add(signal)
        e3.supports_signals.add(signal)

        result = recompute_assumption_status(signal)
        self.assertEqual(result, 'challenged')

    def test_equal_evidence_returns_challenged(self):
        """Equal supporting and contradicting -> challenged."""
        signal = self._create_assumption_signal(self.case, status='untested')
        e1 = self._create_evidence(self.user, self.project)
        e2 = self._create_evidence(self.user, self.project)
        e1.supports_signals.add(signal)
        e2.contradicts_signals.add(signal)

        result = recompute_assumption_status(signal)
        self.assertEqual(result, 'challenged')

    def test_unchanged_status_does_not_save(self):
        """If the computed status matches the current status, no save occurs."""
        signal = self._create_assumption_signal(self.case, status='untested')
        # No evidence -> untested, same as current status
        with patch.object(Signal, 'save') as mock_save:
            result = recompute_assumption_status(signal)
            mock_save.assert_not_called()
        self.assertEqual(result, 'untested')

    def test_status_change_saves_to_db(self):
        """Status change should persist to database."""
        signal = self._create_assumption_signal(self.case, status='untested')
        evidence = self._create_evidence(self.user, self.project)
        evidence.supports_signals.add(signal)

        recompute_assumption_status(signal)

        # Re-fetch from DB to confirm persistence
        signal_from_db = Signal.objects.get(id=signal.id)
        self.assertEqual(signal_from_db.assumption_status, 'confirmed')


class TestCascadeFromEvidenceChange(CascadeTestMixin, TestCase):
    """Test cascade_from_evidence_change() orchestration."""

    def setUp(self):
        self.user = self._create_user()
        self.project = self._create_project(self.user)
        self.case = self._create_case(self.user, self.project)

    def test_no_status_change_skips_downstream(self):
        """When status doesn't change, plan sync and grounding are skipped."""
        signal = self._create_assumption_signal(self.case, status='untested')
        # No evidence -> stays untested
        result = cascade_from_evidence_change(signal)
        self.assertFalse(result['status_changed'])
        self.assertFalse(result['plan_synced'])
        self.assertFalse(result['grounding_updated'])

    @patch('apps.cases.brief_grounding.BriefGroundingEngine.evolve_brief')
    @patch('apps.signals.assumption_cascade._sync_status_to_plan')
    def test_status_change_triggers_plan_sync_and_grounding(
        self, mock_sync, mock_evolve
    ):
        """Status change triggers plan sync and grounding recalculation."""
        signal = self._create_assumption_signal(self.case, status='untested')
        evidence = self._create_evidence(self.user, self.project)
        # Use silent link to avoid triggering the cascade via the M2M handler
        self._link_evidence_silently(evidence, signal, 'supports')

        result = cascade_from_evidence_change(signal)

        self.assertTrue(result['status_changed'])
        self.assertEqual(result['new_status'], 'confirmed')
        mock_sync.assert_called_once_with(self.case.id, signal, 'confirmed')
        mock_evolve.assert_called_once_with(self.case.id)

    @patch('apps.cases.brief_grounding.BriefGroundingEngine.evolve_brief')
    @patch('apps.signals.assumption_cascade._sync_status_to_plan')
    def test_uses_explicit_case_id_over_signal_case(
        self, mock_sync, mock_evolve
    ):
        """Explicit case_id parameter takes precedence over signal.case_id."""
        signal = self._create_assumption_signal(self.case, status='untested')
        evidence = self._create_evidence(self.user, self.project)
        self._link_evidence_silently(evidence, signal, 'supports')

        other_case_id = uuid.uuid4()
        result = cascade_from_evidence_change(signal, case_id=other_case_id)

        self.assertTrue(result['status_changed'])
        mock_sync.assert_called_once_with(other_case_id, signal, 'confirmed')
        mock_evolve.assert_called_once_with(other_case_id)

    @patch('apps.cases.brief_grounding.BriefGroundingEngine.evolve_brief')
    @patch('apps.signals.assumption_cascade._sync_status_to_plan', side_effect=Exception('plan error'))
    def test_plan_sync_failure_does_not_block_grounding(
        self, mock_sync, mock_evolve
    ):
        """Plan sync failure is logged but grounding still runs."""
        signal = self._create_assumption_signal(self.case, status='untested')
        evidence = self._create_evidence(self.user, self.project)
        self._link_evidence_silently(evidence, signal, 'supports')

        result = cascade_from_evidence_change(signal)

        self.assertTrue(result['status_changed'])
        self.assertFalse(result['plan_synced'])
        # Grounding should still be called
        mock_evolve.assert_called_once_with(self.case.id)

    def test_signal_without_case_skips_downstream(self):
        """Signal with no case_id skips plan sync and grounding."""
        event = self._create_event()
        signal = Signal.objects.create(
            type=SignalType.ASSUMPTION,
            text='Orphan assumption',
            normalized_text='orphan assumption',
            confidence=0.8,
            event=event,
            sequence_index=0,
            dedupe_key=uuid.uuid4().hex[:16],
            assumption_status='untested',
        )
        evidence = self._create_evidence(self.user, self.project)
        self._link_evidence_silently(evidence, signal, 'supports')

        result = cascade_from_evidence_change(signal)

        # Status changed but no downstream effects (no case)
        self.assertTrue(result['status_changed'])
        self.assertEqual(result['new_status'], 'confirmed')
        self.assertFalse(result['plan_synced'])
        self.assertFalse(result['grounding_updated'])


class TestOnEvidenceM2MChanged(CascadeTestMixin, TransactionTestCase):
    """
    Test _on_evidence_m2m_changed handler.

    Uses TransactionTestCase because M2M signal handlers fire within
    the caller's transaction and we need to test the full flow.
    """

    def setUp(self):
        self.user = self._create_user()
        self.project = self._create_project(self.user)
        self.case = self._create_case(self.user, self.project)

    @patch('apps.signals.assumption_cascade.cascade_from_evidence_change')
    def test_post_add_triggers_cascade(self, mock_cascade):
        """Adding a signal to supports_signals triggers cascade."""
        signal = self._create_assumption_signal(self.case)
        evidence = self._create_evidence(self.user, self.project)

        # Directly call the handler to test its logic
        _on_evidence_m2m_changed(
            sender=Evidence.supports_signals.through,
            instance=evidence,
            action='post_add',
            pk_set={signal.id},
        )

        mock_cascade.assert_called_once()
        called_signal = mock_cascade.call_args[0][0]
        self.assertEqual(called_signal.id, signal.id)

    @patch('apps.signals.assumption_cascade.cascade_from_evidence_change')
    def test_post_remove_triggers_cascade(self, mock_cascade):
        """Removing a signal from supports_signals triggers cascade."""
        signal = self._create_assumption_signal(self.case)
        evidence = self._create_evidence(self.user, self.project)

        _on_evidence_m2m_changed(
            sender=Evidence.supports_signals.through,
            instance=evidence,
            action='post_remove',
            pk_set={signal.id},
        )

        mock_cascade.assert_called_once()

    @patch('apps.signals.assumption_cascade.cascade_from_evidence_change')
    def test_pre_add_does_not_trigger_cascade(self, mock_cascade):
        """pre_add action should not trigger cascade."""
        signal = self._create_assumption_signal(self.case)
        evidence = self._create_evidence(self.user, self.project)

        _on_evidence_m2m_changed(
            sender=Evidence.supports_signals.through,
            instance=evidence,
            action='pre_add',
            pk_set={signal.id},
        )

        mock_cascade.assert_not_called()

    @patch('apps.signals.assumption_cascade.cascade_from_evidence_change')
    def test_non_assumption_signals_are_skipped(self, mock_cascade):
        """Non-assumption signals in pk_set should not trigger cascade."""
        claim_signal = self._create_claim_signal(self.case)
        evidence = self._create_evidence(self.user, self.project)

        _on_evidence_m2m_changed(
            sender=Evidence.supports_signals.through,
            instance=evidence,
            action='post_add',
            pk_set={claim_signal.id},
        )

        # cascade not called because Signal.objects.filter(type='Assumption') returns nothing
        mock_cascade.assert_not_called()

    @patch('apps.signals.assumption_cascade.cascade_from_evidence_change')
    def test_empty_pk_set_does_nothing(self, mock_cascade):
        """Empty pk_set (e.g. post_clear with no affected signals) does nothing."""
        evidence = self._create_evidence(self.user, self.project)

        _on_evidence_m2m_changed(
            sender=Evidence.supports_signals.through,
            instance=evidence,
            action='post_add',
            pk_set=set(),
        )

        mock_cascade.assert_not_called()

    @patch('apps.signals.assumption_cascade.cascade_from_evidence_change')
    def test_none_pk_set_does_nothing(self, mock_cascade):
        """None pk_set (from post_clear) does nothing."""
        evidence = self._create_evidence(self.user, self.project)

        _on_evidence_m2m_changed(
            sender=Evidence.supports_signals.through,
            instance=evidence,
            action='post_clear',
            pk_set=None,
        )

        mock_cascade.assert_not_called()


class TestM2MIntegration(CascadeTestMixin, TransactionTestCase):
    """
    Integration test: adding evidence via M2M triggers the full cascade
    through the Django signal handler wired in SignalsConfig.ready().
    """

    def setUp(self):
        self.user = self._create_user()
        self.project = self._create_project(self.user)
        self.case = self._create_case(self.user, self.project)

    def test_adding_supporting_evidence_updates_assumption_status(self):
        """
        End-to-end: evidence.supports_signals.add(signal) changes
        assumption_status from untested to confirmed.
        """
        signal = self._create_assumption_signal(self.case, status='untested')
        evidence = self._create_evidence(self.user, self.project)

        # This should trigger the M2M signal -> cascade
        evidence.supports_signals.add(signal)

        signal.refresh_from_db()
        self.assertEqual(signal.assumption_status, 'confirmed')

    def test_removing_all_evidence_reverts_to_untested(self):
        """
        Removing all evidence from an assumption reverts it to untested.
        """
        signal = self._create_assumption_signal(self.case, status='untested')
        evidence = self._create_evidence(self.user, self.project)

        # Add then remove
        evidence.supports_signals.add(signal)
        signal.refresh_from_db()
        self.assertEqual(signal.assumption_status, 'confirmed')

        evidence.supports_signals.remove(signal)
        signal.refresh_from_db()
        self.assertEqual(signal.assumption_status, 'untested')

    def test_mixed_evidence_results_in_challenged(self):
        """
        Adding both supporting and contradicting evidence -> challenged.
        """
        signal = self._create_assumption_signal(self.case, status='untested')
        e1 = self._create_evidence(self.user, self.project)
        e2 = self._create_evidence(self.user, self.project)

        e1.supports_signals.add(signal)
        e2.contradicts_signals.add(signal)

        signal.refresh_from_db()
        self.assertEqual(signal.assumption_status, 'challenged')
