# Plan 8: Case Creation Preview + Companion Bridge Polish

## Goal
Make the `CasePreviewCard` **editable** so users can refine AI analysis before creating a case. Add a **manual case creation** path for users who want to bypass chat analysis. These changes turn the case creation flow from a take-it-or-leave-it decision into a collaborative refinement step.

---

## Architecture Overview

```
Chat conversation reaches decision point
        ↓
analyze_for_case() returns analysis
        ↓
CasePreviewCard renders (NOW EDITABLE)
        ↓
User can edit: title, decision question, questions, assumptions, criteria
        ↓
"Create This Case" → passes user_edits to backend
        ↓
create_case_from_analysis() applies overrides
        ↓
Case created with user's refinements baked in

ALSO:
Project dashboard → "New Case" button
        ↓
QuickCaseModal → title + decision question + stakes
        ↓
create_case() → creates blank case with brief
```

---

## Current State

| Component | File | Status |
|-----------|------|--------|
| CasePreviewCard | `frontend/src/components/chat/cards/CasePreviewCard.tsx` | **Read-only** — displays suggestedTitle, keyQuestions, assumptions, decisionCriteria |
| CasePreviewData type | `frontend/src/lib/types/chat.ts:84-97` | Has suggestedTitle, positionDraft, keyQuestions, assumptions, analysis, decisionCriteria |
| onCreateCase callback | `CasePreviewCardProps` | Passes `(analysis, title)` — **no user_edits** |
| create_case_from_analysis | `backend/apps/cases/services.py:227-404` | Accepts `user_edits: Optional[dict]` — **only uses title override** |
| create_case | `backend/apps/cases/services.py:24-129` | Accepts title, position, stakes, thread_id, project_id — **NO decision_question** |
| CreateCaseSerializer | `backend/apps/cases/serializers.py` | title, position, stakes — **NO decision_question** |

**Key insight:** The `user_edits` parameter already exists in `create_case_from_analysis()` but is only used for title. The infrastructure for editable creation is partially there — we need to expand it.

---

## Implementation Steps

### Step 1: Make CasePreviewCard Editable

**File: `frontend/src/components/chat/cards/CasePreviewCard.tsx`**

Transform the card from read-only display to an editable preview. Add local state for each field, initialized from `card.data`:

```typescript
export function CasePreviewCard({ card, onCreateCase, onAdjust, onDismiss, isCreating }: CasePreviewCardProps) {
    const data = card.data as unknown as CasePreviewData;

    // Editable local state — initialized from AI analysis
    const [editedTitle, setEditedTitle] = useState(data.suggestedTitle);
    const [editedQuestions, setEditedQuestions] = useState<string[]>([...data.keyQuestions]);
    const [editedAssumptions, setEditedAssumptions] = useState<string[]>([...data.assumptions]);
    const [editedCriteria, setEditedCriteria] = useState(
        [...(data.decisionCriteria || [])].map(c => ({ ...c }))
    );
    const [isEditing, setIsEditing] = useState(false);

    const hasEdits = useMemo(() => {
        return editedTitle !== data.suggestedTitle
            || JSON.stringify(editedQuestions) !== JSON.stringify(data.keyQuestions)
            || JSON.stringify(editedAssumptions) !== JSON.stringify(data.assumptions)
            || JSON.stringify(editedCriteria) !== JSON.stringify(data.decisionCriteria);
    }, [editedTitle, editedQuestions, editedAssumptions, editedCriteria, data]);

    // ... render with editable fields
}
```

**For each section, replace static display with editable patterns:**

1. **Title:** Click-to-edit text input
   - Default: shows title as text
   - Click → becomes `<input>` with the title value
   - Blur/Enter → saves, switches back to text display

2. **Key questions:** Editable list
   - Each question: text with hover-reveal edit + delete icons
   - Click edit → inline text input
   - Delete → removes from array
   - "Add question" button at bottom → appends empty string, focuses input

3. **Assumptions:** Same edit/delete/add pattern as questions

4. **Decision criteria:** Each has `criterion` + optional `measurable`
   - Edit: two inputs (criterion text + measurable metric)
   - Delete + add pattern

5. **Visual cues:**
   - "Edited" badge appears when `hasEdits` is true
   - Subtle pencil icon next to section headers
   - Blue left border on edited sections

---

### Step 2: Update onCreateCase Callback to Pass User Edits

**File: `frontend/src/components/chat/cards/CasePreviewCard.tsx`**

Update the "Create This Case" button to pass user edits:

```typescript
// Current:
<Button onClick={() => onCreateCase(analysis, suggestedTitle)}>

// New:
<Button onClick={() => {
    const userEdits = hasEdits ? {
        title: editedTitle,
        key_questions: editedQuestions,
        assumptions: editedAssumptions,
        decision_criteria: editedCriteria,
    } : { title: editedTitle };

    onCreateCase(analysis, editedTitle, userEdits);
}}>
```

**File: `frontend/src/components/chat/cards/CasePreviewCard.tsx` (props)**

```typescript
interface CasePreviewCardProps {
    card: InlineActionCard;
    onCreateCase: (
        analysis: Record<string, unknown>,
        title: string,
        userEdits?: Record<string, unknown>  // NEW
    ) => void;
    onAdjust: () => void;
    onDismiss: () => void;
    isCreating?: boolean;
}
```

**Trace the callback up:** The parent component that renders CasePreviewCard needs to pass `userEdits` through to the API call. Find where `onCreateCase` is defined and ensure it forwards `userEdits` to the `create_case_from_analysis` API call.

---

### Step 3: Backend — Expand `user_edits` Handling

**File: `backend/apps/cases/services.py` — `create_case_from_analysis()`**

Currently only title is extracted from `user_edits`:

```python
# CURRENT (line 255):
title = user_edits.get('title') if user_edits else analysis['suggested_title']
```

Expand to handle all editable fields:

```python
# Apply user edits
title = (user_edits.get('title') if user_edits else None) or analysis['suggested_title']
position = analysis['position_draft']

# Override decision question if provided
decision_question = ''
if user_edits and 'decision_question' in user_edits:
    decision_question = user_edits['decision_question']
elif analysis.get('suggested_question'):
    decision_question = analysis['suggested_question']

# Create case (with decision_question support — Step 4)
case, _ = cls.create_case(
    user=user,
    title=title,
    position=position,
    thread_id=thread_id,
    decision_question=decision_question,  # NEW
)
```

**Override key_questions for inquiry creation (line ~332):**

```python
# Use edited questions if provided, otherwise use analysis
key_questions = analysis.get('key_questions', [])
if user_edits and 'key_questions' in user_edits:
    key_questions = user_edits['key_questions']

for question in key_questions:
    inquiry = InquiryService.create_inquiry(
        case=case,
        title=question,
        elevation_reason=ElevationReason.USER_CREATED,
        description="Auto-created from conversation analysis"
    )
    inquiries.append(inquiry)
```

**Override assumptions for brief content (line ~296):**

```python
# Use edited assumptions if provided
assumptions = analysis.get('assumptions', [])
if user_edits and 'assumptions' in user_edits:
    assumptions = user_edits['assumptions']

brief_content = f"""# {title}

## Background
{analysis.get('background_summary', '')}

## Current Position
{position}

## Key Assumptions
{chr(10).join(f"- {a}" for a in assumptions)}

## Open Questions
{chr(10).join(f"- {q}" for q in key_questions)}

---
*Auto-generated from conversation. Edit freely.*
"""
```

**Override decision_criteria for plan creation:**

The `PlanService.create_initial_plan()` call (line ~358) receives `analysis` — override the criteria in the analysis dict before passing:

```python
# Override criteria in analysis before passing to plan service
if user_edits and 'decision_criteria' in user_edits:
    # Merge user-edited criteria into analysis for plan service
    analysis_for_plan = {**analysis, 'decision_criteria': user_edits['decision_criteria']}
else:
    analysis_for_plan = analysis

plan, _plan_version = PlanService.create_initial_plan(
    case=case,
    analysis=analysis_for_plan,
    inquiries=inquiries,
    correlation_id=correlation_id,
)
```

---

### Step 4: Add `decision_question` to `create_case()`

**File: `backend/apps/cases/services.py` — `CaseService.create_case()`**

Add `decision_question` parameter:

```python
@staticmethod
@transaction.atomic
def create_case(
    user: User,
    title: str,
    position: str = "",
    stakes: StakesLevel = StakesLevel.MEDIUM,
    thread_id: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
    decision_question: str = "",  # NEW
) -> tuple[Case, 'WorkingDocument']:
```

After case creation, set the decision_question:

```python
# After WorkingDocumentService.create_case_with_brief():
if decision_question:
    case.decision_question = decision_question
    case.save(update_fields=['decision_question'])
```

**File: `backend/apps/cases/serializers.py`**

Add `decision_question` to `CreateCaseSerializer`:

```python
class CreateCaseSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500)
    position = serializers.CharField(required=False, allow_blank=True, default="")
    stakes = serializers.ChoiceField(choices=StakesLevel.choices, default=StakesLevel.MEDIUM)
    decision_question = serializers.CharField(required=False, allow_blank=True, default="")  # NEW
```

**File: `backend/apps/cases/views.py`**

Pass `decision_question` in `CaseViewSet.create()`:

```python
case, brief = CaseService.create_case(
    user=request.user,
    title=serializer.validated_data['title'],
    position=serializer.validated_data.get('position', ''),
    stakes=serializer.validated_data.get('stakes', StakesLevel.MEDIUM),
    decision_question=serializer.validated_data.get('decision_question', ''),  # NEW
)
```

---

### Step 5: Companion Transfer Indicator

**File (NEW): `frontend/src/components/chat/cards/CompanionTransferIndicator.tsx`**

A small visual block below CasePreviewCard that shows what data will transfer from the conversation to the new case:

```typescript
interface CompanionTransferIndicatorProps {
    analysis: CasePreviewData['analysis'];
}

export function CompanionTransferIndicator({ analysis }: CompanionTransferIndicatorProps) {
    const companionState = (analysis as any)?.companion_state;
    const hasStructure = !!companionState?.structure_type;
    const researchCount = companionState?.research_count ?? 0;

    const items = [
        { label: 'Conversation context', present: true },
        { label: `Research results (${researchCount})`, present: researchCount > 0 },
        { label: `Companion structure (${companionState?.structure_type || ''})`, present: hasStructure },
    ].filter(item => item.present);

    if (items.length <= 1) return null; // Don't show if only basic context

    return (
        <div className="mt-2 px-3 py-2 rounded-md bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200/50 dark:border-neutral-800/50">
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-1.5 font-medium">
                Transfers to case:
            </p>
            <div className="space-y-0.5">
                {items.map((item, i) => (
                    <div key={i} className="text-xs text-neutral-600 dark:text-neutral-300 flex items-center gap-1.5">
                        <span className="text-success-500">&#x2713;</span>
                        <span>{item.label}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
```

Render it inside `CasePreviewCard` just above the `ActionCardFooter`.

---

### Step 6: QuickCaseModal — Manual Case Creation

**File (NEW): `frontend/src/components/workspace/case/QuickCaseModal.tsx`**

Allows users to create a case directly from the project dashboard without going through chat analysis first:

```typescript
interface QuickCaseModalProps {
    isOpen: boolean;
    onClose: () => void;
    onCreated: (caseData: Case) => void;
    projectId: string;
}
```

**Form fields:**
- Title (text input, required)
- Decision question (textarea, optional) — "What are you trying to decide?"
- Stakes (dropdown: Low / Medium / High, default Medium)

**Behavior:**
- Submit → `casesAPI.createCase({ title, decision_question, stakes, project_id: projectId })`
- The API creates a case with blank brief via `CaseService.create_case()` (now with `decision_question` support from Step 4)
- On success → navigate to new case workspace
- Follow `PremortemModal` pattern for modal structure

**Integration point:** Add "New Case" button to the project detail page header or command palette, wired to open this modal.

---

## Key Files to Modify

| File | Change |
|------|--------|
| `frontend/src/components/chat/cards/CasePreviewCard.tsx` | Transform read-only → editable with local state |
| `backend/apps/cases/services.py` | Expand `user_edits` in `create_case_from_analysis()`, add `decision_question` to `create_case()` |
| `backend/apps/cases/serializers.py` | Add `decision_question` to `CreateCaseSerializer` |
| `backend/apps/cases/views.py` | Pass `decision_question` in create action |
| `frontend/src/components/chat/cards/CompanionTransferIndicator.tsx` | NEW — transfer indicator |
| `frontend/src/components/workspace/case/QuickCaseModal.tsx` | NEW — manual case creation |

**Not modified (reused as-is):**
- `ActionCard`, `ActionCardHeader`, `ActionCardFooter` — existing UI components
- `PlanService.create_initial_plan()` — receives analysis dict, handles criteria from it
- `InquiryService.create_inquiry()` — creates inquiries from question strings

---

## Edge Cases

1. **User edits nothing:** `hasEdits` is false, only title is passed (current behavior preserved)
2. **User deletes all questions:** Empty `key_questions` array → no inquiries created (valid — user can add later)
3. **User deletes all assumptions:** Empty assumptions in brief → just shows empty section header
4. **Long question text:** Text inputs should allow multiline (use `<textarea>` for questions)
5. **CasePreviewCard re-render during streaming:** Card appears after analysis completes, so data is stable
6. **QuickCaseModal with no project:** Modal requires `projectId` prop, won't render without it
7. **Concurrent edits in card:** Only one user edits at a time (card is per-session), no conflict possible

---

## Testing

1. **Frontend unit:** CasePreviewCard shows edit controls when clicking edit icon
2. **Frontend unit:** Editing title + clicking "Create" passes `userEdits` to callback
3. **Frontend unit:** Adding/removing questions updates local state correctly
4. **Backend unit:** `create_case_from_analysis()` with `user_edits.key_questions` creates correct inquiries
5. **Backend unit:** `create_case()` with `decision_question` sets field on Case model
6. **Integration:** Chat → analyze → edit preview → create → verify edits appear in case brief
7. **QuickCaseModal:** Create case with title + decision question → verify case has both fields
