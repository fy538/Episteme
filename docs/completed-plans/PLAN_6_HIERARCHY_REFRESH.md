# Plan 6: Document-Aware Hierarchy Refresh + Change Detection

## Goal
When users add new documents over time, the project hierarchy should **evolve** and users should see **what changed**. This makes Episteme feel like a living knowledge base rather than a one-shot analysis.

---

## Architecture Overview

```
New document uploaded → chunked + embedded
        ↓
build_cluster_hierarchy_task dispatched (already happens)
        ↓
CHANGE: Build stores document manifest in metadata
CHANGE: Diff computed between old and new hierarchy
CHANGE: Insight agent runs with diff context (new/changed/merged)
        ↓
Frontend: ProjectLandscapeView shows change indicators
Frontend: "What changed" card on project dashboard
```

---

## Current State

| Component | File | Status |
|-----------|------|--------|
| Hierarchy build | `backend/apps/graph/hierarchical_clustering.py` | Full rebuild every time, no incremental |
| Build trigger | `backend/tasks/workflows.py:261` | Auto-dispatched after doc upload |
| Manual trigger | `POST /api/v2/projects/{pid}/hierarchy/rebuild/` | Returns 202, dispatches Celery task |
| ClusterHierarchy model | `backend/apps/graph/models.py:563-611` | Has `version`, `is_current`, `metadata` JSONField |
| Insight agent | `backend/apps/graph/insight_agent.py` | Runs after build, dismisses stale insights |
| Stale check | `build_cluster_hierarchy_task` | Checks if new chunks added during build, re-dispatches |
| Landscape view | `frontend/src/components/workspace/project/ProjectLandscapeView.tsx` | Shows current state only, no diffs |
| Metadata | `ClusterHierarchy.metadata` | Stores `total_chunks, total_clusters, levels, duration_ms` — no doc tracking |

**Key finding:** The system already versions hierarchies and auto-dismisses stale insights. The missing pieces are: (a) document manifest tracking, (b) diff computation, (c) insight agent diff awareness, (d) frontend change visualization.

---

## Implementation Steps

### Step 1: Track Document Manifest in Hierarchy Metadata

**File: `backend/apps/graph/hierarchical_clustering.py`**

In `_serialize_tree()`, extend the metadata to include a document manifest:

```python
def _serialize_tree(self, root, start_time, total_chunks, total_clusters, levels,
                    document_manifest=None):
    return {
        'tree': _clean_node(root),
        'metadata': {
            'total_chunks': total_chunks,
            'total_clusters': total_clusters,
            'levels': levels,
            'duration_ms': int((time.time() - start_time) * 1000),
            # NEW: Document tracking
            'document_manifest': document_manifest or [],
            'document_count': len(document_manifest) if document_manifest else 0,
        },
    }
```

In `build_hierarchy()`, collect the manifest before building:

```python
async def build_hierarchy(self, project_id):
    start_time = time.time()

    # 1. Load chunks
    chunks, total_chunks, total_documents, project_title, project_description = (
        self._load_chunks(project_id)
    )

    # NEW: Build document manifest
    document_manifest = self._build_document_manifest(chunks)

    # ... rest of build logic ...

    return self._serialize_tree(
        root, start_time, total_chunks, total_clusters, levels,
        document_manifest=document_manifest,
    )
```

Add the manifest builder:

```python
def _build_document_manifest(self, chunks: list) -> list:
    """Build a manifest of documents included in this hierarchy build."""
    from collections import Counter
    doc_chunks = Counter()
    doc_titles = {}
    for chunk in chunks:
        doc_id = chunk['document_id']
        doc_chunks[doc_id] += 1
        doc_titles[doc_id] = chunk['document_title']

    return [
        {
            'document_id': doc_id,
            'document_title': doc_titles[doc_id],
            'chunk_count': count,
        }
        for doc_id, count in doc_chunks.items()
    ]
```

This costs nothing (just iterating chunks we already loaded) and gives us the foundation for diff computation.

---

### Step 2: Compute Hierarchy Diff

**File: `backend/apps/graph/hierarchy_diff.py`** (NEW)

After a new hierarchy is built, compare it against the previous version:

```python
"""
Hierarchy diff computation — compare two hierarchy versions to detect
what changed: new themes, merged themes, expanded topics, new documents.
"""
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Set
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class HierarchyDiff:
    """Summary of changes between two hierarchy versions."""
    # Theme-level changes
    new_themes: List[dict] = field(default_factory=list)       # Themes in new but not old
    removed_themes: List[dict] = field(default_factory=list)   # Themes in old but not new
    merged_themes: List[dict] = field(default_factory=list)    # Old themes absorbed into new ones
    expanded_themes: List[dict] = field(default_factory=list)  # Themes with significantly more chunks

    # Topic-level changes
    new_topics: List[dict] = field(default_factory=list)
    removed_topics: List[dict] = field(default_factory=list)

    # Document-level changes
    new_documents: List[dict] = field(default_factory=list)    # Docs in new manifest but not old
    removed_documents: List[dict] = field(default_factory=list)

    # Summary stats
    chunks_added: int = 0
    chunks_removed: int = 0
    themes_before: int = 0
    themes_after: int = 0

    @property
    def has_changes(self) -> bool:
        return bool(
            self.new_themes or self.removed_themes or self.merged_themes
            or self.expanded_themes or self.new_documents
        )

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)

    def summary_text(self) -> str:
        """Human-readable summary for the project dashboard."""
        parts = []
        if self.new_themes:
            labels = [t['label'] for t in self.new_themes[:3]]
            parts.append(f"{len(self.new_themes)} new theme(s): {', '.join(labels)}")
        if self.merged_themes:
            parts.append(f"{len(self.merged_themes)} theme(s) merged")
        if self.expanded_themes:
            labels = [t['label'] for t in self.expanded_themes[:3]]
            parts.append(f"{len(self.expanded_themes)} theme(s) expanded: {', '.join(labels)}")
        if self.new_documents:
            titles = [d['document_title'] for d in self.new_documents[:3]]
            parts.append(f"{len(self.new_documents)} new document(s): {', '.join(titles)}")
        if not parts:
            return "No significant changes"
        return "; ".join(parts)


def compute_hierarchy_diff(old_hierarchy, new_hierarchy) -> HierarchyDiff:
    """Compare two ClusterHierarchy instances and return a diff.

    Uses theme/topic label similarity (fuzzy matching) to detect
    renames, merges, and expansions rather than relying on cluster IDs
    (which change every rebuild).
    """
    diff = HierarchyDiff()

    old_tree = (old_hierarchy.tree if old_hierarchy else {}) or {}
    new_tree = (new_hierarchy.tree if new_hierarchy else {}) or {}
    old_meta = (old_hierarchy.metadata if old_hierarchy else {}) or {}
    new_meta = (new_hierarchy.metadata if new_hierarchy else {}) or {}

    # --- Document diff ---
    old_docs = {d['document_id'] for d in old_meta.get('document_manifest', [])}
    new_docs_list = new_meta.get('document_manifest', [])
    new_docs = {d['document_id'] for d in new_docs_list}

    diff.new_documents = [d for d in new_docs_list if d['document_id'] not in old_docs]
    old_docs_list = old_meta.get('document_manifest', [])
    diff.removed_documents = [d for d in old_docs_list if d['document_id'] not in new_docs]

    # --- Chunk counts ---
    diff.chunks_added = max(0,
        new_meta.get('total_chunks', 0) - old_meta.get('total_chunks', 0))
    diff.chunks_removed = max(0,
        old_meta.get('total_chunks', 0) - new_meta.get('total_chunks', 0))

    # --- Theme diff (Level 2 nodes) ---
    old_themes = old_tree.get('children', [])
    new_themes = new_tree.get('children', [])
    diff.themes_before = len(old_themes)
    diff.themes_after = len(new_themes)

    # Match themes by label similarity
    matched_old = set()
    matched_new = set()

    for i, new_theme in enumerate(new_themes):
        best_match = None
        best_score = 0.0
        for j, old_theme in enumerate(old_themes):
            if j in matched_old:
                continue
            score = _label_similarity(new_theme.get('label', ''), old_theme.get('label', ''))
            if score > best_score:
                best_score = score
                best_match = j

        if best_match is not None and best_score >= 0.5:
            # Matched — check if expanded
            matched_old.add(best_match)
            matched_new.add(i)
            old_theme = old_themes[best_match]
            chunk_growth = new_theme.get('chunk_count', 0) - old_theme.get('chunk_count', 0)
            if chunk_growth > 0 and chunk_growth >= old_theme.get('chunk_count', 1) * 0.3:
                diff.expanded_themes.append({
                    'label': new_theme.get('label', ''),
                    'old_chunk_count': old_theme.get('chunk_count', 0),
                    'new_chunk_count': new_theme.get('chunk_count', 0),
                    'growth': chunk_growth,
                })

    # Unmatched new themes = genuinely new
    for i, theme in enumerate(new_themes):
        if i not in matched_new:
            diff.new_themes.append({
                'label': theme.get('label', ''),
                'summary': theme.get('summary', ''),
                'chunk_count': theme.get('chunk_count', 0),
            })

    # Unmatched old themes — check if they were merged into new themes
    for j, old_theme in enumerate(old_themes):
        if j not in matched_old:
            # Check if old theme's chunks appear in any new theme (merge detection)
            old_chunk_set = set(old_theme.get('chunk_ids', []))
            merged_into = None
            for new_theme in new_themes:
                new_chunk_set = set(new_theme.get('chunk_ids', []))
                overlap = len(old_chunk_set & new_chunk_set)
                if overlap >= len(old_chunk_set) * 0.5:
                    merged_into = new_theme.get('label', '')
                    break

            if merged_into:
                diff.merged_themes.append({
                    'old_label': old_theme.get('label', ''),
                    'merged_into': merged_into,
                })
            else:
                diff.removed_themes.append({
                    'label': old_theme.get('label', ''),
                    'chunk_count': old_theme.get('chunk_count', 0),
                })

    return diff


def _label_similarity(a: str, b: str) -> float:
    """Fuzzy label similarity using SequenceMatcher."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()
```

---

### Step 3: Integrate Diff into Build Task

**File: `backend/apps/graph/tasks.py`** (in `build_cluster_hierarchy_task`)

After the new hierarchy is built and saved, compute the diff:

```python
# After saving new hierarchy and marking as current:

# Compute diff against previous version
from apps.graph.hierarchy_diff import compute_hierarchy_diff

previous = ClusterHierarchy.objects.filter(
    project_id=project_id,
    is_current=False,
).order_by('-version').first()

diff = compute_hierarchy_diff(previous, new_hierarchy)

if diff.has_changes:
    # Store diff in metadata
    new_hierarchy.metadata['diff'] = diff.to_dict()
    new_hierarchy.metadata['diff_summary'] = diff.summary_text()
    new_hierarchy.save(update_fields=['metadata'])

    logger.info(
        "hierarchy_diff_computed",
        extra={
            'project_id': str(project_id),
            'version': new_hierarchy.version,
            'new_themes': len(diff.new_themes),
            'merged_themes': len(diff.merged_themes),
            'expanded_themes': len(diff.expanded_themes),
            'new_documents': len(diff.new_documents),
        },
    )
```

---

### Step 4: Enhance Insight Agent with Diff Awareness

**File: `backend/apps/graph/insight_agent.py`**

The insight agent currently discovers tensions and gaps from scratch each time. Enhance it to use the diff for targeted, more meaningful insights:

```python
async def run(self, project_id, hierarchy_diff=None):
    """
    Main entry point. Now accepts optional diff for targeted insights.

    With diff:
    - Only check tension pairs involving NEW or EXPANDED themes (skip stable pairs)
    - Generate "theme emerged" insights for genuinely new themes
    - Generate "theme merged" insights for merged themes

    Without diff (first build):
    - Full tension detection across all theme pairs (existing behavior)
    """
    # ... existing hierarchy loading ...

    self._dismiss_stale_insights(project_id, tree)

    insights = []

    # 1. Detect tensions — scoped to changed themes if diff available
    if hierarchy_diff and hierarchy_diff.has_changes:
        changed_labels = set()
        for t in hierarchy_diff.new_themes:
            changed_labels.add(t['label'])
        for t in hierarchy_diff.expanded_themes:
            changed_labels.add(t['label'])

        # Only check pairs involving at least one changed theme
        tension_insights = await self._detect_tensions(
            project_id, themes,
            filter_labels=changed_labels if changed_labels else None,
        )
    else:
        tension_insights = await self._detect_tensions(project_id, themes)

    insights.extend(tension_insights)

    # 2. NEW: Theme emergence insights
    if hierarchy_diff:
        for new_theme in hierarchy_diff.new_themes:
            insights.append(ProjectInsight(
                project_id=project_id,
                insight_type=InsightType.PATTERN,
                title=f"New theme emerged: {new_theme['label']}",
                content=(
                    f"A new topic area appeared in your project: \"{new_theme['label']}\" "
                    f"({new_theme['summary'][:150]}). "
                    f"This covers {new_theme['chunk_count']} passages."
                ),
                source_type=InsightSource.AGENT_DISCOVERY,
                status=InsightStatus.ACTIVE,
                confidence=0.8,
            ))

        for merged in hierarchy_diff.merged_themes:
            insights.append(ProjectInsight(
                project_id=project_id,
                insight_type=InsightType.CONNECTION,
                title=f"Themes merged: \"{merged['old_label']}\" → \"{merged['merged_into']}\"",
                content=(
                    f"The theme \"{merged['old_label']}\" has been absorbed into "
                    f"\"{merged['merged_into']}\", suggesting these topics are more "
                    f"closely related than initially apparent."
                ),
                source_type=InsightSource.AGENT_DISCOVERY,
                status=InsightStatus.ACTIVE,
                confidence=0.7,
            ))

    # 3. Coverage gaps (existing)
    # ... existing gap detection ...

    # 4. Deduplicate and save
    new_insights = self._deduplicate(project_id, insights)
    # ... existing bulk_create ...
```

Update `_detect_tensions()` to accept an optional `filter_labels` parameter:

```python
async def _detect_tensions(self, project_id, themes, filter_labels=None):
    """
    filter_labels: if provided, only check pairs where at least one
    theme's label is in this set. Saves LLM calls on re-builds.
    """
    pairs = []
    for i in range(len(themes)):
        for j in range(i + 1, len(themes)):
            if filter_labels:
                label_a = themes[i].get('label', '')
                label_b = themes[j].get('label', '')
                if label_a not in filter_labels and label_b not in filter_labels:
                    continue  # Skip — neither theme changed
            pairs.append((themes[i], themes[j]))

    # ... rest of existing logic (semaphore, LLM calls, etc.)
```

---

### Step 5: Pass Diff from Task to Insight Agent

**File: `backend/apps/graph/tasks.py`**

Update the insight discovery dispatch to pass the diff:

```python
# After computing diff (Step 3):
# Instead of: run_insight_discovery_task.delay(project_id=project_id)
# Do:
diff_dict = diff.to_dict() if diff.has_changes else None
run_insight_discovery_task.delay(
    project_id=str(project_id),
    hierarchy_diff=diff_dict,
)
```

Update `run_insight_discovery_task` to accept and reconstruct the diff:

```python
@shared_task
def run_insight_discovery_task(project_id: str, hierarchy_diff: dict = None):
    from apps.graph.insight_agent import InsightDiscoveryAgent
    from apps.graph.hierarchy_diff import HierarchyDiff

    diff = None
    if hierarchy_diff:
        diff = HierarchyDiff(**hierarchy_diff)

    agent = InsightDiscoveryAgent()
    async_to_sync(agent.run)(uuid.UUID(project_id), hierarchy_diff=diff)
```

---

### Step 6: Expose Diff via API

**File: `backend/apps/graph/views.py`**

The hierarchy API endpoint already returns `metadata`. Since we store the diff in `metadata['diff']`, it's automatically available. But add a convenience field:

```python
# In the hierarchy serializer or view:
class ClusterHierarchySerializer(serializers.ModelSerializer):
    diff_summary = serializers.SerializerMethodField()

    def get_diff_summary(self, obj):
        meta = obj.metadata or {}
        return meta.get('diff_summary', None)

    class Meta:
        model = ClusterHierarchy
        fields = [...existing..., 'diff_summary']
```

---

### Step 7: Frontend — Show Diff on Project Dashboard

**File: `frontend/src/components/workspace/project/ProjectLandscapeView.tsx`**

Add a "What Changed" card at the top of the landscape view when a diff exists:

```typescript
// New prop:
interface ProjectLandscapeViewProps {
    hierarchy: ClusterHierarchy;
    insights: ProjectInsight[];
    // ... existing props ...
}

// In the component, extract diff from hierarchy metadata:
const diff = hierarchy.metadata?.diff;
const diffSummary = hierarchy.metadata?.diff_summary;

// Render change card:
{diff && diff.new_themes?.length + diff.expanded_themes?.length + diff.new_documents?.length > 0 && (
    <HierarchyChangeCard
        diff={diff}
        summary={diffSummary}
        version={hierarchy.version}
        onDismiss={() => setDiffDismissed(true)}
    />
)}
```

---

### Step 8: Create HierarchyChangeCard Component

**File: `frontend/src/components/workspace/project/HierarchyChangeCard.tsx`** (NEW)

A card that shows what changed since the last hierarchy build:

```typescript
interface HierarchyChangeCardProps {
    diff: HierarchyDiff;
    summary: string;
    version: number;
    onDismiss: () => void;
}
```

**Visual design:**

```
┌─────────────────────────────────────────────────────────┐
│ 🔄 Knowledge base updated (v3)                    [✕]  │
│                                                         │
│  📄 2 new documents: "Q3 Report", "Competitor Brief"    │
│  🌿 1 new theme: "Market Expansion Strategy"            │
│  📈 2 themes expanded: "Revenue Model", "Team Scaling"  │
│  🔗 1 theme merged: "Hiring" → "Team & Organization"   │
│                                                         │
│  4 new insights discovered                              │
└─────────────────────────────────────────────────────────┘
```

Each line is expandable for details. Uses Framer Motion for smooth entry animation. Dismissible (persisted in localStorage keyed by `hierarchy_version_{projectId}`).

---

### Step 9: Highlight New/Changed Themes in Landscape

**File: `frontend/src/components/workspace/project/ProjectLandscapeView.tsx`**

When a diff exists, add visual indicators to theme cards:

```typescript
// For each theme card, check if it's in the diff:
const isNewTheme = diff?.new_themes?.some(t => t.label === theme.label);
const isExpanded = diff?.expanded_themes?.some(t => t.label === theme.label);

// Add badge:
{isNewTheme && (
    <span className="text-xs px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded-full">
        New
    </span>
)}
{isExpanded && (
    <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded-full">
        +{expandedInfo.growth} chunks
    </span>
)}
```

---

### Step 10: Auto-Refresh Trigger After Multiple Documents

**File: `backend/tasks/workflows.py`**

Currently every document upload triggers a full hierarchy rebuild. For efficiency, add debouncing — if multiple documents are uploaded in quick succession, only rebuild once:

```python
# Instead of immediate dispatch:
# build_cluster_hierarchy_task.delay(project_id=str(document.project_id))

# Use a delayed dispatch with dedup:
from django.core.cache import cache

HIERARCHY_REBUILD_DELAY = 30  # seconds
cache_key = f'hierarchy_rebuild_pending:{document.project_id}'

if not cache.get(cache_key):
    cache.set(cache_key, True, timeout=HIERARCHY_REBUILD_DELAY)
    build_cluster_hierarchy_task.apply_async(
        kwargs={'project_id': str(document.project_id)},
        countdown=HIERARCHY_REBUILD_DELAY,
    )
    logger.info(
        "hierarchy_rebuild_scheduled",
        extra={
            'project_id': str(document.project_id),
            'delay_seconds': HIERARCHY_REBUILD_DELAY,
        },
    )
```

This means if a user uploads 5 documents in 30 seconds, only one hierarchy rebuild runs (after the last upload + 30s). The existing stale check in the task (chunk_count_before vs after) provides a safety net.

---

## Key Files to Modify/Create

| File | Change |
|------|--------|
| `backend/apps/graph/hierarchical_clustering.py` | Add document manifest to metadata, pass to _serialize_tree |
| `backend/apps/graph/hierarchy_diff.py` | **NEW** — diff computation module |
| `backend/apps/graph/tasks.py` | Compute diff after build, pass to insight agent |
| `backend/apps/graph/insight_agent.py` | Accept diff, scope tension detection, emit emergence insights |
| `backend/apps/graph/views.py` | Add diff_summary to serializer |
| `backend/tasks/workflows.py` | Add debounced rebuild dispatch (30s delay) |
| `frontend/src/components/workspace/project/HierarchyChangeCard.tsx` | **NEW** — "what changed" card |
| `frontend/src/components/workspace/project/ProjectLandscapeView.tsx` | Show change card + theme badges |

---

## Why Full Rebuild (Not Incremental Clustering)

We considered an incremental approach (add new chunks to existing clusters) but decided against it for v1:

1. **Agglomerative clustering is global** — adding new chunks can fundamentally change cluster boundaries. An "add to nearest cluster" heuristic accumulates drift over many updates.
2. **Full rebuild is fast** — with 384-dim embeddings and sklearn, clustering 1000 chunks takes <1 second. The bottleneck is LLM summarization (parallel, 5 concurrent).
3. **LLM summaries need rewriting anyway** — even if clusters don't change, the summary should reflect new content. This means the LLM cost is the same either way.
4. **Diff computation gives us the incremental UX** — users see "what changed" without us needing incremental clustering. The diff is computed post-hoc on the full rebuild results.
5. **Future optimization:** If projects grow to 10k+ chunks, we can add incremental clustering then. For now, the 30-second debounce + full rebuild is simpler and correct.

---

## Edge Cases

1. **First build (no previous version):** Diff is empty, no change card shown, full tension detection runs
2. **All themes are new (major restructure):** Diff shows all themes as new — this is correct, the user should see it
3. **Document deleted:** Not in new manifest → shows as "removed document" in diff
4. **Concurrent uploads during build:** Existing stale check re-dispatches build, diff computed against the last completed version
5. **Very large projects (1000+ chunks):** Full rebuild still works, debouncing prevents redundant builds
6. **Hierarchy build fails:** Diff not computed, previous version stays as `is_current=True`

---

## Testing

1. **Unit test:** `compute_hierarchy_diff()` with mock trees — test new themes, merged themes, expanded themes
2. **Unit test:** `_label_similarity()` matches fuzzy labels correctly
3. **Unit test:** `_build_document_manifest()` produces correct counts
4. **Integration test:** Upload doc → build hierarchy → upload another doc → rebuild → verify diff stored in metadata
5. **Integration test:** Insight agent with diff → only checks pairs involving changed themes
6. **Frontend unit:** HierarchyChangeCard renders correct change types
7. **Frontend unit:** Theme badges show "New" and "+N chunks" correctly
