# Readiness System: Phase 2 & 3 Implementation Plan

## Current State (Phase 1 ✅)

**What We Built:**
- Smart AI-generated checklist items based on case context
- Auto-completion when linked inquiries resolve
- AI explains "why important" for each item
- Items linked to inquiries and assumption signals
- Flat list structure (no hierarchy yet)
- Basic frontend with expand/collapse

**What's Working:**
- AI generates 5-7 contextual items analyzing: decision question, assumptions, inquiries, stakeholders
- Auto-linking to inquiries by title matching
- Signal-driven auto-completion with completion notes
- User can manually add/edit/delete/complete items

---

## Phase 2: Hierarchical Readiness & Visual Intelligence

**Goal:** Transform the flat checklist into an intelligent, hierarchical system that shows dependencies and reasoning structure visually.

### 2.1 Hierarchical Checklist Structure

**Problem:** Current flat list doesn't show relationships between readiness items. Some items depend on others.

**Solution:** Add parent-child relationships and display as expandable tree.

#### Backend Changes

**File:** `backend/apps/cases/models.py`

```python
class ReadinessChecklistItem(UUIDModel, TimestampedModel):
    # ... existing fields ...

    # NEW: Hierarchical structure
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children',
        help_text="Parent item (for nested/dependent items)"
    )

    # NEW: Item type for better organization
    item_type = models.CharField(
        max_length=50,
        choices=[
            ('validation', 'Validate Assumption'),
            ('investigation', 'Complete Investigation'),
            ('analysis', 'Perform Analysis'),
            ('stakeholder', 'Stakeholder Input'),
            ('alternative', 'Evaluate Alternative'),
            ('criteria', 'Define Criteria'),
            ('custom', 'Custom'),
        ],
        default='custom',
        help_text="Type of readiness item"
    )

    # NEW: Dependencies
    blocks = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='blocked_by',
        blank=True,
        help_text="Items that cannot be completed until this one is done"
    )

    class Meta:
        ordering = ['parent__order', 'order', 'id']  # Parent first, then children
```

**Migration:**
```bash
python manage.py makemigrations cases -n add_checklist_hierarchy
python manage.py migrate
```

#### Enhanced AI Generation

**File:** `backend/apps/cases/checklist_service.py`

Update prompt to generate hierarchical items:

```python
async def generate_smart_checklist(case) -> List[Dict[str, Any]]:
    # ... existing context gathering ...

    prompt = f"""Analyze this decision case and suggest a HIERARCHICAL checklist.

**STRUCTURE:**
- Create parent items for major categories (e.g., "Validate Key Assumptions", "Complete Critical Inquiries")
- Add 2-4 child items under each parent with specific actions
- Use item types: validation, investigation, analysis, stakeholder, alternative, criteria

**Case**: {case.title}
**Decision Question**: {case.decision_question or 'Not yet defined'}

**Detected Assumptions** ({len(assumptions)}):
{chr(10).join(f'- {a}' for a in assumptions)}

**Open Inquiries** ({len(inquiries)}):
{chr(10).join(f'- {i["title"]} ({i["status"]})' for i in inquiries)}

**Guidelines:**
- Parent items are high-level goals (e.g., "Understand costs and resources")
- Child items are specific actions (e.g., "Calculate migration costs", "Assess team capacity")
- Mark critical path items as is_required: true
- Link child items to specific inquiries when relevant

Return JSON array:
[{{
    "description": "...",
    "is_required": true,
    "why_important": "...",
    "item_type": "validation",
    "parent_description": null,  // or parent description for child items
    "linked_inquiry_title": null,
    "blocks": []  // descriptions of items this blocks
}}]
"""

    # ... generate and parse ...

    # NEW: Build hierarchy
    items_with_parents = _build_hierarchy(items_data)
    return items_with_parents
```

#### Frontend Component

**File:** `frontend/src/components/readiness/HierarchicalChecklist.tsx`

```typescript
interface HierarchicalItem extends ReadinessChecklistItemData {
  children: HierarchicalItem[];
  level: number;
}

export function HierarchicalChecklist({ items, ... }) {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  // Build tree structure
  const tree = useMemo(() => buildTree(items), [items]);

  return (
    <div className="space-y-2">
      {tree.map(item => (
        <ChecklistNode
          key={item.id}
          item={item}
          expanded={expandedItems.has(item.id)}
          onToggleExpand={() => toggleExpand(item.id)}
          level={0}
        />
      ))}
    </div>
  );
}

function ChecklistNode({ item, level, expanded, onToggleExpand }) {
  const hasChildren = item.children.length > 0;
  const allChildrenComplete = hasChildren &&
    item.children.every(c => c.is_complete);

  return (
    <div className={`ml-${level * 6}`}>
      <div className="flex items-center gap-2">
        {hasChildren && (
          <button onClick={onToggleExpand}>
            {expanded ? <ChevronDown /> : <ChevronRight />}
          </button>
        )}

        <ChecklistItem
          item={item}
          showProgress={hasChildren}
          childProgress={`${item.children.filter(c => c.is_complete).length}/${item.children.length}`}
        />
      </div>

      {hasChildren && expanded && (
        <div className="mt-2">
          {item.children.map(child => (
            <ChecklistNode
              key={child.id}
              item={child}
              level={level + 1}
              expanded={expandedItems.has(child.id)}
              onToggleExpand={() => toggleExpand(child.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
```

**Estimated Effort:**
- Backend: 4 hours (model, migration, service updates)
- Frontend: 6 hours (tree component, drag-drop reordering)
- Testing: 2 hours

---

### 2.2 Dependency Visualization

**Problem:** Users can't see how checklist items relate to each other or what's blocking what.

**Solution:** Add dependency graph view showing blocking relationships.

#### Backend API

**File:** `backend/apps/cases/views.py`

```python
@action(detail=True, methods=['get'], url_path='readiness-checklist/graph')
def checklist_graph(self, request, pk=None):
    """
    Get dependency graph for readiness checklist.

    GET /api/cases/{id}/readiness-checklist/graph/

    Returns nodes and edges for visualization.
    """
    case = self.get_object()
    items = ReadinessChecklistItem.objects.filter(case=case)

    nodes = []
    edges = []

    for item in items:
        nodes.append({
            'id': str(item.id),
            'label': item.description[:50],
            'type': item.item_type,
            'is_complete': item.is_complete,
            'is_required': item.is_required,
            'has_linked_inquiry': item.linked_inquiry_id is not None,
        })

        # Parent-child edges
        if item.parent:
            edges.append({
                'source': str(item.parent_id),
                'target': str(item.id),
                'type': 'contains',
            })

        # Blocking edges
        for blocked in item.blocks.all():
            edges.append({
                'source': str(item.id),
                'target': str(blocked.id),
                'type': 'blocks',
            })

        # Inquiry link edges
        if item.linked_inquiry:
            edges.append({
                'source': f'inquiry-{item.linked_inquiry_id}',
                'target': str(item.id),
                'type': 'validates',
            })

    return Response({
        'nodes': nodes,
        'edges': edges,
    })
```

#### Frontend Visualization

**File:** `frontend/src/components/readiness/ReadinessGraph.tsx`

Use React Flow for graph visualization:

```typescript
import ReactFlow, { Node, Edge, Background, Controls } from 'reactflow';
import 'reactflow/dist/style.css';

export function ReadinessGraph({ caseId }) {
  const [graphData, setGraphData] = useState<{ nodes: Node[], edges: Edge[] }>();

  useEffect(() => {
    async function loadGraph() {
      const resp = await fetch(`/api/cases/${caseId}/readiness-checklist/graph/`);
      const data = await resp.json();

      // Layout nodes with dagre
      const { nodes, edges } = layoutGraph(data.nodes, data.edges);
      setGraphData({ nodes, edges });
    }
    loadGraph();
  }, [caseId]);

  const nodeTypes = {
    checklistItem: ChecklistNode,
    inquiry: InquiryNode,
  };

  const edgeTypes = {
    blocks: BlockingEdge,
    validates: ValidatesEdge,
    contains: ContainsEdge,
  };

  return (
    <div className="h-[600px] border rounded-lg">
      <ReactFlow
        nodes={graphData?.nodes}
        edges={graphData?.edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
```

**Estimated Effort:**
- Backend: 2 hours
- Frontend: 8 hours (React Flow integration, custom nodes/edges, layout)
- Testing: 2 hours

---

### 2.3 Integration with Reasoning Graph

**Problem:** Readiness checklist is isolated from the broader reasoning graph (signals, evidence, inquiries).

**Solution:** Unify visualization to show how checklist items connect to assumptions, inquiries, and evidence.

#### Unified Graph View

**File:** `backend/apps/reasoning/views.py`

Enhance existing `case_graph` endpoint:

```python
@action(detail=False, methods=['get'], url_path='case/(?P<case_id>[^/.]+)')
def case_graph(self, request, case_id=None):
    """Enhanced to include readiness checklist nodes"""

    # ... existing code for inquiries, signals, evidence ...

    # NEW: Add readiness checklist nodes
    checklist_items = ReadinessChecklistItem.objects.filter(case=case)
    for item in checklist_items:
        nodes.append({
            'id': f'checklist-{item.id}',
            'type': 'checklist_item',
            'label': item.description[:40],
            'itemType': item.item_type,
            'isComplete': item.is_complete,
            'isRequired': item.is_required,
        })

        # Link to inquiry
        if item.linked_inquiry:
            edges.append({
                'source': f'inquiry-{item.linked_inquiry_id}',
                'target': f'checklist-{item.id}',
                'type': 'validates',
                'label': 'validates readiness',
            })

        # Link to assumption signal
        if item.linked_assumption_signal:
            edges.append({
                'source': f'signal-{item.linked_assumption_signal_id}',
                'target': f'checklist-{item.id}',
                'type': 'addresses',
                'label': 'addresses',
            })

        # Blocking relationships
        for blocked in item.blocks.all():
            edges.append({
                'source': f'checklist-{item.id}',
                'target': f'checklist-{blocked.id}',
                'type': 'blocks',
                'label': 'blocks',
            })

    return Response({'nodes': nodes, 'edges': edges})
```

#### Frontend Integration

**File:** `frontend/src/components/reasoning/UnifiedReasoningGraph.tsx`

```typescript
export function UnifiedReasoningGraph({ caseId }) {
  const [filter, setFilter] = useState({
    showInquiries: true,
    showSignals: true,
    showEvidence: false,  // Too cluttered
    showChecklist: true,
  });

  return (
    <div>
      <GraphFilterPanel filter={filter} onChange={setFilter} />

      <ReactFlow
        nodes={filteredNodes}
        edges={filteredEdges}
        nodeTypes={{
          inquiry: InquiryNode,
          signal: SignalNode,
          evidence: EvidenceNode,
          checklist_item: ChecklistNode,  // NEW
        }}
      />

      <GraphLegend />
    </div>
  );
}
```

**Estimated Effort:**
- Backend: 2 hours
- Frontend: 4 hours
- Testing: 2 hours

---

## Phase 3: Advanced Intelligence & Proactive Guidance

**Goal:** Make the readiness system proactive and deeply intelligent - it notices problems, suggests next steps, and guides the user.

### 3.1 Smart Auto-Linking to Signals

**Problem:** Currently only links to inquiries manually. Many checklist items should link to assumption signals.

**Solution:** Auto-detect which assumption signals relate to which checklist items.

#### Service Enhancement

**File:** `backend/apps/cases/checklist_service.py`

```python
async def link_checklist_to_signals(case):
    """
    Automatically link checklist items to relevant assumption signals.
    Uses LLM to determine semantic relevance.
    """
    items = ReadinessChecklistItem.objects.filter(
        case=case,
        linked_assumption_signal__isnull=True  # Only unlinked items
    )

    assumptions = Signal.objects.filter(
        case=case,
        type='assumption',
        dismissed_at__isnull=True
    )

    if not items.exists() or not assumptions.exists():
        return

    provider = get_llm_provider('fast')

    # Batch link using LLM
    for item in items:
        prompt = f"""Which assumption (if any) does this readiness item address?

Readiness Item: "{item.description}"
Why Important: "{item.why_important}"

Assumptions:
{chr(10).join(f'{i}. {a.text}' for i, a in enumerate(assumptions, 1))}

Respond with JUST the number (1-{len(assumptions)}) or "none".
"""

        response = await provider.chat(messages=[{'role': 'user', 'content': prompt}])

        try:
            index = int(response.strip()) - 1
            if 0 <= index < len(assumptions):
                item.linked_assumption_signal = assumptions[index]
                item.save()
                logger.info(f"Linked checklist item {item.id} to assumption {assumptions[index].id}")
        except ValueError:
            pass  # "none" response
```

**Auto-run after checklist generation:**

```python
# In generate_checklist view:
items_data = await generate_smart_checklist(case)
# ... create items ...
await link_checklist_to_signals(case)  # NEW
```

**Estimated Effort:** 3 hours

---

### 3.2 Readiness Warnings & Proactive Suggestions

**Problem:** User has to manually check readiness. System should proactively warn about gaps.

**Solution:** AI analyzes completeness and suggests what's missing.

#### Warning System

**File:** `backend/apps/cases/readiness_analyzer.py` (NEW)

```python
"""
Proactive readiness analysis and warnings.
"""
import logging
from typing import List, Dict, Any
from apps.llm.provider import get_llm_provider

logger = logging.getLogger(__name__)


async def analyze_readiness_gaps(case) -> Dict[str, Any]:
    """
    Analyze case readiness and identify gaps/warnings.

    Returns:
        {
            'overall_readiness': 'low' | 'medium' | 'high',
            'critical_gaps': [...],
            'warnings': [...],
            'suggestions': [...],
        }
    """
    provider = get_llm_provider('fast')

    # Gather context
    checklist = list(case.readiness_checklist.all().values(
        'description', 'is_required', 'is_complete', 'item_type'
    ))

    required_incomplete = [
        item for item in checklist
        if item['is_required'] and not item['is_complete']
    ]

    open_inquiries = list(case.inquiries.filter(
        status__in=['open', 'investigating']
    ).values('title', 'priority'))

    unvalidated_assumptions = list(Signal.objects.filter(
        case=case,
        type='assumption',
        readiness_items__isnull=True  # Not linked to any checklist item
    ).values('text')[:10])

    # Analyze with LLM
    prompt = f"""Analyze this decision case for readiness gaps and warnings.

**Case**: {case.title}
**Decision Question**: {case.decision_question}

**Required Incomplete Items** ({len(required_incomplete)}):
{chr(10).join(f'- {item["description"]}' for item in required_incomplete[:10])}

**Open Inquiries** ({len(open_inquiries)}):
{chr(10).join(f'- {inq["title"]}' for inq in open_inquiries[:10])}

**Unaddressed Assumptions** ({len(unvalidated_assumptions)}):
{chr(10).join(f'- {a["text"]}' for a in unvalidated_assumptions)}

Provide:
1. Overall readiness level (low/medium/high)
2. Top 3 critical gaps blocking decision
3. Warnings about risks or missing validation
4. Suggestions for next steps

Return JSON:
{{
    "overall_readiness": "low",
    "critical_gaps": ["...", "...", "..."],
    "warnings": ["...", "..."],
    "suggestions": ["...", "..."]
}}
"""

    response = ""
    async for chunk in provider.stream_chat(
        messages=[{'role': 'user', 'content': prompt}],
    ):
        response += chunk.content

    # Parse JSON
    import json
    import re
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())

    # Fallback
    return {
        'overall_readiness': 'low' if len(required_incomplete) > 3 else 'medium',
        'critical_gaps': [item['description'] for item in required_incomplete[:3]],
        'warnings': ['Several required items remain incomplete'],
        'suggestions': ['Focus on completing critical checklist items first'],
    }
```

#### API Endpoint

**File:** `backend/apps/cases/views.py`

```python
@action(detail=True, methods=['get'], url_path='readiness-analysis')
async def readiness_analysis(self, request, pk=None):
    """
    Get AI analysis of readiness gaps and warnings.

    GET /api/cases/{id}/readiness-analysis/
    """
    case = self.get_object()

    from apps.cases.readiness_analyzer import analyze_readiness_gaps
    analysis = await analyze_readiness_gaps(case)

    return Response(analysis)
```

#### Frontend Warning Panel

**File:** `frontend/src/components/readiness/ReadinessWarnings.tsx`

```typescript
export function ReadinessWarnings({ caseId }) {
  const [analysis, setAnalysis] = useState<any>(null);

  useEffect(() => {
    async function loadAnalysis() {
      const resp = await fetch(`/api/cases/${caseId}/readiness-analysis/`);
      setAnalysis(await resp.json());
    }
    loadAnalysis();
  }, [caseId]);

  if (!analysis) return <Spinner />;

  return (
    <div className="space-y-4">
      <ReadinessScore level={analysis.overall_readiness} />

      {analysis.critical_gaps.length > 0 && (
        <WarningCard
          title="Critical Gaps"
          icon={<AlertTriangle className="text-red-500" />}
          items={analysis.critical_gaps}
        />
      )}

      {analysis.warnings.length > 0 && (
        <WarningCard
          title="Warnings"
          icon={<AlertCircle className="text-yellow-500" />}
          items={analysis.warnings}
        />
      )}

      {analysis.suggestions.length > 0 && (
        <SuggestionCard
          title="Suggested Next Steps"
          items={analysis.suggestions}
        />
      )}
    </div>
  );
}
```

**Estimated Effort:**
- Backend: 4 hours
- Frontend: 4 hours
- Testing: 2 hours

---

### 3.3 Readiness Timeline & Projection

**Problem:** User doesn't know how long it will take to become ready.

**Solution:** Estimate time to completion based on inquiry complexity and historical data.

#### Backend Service

**File:** `backend/apps/cases/readiness_analyzer.py`

```python
async def estimate_completion_timeline(case) -> Dict[str, Any]:
    """
    Estimate how long until case is ready.

    Analyzes:
    - Incomplete required items
    - Open inquiry complexity
    - Historical completion times

    Returns timeline estimate and critical path.
    """
    provider = get_llm_provider('fast')

    required_incomplete = case.readiness_checklist.filter(
        is_required=True,
        is_complete=False
    )

    # Analyze inquiry complexity
    open_inquiries = case.inquiries.filter(status__in=['open', 'investigating'])

    prompt = f"""Estimate time to decision readiness for this case.

**Incomplete Required Items** ({required_incomplete.count()}):
{chr(10).join(f'- {item.description}' for item in required_incomplete[:10])}

**Open Inquiries** ({open_inquiries.count()}):
{chr(10).join(f'- {inq.title}' for inq in open_inquiries[:10])}

For each item/inquiry, estimate:
- Simple validation: 1-2 hours
- Research/analysis: 4-8 hours
- Stakeholder input: 1-3 days
- External data gathering: 2-5 days

Return JSON:
{{
    "estimated_hours": 24,
    "estimated_days": 3,
    "critical_path": [
        {{"item": "...", "estimated_hours": 8, "reason": "..."}},
        ...
    ],
    "confidence": "medium"
}}
"""

    # ... LLM call and parsing ...
```

**Estimated Effort:** 3 hours

---

### 3.4 Smart Checklist Templates by Decision Type

**Problem:** Starting from scratch every time. Common decision patterns should have templates.

**Solution:** Create and learn from decision type templates.

#### Template System

**File:** `backend/apps/cases/checklist_templates.py` (NEW)

```python
"""
Readiness checklist templates for common decision types.
"""

TEMPLATES = {
    'technology_migration': {
        'name': 'Technology Migration Decision',
        'items': [
            {
                'description': 'Calculate total migration costs (time, resources, opportunity cost)',
                'type': 'analysis',
                'is_required': True,
                'why_important': 'Ensures budget alignment and prevents cost overruns',
            },
            {
                'description': 'Assess team skills and capacity for new technology',
                'type': 'stakeholder',
                'is_required': True,
                'why_important': 'Team readiness determines feasibility and timeline',
            },
            {
                'description': 'Evaluate at least 2 alternatives to migration',
                'type': 'alternative',
                'is_required': True,
                'why_important': 'Comparing alternatives prevents premature commitment',
            },
            {
                'description': 'Identify and validate critical technical assumptions',
                'type': 'validation',
                'is_required': True,
                'why_important': 'Untested assumptions can derail migration',
            },
            {
                'description': 'Define success criteria and measurement plan',
                'type': 'criteria',
                'is_required': True,
                'why_important': 'Clear criteria enable post-migration evaluation',
            },
            {
                'description': 'Create rollback plan for failure scenarios',
                'type': 'analysis',
                'is_required': False,
                'why_important': 'Reduces risk of irreversible mistakes',
            },
        ],
    },

    'product_feature': {
        'name': 'New Product Feature Decision',
        'items': [
            # ... template items ...
        ],
    },

    'hiring': {
        'name': 'Key Hire Decision',
        'items': [
            # ... template items ...
        ],
    },
}


def get_template_for_case(case) -> str:
    """
    Auto-detect which template fits this case.
    Uses LLM to classify decision type.
    """
    # ... LLM classification ...
```

#### Template Selection UI

**File:** `frontend/src/components/readiness/TemplateSelector.tsx`

```typescript
export function TemplateSelector({ caseId, onApply }) {
  const [templates, setTemplates] = useState([]);
  const [suggested, setSuggested] = useState<string | null>(null);

  return (
    <Dialog>
      <DialogTitle>Choose Checklist Template</DialogTitle>

      {suggested && (
        <div className="bg-blue-50 p-3 rounded mb-4">
          <span className="text-sm">
            Suggested: <strong>{templates.find(t => t.id === suggested)?.name}</strong>
          </span>
        </div>
      )}

      <div className="grid gap-3">
        {templates.map(template => (
          <TemplateCard
            key={template.id}
            template={template}
            isSuggested={template.id === suggested}
            onSelect={() => onApply(template.id)}
          />
        ))}
      </div>
    </Dialog>
  );
}
```

**Estimated Effort:**
- Backend: 6 hours (templates, classification, API)
- Frontend: 4 hours
- Testing: 2 hours

---

## Summary: Phase 2 & 3 Timeline

### Phase 2: Hierarchical Readiness & Visual Intelligence (30-35 hours)

| Feature | Backend | Frontend | Testing | Total |
|---------|---------|----------|---------|-------|
| Hierarchical structure | 4h | 6h | 2h | **12h** |
| Dependency visualization | 2h | 8h | 2h | **12h** |
| Reasoning graph integration | 2h | 4h | 2h | **8h** |

### Phase 3: Advanced Intelligence (25-30 hours)

| Feature | Backend | Frontend | Testing | Total |
|---------|---------|----------|---------|-------|
| Auto-link to signals | 3h | - | 1h | **4h** |
| Readiness warnings | 4h | 4h | 2h | **10h** |
| Timeline projection | 3h | 2h | 1h | **6h** |
| Smart templates | 6h | 4h | 2h | **12h** |

**Total Estimated Effort: 55-65 hours**

---

## Recommended Implementation Order

### Sprint 1 (Phase 2a): Hierarchical Foundation
1. ✅ Add parent/item_type/blocks fields to model
2. ✅ Migration
3. ✅ Update AI generation for hierarchy
4. ✅ Build hierarchical frontend component

### Sprint 2 (Phase 2b): Visualization
1. ✅ Add checklist graph API endpoint
2. ✅ Build ReadinessGraph component with React Flow
3. ✅ Integrate with reasoning graph

### Sprint 3 (Phase 3a): Intelligence
1. ✅ Auto-linking to signals
2. ✅ Readiness warnings/gaps analysis
3. ✅ Warning panel UI

### Sprint 4 (Phase 3b): Templates & Projection
1. ✅ Template system
2. ✅ Timeline estimation
3. ✅ Template selector UI

---

## Success Criteria

**Phase 2:**
- ✅ Users can organize checklist items hierarchically
- ✅ Dependency graph shows blocking relationships clearly
- ✅ Checklist integrates seamlessly with reasoning graph
- ✅ Visual representation helps users see connections

**Phase 3:**
- ✅ System proactively identifies readiness gaps
- ✅ Auto-linking reduces manual work by 70%+
- ✅ Warnings highlight risks users might miss
- ✅ Templates accelerate checklist creation 5x
- ✅ Timeline estimates help users plan work

---

## Key Design Principles

1. **Show, Don't Score**: Never show "67% ready" - show specific gaps
2. **Explain Why**: Every item, warning, and suggestion includes reasoning
3. **Transparent AI**: User sees what AI detected and can override
4. **Progressive Disclosure**: Start simple, reveal complexity on demand
5. **Action-Oriented**: Every insight leads to a clear next step

This aligns with your vision: **Making users feel confident by showing them exactly what they don't know yet.**
