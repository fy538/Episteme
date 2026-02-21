# Plan 9: Decision Capture + Outcome Tracking

## Goal
Close the investigation loop. When a case reaches the "ready" stage, users should be able to **record their decision** — what they decided, why, and what could go wrong. After deciding, they can **track outcomes** over time to learn from their decision-making process. This is the capstone feature that makes Episteme a complete decision support system.

---

## Architecture Overview

```
Case reaches stage=ready
        ↓
CaseHome shows "Record Your Decision" button (ContextPanel, ready stage)
        ↓
User clicks → DecisionCaptureModal opens
        ↓
User fills: decision text, key reasons, confidence, caveats,
           which assumptions were validated, outcome check date
        ↓
Submit → POST /cases/{id}/record-decision/
        ↓
Backend: DecisionService.record_decision()
  - Creates DecisionRecord
  - Sets Case.status = 'decided'
  - Emits DECISION_RECORDED event
        ↓
CaseHome re-renders with DecisionSummaryView
        ↓
[Later] Outcome check date approaches
        ↓
OutcomeCheckBanner appears: "How did it go?"
        ↓
User adds outcome note → POST /cases/{id}/outcome-note/
        ↓
Note appended to DecisionRecord.outcome_notes
```

---

## Current State

| Component | File | Status |
|-----------|------|--------|
| CaseStatus | `backend/apps/cases/models.py:12-15` | DRAFT, ACTIVE, ARCHIVED — **no DECIDED** |
| CaseStage | `backend/apps/cases/models.py:40-45` | exploring → investigating → synthesizing → ready |
| Case model | `backend/apps/cases/models.py:48-` | Has decision_question, constraints, success_criteria, stakeholders, premortem_text |
| CaseHome | `frontend/src/components/workspace/case/CaseHome.tsx` | Stage-adaptive ContextPanel; at ready stage shows criteria checklist, premortem, judgment summary |
| ContextPanel | CaseHome.tsx (line 580) | Renders `SynthesizingContext` at ready stage — judgment tools but **no decision capture** |
| EventType | `backend/apps/events/models.py:20+` | Comprehensive events for case lifecycle, inquiry, evidence — **no decision events** |
| Celery tasks | `backend/apps/cases/tasks.py` | `run_case_extraction_pipeline` — pattern for periodic tasks |
| PremortemModal | `frontend/src/components/cases/PremortemModal.tsx` | Modal pattern to follow — overlay, form, save, close |
| Case type (frontend) | `frontend/src/lib/types/case.ts:22-62` | `status: 'draft' \| 'active' \| 'archived'` — no 'decided' |

**Key gap:** There's no way to formally record a decision or track its outcomes. The "ready" stage is a dead end — users reach it but have no completion action.

---

## Implementation Steps

### Step 1: Create `DecisionRecord` Model

**File: `backend/apps/cases/models.py`**

Add a new model linked 1:1 to Case:

```python
class DecisionRecord(UUIDModel, TimestampedModel):
    """
    Records the user's final decision for a case.

    Created when user transitions from investigating to decided.
    Tracks the decision rationale, confidence, and long-term outcomes.
    """
    case = models.OneToOneField(
        Case,
        on_delete=models.CASCADE,
        related_name='decision'
    )
    decision_text = models.TextField(
        help_text="What was decided — the actual decision statement"
    )
    key_reasons = models.JSONField(
        default=list,
        help_text="List of reason strings: why this decision was made"
    )
    confidence_level = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Decision confidence 0-100"
    )
    caveats = models.TextField(
        blank=True,
        help_text="Known risks, conditions, or things to watch for"
    )
    linked_assumption_ids = models.JSONField(
        default=list,
        help_text="UUIDs of assumptions the user marked as validated during decision"
    )
    decided_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the decision was formally recorded"
    )
    outcome_check_date = models.DateField(
        null=True,
        blank=True,
        help_text="When to check back on how the decision played out"
    )
    outcome_notes = models.JSONField(
        default=list,
        help_text="List of outcome observations: [{date, note, sentiment}]"
    )
```

**Run migration:** `python manage.py makemigrations cases`

---

### Step 2: Add `DECIDED` to `CaseStatus`

**File: `backend/apps/cases/models.py`**

```python
class CaseStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    ACTIVE = 'active', 'Active'
    DECIDED = 'decided', 'Decided'        # NEW
    ARCHIVED = 'archived', 'Archived'
```

This is the terminal investigation state. A decided case is still fully accessible (all data preserved), but the investigation is considered complete.

**Note:** Add `'decided'` to `CaseService.ALLOWED_UPDATE_FIELDS` status transitions, and validate that status can only transition to 'decided' from 'active' (not from 'draft' or 'archived').

---

### Step 3: Add Decision Event Types

**File: `backend/apps/events/models.py`**

Add to the EventType choices:

```python
class EventType(models.TextChoices):
    # ... existing events ...

    # Decision lifecycle
    DECISION_RECORDED = 'DecisionRecorded', 'Decision Recorded'
    OUTCOME_NOTE_ADDED = 'OutcomeNoteAdded', 'Outcome Note Added'
```

These go in the PROVENANCE section since they're human-readable case history events.

---

### Step 4: Create `DecisionService`

**File (NEW): `backend/apps/cases/decision_service.py`**

Follow the `CaseService` pattern — `@staticmethod`, `@transaction.atomic`, EventService for provenance:

```python
"""
Decision service — record decisions and track outcomes
"""
import logging
import uuid
from datetime import date
from typing import Optional, List

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .models import Case, CaseStatus, DecisionRecord
from apps.events.services import EventService
from apps.events.models import EventType, ActorType

logger = logging.getLogger(__name__)


class DecisionService:
    """Service for recording decisions and tracking outcomes."""

    @staticmethod
    @transaction.atomic
    def record_decision(
        user: User,
        case_id: uuid.UUID,
        decision_text: str,
        key_reasons: List[str],
        confidence_level: int,
        caveats: str = "",
        linked_assumption_ids: Optional[List[str]] = None,
        outcome_check_date: Optional[date] = None,
    ) -> DecisionRecord:
        """
        Record a formal decision for a case.

        Creates a DecisionRecord, transitions the case to DECIDED status,
        and emits a DECISION_RECORDED provenance event.

        Args:
            user: User recording the decision
            case_id: Case UUID
            decision_text: What was decided
            key_reasons: List of reason strings
            confidence_level: 0-100 confidence
            caveats: Optional risk notes
            linked_assumption_ids: UUIDs of validated assumptions
            outcome_check_date: Optional date to check outcomes

        Returns:
            Created DecisionRecord

        Raises:
            Case.DoesNotExist: If case not found or not owned by user
            ValueError: If case already has a decision
        """
        case = Case.objects.select_for_update().get(id=case_id, user=user)

        # Validate: can't decide twice
        if hasattr(case, 'decision') and case.decision:
            raise ValueError("Case already has a recorded decision")

        # Validate: case must be active (not draft or archived)
        if case.status not in (CaseStatus.ACTIVE,):
            raise ValueError(f"Cannot record decision on case with status '{case.status}'")

        # Create decision record
        record = DecisionRecord.objects.create(
            case=case,
            decision_text=decision_text,
            key_reasons=key_reasons,
            confidence_level=max(0, min(100, confidence_level)),
            caveats=caveats,
            linked_assumption_ids=linked_assumption_ids or [],
            outcome_check_date=outcome_check_date,
        )

        # Transition case status
        case.status = CaseStatus.DECIDED
        case.save(update_fields=['status', 'updated_at'])

        # Emit provenance event
        EventService.append(
            event_type=EventType.DECISION_RECORDED,
            payload={
                'decision_id': str(record.id),
                'decision_text': decision_text[:200],  # Truncate for event payload
                'confidence_level': confidence_level,
                'reasons_count': len(key_reasons),
                'has_outcome_check': outcome_check_date is not None,
            },
            actor_type=ActorType.USER,
            actor_id=user.id,
            case_id=case.id,
        )

        logger.info(
            "decision_recorded",
            extra={
                'case_id': str(case_id),
                'confidence': confidence_level,
                'reasons_count': len(key_reasons),
            }
        )

        return record

    @staticmethod
    @transaction.atomic
    def add_outcome_note(
        user: User,
        case_id: uuid.UUID,
        note: str,
        sentiment: str = "neutral",
    ) -> DecisionRecord:
        """
        Add an outcome observation to an existing decision.

        Args:
            user: User adding the note
            case_id: Case UUID
            note: Outcome observation text
            sentiment: 'positive', 'neutral', or 'negative'

        Returns:
            Updated DecisionRecord

        Raises:
            DecisionRecord.DoesNotExist: If no decision exists for this case
        """
        case = Case.objects.get(id=case_id, user=user)
        record = DecisionRecord.objects.select_for_update().get(case=case)

        # Append note
        notes = record.outcome_notes or []
        notes.append({
            'date': timezone.now().isoformat(),
            'note': note,
            'sentiment': sentiment,
        })
        record.outcome_notes = notes
        record.save(update_fields=['outcome_notes', 'updated_at'])

        # Emit event
        EventService.append(
            event_type=EventType.OUTCOME_NOTE_ADDED,
            payload={
                'decision_id': str(record.id),
                'note_index': len(notes) - 1,
                'sentiment': sentiment,
            },
            actor_type=ActorType.USER,
            actor_id=user.id,
            case_id=case.id,
        )

        return record
```

---

### Step 5: API Endpoints

**File: `backend/apps/cases/views.py`**

Add `@action` methods to `CaseViewSet`:

```python
from rest_framework.decorators import action

class CaseViewSet(viewsets.ModelViewSet):
    # ... existing methods ...

    @action(detail=True, methods=['post'], url_path='record-decision')
    def record_decision(self, request, pk=None):
        """Record a formal decision for this case."""
        serializer = RecordDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            record = DecisionService.record_decision(
                user=request.user,
                case_id=pk,
                **serializer.validated_data,
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=400)

        return Response(DecisionRecordSerializer(record).data, status=201)

    @action(detail=True, methods=['get'], url_path='decision')
    def get_decision(self, request, pk=None):
        """Get the decision record for this case."""
        case = self.get_object()
        try:
            record = case.decision
        except DecisionRecord.DoesNotExist:
            return Response({'detail': 'No decision recorded'}, status=404)

        return Response(DecisionRecordSerializer(record).data)

    @action(detail=True, methods=['post'], url_path='outcome-note')
    def add_outcome_note(self, request, pk=None):
        """Add an outcome observation note."""
        serializer = OutcomeNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            record = DecisionService.add_outcome_note(
                user=request.user,
                case_id=pk,
                **serializer.validated_data,
            )
        except DecisionRecord.DoesNotExist:
            return Response({'error': 'No decision recorded for this case'}, status=404)

        return Response(DecisionRecordSerializer(record).data)
```

**File: `backend/apps/cases/serializers.py`**

Add serializers:

```python
class RecordDecisionSerializer(serializers.Serializer):
    """Input serializer for recording a decision."""
    decision_text = serializers.CharField(max_length=5000)
    key_reasons = serializers.ListField(
        child=serializers.CharField(max_length=1000),
        max_length=20,
    )
    confidence_level = serializers.IntegerField(min_value=0, max_value=100)
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
            'id', 'case', 'decision_text', 'key_reasons',
            'confidence_level', 'caveats', 'linked_assumption_ids',
            'decided_at', 'outcome_check_date', 'outcome_notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class OutcomeNoteSerializer(serializers.Serializer):
    """Input serializer for adding an outcome note."""
    note = serializers.CharField(max_length=5000)
    sentiment = serializers.ChoiceField(
        choices=['positive', 'neutral', 'negative'],
        default='neutral',
    )
```

---

### Step 6: Frontend Types + API Methods

**File: `frontend/src/lib/types/case.ts`**

Add `'decided'` to Case status and define DecisionRecord:

```typescript
export interface Case {
    // ...existing fields...
    status: 'draft' | 'active' | 'decided' | 'archived';   // ADD 'decided'
    // ...
}

export interface DecisionRecord {
    id: string;
    case: string;
    decision_text: string;
    key_reasons: string[];
    confidence_level: number;      // 0-100
    caveats: string;
    linked_assumption_ids: string[];
    decided_at: string;
    outcome_check_date?: string;   // ISO date
    outcome_notes: OutcomeNote[];
    created_at: string;
    updated_at: string;
}

export interface OutcomeNote {
    date: string;
    note: string;
    sentiment: 'positive' | 'neutral' | 'negative';
}
```

**File: `frontend/src/lib/api/cases.ts`**

Add API methods:

```typescript
export const casesAPI = {
    // ...existing methods...

    async recordDecision(caseId: string, data: {
        decision_text: string;
        key_reasons: string[];
        confidence_level: number;
        caveats?: string;
        linked_assumption_ids?: string[];
        outcome_check_date?: string;
    }): Promise<DecisionRecord> {
        return apiClient.post<DecisionRecord>(`/cases/${caseId}/record-decision/`, data);
    },

    async getDecision(caseId: string): Promise<DecisionRecord> {
        return apiClient.get<DecisionRecord>(`/cases/${caseId}/decision/`);
    },

    async addOutcomeNote(caseId: string, data: {
        note: string;
        sentiment?: 'positive' | 'neutral' | 'negative';
    }): Promise<DecisionRecord> {
        return apiClient.post<DecisionRecord>(`/cases/${caseId}/outcome-note/`, data);
    },
};
```

---

### Step 7: `DecisionCaptureModal`

**File (NEW): `frontend/src/components/cases/DecisionCaptureModal.tsx`**

Multi-field form for recording the decision. Follow `PremortemModal` pattern (overlay, keyboard handling, error state):

```typescript
interface DecisionCaptureModalProps {
    caseId: string;
    isOpen: boolean;
    onClose: () => void;
    onSaved?: () => void;
    assumptions?: PlanAssumption[];  // Pass from CaseHome for checklist
}
```

**Form layout:**

```
┌──────────────────────────────────────────────────┐
│  Record Your Decision                            │
│                                                  │
│  What have you decided? *                        │
│  ┌──────────────────────────────────────────┐    │
│  │ [textarea]                               │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  Why? (Key reasons) *                            │
│  ┌──────────────────────────────────────────┐    │
│  │ 1. [reason input]                 [✕]    │    │
│  │ 2. [reason input]                 [✕]    │    │
│  │ + Add reason                             │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  How confident are you?                          │
│  ──●──────────────────── 72%                     │
│                                                  │
│  What could go wrong? (optional)                 │
│  ┌──────────────────────────────────────────┐    │
│  │ [textarea]                               │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  Which assumptions were validated?               │
│  ☑ Market size assumption                        │
│  ☑ Technical feasibility                         │
│  ☐ Competitor response timing                    │
│                                                  │
│  When should we check back? (optional)           │
│  [date picker: ____-__-__]                       │
│                                                  │
│            [Cancel]  [Record Decision]           │
└──────────────────────────────────────────────────┘
```

**Key interactions:**
- Decision text + at least one reason required for submit
- Confidence slider (0-100) with color: green (>70), amber (40-70), red (<40)
- Assumption checklist: shows all plan assumptions with their current status, user checks which ones were validated through investigation
- Date picker: suggests common intervals (30 days, 60 days, 90 days) as quick-select options
- Submit: calls `casesAPI.recordDecision()` → on success calls `onSaved()` → parent refreshes data

---

### Step 8: `DecisionSummaryView`

**File (NEW): `frontend/src/components/cases/DecisionSummaryView.tsx`**

Read-only display of the recorded decision, shown in CaseHome when status === 'decided':

```typescript
interface DecisionSummaryViewProps {
    decision: DecisionRecord;
    assumptions?: PlanAssumption[];  // For cross-referencing validated assumptions
    onAddOutcomeNote?: (note: string, sentiment: string) => void;
}
```

**Layout:**

```
┌──────────────────────────────────────────────────────┐
│  Decision                                             │
│  ─────────────────────────────────────────────────── │
│                                                       │
│  "We should proceed with Option B because..."        │
│                                                       │
│  Key Reasons                                          │
│  1. Market timing aligns with Q2 launch               │
│  2. Engineering team capacity available                │
│  3. Competitive landscape favorable                   │
│                                                       │
│  ┌─────────┐                                         │
│  │  72%    │ Confidence                               │
│  │  ████   │                                         │
│  └─────────┘                                         │
│                                                       │
│  Caveats                                              │
│  "Depends on supplier agreement closing by March"     │
│                                                       │
│  Assumptions Validated                                │
│  ✓ Market size assumption                             │
│  ✓ Technical feasibility                              │
│  ✗ Competitor response timing (untested)              │
│                                                       │
│  ─────────────────────────────────────────────────── │
│  Outcome Timeline                                     │
│                                                       │
│  📅 Mar 15, 2026 — Positive                          │
│  "Initial results promising, team morale high"        │
│                                                       │
│  📅 Apr 1, 2026 — Neutral                            │
│  "Supplier agreement delayed by 2 weeks"              │
│                                                       │
│  [+ Add Outcome Note]                                 │
│                                                       │
│  Next check: May 15, 2026 (in 32 days)               │
└──────────────────────────────────────────────────────┘
```

**"Add Outcome Note" flow:**
- Click button → expands inline form (textarea + sentiment radio: positive/neutral/negative)
- Submit → `casesAPI.addOutcomeNote(caseId, { note, sentiment })`
- New note appears at bottom of timeline

---

### Step 9: `OutcomeCheckBanner`

**File (NEW): `frontend/src/components/cases/OutcomeCheckBanner.tsx`**

Sticky reminder banner that appears when the outcome check date is approaching:

```typescript
interface OutcomeCheckBannerProps {
    caseTitle: string;
    outcomeCheckDate: string;  // ISO date
    onAddNote: () => void;     // Scrolls to outcome note form or opens modal
    onDismiss: () => void;     // Hides banner for this session
}
```

**Show when:**
- `case.status === 'decided'`
- `decision.outcome_check_date` is within 7 days of today (or past due)

**Visual:**
```
┌────────────────────────────────────────────────────────────────┐
│ ⏰ Time to check: How did your decision on "Project B" turn  │
│    out?                                        [Add Note] [✕] │
└────────────────────────────────────────────────────────────────┘
```

- Amber background for upcoming, red for overdue
- "Add Note" button opens inline form or scrolls to DecisionSummaryView
- Dismiss button hides for current session (stores in sessionStorage)

---

### Step 10: Update CaseHome for Decision Flow

**File: `frontend/src/components/workspace/case/CaseHome.tsx`**

Three changes:

**10a. Add "Record Decision" button at ready stage:**

In the `SynthesizingContext` component (renders at synthesizing + ready stages), add a prominent CTA when stage is `ready`:

```typescript
// In SynthesizingContext render, at the bottom:
{stage === 'ready' && (
    <div className="mt-6 p-4 rounded-lg border-2 border-accent-200 dark:border-accent-800 bg-accent-50/50 dark:bg-accent-900/10 text-center">
        <p className="text-sm text-neutral-700 dark:text-neutral-300 mb-3">
            Your investigation is complete. Ready to record your decision?
        </p>
        <Button onClick={() => setShowDecisionCapture(true)}>
            Record Your Decision
        </Button>
    </div>
)}
```

**10b. Show DecisionSummaryView when decided:**

In the main CaseHome render, check case status:

```typescript
// If case is decided, show DecisionSummaryView instead of ContextPanel
{data.case.status === 'decided' && decision ? (
    <>
        <OutcomeCheckBanner ... />
        <DecisionSummaryView
            decision={decision}
            assumptions={content?.assumptions}
            onAddOutcomeNote={handleAddOutcomeNote}
        />
    </>
) : (
    <ContextPanel ... />
)}
```

**10c. Fetch decision data:**

Add decision fetch to `useCaseHome` or fetch separately:

```typescript
const [decision, setDecision] = useState<DecisionRecord | null>(null);

useEffect(() => {
    if (data?.case.status === 'decided') {
        casesAPI.getDecision(caseId)
            .then(setDecision)
            .catch(() => {}); // Silently fail — decision might not exist yet
    }
}, [data?.case.status, caseId]);
```

**10d. DecisionCaptureModal integration:**

```typescript
const [showDecisionCapture, setShowDecisionCapture] = useState(false);

// In render:
<DecisionCaptureModal
    caseId={caseId}
    isOpen={showDecisionCapture}
    onClose={() => setShowDecisionCapture(false)}
    onSaved={() => {
        setShowDecisionCapture(false);
        queryClient.invalidateQueries({ queryKey: ['case-home', caseId] });
    }}
    assumptions={content?.assumptions}
/>
```

Pass `setShowDecisionCapture` down to `ContextPanel` → `SynthesizingContext` via a callback prop.

---

### Step 11: Celery Periodic Task (Optional, Low Priority)

**File: `backend/apps/cases/tasks.py`**

Add a daily task that checks for upcoming outcome check dates:

```python
from celery import shared_task
from datetime import date, timedelta

@shared_task
def check_outcome_reminders():
    """
    Daily task: find decided cases where outcome_check_date is
    approaching (within 7 days) or past due, and create notifications.
    """
    from .models import DecisionRecord

    upcoming = DecisionRecord.objects.filter(
        outcome_check_date__lte=date.today() + timedelta(days=7),
        outcome_check_date__gte=date.today() - timedelta(days=30),  # Don't nag beyond 30 days
    ).select_related('case')

    for record in upcoming:
        # Check if user already added a recent note (within last 7 days)
        recent_notes = [
            n for n in (record.outcome_notes or [])
            if n.get('date', '') > (date.today() - timedelta(days=7)).isoformat()
        ]
        if not recent_notes:
            # TODO: Create notification (depends on notification system)
            # For now, log it
            logger.info(
                "outcome_check_due",
                extra={
                    'case_id': str(record.case_id),
                    'check_date': str(record.outcome_check_date),
                }
            )
```

**Register in celery beat schedule** (in settings or celery config):

```python
CELERY_BEAT_SCHEDULE = {
    'check-outcome-reminders': {
        'task': 'apps.cases.tasks.check_outcome_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
}
```

This step is lower priority — can be deferred until a notification system exists.

---

## Key Files to Modify

| File | Change |
|------|--------|
| `backend/apps/cases/models.py` | Add `DecisionRecord` model, `DECIDED` to CaseStatus |
| `backend/apps/cases/migrations/XXXX_...` | Auto-generated migration |
| `backend/apps/events/models.py` | Add `DECISION_RECORDED`, `OUTCOME_NOTE_ADDED` event types |
| `backend/apps/cases/decision_service.py` | NEW — `DecisionService` with `record_decision()`, `add_outcome_note()` |
| `backend/apps/cases/serializers.py` | Add `RecordDecisionSerializer`, `DecisionRecordSerializer`, `OutcomeNoteSerializer` |
| `backend/apps/cases/views.py` | Add `record-decision`, `decision`, `outcome-note` actions to CaseViewSet |
| `backend/apps/cases/tasks.py` | Add `check_outcome_reminders` periodic task |
| `frontend/src/lib/types/case.ts` | Add `'decided'` status, `DecisionRecord` interface, `OutcomeNote` interface |
| `frontend/src/lib/api/cases.ts` | Add `recordDecision()`, `getDecision()`, `addOutcomeNote()` |
| `frontend/src/components/cases/DecisionCaptureModal.tsx` | NEW — multi-field decision form |
| `frontend/src/components/cases/DecisionSummaryView.tsx` | NEW — decision display + outcome timeline |
| `frontend/src/components/cases/OutcomeCheckBanner.tsx` | NEW — reminder banner |
| `frontend/src/components/workspace/case/CaseHome.tsx` | Integrate decision button, summary view, banner |

**Not modified (reused as-is):**
- `CaseService` — decision is a separate service, doesn't modify case creation
- `PlanService` — plan is not affected by decision recording
- Investigation views — all remain accessible after decision (read-only state)
- `PremortemModal` — pattern reference only, not modified

---

## Edge Cases

1. **Case not at ready stage:** "Record Decision" button only appears at `stage=ready`; backend validates `case.status == 'active'`
2. **Decision already recorded:** Backend returns 400 "Case already has a recorded decision"; frontend hides the button after decision exists
3. **Outcome check in far future:** No banner shown until within 7 days; user can still add notes manually anytime
4. **Case archived after decision:** Decision data preserved; outcome notes can still be added (or not — check status in service)
5. **Empty key_reasons:** Frontend requires at least one reason; backend `ListField` with `min_length=1`
6. **Very old outcome checks:** Stop showing banner after 30 days past the check date (avoid eternal nag)
7. **Multiple outcome notes:** Append to JSON array, render chronologically in timeline
8. **Assumption cross-reference:** `linked_assumption_ids` may reference assumptions that were later deleted from plan — show gracefully ("2 of 5 assumptions validated; 3 no longer tracked")
9. **Decided case in cases list:** Update cases list page status filter to include 'decided' option with appropriate badge color (blue or purple)

---

## Testing

1. **Backend unit:** `DecisionService.record_decision()` creates record, transitions status, emits event
2. **Backend unit:** `DecisionService.add_outcome_note()` appends to notes list
3. **Backend unit:** Cannot record decision on draft/archived case (ValueError)
4. **Backend unit:** Cannot record decision twice (ValueError)
5. **Backend API:** POST `/cases/{id}/record-decision/` returns 201 with valid data, 400 on duplicate
6. **Backend API:** GET `/cases/{id}/decision/` returns 404 when no decision, 200 when exists
7. **Frontend unit:** DecisionCaptureModal validates required fields (decision text, at least 1 reason)
8. **Frontend unit:** DecisionSummaryView renders all fields including outcome timeline
9. **Frontend unit:** OutcomeCheckBanner shows only when date is within 7 days
10. **Integration:** Create case → investigate → ready → record decision → verify status changed to 'decided'
11. **Integration:** Record decision with outcome_check_date → wait for date → verify banner appears
