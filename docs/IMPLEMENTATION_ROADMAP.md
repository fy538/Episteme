# Implementation Status & Roadmap

## ✅ COMPLETE: Backend (Phases 0-2.4)

All backend features are implemented and ready for frontend integration.

### What Works (via API)

**Phase 0-1: Foundation**
- ✅ Event store (immutable, append-only)
- ✅ Auth (JWT)
- ✅ Chat (threads, messages)
- ✅ Cases (durable work objects)
- ✅ Signal extraction from user chat

**Phase 2: Knowledge Management**
- ✅ Projects (top-level containers)
- ✅ Documents (upload, chunk, embed)
- ✅ Evidence (facts from documents)
- ✅ Research-backed chunking (512 tokens)

**Phase 2.3: Knowledge Graph**
- ✅ Signal → depends_on → Signal
- ✅ Signal → contradicts → Signal
- ✅ Evidence → supports/contradicts → Signal
- ✅ Graph traversal utilities
- ✅ Graph query API

**Phase 2.4: Artifacts**
- ✅ Artifact model (block-based, version-controlled)
- ✅ Google ADK agents (research, critique, brief)
- ✅ Generation workflows
- ✅ Block editing with versioning
- ✅ Full provenance tracking

---

## 🔄 PARTIAL: Frontend (Phase 3)

Frontend scaffolding exists with some components, but needs updates for new features.

### What Exists

**Infrastructure:**
- ✅ Next.js 14 + TypeScript
- ✅ Tailwind CSS
- ✅ API client ([`src/lib/api/client.ts`](../frontend/src/lib/api/client.ts))
- ✅ React Query
- ✅ Zustand (state management)

**Pages:**
- ✅ Chat page ([`src/app/chat/page.tsx`](../frontend/src/app/chat/page.tsx))
- ✅ Case page ([`src/app/cases/[caseId]/page.tsx`](../frontend/src/app/cases/[caseId]/page.tsx))
- ✅ Document page

**Components:**
- ✅ ChatInterface
- ✅ MessageList, MessageInput
- ✅ StructureSidebar
- ✅ SignalsList
- ✅ CaseCard
- ✅ DocumentTree
- ✅ BriefEditor (Tiptap-based)

**API Clients:**
- ✅ chatAPI
- ✅ casesAPI
- ✅ signalsAPI
- ✅ documentsAPI
- ✅ inquiriesAPI

### What Needs Adding/Updating

**API Clients (NEW):**
- ❌ evidenceAPI - CRUD + rating + linking
- ❌ artifactsAPI - CRUD + generation + versioning
- ❌ graphAPI - Dependency queries, evidence queries

**Components (NEW):**
- ❌ EvidenceCard - Display evidence with ratings
- ❌ EvidenceList - Filter by type, credibility
- ❌ ArtifactViewer - Render blocks with citations
- ❌ ArtifactVersionSelector - Switch between versions
- ❌ GraphView - Visualize dependencies (optional)
- ❌ GenerationButtons - Trigger research/critique/brief

**Components (UPDATE):**
- ⚠️ SignalsList - Add "Show Evidence" button → graph query
- ⚠️ CaseCard - Show evidence count, artifact count
- ⚠️ DocumentTree - Show evidence extracted count

---

## 📋 Remaining Work Breakdown

### Week 1: API Client Updates

**Create new API clients:**

1. **evidenceAPI** ([`src/lib/api/evidence.ts`](../frontend/src/lib/api/evidence.ts)):
```typescript
export const evidenceAPI = {
  list: (filters) => GET /api/evidence/,
  get: (id) => GET /api/evidence/{id}/,
  rate: (id, rating) => PATCH /api/evidence/{id}/rate/,
  linkSignal: (id, signalId, relationship) => POST /api/evidence/{id}/link-signal/,
  relatedSignals: (id) => GET /api/evidence/{id}/related-signals/,
};
```

2. **artifactsAPI** ([`src/lib/api/artifacts.ts`](../frontend/src/lib/api/artifacts.ts)):
```typescript
export const artifactsAPI = {
  list: (caseId) => GET /api/artifacts/?case_id={caseId},
  get: (id) => GET /api/artifacts/{id}/,
  versions: (id) => GET /api/artifacts/{id}/versions/,
  editBlock: (id, blockId, content) => PATCH /api/artifacts/{id}/edit_block/,
  publish: (id) => POST /api/artifacts/{id}/publish/,
  
  // Generation
  generateResearch: (caseId, topic) => POST /api/artifacts/generate_research/,
  generateCritique: (caseId, signalId) => POST /api/artifacts/generate_critique/,
  generateBrief: (caseId) => POST /api/artifacts/generate_brief/,
};
```

3. **graphAPI** ([`src/lib/api/graph.ts`](../frontend/src/lib/api/graph.ts)):
```typescript
export const graphAPI = {
  signalDependencies: (id) => GET /api/signals/{id}/dependencies/,
  signalEvidence: (id) => GET /api/signals/{id}/evidence/,
  signalContradictions: (id) => GET /api/signals/{id}/contradictions/,
  linkSignals: (id, targetId, relationship) => POST /api/signals/{id}/link/,
};
```

---

### Week 2: Evidence UI

**Create components:**

1. **EvidenceCard** ([`src/components/evidence/EvidenceCard.tsx`](../frontend/src/components/evidence/EvidenceCard.tsx)):
- Display evidence text
- Type badge (Metric, Benchmark, Fact)
- Credibility rating (stars, editable)
- "Show Source" → opens chunk preview
- "Link to Signal" button

2. **EvidenceList** ([`src/components/evidence/EvidenceList.tsx`](../frontend/src/components/evidence/EvidenceList.tsx)):
- List evidence for case
- Filter by type, credibility
- Group by document

3. **ChunkPreview** ([`src/components/evidence/ChunkPreview.tsx`](../frontend/src/components/evidence/ChunkPreview.tsx)):
- Modal showing source chunk
- Highlight evidence text
- Show context (prev/next chunks)

---

### Week 3: Artifact UI

**Create components:**

1. **ArtifactViewer** ([`src/components/artifacts/ArtifactViewer.tsx`](../frontend/src/components/artifacts/ArtifactViewer.tsx)):
- Render blocks (heading, paragraph, list, quote)
- Show citations (hover to see source)
- Edit mode toggle
- Version selector

2. **BlockEditor** ([`src/components/artifacts/BlockEditor.tsx`](../frontend/src/components/artifacts/BlockEditor.tsx)):
- Inline editing for blocks
- Save on blur → creates new version
- Citation autocomplete

3. **GenerationPanel** ([`src/components/artifacts/GenerationPanel.tsx`](../frontend/src/components/artifacts/GenerationPanel.tsx)):
- "Generate Research" button with topic input
- "Red-team This" button (select signal)
- "Create Brief" button
- Progress indicators
- Result preview

---

### Week 4: Integration & Polish

**Update existing components:**

1. Update SignalsList:
- Add "Show Evidence" button
- Display support/contradict counts

2. Update CaseCard:
- Show artifact count
- "Generate Brief" quick action

3. Add GraphView (optional):
- Visualize signal dependencies
- Show evidence links

**Integration tests:**
- Full workflow test (chat → signal → evidence → artifact)
- Generation tests
- Editing tests

---

## 🚀 Quick Start Guide

### Backend is Ready

```bash
# 1. Rebuild with new dependencies
docker-compose build backend
docker-compose up -d

# 2. Run migrations
docker-compose exec backend python manage.py makemigrations
docker-compose exec backend python manage.py migrate

# 3. Test backend
docker-compose exec backend pytest
```

### Frontend Needs Updates

```bash
cd frontend

# 1. Install dependencies (already done)
npm install

# 2. Add new API clients (Week 1 work)
# - src/lib/api/evidence.ts
# - src/lib/api/artifacts.ts  
# - src/lib/api/graph.ts

# 3. Add new components (Weeks 2-3)
# - components/evidence/
# - components/artifacts/
# - components/generation/

# 4. Start dev server
npm run dev
```

---

## 📊 Completion Status

| Phase | Status | Components |
|-------|--------|------------|
| **Phase 0** | ✅ 100% | Event store, Auth, Chat, Cases |
| **Phase 1** | ✅ 100% | Signal extraction, WorkingView |
| **Phase 2.1** | ✅ 100% | Projects, Documents, Chunking |
| **Phase 2.2** | ✅ 100% | Evidence model |
| **Phase 2.3** | ✅ 100% | Knowledge graph |
| **Phase 2.4** | ✅ 100% | Artifacts + ADK agents |
| **Phase 3** | 🔄 40% | Frontend (partial) |

**Backend: 100% Complete**  
**Frontend: 40% Complete** (infrastructure + chat exists, needs Evidence/Artifacts UI)

---

## ⏱️ Time to Dogfooding

**Remaining work: ~3 weeks**

- Week 1: API clients (evidence, artifacts, graph)
- Week 2: Evidence UI components
- Week 3: Artifact UI + generation

After 3 weeks: Full dogfooding capability!

---

## 🎯 Minimum Viable Frontend (1 week alternative)

If you want to dogfood FASTER:

**Week 1 Only:**
- Add evidenceAPI, artifactsAPI clients
- Simple EvidenceList component (table view)
- Simple ArtifactList component (list view)
- Generation buttons in case page

**Skip:**
- Advanced graph visualization
- Fancy block editor
- Polish/animations

**Result:** Can use all backend features, just with simpler UI.

---

## Next Step Options

**Option A: Complete Frontend (3 weeks)**
Implement all remaining components for full experience.

**Option B: Minimal Frontend (1 week)**
Basic UI for all features, iterate later.

**Option C: Backend Testing First**
Test backend thoroughly via API/Postman before frontend.
Record what works/doesn't work.
Then build frontend with known requirements.

**What would you like to do?**

The backend is feature-complete. Frontend can be as polished or minimal as you want for initial dogfooding.
