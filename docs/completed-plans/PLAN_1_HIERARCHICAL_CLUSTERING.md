# Plan 1: Hierarchical Clustering + Project Landscape

## Context & Strategic Decisions

This plan emerges from a series of product architecture decisions made during a deep design session. Here is the full context you need:

### Why We're Doing This

We redesigned the product around three levels of structure:

1. **Project level = Orientation.** A project is a container. The user dumps documents into it and sees themes, coverage, connections. There is no objective, no decision question, no reasoning to do. The project provides a landscape — "here's what your documents contain."

2. **Case level = Investigation.** A case has an objective (a `decision_question`). This is where reasoning happens — Claims, Evidence, Assumptions, Tensions. The graph is a case-level tool, not a project-level tool.

3. **Chat level = Exploration.** The user chats, and an organic companion tracks the conversation structure. At transition moments, the companion suggests opening a case.

**The key decision: We are removing project-level node extraction entirely.** Currently, when documents are uploaded, the system extracts Claims/Evidence/Assumptions/Tensions as graph nodes at the project level. We decided this is wrong because:
- There's no objective at the project level, so extraction is unfocused
- It produces generic nodes that may not be relevant to any specific case
- It's expensive (complex LLM extraction with tool_use, deduplication, consolidation)
- It imposes a reasoning framework (CEAT) where the user just wants to understand what's in their documents

Instead, extraction happens at the **case level** when a case is opened with a decision question (see Plan 3). The project level uses **hierarchical chunk clustering with LLM summaries** for orientation.

### What Replaces Node Extraction

Documents are already chunked and embedded. We keep that. But instead of extracting typed nodes from chunks, we:

1. Cluster chunks hierarchically (recursive agglomerative clustering)
2. Summarize each cluster with LLM at every level
3. Display the hierarchy as a zoomable landscape (progressive disclosure)
4. Run background agents that discover tensions, blind spots, and patterns across clusters → stored as `ProjectInsight` records

This is Aha Moment #1: "I dumped my documents in, and I can see the structure of my knowledge — themes I can explore, gaps I can identify, tensions across my sources."

---

## Current Architecture (What Exists Today)

### Backend

**Document Chunking (already exists, keep as-is):**
- `DocumentChunk` model in `backend/apps/documents/models.py`
- Each chunk has: `content` (text), `embedding` (384-dim pgvector via sentence-transformers all-MiniLM-L6-v2), `document` FK, `chunk_index`, `token_count`
- Chunks created during document upload/processing

**Current Flat Clustering (`backend/apps/graph/clustering.py`):**
- `ChunkClusteringService` — agglomerative clustering with:
  - `distance_threshold=0.65`, `metric='cosine'`, `linkage='average'`
  - Produces flat (one-level) clusters
  - Used by thematic summary pipeline
- `ClusteringService` — Leiden community detection on graph nodes (will be removed/repurposed)
  - Used by full summary pipeline
  - Has semantic refinement (split high-variance, merge small)
  - Has orphan assignment by embedding similarity

**Current Summary Pipeline (`backend/apps/graph/summary_service.py`):**
- `ProjectSummaryService` with tiers:
  - `SEED`: Template-based when <5 nodes
  - `THEMATIC`: Fast (~3s), clusters DocumentChunks, LLM labels themes — **this is closest to what we want**
  - `FULL`: Clusters graph nodes (Leiden), synthesizes with full argumentative analysis
- Thematic summary already works with chunks, not nodes. We're extending this approach.
- Summary stored in `ProjectSummary` model with versioning, staleness tracking, auto-regeneration

**Current Thematic Summary Prompts (`backend/apps/intelligence/thematic_summary_prompts.py`):**
- `build_thematic_summary_system_prompt()` — instructs labeling, narrative, overview, gap identification
- `build_thematic_summary_user_prompt(...)` — formats clusters with coverage %, representative passages, doc distribution

**Current Extraction Pipeline (`backend/apps/graph/extraction.py`):**
- `extract_nodes_from_document()` — full pipeline: LLM extraction → node creation → edge creation → embedding → chunk provenance matching
- For long docs: section-based extraction with dedup (cosine sim > 0.90) and consolidation pass
- **This will no longer run at the project level.** It will be repurposed for case-level extraction (Plan 3).

### Frontend

**Project Home (`frontend/src/components/workspace/project/ProjectHomePage.tsx`):**
- Currently shows: ProjectSummaryView + stats bar + case cards + action items
- Scoped chat input for project-linked threads

**Project Summary View (`frontend/src/components/workspace/project/ProjectSummaryView.tsx`):**
- Renders 5 sections: Overview, Key Findings (with coverage %), Emerging Picture, Attention Needed, What Changed
- Citation popovers linking to graph nodes (`[nodeId:UUID]` format)
- Supports: seed, thematic, generating, full, failed states
- Uses Framer Motion for animations

**Graph Visualization (`frontend/src/components/graph/GraphCanvas.tsx`):**
- ReactFlow-based force-directed graph
- Node types: GraphNodeCard (claim/evidence/assumption/tension), ClusterNode
- ELK-powered layout via `useGraphLayout.ts`
- **At the project level, this will be replaced by the hierarchical landscape view.** The graph visualization remains for cases.

**Key Frontend Dependencies:**
- Tailwind CSS 3.4 (custom, no shadcn)
- Framer Motion 12.29
- @xyflow/react (ReactFlow) for graph viz
- React Query v5.28 for data fetching
- Next.js App Router

---

## Implementation Plan

### Phase 1: Hierarchical Chunk Clustering (Backend)

#### 1.1 Create HierarchicalClusteringService

**File:** `backend/apps/graph/hierarchical_clustering.py` (new)

This service takes a project's chunks, builds a multi-level hierarchy via recursive agglomerative clustering, and returns a tree structure.

**Algorithm:**

```
Level 0 (Leaves): Raw DocumentChunks with 384-dim embeddings
    │ Agglomerative clustering (cosine, average linkage, distance_threshold=0.65)
    ▼
Level 1 (Topics): 10-30 clusters of chunks
    Each cluster gets: LLM summary (1-3 sentences), LLM label (2-5 words), embedding of summary
    │ Agglomerative clustering on Level 1 summary embeddings (distance_threshold=0.55)
    ▼
Level 2 (Themes): 3-7 super-clusters
    Each gets: LLM synthesis (2-4 sentences), LLM label (2-5 words), embedding of synthesis
    │ If >7 Level 2 clusters, one more merge pass
    ▼
Level 3 (Root): 1 project overview
    Synthesizes all Level 2 themes into a project narrative
```

**Key design decisions:**
- Use the existing `ChunkClusteringService` agglomerative approach for Level 0→1 (proven, no external deps)
- For Level 1→2 and beyond, cluster the summary embeddings using the same algorithm but with a lower distance threshold (summaries are more abstract, so they cluster differently)
- Stop recursing when you have ≤7 clusters at a level, or when a merge pass doesn't reduce count
- Each level's summaries are generated in parallel (batch LLM calls)
- Embeddings for summaries use the same `sentence-transformers all-MiniLM-L6-v2` pipeline

**Methods:**
```python
class HierarchicalClusteringService:
    async def build_hierarchy(self, project_id: uuid.UUID) -> ClusterTree:
        """Main entry point. Returns full cluster tree."""

    def _cluster_embeddings(self, embeddings: np.ndarray, ids: list, distance_threshold: float) -> list[set]:
        """Agglomerative clustering on embedding matrix. Returns list of ID sets."""

    async def _summarize_cluster(self, items: list[dict], level: int) -> dict:
        """LLM call to summarize a cluster. Returns {label, summary, embedding}."""

    async def _summarize_clusters_batch(self, clusters: list, level: int) -> list[dict]:
        """Parallel LLM calls for all clusters at a level."""

    def _should_recurse(self, num_clusters: int, level: int) -> bool:
        """Stop when ≤7 clusters or level ≥3."""
```

**ClusterTree data structure:**
```python
@dataclass
class ClusterTreeNode:
    id: uuid.UUID
    level: int  # 0=chunk, 1=topic, 2=theme, 3=root
    label: str  # LLM-generated label (2-5 words)
    summary: str  # LLM-generated summary
    embedding: list[float]  # 384-dim
    children: list[ClusterTreeNode]  # child nodes
    chunk_ids: list[uuid.UUID]  # leaf chunk IDs (for Level 0 nodes)
    document_ids: list[uuid.UUID]  # unique documents contributing to this cluster
    chunk_count: int  # total chunks in subtree
    coverage_pct: float  # % of total project chunks
```

#### 1.2 Create ClusterHierarchy Model

**File:** `backend/apps/graph/models.py` (add to existing)

```python
class ClusterHierarchy(models.Model):
    """Stores the hierarchical cluster tree for a project."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='cluster_hierarchies')
    version = models.IntegerField(default=1)
    status = models.CharField(max_length=20)  # building | ready | failed
    tree = models.JSONField()  # Serialized ClusterTreeNode tree
    metadata = models.JSONField(default=dict)  # {model, duration_ms, total_chunks, total_clusters, levels}
    is_current = models.BooleanField(default=True)  # Latest version flag
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['project', '-created_at']),
            models.Index(fields=['project', 'is_current']),
        ]
```

#### 1.3 Create ProjectInsight Model

**File:** `backend/apps/graph/models.py` (add to existing)

```python
class ProjectInsight(models.Model):
    """Agent-discovered observations about a project's knowledge base."""

    class InsightType(models.TextChoices):
        TENSION = 'tension', 'Tension'  # Cross-document/cluster contradiction
        BLIND_SPOT = 'blind_spot', 'Blind Spot'  # Coverage gap
        PATTERN = 'pattern', 'Pattern'  # Recurring theme across cases
        STALE_FINDING = 'stale_finding', 'Stale Finding'  # Invalidated by case results
        CONNECTION = 'connection', 'Connection'  # Unexpected link between clusters

    class InsightSource(models.TextChoices):
        AGENT_DISCOVERY = 'agent_discovery'
        CASE_PROMOTION = 'case_promotion'
        USER_CREATED = 'user_created'

    class InsightStatus(models.TextChoices):
        ACTIVE = 'active'
        ACKNOWLEDGED = 'acknowledged'
        RESOLVED = 'resolved'
        DISMISSED = 'dismissed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='insights')
    insight_type = models.CharField(max_length=20, choices=InsightType.choices)
    title = models.CharField(max_length=200)  # Short description
    content = models.TextField()  # Detailed explanation
    source_type = models.CharField(max_length=20, choices=InsightSource.choices)
    source_chunks = models.ManyToManyField('documents.DocumentChunk', blank=True)  # Evidence
    source_cluster_ids = models.JSONField(default=list)  # Cluster IDs involved
    source_case = models.ForeignKey('cases.Case', null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=InsightStatus.choices, default='active')
    confidence = models.FloatField(default=0.7)  # Agent's confidence
    metadata = models.JSONField(default=dict)  # {model, prompt_tokens, etc.}
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['project', 'insight_type']),
            models.Index(fields=['project', '-created_at']),
        ]
```

#### 1.4 Wire Hierarchical Clustering into Document Upload Flow

**File:** `backend/apps/documents/services.py` (modify)

Currently, after chunking + embedding, the flow calls `extract_nodes_from_document()`. Change this to:

1. After chunking + embedding completes:
   - Generate thematic summary (keep existing fast path, ~3s)
   - Schedule hierarchical clustering (async, runs in background)
   - **Do NOT call `extract_nodes_from_document()`** at the project level
2. Hierarchical clustering runs:
   - Fetches all project chunks
   - Builds hierarchy
   - Stores as `ClusterHierarchy` (version incremented, `is_current=True` on new, `False` on old)
3. After hierarchy is built:
   - The thematic summary can be regenerated FROM the hierarchy (or the hierarchy replaces the thematic summary entirely)

**Staleness:** When new documents are uploaded, mark `ClusterHierarchy.is_current` as needing rebuild. Use same debounce pattern as `ProjectSummary.mark_stale()` (30s cooldown).

#### 1.5 Hierarchical Summary Generation

**File:** `backend/apps/graph/hierarchical_summary.py` (new)

The hierarchy already has summaries at every level. But we also want a project-level overview that synthesizes everything. This replaces the current `generate_summary()` full pipeline.

```python
class HierarchicalSummaryService:
    async def generate_project_overview(self, project_id: uuid.UUID, hierarchy: ClusterHierarchy) -> ProjectSummary:
        """Generate project summary from hierarchy tree."""
        # 1. Collect Level 2 (theme) summaries
        # 2. LLM call: synthesize themes into overview narrative
        # 3. Identify attention items from cross-theme analysis
        # 4. Store as ProjectSummary with status=FULL

    async def generate_level_summary(self, node: ClusterTreeNode, context: str) -> str:
        """Generate summary for a single hierarchy node from its children."""
        # Used during hierarchy building
```

**Summary sections (maps to existing ProjectSummary.sections):**
- `overview`: Synthesized from Level 2 themes
- `key_findings`: Each Level 2 theme becomes a finding, with Level 1 topics as supporting detail
- `emerging_picture`: Cross-theme connections and synthesis
- `attention_needed`: Populated by background agent insights (ProjectInsight records)
- `coverage_gaps`: Identified during hierarchy building (thin clusters, single-document clusters)
- `what_changed`: Diff between current and previous hierarchy version

#### 1.6 Background Agent for Insight Discovery

**File:** `backend/apps/graph/insight_agent.py` (new)

A periodic agent that analyzes the project's hierarchical clusters and produces `ProjectInsight` records.

**Triggers:**
- After hierarchy is built/rebuilt
- Periodically (e.g., daily for active projects)
- After a case is resolved (check for stale findings)

**What it looks for:**

1. **Cross-cluster tensions:** Take representative chunks from different clusters, look for contradictions. Send pairs of cluster summaries to LLM: "Do these clusters contain contradictory claims? If so, describe the tension."

2. **Coverage gaps:** Clusters with few chunks, single-document clusters, topics mentioned in one cluster but not explored. Heuristic + LLM verification.

3. **Patterns across cases:** If project has resolved cases, look for recurring themes in case findings. "Cases X, Y, and Z all surfaced concerns about operational complexity. This is a pattern."

4. **Stale findings:** When a case challenges an assumption or resolves a tension, check if project documents still assert the challenged assumption. Flag as stale.

**Implementation approach:**
```python
class InsightDiscoveryAgent:
    async def run(self, project_id: uuid.UUID) -> list[ProjectInsight]:
        hierarchy = ClusterHierarchy.objects.filter(project_id=project_id, is_current=True).first()
        if not hierarchy:
            return []

        insights = []
        insights.extend(await self._detect_cross_cluster_tensions(hierarchy))
        insights.extend(await self._detect_coverage_gaps(hierarchy))
        insights.extend(await self._detect_case_patterns(project_id))

        # Deduplicate against existing active insights
        # Store new insights
        return insights
```

### Phase 2: Project Landscape Frontend

#### 2.1 Create Hierarchical Landscape View

**File:** `frontend/src/components/workspace/project/ProjectLandscapeView.tsx` (new)

This replaces the graph visualization at the project level. It's a zoomable, explorable view of the cluster hierarchy.

**Design approach: Nested cards with progressive disclosure** (not treemap or circle packing — text-heavy content needs readable layouts).

**Structure:**
```
┌─────────────────────────────────────────────┐
│ Project Overview (Level 3 - root narrative) │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────┐  ┌──────────────┐         │
│  │ Theme A      │  │ Theme B      │         │
│  │ 2-line synth │  │ 2-line synth │  ...    │
│  │ 45% coverage │  │ 30% coverage │         │
│  │ 3 docs       │  │ 2 docs       │         │
│  └──────────────┘  └──────────────┘         │
│                                             │
│  Click a theme to expand ↓                  │
│                                             │
│  ┌──────────────────────────────────┐       │
│  │ Theme A (expanded)               │       │
│  │ Full synthesis paragraph         │       │
│  │                                  │       │
│  │  ┌─────────┐ ┌─────────┐        │       │
│  │  │ Topic 1 │ │ Topic 2 │ ...    │       │
│  │  │ summary │ │ summary │        │       │
│  │  │ 5 chunks│ │ 8 chunks│        │       │
│  │  └─────────┘ └─────────┘        │       │
│  │                                  │       │
│  │  Click a topic to see sources ↓  │       │
│  │                                  │       │
│  │  ┌──────────────────────┐        │       │
│  │  │ Topic 1 (expanded)   │        │       │
│  │  │ Full summary         │        │       │
│  │  │                      │        │       │
│  │  │ Source: doc1.pdf p.3  │        │       │
│  │  │ "Actual chunk text..." │      │       │
│  │  │                      │        │       │
│  │  │ Source: doc2.pdf p.7  │        │       │
│  │  │ "Another chunk..."   │        │       │
│  │  └──────────────────────┘        │       │
│  └──────────────────────────────────┘       │
│                                             │
│  ┌──────────────────────────────────┐       │
│  │ Insights (from ProjectInsight)   │       │
│  │                                  │       │
│  │ ⚡ Tension: Docs disagree on X   │       │
│  │ 🔍 Blind spot: No coverage of Y  │       │
│  │ 📊 Pattern: Z keeps recurring    │       │
│  └──────────────────────────────────┘       │
└─────────────────────────────────────────────┘
```

**Component hierarchy:**
```
ProjectLandscapeView
├── LandscapeOverview (root narrative, top-level stats)
├── ThemeGrid (Level 2 clusters as cards)
│   └── ThemeCard (expandable)
│       ├── ThemeHeader (label, coverage %, doc count)
│       ├── ThemeSynthesis (summary text, shown on expand)
│       └── TopicList (Level 1 clusters)
│           └── TopicCard (expandable)
│               ├── TopicHeader (label, chunk count)
│               ├── TopicSummary (1-3 sentence summary)
│               └── ChunkList (Level 0 — actual source text)
│                   └── ChunkCard (document attribution, chunk text)
├── InsightsPanel (ProjectInsight records)
│   └── InsightCard (type icon, title, content, action buttons)
└── CoverageBar (visual indicator of theme coverage distribution)
```

**Props:**
```typescript
interface ProjectLandscapeViewProps {
  hierarchy: ClusterHierarchy;  // The tree data
  insights: ProjectInsight[];  // Agent-discovered observations
  isBuilding: boolean;  // Hierarchy is being built
  onOpenCase: (context?: { themeId?: string; insightId?: string }) => void;
  onAcknowledgeInsight: (insightId: string) => void;
  onDismissInsight: (insightId: string) => void;
}
```

**Animations (Framer Motion):**
- Theme cards: staggered entrance on load
- Expand/collapse: `AnimatePresence` with height animation
- Topic cards within expanded theme: staggered with delay
- Chunk text: fade in on topic expand
- Insights: slide in from right

#### 2.2 TypeScript Types

**File:** `frontend/src/lib/types/hierarchy.ts` (new)

```typescript
interface ClusterTreeNode {
  id: string;
  level: number;  // 0=chunk, 1=topic, 2=theme, 3=root
  label: string;
  summary: string;
  children: ClusterTreeNode[];
  chunk_ids: string[];
  document_ids: string[];
  chunk_count: number;
  coverage_pct: number;
}

interface ClusterHierarchy {
  id: string;
  project_id: string;
  version: number;
  status: 'building' | 'ready' | 'failed';
  tree: ClusterTreeNode;  // Root node
  metadata: {
    total_chunks: number;
    total_clusters: number;
    levels: number;
    duration_ms: number;
  };
  created_at: string;
}

interface ProjectInsight {
  id: string;
  project_id: string;
  insight_type: 'tension' | 'blind_spot' | 'pattern' | 'stale_finding' | 'connection';
  title: string;
  content: string;
  source_type: 'agent_discovery' | 'case_promotion' | 'user_created';
  source_cluster_ids: string[];
  status: 'active' | 'acknowledged' | 'resolved' | 'dismissed';
  confidence: number;
  created_at: string;
}
```

#### 2.3 API Endpoints

**File:** `backend/apps/graph/views.py` (add endpoints)

```
GET /api/projects/{project_id}/hierarchy/
  → Returns current ClusterHierarchy (is_current=True)
  → Include chunk text for Level 0 nodes (with pagination for large clusters)

POST /api/projects/{project_id}/hierarchy/rebuild/
  → Triggers async hierarchy rebuild

GET /api/projects/{project_id}/insights/
  → Returns active ProjectInsight records
  → Filterable by type, status

PATCH /api/projects/{project_id}/insights/{insight_id}/
  → Update status (acknowledge, resolve, dismiss)
```

**File:** `frontend/src/lib/api/projects.ts` (add methods)

```typescript
projectsAPI.getHierarchy(projectId: string): Promise<ClusterHierarchy>
projectsAPI.rebuildHierarchy(projectId: string): Promise<void>
projectsAPI.getInsights(projectId: string, filters?): Promise<ProjectInsight[]>
projectsAPI.updateInsight(projectId: string, insightId: string, updates): Promise<ProjectInsight>
```

#### 2.4 Update ProjectHomePage

**File:** `frontend/src/components/workspace/project/ProjectHomePage.tsx` (modify)

Replace the current layout with:
1. `ProjectLandscapeView` as the main content area (replaces ProjectSummaryView + graph)
2. Keep: case cards, scoped chat input, action items
3. Remove: GraphCanvas at project level, graph health bar at project level
4. Add: InsightsPanel showing active insights with action buttons

The project route (`frontend/src/app/(app)/projects/[projectId]/page.tsx`) needs to fetch hierarchy data via React Query:

```typescript
const { data: hierarchy, isLoading: hierarchyLoading } = useQuery({
  queryKey: ['hierarchy', projectId],
  queryFn: () => projectsAPI.getHierarchy(projectId),
});

const { data: insights } = useQuery({
  queryKey: ['insights', projectId],
  queryFn: () => projectsAPI.getInsights(projectId),
});
```

### Phase 3: Remove Project-Level Extraction

#### 3.1 Remove Extraction Trigger from Document Upload

**File:** `backend/apps/documents/services.py` (modify)

Remove the call to `extract_nodes_from_document()` that fires after chunking. The chunking + embedding step remains. After chunking:
1. Trigger thematic summary (keep for fast feedback)
2. Schedule hierarchical clustering (async)
3. Do NOT extract nodes

#### 3.2 Update ProjectSummary Pipeline

**File:** `backend/apps/graph/summary_service.py` (modify)

- Remove the `FULL` summary generation path that depends on graph nodes
- Replace with hierarchy-based summary generation (calls `HierarchicalSummaryService`)
- Keep `THEMATIC` as the fast-path (it already works with chunks)
- `FULL` now means "generated from hierarchy" instead of "generated from graph"
- Keep staleness/versioning infrastructure

#### 3.3 Update ProjectSummaryView

**File:** `frontend/src/components/workspace/project/ProjectSummaryView.tsx` (modify)

- Remove citation popovers that link to graph nodes (`[nodeId:UUID]` format)
- Replace with citations that link to cluster hierarchy nodes or source chunks
- Citation click behavior: instead of jumping to graph, expand the relevant theme/topic in the landscape view

#### 3.4 Keep Graph for Cases

The `GraphCanvas`, `GraphNodeCard`, `ClusterNode`, edge components, `useGraphLayout` — all of these remain. They are used in the case workspace view. The graph is a case-level tool.

---

## Migration Considerations

1. **Existing projects with extracted nodes:** Keep existing nodes in the database. They don't need to be deleted. They just won't be displayed at the project level anymore. When cases reference them via `CaseNodeReference`, they still work.

2. **ProjectSummary compatibility:** The `ProjectSummary` model stays. Its `sections` field format is compatible. The `clusters` field will now store hierarchy references instead of node clusters.

3. **Thematic summary as bridge:** The existing thematic summary (chunk-based) serves as the fast initial view while the full hierarchy builds. This is already the pattern today.

---

## Dependencies

- **Plan 3 (Case Extraction)** depends on this: case extraction needs to pull relevant chunks from the hierarchy. This plan must provide an API for "given a query, return the most relevant chunks from the hierarchy."
- **Plan 2 (Companion)** is independent: the companion works with or without the hierarchy. But the companion can reference hierarchy themes in chat context.

---

## Definition of Done

1. Documents upload → chunks + embeddings (existing) → hierarchical clustering (new) → multi-level tree stored
2. Project home page shows landscape view with expandable themes → topics → chunks
3. ProjectInsight model exists; background agent produces at least tension detection and coverage gap analysis
4. Insights appear on project home page
5. Project-level node extraction is disabled
6. Project summary is generated from hierarchy, not from graph nodes
7. Existing case graph functionality is unaffected
8. All existing tests pass (or are updated for new architecture)
