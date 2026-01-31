# Frontend Audit: Current Scope & Gaps

## What Frontend Should Do (Current Scope)

Based on the product vision and implemented backend, the frontend needs to support the "serious chat" loop:

### Core Loop (Phase 0-1)
1. User chats naturally
2. Signals extracted and displayed
3. User can open a case
4. User sees suggested signals as chips
5. User confirms/rejects/edits signals
6. User sees "what changed" timeline

### Extended Loop (Phase 2)
7. User uploads documents
8. Evidence extracted and displayed
9. User rates evidence credibility
10. User links evidence to signals (graph)

### AI Generation Loop (Phase 2.4)
11. User generates research (AI + web search)
12. User generates critique (red-team)
13. User generates brief (synthesize)
14. User views/edits artifacts
15. Version history tracked

---

## ✅ What Exists

### Pages
- ✅ Landing page (`/`)
- ✅ Chat page (`/chat`)
- ✅ Case workspace (`/cases/[caseId]`)
- ✅ Document viewer (`/cases/[caseId]/documents/[docId]`)

### Core Components

**Chat:**
- ✅ ChatInterface - Main chat UI
- ✅ MessageList - Display messages
- ✅ MessageInput - Send messages

**Structure:**
- ✅ StructureSidebar - Shows signals, case info
- ✅ SignalsList - Display extracted signals
- ✅ CaseCard - Case summary
- ✅ InquirySuggestions - (existing feature)

**Documents:**
- ✅ DocumentTree - Navigation sidebar
- ✅ AIDocumentViewer - View AI-generated docs
- ✅ BriefEditor - Tiptap-based editor

**Evidence (NEW):**
- ✅ EvidenceCard - Display single evidence
- ✅ EvidenceList - Browse/filter evidence

**Artifacts (NEW):**
- ✅ ArtifactViewer - View artifact blocks
- ✅ GenerationPanel - Trigger AI generation

### API Clients
- ✅ client.ts - Base HTTP client
- ✅ chat.ts
- ✅ cases.ts
- ✅ signals.ts
- ✅ documents.ts
- ✅ inquiries.ts
- ✅ evidence.ts (NEW)
- ✅ artifacts.ts (NEW)
- ✅ graph.ts (NEW)

---

## ⚠️ Gaps & Integration Needed

### Gap 1: Signal Chips Actions

**Status:** SignalsList displays signals, but might not have working confirm/reject/edit

**Need to verify:**
```tsx
// In SignalsList.tsx
// Should have:
<button onClick={() => confirmSignal(signal.id)}>Confirm</button>
<button onClick={() => rejectSignal(signal.id)}>Reject</button>
<button onClick={() => editSignal(signal.id)}>Edit</button>
```

**If missing:** Need to integrate signalsAPI.confirm(), .reject(), .edit()

---

### Gap 2: Evidence Integration into Case Page

**Status:** EvidenceList component exists, but not integrated into case workspace

**Need:**
```tsx
// In /cases/[caseId]/page.tsx
// Add tab or section for Evidence:

<Tab label="Evidence">
  <EvidenceList caseId={caseId} />
</Tab>
```

---

### Gap 3: Artifact Integration into Case Page

**Status:** ArtifactViewer exists, but not integrated into case workspace

**Need:**
```tsx
// In /cases/[caseId]/page.tsx
// Add section for Artifacts:

<div>
  <h3>Generated Artifacts</h3>
  {artifacts.map(artifact => (
    <ArtifactCard artifact={artifact} />
  ))}
  
  <GenerationPanel caseId={caseId} />
</div>
```

---

### Gap 4: Document Upload UI

**Status:** Unclear if upload interface exists

**Need to check:**
- Is there a file upload component?
- Can users upload PDFs, DOCX?
- Is there processing status display?

**If missing, need:**
```tsx
<DocumentUpload
  onUpload={(file) => documentsAPI.upload(caseId, file)}
  onProgress={(status) => setStatus(status)}
/>
```

---

### Gap 5: Auth/Login Flow

**Status:** API client has token management, but no login page visible

**Need:**
```tsx
// /app/login/page.tsx
<LoginForm
  onLogin={(username, password) => authAPI.login()}
/>
```

---

### Gap 6: Type Definitions

**Status:** Existing types for Chat, Case, Signal. Need types for Evidence, Artifact.

**Need:**
```typescript
// src/lib/types/evidence.ts
export interface Evidence {
  id: string;
  text: string;
  type: 'metric' | 'benchmark' | 'fact' | 'claim' | 'quote';
  // ...
}

// src/lib/types/artifact.ts
export interface Artifact {
  // ...
}
```

---

### Gap 7: Graph Visualization (Optional)

**Status:** Graph API client exists, but no visualization component

**Need (optional for dogfooding):**
```tsx
<SignalGraphView
  signalId={signal.id}
  onNodeClick={(nodeId) => navigate(nodeId)}
/>
```

This is **NOT critical** for initial dogfooding. Can use text-based dependency view first.

---

## 🎯 What's CRITICAL vs NICE-TO-HAVE

### CRITICAL (Must Have for Dogfooding)

These are essential for the core loop:

1. **Signal Actions** - Confirm/reject/edit buttons working
   - Status: ⚠️ Verify implementation
   - Effort: ~1 hour if missing

2. **Evidence in Case View** - Show extracted evidence
   - Status: ❌ Not integrated
   - Effort: ~2 hours (add tab/section to case page)

3. **Artifact in Case View** - Show generated artifacts
   - Status: ❌ Not integrated
   - Effort: ~2 hours (add artifacts section)

4. **Document Upload** - Upload PDFs/docs
   - Status: ⚠️ Verify exists
   - Effort: ~3 hours if missing

5. **Auth/Login** - User can log in
   - Status: ⚠️ Verify exists
   - Effort: ~2 hours if missing

**Total if all missing: ~1 day of work**

---

### NICE-TO-HAVE (Defer)

These enhance UX but aren't required:

- Graph visualization (React Flow)
- Advanced artifact editing (rich Tiptap)
- Real-time collaboration
- Advanced search
- Export to PDF

---

## 📋 Verification Checklist

Run through these to confirm frontend is ready:

### 1. Can User Chat?
- [ ] Open /chat
- [ ] Send message
- [ ] See response

### 2. Are Signals Extracted?
- [ ] Signals appear in sidebar
- [ ] Click confirm → signal status changes
- [ ] Click reject → signal dismissed

### 3. Can User Create Case?
- [ ] "Open Case" button visible
- [ ] Click → case created
- [ ] Navigate to case workspace

### 4. Can User Upload Document?
- [ ] In case workspace, upload button exists
- [ ] Select PDF → uploads
- [ ] Processing status shown
- [ ] Evidence appears when complete

### 5. Can User View Evidence?
- [ ] Evidence list visible in case
- [ ] Can rate evidence (stars)
- [ ] Can see source chunk

### 6. Can User Generate Artifacts?
- [ ] "Generate Research" button exists
- [ ] Enter topic → research generated
- [ ] "Red-Team" button exists
- [ ] "Generate Brief" button exists

### 7. Can User View/Edit Artifacts?
- [ ] Artifact appears in list
- [ ] Click → opens artifact viewer
- [ ] Can see blocks
- [ ] Can edit block → new version created

---

## 🔍 My Assessment

**Frontend Status: 85% Complete**

**What definitely works:**
- Chat interface ✅
- Signal display ✅
- Case workspace structure ✅
- Document tree navigation ✅
- NEW: Evidence components ✅
- NEW: Artifact components ✅
- NEW: Generation panel ✅

**What needs verification/integration:**
- Signal confirm/reject buttons (might exist, need to verify API integration)
- Evidence tab in case page (component exists, need to add to page)
- Artifacts section in case page (component exists, need to add to page)
- Document upload (might exist, need to verify)
- Login page (might exist, need to verify)

**What's definitely missing:**
- Type definitions for Evidence and Artifact
- Integration of new components into case workspace

---

## 🛠️ Quick Integration Tasks

### Task 1: Add Type Definitions (30 min)

Create `src/lib/types/evidence.ts` and `src/lib/types/artifact.ts`

### Task 2: Integrate Evidence into Case Page (1 hour)

Update `/cases/[caseId]/page.tsx`:
```tsx
import { EvidenceList } from '@/components/evidence/EvidenceList';

// Add evidence tab/section
<div className="mt-6">
  <h3>Evidence</h3>
  <EvidenceList caseId={caseId} />
</div>
```

### Task 3: Integrate Artifacts into Case Page (1 hour)

```tsx
import { GenerationPanel } from '@/components/artifacts/GenerationPanel';
import { artifactsAPI } from '@/lib/api/artifacts';

// Add generation section
<GenerationPanel caseId={caseId} />

// Add artifacts list
<div className="mt-6">
  {artifacts.map(artifact => (
    <ArtifactCard key={artifact.id} artifact={artifact} />
  ))}
</div>
```

### Task 4: Verify Signal Actions (30 min)

Check if SignalsList has working buttons. If not, add:
```tsx
import { signalsAPI } from '@/lib/api/signals';

const handleConfirm = async (id) => {
  await signalsAPI.confirm(id);
  refreshSignals();
};
```

---

## 🎯 Recommended Next Steps

### Option A: Quick Integration (1 day)
Do the 4 tasks above to connect existing components.
Result: Fully functional dogfooding system.

### Option B: Verify & Test (2-3 hours)
Manually test each feature via frontend.
Document what works, what doesn't.
Then fix gaps.

### Option C: Start Dogfooding As-Is
If chat + signals + cases work, start using it.
Add Evidence/Artifacts integration as you need them.

**My recommendation: Option B → verify what's actually working, then Option A to fill gaps.**

Want me to help verify specific components or fill the integration gaps?
