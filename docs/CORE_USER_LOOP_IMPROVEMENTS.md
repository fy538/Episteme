# Core User Loop: Case & Inquiry Experience Improvements

## The Real Product: Making Decisions Better

Skills are configuration. The **core loop** is:
```
Chat → Detect decision → Create case → Investigate (inquiries) → Connect dots → Decide
```

---

## Critical Gaps Identified

### 1. **Post-Case-Creation Void**
After case created, users land on a brief view with no guidance.

**What's missing:**
- No onboarding ("Here's what we auto-created for you")
- Assumptions stored but not highlighted
- Auto-created inquiries buried in a list
- No clear "What should I do next?"

### 2. **Inquiry Workflow Not Prominent**
Inquiries auto-created but users don't notice or use them.

**What's missing:**
- No emphasis on auto-created inquiries
- No "Start investigating" call-to-action
- No explanation of purpose
- Investigation plan exists but buried

### 3. **Connecting Dots Requires Manual Work**
System has the data but doesn't surface connections.

**What's missing:**
- Assumptions in brief not linked to inquiries
- Signals not visually connected to inquiries
- Evidence not aggregated/summarized
- No "here's what's related" suggestions

---

## Proposed Improvements: Focus on Core Loop

### Improvement 1: Post-Creation Onboarding

**After case created, show:**

```
┌─────────────────────────────────────────────────┐
│  ✓ Case Created: FDA Device Approval            │
├─────────────────────────────────────────────────┤
│                                                 │
│  🎯 What We Created for You                     │
│                                                 │
│  ✓ Case Brief (draft outline)                  │
│    └─ Pre-filled with conversation summary     │
│                                                 │
│  ✓ 3 Key Inquiries (auto-detected)             │
│    • What are the FDA pathway options?         │
│    • What timeline should we expect?           │
│    • What are the cost implications?           │
│                                                 │
│  ✓ 4 Untested Assumptions (highlighted)        │
│    • Device is Class II                        │
│    • We have substantial equivalence           │
│    [Click to investigate as inquiry]           │
│                                                 │
│  📍 Next Steps                                  │
│  1. Review auto-created inquiries              │
│  2. Start investigating →[Begin First Inquiry] │
│  3. Gather evidence from documents             │
│                                                 │
│  [Start Guided Workflow] [Skip to Brief]       │
└─────────────────────────────────────────────────┘
```

**Implementation:**
```python
# New endpoint
GET /api/cases/{id}/onboarding/

Returns:
{
    'auto_created': {
        'inquiries': [{title, description, status}],
        'assumptions': [{text, highlighted: true}],
        'brief_sections': ['Background', 'Position', ...]
    },
    'next_steps': [
        {action: 'review_inquiries', completed: false},
        {action: 'start_investigation', completed: false}
    ],
    'first_time_user': bool
}
```

### Improvement 2: Highlight Assumptions in Brief

**Visual treatment:**

```
## Position

We should pursue 510(k) approval for our Class II device.

## Key Assumptions

⚠️ Our device is Class II
   [Validate this] → Creates inquiry

⚠️ We have a valid predicate device
   [Investigate] → Creates inquiry
   
⚠️ Submission timeline is 6 months
   [Challenge this] → Runs critique agent

[These were auto-detected from your conversation]
```

**Implementation:**
```python
# Enhance brief rendering
# backend/apps/cases/serializers.py

class CaseBriefSerializer(serializers.ModelSerializer):
    assumptions_highlighted = serializers.SerializerMethodField()
    
    def get_assumptions_highlighted(self, obj):
        """Extract assumptions from ai_structure for highlighting"""
        assumptions = obj.ai_structure.get('assumptions', [])
        
        return [{
            'text': a,
            'linked_inquiry': self._find_inquiry_for_assumption(obj, a),
            'validated': self._is_validated(obj, a)
        } for a in assumptions]
```

### Improvement 3: Inquiry-First Landing

**When case opens, show inquiries prominently:**

```
┌─────────────────────────────────────────────────┐
│  Case: FDA Device Approval                      │
├─────────────────────────────────────────────────┤
│                                                 │
│  🔍 Active Investigations (3)                   │
│                                                 │
│  1. What are the FDA pathway options?           │
│     Status: OPEN                                │
│     Evidence: 0  Objections: 0                  │
│     [Start Investigation] →                     │
│                                                 │
│  2. What timeline should we expect?             │
│     Status: OPEN                                │
│     [Start Investigation] →                     │
│                                                 │
│  3. What are the cost implications?             │
│     Status: OPEN                                │
│     [Start Investigation] →                     │
│                                                 │
│  [+ Add Inquiry] [Generate from Assumptions]    │
│                                                 │
│  ────────────────────────────────────────────   │
│                                                 │
│  📋 Brief  📊 Evidence Map  💬 Chat             │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Implementation:**
```python
# New view mode: Inquiry Dashboard
GET /api/cases/{id}/inquiry_dashboard/

Returns:
{
    'inquiries': [
        {
            'id': 'uuid',
            'title': '...',
            'status': 'OPEN',
            'evidence_count': 0,
            'objections_count': 0,
            'auto_created': true,
            'next_action': 'start_investigation'
        }
    ],
    'summary': {
        'total': 3,
        'open': 3,
        'investigating': 0,
        'resolved': 0
    },
    'suggested_priorities': ['inquiry1', 'inquiry3', 'inquiry2']  # AI-ranked
}
```

### Improvement 4: "Connect the Dots" Intelligence

**Auto-link related items:**

```python
# New service: ConnectionSuggester
class ConnectionSuggester:
    """Suggest connections between signals, inquiries, evidence"""
    
    @staticmethod
    async def suggest_for_assumption(assumption_text: str, case: Case):
        """Suggest which inquiry to link to, or if new inquiry needed"""
        
        # Check existing inquiries
        inquiries = case.inquiries.filter(status__in=['OPEN', 'INVESTIGATING'])
        
        # Use embeddings to find related inquiry
        # Or use LLM to match
        
        return {
            'should_create_new': bool,
            'existing_match': inquiry_id or None,
            'match_confidence': 0.0-1.0,
            'suggested_title': str  # If creating new
        }
    
    @staticmethod
    async def suggest_evidence_for_inquiry(inquiry: Inquiry):
        """Suggest which documents/chunks might contain evidence"""
        
        # Search vector DB for relevant chunks
        # Return top matches
        
        return {
            'suggested_documents': [...],
            'relevant_chunks': [...],
            'confidence': 0.0-1.0
        }
```

**UI for connections:**

```
In brief, when user hovers over assumption:
┌────────────────────────────────────┐
│ 💡 Connected Items                │
│                                    │
│ This assumption relates to:        │
│ • Inquiry: "What are pathway..."   │
│ • 3 signals mention this           │
│ • Evidence: Document-5.pdf         │
│                                    │
│ [View Connections]                 │
└────────────────────────────────────┘
```

### Improvement 5: Guided Investigation Workflow

**For each inquiry, provide clear path:**

```
Inquiry: "What are the FDA pathway options?"

┌─────────────────────────────────────────────────┐
│  Investigation Status: Not Started              │
├─────────────────────────────────────────────────┤
│                                                 │
│  Suggested Steps:                               │
│  1. ☐ Generate investigation plan               │
│       [Generate] → AI creates research plan    │
│                                                 │
│  2. ☐ Run research agent                        │
│       [Research FDA pathways] → Comprehensive  │
│                                                 │
│  3. ☐ Add evidence from documents               │
│       [Search documents] → Cite sources        │
│                                                 │
│  4. ☐ Consider objections                       │
│       [Generate critique] → Challenge thinking │
│                                                 │
│  5. ☐ Resolve with conclusion                   │
│       [Write conclusion] → Mark resolved       │
│                                                 │
│  [Start Investigation] (marks as INVESTIGATING) │
└─────────────────────────────────────────────────┘
```

**Implementation:**
```python
# Endpoint
POST /api/inquiries/{id}/start_investigation/

# Updates status to INVESTIGATING
# Auto-generates investigation plan if not exists
# Returns guided workflow steps
```

### Improvement 6: Evidence Aggregation View

**Show evidence strength at a glance:**

```
Inquiry: "What timeline should we expect?"

Evidence Summary:
├─ Supporting (3)
│  ├─ "Typical 510(k): 90-180 days" (Credibility: 0.9)
│  ├─ "Our previous: 120 days" (Credibility: 0.95)
│  └─ "Industry average: 4-6 months" (Credibility: 0.8)
│
├─ Contradicting (1)
│  └─ "Complex devices: up to 12 months" (Credibility: 0.7)
│
└─ Neutral (0)

Aggregate Confidence: 0.85 (Strong support for 3-6 month timeline)

[Resolve Inquiry with this evidence]
```

**Implementation:**
```python
# Endpoint
GET /api/inquiries/{id}/evidence_summary/

Returns:
{
    'supporting': [{evidence}, ...],
    'contradicting': [{evidence}, ...],
    'neutral': [{evidence}, ...],
    'aggregate_confidence': 0.85,
    'recommended_conclusion': "Timeline: 3-6 months",
    'strength': 'strong' | 'moderate' | 'weak'
}
```

---

## Revised User Loop (Core Focus)

### Phase 1: Chat & Detection
```
User chats → System detects decision → Suggests case
```
**Status**: ✅ Works well (already implemented)

### Phase 2: Case Creation
```
User confirms → Case + Brief + Inquiries auto-created
```
**Improvements needed**:
- ✅ Add onboarding component
- ✅ Highlight what was auto-created
- ✅ Provide "next steps" guidance

### Phase 3: Investigation (MOST IMPORTANT)
```
User works through inquiries → Gathers evidence → Validates assumptions
```
**Improvements needed**:
- ✅ Make inquiries prominent
- ✅ Guided investigation workflow
- ✅ Auto-suggest evidence from documents
- ✅ Aggregate evidence strength
- ✅ Visual connection mapping

### Phase 4: Synthesis
```
Inquiries resolved → Agent generates brief → User decides
```
**Improvements needed**:
- ✅ Auto-update brief when inquiries resolve
- ✅ Evidence-backed recommendations
- ✅ Confidence scoring

---

## Implementation Priority

### High Priority (Core Loop)
1. **Post-creation onboarding** - Users need guidance
2. **Highlight assumptions** - They're captured but not visible
3. **Inquiry prominence** - Make them the focus
4. **Evidence aggregation** - Show strength at a glance

### Medium Priority (Polish)
5. **Guided investigation** - Step-by-step workflow
6. **Connection suggestions** - Auto-link related items
7. **Auto-brief updates** - When inquiries resolve

### Low Priority (Nice-to-Have)
8. **Evidence visualization** - Graphs/charts
9. **Inquiry dependencies** - Track blocking relationships
10. **Collaboration features** - Comments, assignments

---

## Quick Wins We Can Implement Now

### Win 1: Onboarding Component
```python
# backend/apps/cases/views.py
@action(detail=True, methods=['get'])
def onboarding(self, request, pk=None):
    """Get onboarding data for newly created case"""
    case = self.get_object()
    
    # Get auto-created items
    inquiries = case.inquiries.all()
    brief = case.main_brief
    
    # Extract assumptions from brief
    assumptions = brief.ai_structure.get('assumptions', []) if brief else []
    
    return Response({
        'auto_created': {
            'inquiries': InquiryListSerializer(inquiries, many=True).data,
            'assumptions': assumptions,
            'brief_exists': brief is not None
        },
        'next_steps': [
            {'action': 'review_assumptions', 'completed': False},
            {'action': 'start_first_inquiry', 'completed': False},
            {'action': 'gather_evidence', 'completed': False}
        ]
    })
```

### Win 2: Assumptions Highlighting
```python
# backend/apps/cases/serializers.py
class CaseBriefDetailSerializer(serializers.ModelSerializer):
    highlighted_assumptions = serializers.SerializerMethodField()
    
    def get_highlighted_assumptions(self, obj):
        assumptions = obj.ai_structure.get('assumptions', [])
        
        return [{
            'text': assumption,
            'exists_as_inquiry': Inquiry.objects.filter(
                case=obj.case,
                title__icontains=assumption[:30]
            ).exists(),
            'related_signals': obj.case.signals.filter(
                text__icontains=assumption[:20]
            ).count()
        } for assumption in assumptions]
```

### Win 3: Inquiry Dashboard View
```python
# backend/apps/inquiries/views.py
@action(detail=False, methods=['get'])
def dashboard(self, request):
    """Get inquiry dashboard for user's cases"""
    case_id = request.query_params.get('case_id')
    
    inquiries = Inquiry.objects.filter(
        case_id=case_id,
        case__user=request.user
    )
    
    return Response({
        'by_status': {
            'open': InquiryListSerializer(
                inquiries.filter(status='OPEN'),
                many=True
            ).data,
            'investigating': InquiryListSerializer(
                inquiries.filter(status='INVESTIGATING'),
                many=True
            ).data,
            'resolved': InquiryListSerializer(
                inquiries.filter(status='RESOLVED'),
                many=True
            ).data
        },
        'summary': {
            'total': inquiries.count(),
            'open': inquiries.filter(status='OPEN').count(),
            'resolved': inquiries.filter(status='RESOLVED').count(),
            'completion_rate': _calculate_completion_rate(inquiries)
        },
        'next_actions': _suggest_next_actions(inquiries)
    })
```

### Win 4: Evidence Summary for Inquiry
```python
# backend/apps/inquiries/views.py
@action(detail=True, methods=['get'])
def evidence_summary(self, request, pk=None):
    """Get aggregated evidence summary for inquiry"""
    inquiry = self.get_object()
    evidence = Evidence.objects.filter(inquiry=inquiry)
    
    supporting = evidence.filter(direction='SUPPORTS')
    contradicting = evidence.filter(direction='CONTRADICTS')
    neutral = evidence.filter(direction='NEUTRAL')
    
    # Calculate aggregate confidence
    if evidence.exists():
        support_strength = supporting.count() / evidence.count()
        avg_credibility = evidence.aggregate(
            models.Avg('user_credibility_rating')
        )['user_credibility_rating__avg'] or 0.0
        
        aggregate_confidence = support_strength * avg_credibility
    else:
        aggregate_confidence = 0.0
    
    return Response({
        'supporting': EvidenceSerializer(supporting, many=True).data,
        'contradicting': EvidenceSerializer(contradicting, many=True).data,
        'neutral': EvidenceSerializer(neutral, many=True).data,
        'aggregate_confidence': aggregate_confidence,
        'strength': 'strong' if aggregate_confidence > 0.7 else 'moderate' if aggregate_confidence > 0.4 else 'weak',
        'ready_to_resolve': aggregate_confidence > 0.6 and evidence.count() >= 2
    })
```

---

## Refocusing Skills: Background Configuration

### How Skills Should Work (Invisible Unless Needed)

**Default experience (no skills visible):**
```
User creates case → Works on inquiries → Agents help → Decision made
[Skills working in background, user doesn't see them]
```

**Power user experience (wants customization):**
```
User clicks [Settings] → Sees available skills → Activates for case
[Skills become visible tool, not main feature]
```

**Skill management (rare, admin-level):**
```
Org admin → [Settings] → [Skills] → Create/manage org skills
[Separate admin section, not primary workflow]
```

### UI Hierarchy

**Primary Navigation:**
```
[Cases] [Chat] [Documents]  ← Core product
```

**Settings/Configuration:**
```
Settings > 
├─ Skills (available, not prominent)
├─ Preferences
└─ Team Settings
```

**NOT:**
```
[Cases] [Skills] [Inquiries]  ← Makes skills too prominent
```

---

## Recommended Implementation Focus

### Next Sprint: Core Loop Polish

1. **Onboarding Component** (1-2 days)
   - Show what was auto-created
   - Provide next steps
   - Guide first-time users

2. **Assumption Highlighting** (1 day)
   - Visual treatment in brief
   - One-click to create inquiry
   - Validation status

3. **Inquiry Dashboard** (2 days)
   - Prominent inquiry view
   - Status summary
   - Next action suggestions

4. **Evidence Aggregation** (1-2 days)
   - Summary view per inquiry
   - Confidence calculation
   - "Ready to resolve" indicator

### Later: Polish & Scale

5. **Auto-promotion** (1 day)
   - Background task to suggest signal → inquiry promotions
   - Weekly digest of suggestions

6. **Connection suggestions** (2 days)
   - AI-suggested links between items
   - "Related to this" sidebar

7. **Investigation guidance** (1 day)
   - Step-by-step workflow
   - Progress tracking

---

## Skills Take a Back Seat

**Skills remain powerful but background:**

- Default: 1-2 org-wide skills pre-configured
- Users don't create skills unless they're power users
- Skill activation optional (case works fine without)
- Skill management in settings, not main nav

**The skill system we built enables:**
- Vertical specialization (legal, medical, product)
- Team knowledge capture
- But it's **not the main user journey**

---

Want me to implement the **core loop improvements** instead? I'd focus on:

1. Post-creation onboarding
2. Assumption highlighting
3. Inquiry dashboard
4. Evidence aggregation

These improve the **decision-making experience**, which is your actual product!