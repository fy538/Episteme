# Plan 5: Case Graph Visualization + Interactive Analysis

## Goal
After case extraction runs, users should see an **interactive investigation board** — a CEAT (Claims, Evidence, Assumptions, Tensions) graph that visualizes the extracted reasoning structure, overlays the analysis results (blind spots, unsupported claims, untested assumptions), and lets users interact with nodes to deepen their investigation.

---

## Architecture Overview

```
Case extraction completes
        ↓
case.metadata['extraction_status'] = 'complete'
case.metadata['analysis'] = { blind_spots, assumptions, evidence_coverage, readiness }
        ↓
CaseExtractionProgress detects completion → triggers graph fetch
        ↓
useCaseGraph hook → GET /api/v2/projects/{pid}/cases/{cid}/graph/
        ↓
CaseGraphView renders GraphCanvas with analysis overlays
        ↓
User clicks node → detail drawer + "Ask about this" → chat panel
```

---

## Current State

| Component | File | Status |
|-----------|------|--------|
| GraphCanvas | `frontend/src/components/graph/GraphCanvas.tsx` | Fully wired, accepts `caseId` prop |
| GraphNodeCard | `frontend/src/components/graph/nodes/GraphNodeCard.tsx` | 3-tier zoom rendering (compact/summary/detail) |
| Edge components | `frontend/src/components/graph/edges/` | Supports/Contradicts/DependsOn styled |
| useGraphLayout | `frontend/src/components/graph/useGraphLayout.ts` | ELK layout, cluster collapse, filtering |
| useProjectGraph | `frontend/src/hooks/useProjectGraph.ts` | React Query hook — pattern to follow |
| Case workspace | `frontend/src/app/(app)/cases/[caseId]/page.tsx` | Has `viewMode` switch, 6 existing views |
| Case graph endpoint | `GET /api/v2/projects/{pid}/cases/{cid}/graph/` | Returns nodes + edges, filter by type |
| CaseExtractionProgress | `frontend/src/components/workspace/case/CaseExtractionProgress.tsx` | Phase tracking, AnalysisSummary on complete |
| Case metadata | `Case.metadata` JSONField | Stores extraction_result + analysis |

**Key insight:** GraphCanvas **already supports case scope** via its `caseId` prop. The main work is creating the view mode, the data hook, and the analysis overlay layer.

---

## Implementation Steps

### Step 1: Create useCaseGraph Hook

**File: `frontend/src/hooks/useCaseGraph.ts`** (NEW)

Mirrors `useProjectGraph` but fetches case-scoped graph data:

```typescript
'use client';
import { useQuery } from '@tanstack/react-query';
import { graphAPI } from '@/lib/api/graph';
import type { GraphData } from '@/lib/types/graph';

export function useCaseGraph(projectId: string | undefined, caseId: string | undefined) {
    return useQuery<GraphData>({
        queryKey: ['case-graph', projectId, caseId],
        queryFn: () => graphAPI.getCaseGraph(projectId!, caseId!),
        enabled: !!projectId && !!caseId,
        staleTime: 30_000,
        refetchOnWindowFocus: false,
    });
}
```

Also add a hook for the analysis data:

```typescript
export function useCaseAnalysis(caseId: string | undefined) {
    return useQuery<CaseAnalysis>({
        queryKey: ['case-analysis', caseId],
        queryFn: () => casesAPI.getAnalysis(caseId!),
        enabled: !!caseId,
        staleTime: 60_000,
    });
}
```

---

### Step 2: Add 'graph' View Mode to Case Workspace

**File: `frontend/src/app/(app)/cases/[caseId]/page.tsx`**

Add `'graph'` to the ViewMode type and the renderMainContent switch:

```typescript
// In ViewMode type (or wherever it's defined):
type ViewMode = 'home' | 'brief' | 'readiness' | 'inquiry-dashboard' | 'inquiry' | 'document' | 'graph';

// In renderMainContent():
case 'graph':
    return (
        <CaseGraphView
            projectId={projectId}
            caseId={caseId}
            analysis={caseAnalysis}
            onAskAboutNode={(node) => {
                // Open chat panel with node context
                setChatContext({ type: 'node', nodeId: node.id, content: node.content });
                setIsChatCollapsed(false);
            }}
        />
    );
```

Add a navigation entry — either in the breadcrumb/tab bar or a command palette entry:

```typescript
// In the view mode selector / command palette:
{ label: 'Investigation Graph', value: 'graph', icon: NetworkIcon, shortcut: '⌘G' }
```

---

### Step 3: Create CaseGraphView Component

**File: `frontend/src/components/workspace/case/CaseGraphView.tsx`** (NEW)

This is the main wrapper that composes GraphCanvas with case-specific features:

```typescript
interface CaseGraphViewProps {
    projectId: string;
    caseId: string;
    analysis?: CaseAnalysis;
    onAskAboutNode?: (node: GraphNode) => void;
}
```

**Layout:**
```
┌──────────────────────────────────────────────────────────┐
│  Decision Question (header bar)            [Filters] [?] │
├────────────────────────────────────────┬─────────────────┤
│                                        │ Analysis Panel  │
│                                        │                 │
│           GraphCanvas                  │ Readiness: 65%  │
│        (full height, flex-1)           │ ▸ 2 blind spots │
│                                        │ ▸ 1 untested    │
│                                        │ ▸ 3 unsupported │
│                                        │                 │
│                                        │ [Re-extract]    │
└────────────────────────────────────────┴─────────────────┘
```

**Component structure:**
```tsx
function CaseGraphView({ projectId, caseId, analysis, onAskAboutNode }: CaseGraphViewProps) {
    const { data: graphData, isLoading } = useCaseGraph(projectId, caseId);
    const [highlightedNodeIds, setHighlightedNodeIds] = useState<string[]>([]);
    const [analysisPanelOpen, setAnalysisPanelOpen] = useState(true);

    // Derive highlight sets from analysis
    const unsupportedClaimIds = useMemo(() => {
        if (!analysis?.evidence_coverage?.unsupported_claims) return [];
        return analysis.evidence_coverage.unsupported_claims.map(c => c.node_id);
    }, [analysis]);

    const untestedAssumptionIds = useMemo(() => {
        if (!analysis?.assumption_assessment) return [];
        return analysis.assumption_assessment
            .filter(a => a.load_bearing && a.supporting_evidence === 0)
            .map(a => a.node_id);
    }, [analysis]);

    if (isLoading) return <GraphSkeleton />;
    if (!graphData?.nodes?.length) return <EmptyGraphState caseId={caseId} />;

    return (
        <div className="flex h-full">
            <div className="flex-1 relative">
                {/* Header */}
                <CaseGraphHeader
                    decisionQuestion={case.decision_question}
                    nodeCount={graphData.nodes.length}
                    edgeCount={graphData.edges.length}
                />

                {/* Graph */}
                <GraphCanvas
                    graphNodes={graphData.nodes}
                    graphEdges={graphData.edges}
                    projectId={projectId}
                    caseId={caseId}
                    highlightedNodeIds={highlightedNodeIds}
                    onAskAboutNode={onAskAboutNode}
                    totalNodeCount={graphData.total_node_count}
                    truncated={graphData.truncated}
                />
            </div>

            {/* Analysis sidebar */}
            {analysisPanelOpen && analysis && (
                <AnalysisPanel
                    analysis={analysis}
                    onHighlightNodes={setHighlightedNodeIds}
                    onClose={() => setAnalysisPanelOpen(false)}
                />
            )}
        </div>
    );
}
```

---

### Step 4: Create AnalysisPanel Component

**File: `frontend/src/components/workspace/case/AnalysisPanel.tsx`** (NEW)

A sidebar panel that displays the case analysis results and enables graph interaction:

```typescript
interface AnalysisPanelProps {
    analysis: CaseAnalysis;
    onHighlightNodes: (nodeIds: string[]) => void;
    onClose: () => void;
}
```

**Sections:**

1. **Decision Readiness** (top)
   - Circular confidence gauge (0-100%)
   - Color: green (≥80%), amber (50-79%), red (<50%)
   - Issues list below

2. **Blind Spots** (expandable)
   - Cards with severity badge (high=red, medium=amber, low=gray)
   - Description + suggested action
   - Click → highlights related nodes on graph (if relevant_theme_ids present)

3. **Untested Assumptions** (expandable)
   - Only shows load-bearing assumptions with 0 supporting evidence
   - Each shows: content, "Load-bearing: depends_on from N claims"
   - Click → highlights the assumption node + its dependents
   - Hover → `setHighlightedNodeIds([assumption.node_id, ...involved_nodes])`

4. **Unsupported Claims** (expandable)
   - Claims with no 'supports' edges from evidence
   - Click → highlights the claim node
   - Badge: "N of M claims unsupported"

5. **Key Tensions** (expandable)
   - Tension nodes with involved_nodes
   - Click → highlights tension + the nodes it connects
   - Status badge (surfaced/acknowledged/resolved)

6. **Re-extract Button** (bottom)
   - "Add more evidence" → triggers incremental extraction
   - Shows last extraction timestamp

**Interaction pattern:** Hovering/clicking any issue in the panel → calls `onHighlightNodes([...nodeIds])` → GraphCanvas highlights those nodes (dims others to 30% opacity, matching existing highlight behavior).

---

### Step 5: Create EmptyGraphState Component

**File: `frontend/src/components/workspace/case/EmptyGraphState.tsx`** (NEW)

Shown when case extraction hasn't run yet or returned zero nodes:

```
┌─────────────────────────────────────────┐
│                                         │
│     🔍  No evidence graph yet           │
│                                         │
│  Add documents to your project and      │
│  this case will automatically extract   │
│  claims, evidence, and assumptions.     │
│                                         │
│  [Upload Documents]  [Re-extract]       │
│                                         │
└─────────────────────────────────────────┘
```

Check `case.metadata.extraction_status`:
- `'pending'` or `'retrieving'` or `'extracting'`: Show CaseExtractionProgress (inline)
- `'failed'`: Show error message + retry button
- `'complete'` with 0 nodes: Show "No relevant evidence found" + suggest adding more docs
- No status: Show upload prompt

---

### Step 6: Enhance GraphNodeCard for Case Context

**File: `frontend/src/components/graph/nodes/GraphNodeCard.tsx`**

Add case-specific visual enhancements to the existing node card (these are additive, not breaking):

**6a. Analysis badges on nodes:**

When a node appears in the analysis results, show a small badge:

```typescript
// In DetailCard (close zoom) render:
const isUnsupported = analysisFlags?.unsupported;
const isUntested = analysisFlags?.untestedLoadBearing;
const isTensionNode = node.node_type === 'tension';

// Add badge row:
{isUnsupported && (
    <span className="text-xs px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded">
        ⚠ Unsupported
    </span>
)}
{isUntested && (
    <span className="text-xs px-1.5 py-0.5 bg-red-100 text-red-700 rounded">
        ⚡ Untested
    </span>
)}
```

**How to pass analysis flags:** The `CaseGraphView` can pre-compute a `Map<nodeId, AnalysisFlags>` from the analysis data and pass it through `GraphCanvas` → `useGraphLayout` → node `data` prop. This avoids modifying GraphCanvas's interface — just enrich the `data.graphNode.properties` before passing nodes in.

**6b. Scope badge:**

Show whether a node is case-scoped (extracted for this case) or project-scoped (pulled from project graph):

```typescript
// In DetailCard:
{node.scope === 'case' && (
    <span className="text-xs text-muted-foreground">📦 Case-local</span>
)}
{node.scope === 'project' && (
    <span className="text-xs text-muted-foreground">🌐 Project</span>
)}
```

---

### Step 7: Wire Up "Ask About This Node" → Chat Panel

**File: `frontend/src/app/(app)/cases/[caseId]/page.tsx`**

The `onAskAboutNode` callback already exists on GraphCanvas. Wire it to open the chat panel with node context:

```typescript
const handleAskAboutNode = useCallback((node: GraphNode) => {
    // Pre-fill chat input with question about this node
    const prompt = node.node_type === 'assumption'
        ? `How can we test this assumption: "${node.content}"?`
        : node.node_type === 'tension'
        ? `How should we resolve this tension: "${node.content}"?`
        : `Tell me more about: "${node.content}"`;

    // Set chat context for the next message
    setChatPrefill(prompt);
    setIsChatCollapsed(false);
}, []);
```

This should feel natural — click a node, chat opens with a contextual question, user can edit and send.

---

### Step 8: Backend — Add Case Analysis Endpoint (if not exists)

**File: `backend/apps/cases/views.py`**

Ensure there's an endpoint to fetch the analysis separately from the full case:

```python
# GET /api/cases/{case_id}/analysis/
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def case_analysis_view(request, case_id):
    case = get_object_or_404(Case, id=case_id, user=request.user)
    analysis = (case.metadata or {}).get('analysis', {})
    extraction_status = (case.metadata or {}).get('extraction_status', 'none')

    return Response({
        'extraction_status': extraction_status,
        'analysis': analysis,
        'extraction_result': (case.metadata or {}).get('extraction_result', {}),
    })
```

This keeps the analysis fetch lightweight (no full case serialization).

---

### Step 9: Connect Extraction Completion → Graph View

**File: `frontend/src/components/workspace/case/CaseExtractionProgress.tsx`**

After extraction completes, add a CTA to view the graph:

```typescript
// In the "completed" state render:
{status === 'complete' && nodeCount > 0 && (
    <div className="mt-4">
        <AnalysisSummary analysis={analysis} />
        <button
            onClick={() => setViewMode('graph')}
            className="mt-3 btn-primary"
        >
            View Investigation Graph ({nodeCount} nodes)
        </button>
    </div>
)}
```

---

## Key Files to Modify

| File | Change |
|------|--------|
| `frontend/src/hooks/useCaseGraph.ts` | NEW — React Query hook for case graph data |
| `frontend/src/components/workspace/case/CaseGraphView.tsx` | NEW — main graph view wrapper |
| `frontend/src/components/workspace/case/AnalysisPanel.tsx` | NEW — analysis sidebar with graph interaction |
| `frontend/src/components/workspace/case/EmptyGraphState.tsx` | NEW — empty/loading/error states |
| `frontend/src/app/(app)/cases/[caseId]/page.tsx` | Add `'graph'` view mode + navigation |
| `frontend/src/hooks/useCaseWorkspace.ts` | Extend ViewMode type |
| `frontend/src/components/graph/nodes/GraphNodeCard.tsx` | Add analysis badges (unsupported, untested) |
| `frontend/src/components/workspace/case/CaseExtractionProgress.tsx` | Add "View Graph" CTA on completion |
| `backend/apps/cases/views.py` | Add analysis endpoint (if missing) |
| `backend/apps/cases/urls.py` | Wire analysis endpoint |

**Not modified (reused as-is):**
- `GraphCanvas.tsx` — already supports `caseId`, `highlightedNodeIds`, `onAskAboutNode`
- `useGraphLayout.ts` — works for case-scoped data without changes
- Graph node/edge components — render correctly for all CEAT types
- Case graph API endpoint — already exists and returns correct data

---

## Visual Design Notes

**Color palette for CEAT nodes:**
- Claims: blue-500 (assertive, central)
- Evidence: emerald-500 (grounded, factual)
- Assumptions: amber-500 (caution, needs testing)
- Tensions: rose-500 (conflict, attention)

These should already be defined in the existing GraphNodeCard — verify and ensure consistency.

**Analysis overlay states:**
- Default: all nodes normal opacity
- Highlight mode (from AnalysisPanel click): highlighted nodes full opacity + ring-2, others opacity-30
- Clear highlights: click empty canvas or press Escape

---

## Edge Cases

1. **No extraction yet:** Show EmptyGraphState with extraction trigger
2. **Extraction failed:** Show error + retry in EmptyGraphState
3. **Zero nodes extracted (but chunks existed):** "No relevant evidence found" — suggest different decision question or more docs
4. **Very large graph (>500 nodes):** GraphCanvas already handles this with zoom tiers + cluster collapse
5. **Analysis not yet computed (extraction still running):** Show graph without analysis panel, add loading spinner for analysis
6. **Case has no project:** Shouldn't happen (project is required FK), but gracefully show error

---

## Testing

1. **Frontend unit:** CaseGraphView renders graph with mock data
2. **Frontend unit:** AnalysisPanel highlights correct nodes for each issue type
3. **Frontend unit:** EmptyGraphState shows correct state for each extraction_status
4. **Integration:** Create case → run extraction → verify graph view shows nodes
5. **Interaction:** Click "Unsupported claim" in AnalysisPanel → verify node highlights on graph
6. **Interaction:** Click node → "Ask about this" → verify chat opens with context
