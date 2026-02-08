# Dashboard Implementation Plan

## Overview

This document outlines the implementation plan for the new hierarchical dashboard vision, based on our product strategy discussions. The goal is to create a workspace that surfaces one clear AI action at each level, with intelligence bubbling up from Case → Project → Home.

---

## Current State

### What Exists
- `DashboardOverview.tsx` - Basic home view with hardcoded intelligence cards
- `ProjectView.tsx` - Project view with tabs (overview, cases, inquiries, threads, docs)
- `CaseCardExpanded.tsx` - Case card with expandable inquiries
- Intelligence cards (`ResearchCompleteCard`, `AttentionNeededCard`, etc.) - All hardcoded
- `ReadinessChecklist.tsx` - Exists but not prominently displayed
- `useEvidenceLandscape` hook - Returns evidence counts
- `useReadinessChecklist` hook - Manages checklist items

### What's Missing
- Hierarchical intelligence (one action bubbling up)
- Dynamic intelligence cards (connected to real data)
- Readiness meter on dashboard views
- Tensions and blind spots display
- "Continue" section
- Suggested exploration prompts
- Case-level AI summary with context control

---

## Implementation Phases

### Phase 1: Foundation - Types & Hooks (Week 1)

#### 1.1 Define Intelligence Types

Create `/lib/types/intelligence.ts`:

```typescript
// The types of AI actions we can surface
export type IntelligenceType =
  | 'tension'        // Sources disagree
  | 'blind_spot'     // Missing analysis
  | 'explore'        // New angle to consider
  | 'research_ready' // Research completed, needs review
  | 'ready'          // Case/inquiry ready for decision
  | 'continue'       // Resume previous work
  | 'stale';         // Not touched recently

export type IntelligencePriority = 'blocking' | 'important' | 'suggested';

export interface IntelligenceItem {
  id: string;
  type: IntelligenceType;
  priority: IntelligencePriority;

  // Content
  title: string;
  description: string;

  // Context - where does this come from?
  projectId?: string;
  projectTitle?: string;
  caseId?: string;
  caseTitle?: string;
  inquiryId?: string;
  inquiryTitle?: string;

  // For tensions - the conflicting sources
  tension?: {
    sourceA: { name: string; content: string; implication?: string };
    sourceB: { name: string; content: string; implication?: string };
  };

  // For blind spots
  blindSpot?: {
    area: string;
    impact: string;
    suggestedAction: 'research' | 'discuss' | 'add_inquiry';
  };

  // For exploration prompts
  exploration?: {
    question: string;
    context: string;
    relatedItems?: string[]; // IDs of related cases/inquiries
  };

  // Metadata
  createdAt: string;
  dismissed?: boolean;
}

// Aggregated readiness for a case
export interface CaseReadiness {
  caseId: string;
  score: number; // 0-100
  inquiriesTotal: number;
  inquiriesResolved: number;
  tensionsCount: number;
  blindSpotsCount: number;
  isReady: boolean;
  blockers: IntelligenceItem[];
}

// Aggregated readiness for a project
export interface ProjectReadiness {
  projectId: string;
  casesTotal: number;
  casesReady: number;
  topAction: IntelligenceItem | null;
  cases: CaseReadiness[];
}
```

#### 1.2 Create Intelligence Hook

Create `/hooks/useIntelligence.ts`:

```typescript
/**
 * Hook to fetch and rank intelligence items
 * Returns the most important action at each level
 */
export function useIntelligence(options: {
  scope: 'home' | 'project' | 'case';
  projectId?: string;
  caseId?: string;
}) {
  // For now, return mock data
  // Later, this will aggregate from:
  // - Evidence landscape (tensions, blind spots)
  // - Readiness checklist
  // - Signals
  // - Background research status

  return {
    topAction: IntelligenceItem | null,
    allItems: IntelligenceItem[],
    isLoading: boolean,
    refresh: () => void,
  };
}
```

#### 1.3 Create Case Readiness Hook

Create `/hooks/useCaseReadiness.ts`:

```typescript
/**
 * Hook to compute case readiness score and status
 */
export function useCaseReadiness(caseId: string) {
  // Aggregates:
  // - Inquiry completion status
  // - Evidence landscape gaps
  // - Unresolved tensions
  // - Blind spots

  return {
    score: number, // 0-100
    inquiries: { total, resolved, investigating, open },
    tensions: IntelligenceItem[],
    blindSpots: IntelligenceItem[],
    isReady: boolean,
    nextAction: IntelligenceItem | null,
  };
}
```

---

### Phase 2: Component Structure (Week 1-2)

#### 2.1 New Components to Create

```
/components/workspace/
├── dashboard/
│   ├── HomePage.tsx              # New home page component
│   ├── ContinueCard.tsx          # "Continue where you left off"
│   ├── RecommendedAction.tsx     # The ONE action card
│   ├── NewActivityFeed.tsx       # "While you were away"
│   └── ProjectList.tsx           # Projects with readiness indicators
│
├── intelligence/
│   ├── IntelligenceCard.tsx      # Base card (exists, enhance)
│   ├── TensionCard.tsx           # Tension-specific display
│   ├── BlindSpotCard.tsx         # Blind spot display
│   ├── ExplorationCard.tsx       # Suggested question
│   ├── ResearchReadyCard.tsx     # Research to review
│   └── ReadyForReviewCard.tsx    # Case ready for decision
│
├── case/
│   ├── CaseHomePage.tsx          # New case home view
│   ├── ReadinessMeter.tsx        # Visual progress indicator
│   ├── InquiriesList.tsx         # Inquiries with status
│   ├── CaseBriefSummary.tsx      # AI summary (editable)
│   ├── SourcesList.tsx           # Sources with linkage
│   └── RecentChat.tsx            # Chat preview with continue
│
├── project/
│   ├── ProjectHomePage.tsx       # Enhanced project view
│   └── CaseList.tsx              # Cases with readiness
│
└── actions/
    ├── TensionResolutionView.tsx # Split view for resolving tensions
    ├── BlindSpotModal.tsx        # Quick action modal
    └── BriefContextModal.tsx     # Context control for brief generation
```

#### 2.2 Shared UI Components

```
/components/ui/
├── readiness-meter.tsx    # Reusable progress indicator
├── action-card.tsx        # Styled action card
└── tree-list.tsx          # Expandable tree for inquiries
```

---

### Phase 3: Wire Up Structure with Lorem Ipsum (Week 2)

This is where we build the skeleton with placeholder data.

#### 3.1 Home Page Structure

Replace `DashboardOverview.tsx` with new `HomePage.tsx`:

```tsx
export function HomePage() {
  // Mock data for now
  const mockTopAction: IntelligenceItem = {
    id: '1',
    type: 'tension',
    priority: 'blocking',
    title: 'Revenue recognition method unclear',
    description: 'Sources disagree on revenue recognition method.',
    projectTitle: 'ACME Acquisition',
    caseTitle: 'Financial Due Diligence',
    // ...
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 p-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Episteme</h1>
        <span className="text-sm text-neutral-500">Thu, Feb 6</span>
      </div>

      {/* Recommended Action */}
      <section>
        <RecommendedAction item={mockTopAction} />
      </section>

      {/* While You Were Away */}
      <section>
        <h2 className="text-sm font-medium text-neutral-500 mb-3">
          WHILE YOU WERE AWAY
        </h2>
        <NewActivityFeed items={mockActivityItems} />
      </section>

      {/* Projects */}
      <section>
        <h2 className="text-sm font-medium text-neutral-500 mb-3">
          PROJECTS
        </h2>
        <ProjectList projects={mockProjects} />
      </section>
    </div>
  );
}
```

#### 3.2 Project Page Structure

Enhance `ProjectView.tsx`:

```tsx
export function ProjectHomePage({ project, cases }) {
  const mockTopAction = { /* ... */ };
  const mockExploration = { /* ... */ };

  return (
    <div className="max-w-4xl mx-auto space-y-6 p-6">
      {/* Header with back nav */}
      <header>
        <Link href="/workspace">← Home</Link>
        <h1>{project.title}</h1>
        <div className="flex gap-2">
          <Button variant="ghost" size="icon">⚙</Button>
          <Button variant="ghost" size="icon">○</Button> {/* New Chat */}
        </div>
      </header>

      {/* Recommended Action */}
      <RecommendedAction item={mockTopAction} />

      {/* Worth Exploring */}
      <section>
        <h2>WORTH EXPLORING</h2>
        <ExplorationCard item={mockExploration} />
      </section>

      {/* New This Week */}
      <section>
        <h2>NEW THIS WEEK</h2>
        <NewActivityFeed items={mockActivityItems} />
      </section>

      {/* Cases */}
      <section>
        <h2>CASES</h2>
        <CaseList cases={cases} />
      </section>
    </div>
  );
}
```

#### 3.3 Case Page Structure

Create `CaseHomePage.tsx`:

```tsx
export function CaseHomePage({ caseData, inquiries }) {
  const mockReadiness = {
    score: 75,
    inquiries: { total: 4, resolved: 3 },
    tensions: 1,
    blindSpots: 2,
  };

  const mockTopAction = { /* tension */ };
  const mockSummary = "Analysis indicates company is financially healthy...";

  return (
    <div className="max-w-4xl mx-auto space-y-6 p-6">
      {/* Header */}
      <header>
        <Link href={`/workspace/projects/${caseData.project}`}>
          ← {caseData.projectTitle}
        </Link>
        <h1>{caseData.title}</h1>
        <div className="flex gap-2">
          <Button variant="ghost" size="icon">⚙</Button>
          <Button variant="ghost" size="icon">○</Button>
          <Button variant="ghost" size="icon">📄</Button>
        </div>
      </header>

      {/* Readiness Meter */}
      <ReadinessMeter
        score={mockReadiness.score}
        inquiries={mockReadiness.inquiries}
        tensions={mockReadiness.tensions}
        blindSpots={mockReadiness.blindSpots}
      />

      {/* Recommended Action */}
      <section>
        <h2>RECOMMENDED ACTION</h2>
        <RecommendedAction item={mockTopAction} variant="detailed" />
      </section>

      {/* Inquiries */}
      <section>
        <h2>INQUIRIES</h2>
        <InquiriesList inquiries={inquiries} />
      </section>

      {/* Case Brief */}
      <section>
        <h2>CASE BRIEF</h2>
        <CaseBriefSummary
          summary={mockSummary}
          onEdit={() => {}}
          onRegenerate={() => {}}
          onContextSettings={() => {}}
        />
      </section>

      {/* Sources */}
      <section>
        <h2>SOURCES</h2>
        <SourcesList sources={mockSources} />
      </section>

      {/* Recent Chat */}
      <section>
        <h2>RECENT CHAT</h2>
        <RecentChat
          lastMessage="Let me analyze the revenue..."
          timestamp="Yesterday 4:32 PM"
          onContinue={() => {}}
        />
      </section>
    </div>
  );
}
```

---

### Phase 4: Action Landing Experiences (Week 3)

#### 4.1 Tension Resolution View

Create `TensionResolutionView.tsx`:

```tsx
export function TensionResolutionView({ tension, onResolve, onDismiss }) {
  return (
    <div className="grid grid-cols-2 gap-6">
      {/* Source A */}
      <div className="border rounded-lg p-4">
        <h3>{tension.sourceA.name}</h3>
        <p>{tension.sourceA.content}</p>
        <p className="text-sm text-neutral-500">{tension.sourceA.implication}</p>
        <Button onClick={() => onResolve('A')}>Accept Source A</Button>
      </div>

      {/* Source B */}
      <div className="border rounded-lg p-4">
        <h3>{tension.sourceB.name}</h3>
        <p>{tension.sourceB.content}</p>
        <p className="text-sm text-neutral-500">{tension.sourceB.implication}</p>
        <Button onClick={() => onResolve('B')}>Accept Source B</Button>
      </div>

      {/* Chat */}
      <div className="col-span-2">
        <ChatInput placeholder="Discuss this tension..." />
      </div>

      <Button variant="ghost" onClick={onDismiss}>Note as Unresolved</Button>
    </div>
  );
}
```

#### 4.2 Blind Spot Modal

Create `BlindSpotModal.tsx`:

```tsx
export function BlindSpotModal({ blindSpot, onResearch, onDiscuss, onAddInquiry, onDismiss }) {
  return (
    <Dialog>
      <DialogHeader>
        <h2>Blind Spot Detected</h2>
      </DialogHeader>

      <DialogContent>
        <p className="font-medium">{blindSpot.title}</p>
        <p className="text-sm">{blindSpot.description}</p>

        <div className="mt-4">
          <h3>RECOMMENDED</h3>
          <Card onClick={onResearch}>
            <p>🔍 Research {blindSpot.area}</p>
            <p className="text-sm">Generate research on this topic</p>
            <p className="text-xs">Estimated: 2-3 minutes</p>
          </Card>
        </div>

        <div className="mt-4 flex gap-2">
          <Button variant="ghost" onClick={onDiscuss}>💬 Discuss</Button>
          <Button variant="ghost" onClick={onAddInquiry}>📋 Add Inquiry</Button>
          <Button variant="ghost" onClick={onDismiss}>✓ Mark Addressed</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

#### 4.3 Brief Context Modal

Create `BriefContextModal.tsx`:

```tsx
export function BriefContextModal({ inquiries, sources, onRegenerate }) {
  const [selectedInquiries, setSelectedInquiries] = useState(inquiries.map(i => i.id));
  const [selectedSources, setSelectedSources] = useState(sources.map(s => s.id));
  const [focus, setFocus] = useState<'balanced' | 'risk' | 'recommendation' | 'executive'>('balanced');
  const [customInstructions, setCustomInstructions] = useState('');

  return (
    <Dialog>
      <DialogHeader>
        <h2>Brief Context Settings</h2>
      </DialogHeader>

      <DialogContent>
        <section>
          <h3>INQUIRIES</h3>
          {inquiries.map(inq => (
            <Checkbox
              key={inq.id}
              checked={selectedInquiries.includes(inq.id)}
              onChange={() => toggle(inq.id)}
            >
              {inq.title}
            </Checkbox>
          ))}
        </section>

        <section>
          <h3>SOURCES</h3>
          {sources.map(src => (
            <Checkbox
              key={src.id}
              checked={selectedSources.includes(src.id)}
              onChange={() => toggle(src.id)}
            >
              {src.name}
              {!src.linkedToInquiry && <span className="text-xs">(not linked)</span>}
            </Checkbox>
          ))}
        </section>

        <section>
          <h3>FOCUS</h3>
          <RadioGroup value={focus} onChange={setFocus}>
            <Radio value="balanced">Balanced overview</Radio>
            <Radio value="risk">Risk-focused</Radio>
            <Radio value="recommendation">Recommendation-focused</Radio>
            <Radio value="executive">Executive summary (shorter)</Radio>
          </RadioGroup>
        </section>

        <section>
          <h3>CUSTOM INSTRUCTIONS</h3>
          <Textarea
            value={customInstructions}
            onChange={e => setCustomInstructions(e.target.value)}
            placeholder="Focus on valuation implications..."
          />
        </section>

        <Button onClick={() => onRegenerate({
          inquiries: selectedInquiries,
          sources: selectedSources,
          focus,
          customInstructions
        })}>
          Regenerate
        </Button>
      </DialogContent>
    </Dialog>
  );
}
```

---

### Phase 5: Connect to Real Data (Week 4)

#### 5.1 Backend API Endpoints Needed

```
GET /api/intelligence/
  ?scope=home|project|case
  &project_id=xxx
  &case_id=xxx

Returns:
{
  top_action: IntelligenceItem,
  items: IntelligenceItem[],
  activity: ActivityItem[],
}

GET /api/cases/{id}/readiness/
Returns:
{
  score: number,
  inquiries: { total, resolved, investigating, open },
  tensions: IntelligenceItem[],
  blind_spots: IntelligenceItem[],
  is_ready: boolean,
}

POST /api/cases/{id}/brief/generate/
Body: { inquiries, sources, focus, custom_instructions }
Returns: { summary: string }
```

#### 5.2 Update Hooks to Use Real API

```typescript
// useIntelligence.ts
export function useIntelligence(options) {
  return useQuery({
    queryKey: ['intelligence', options.scope, options.projectId, options.caseId],
    queryFn: () => api.get('/intelligence/', { params: options }),
  });
}

// useCaseReadiness.ts
export function useCaseReadiness(caseId: string) {
  return useQuery({
    queryKey: ['case-readiness', caseId],
    queryFn: () => api.get(`/cases/${caseId}/readiness/`),
  });
}
```

---

## File Changes Summary

### New Files to Create

```
/lib/types/intelligence.ts
/hooks/useIntelligence.ts
/hooks/useCaseReadiness.ts

/components/workspace/dashboard/HomePage.tsx
/components/workspace/dashboard/ContinueCard.tsx
/components/workspace/dashboard/RecommendedAction.tsx
/components/workspace/dashboard/NewActivityFeed.tsx
/components/workspace/dashboard/ProjectList.tsx

/components/workspace/case/CaseHomePage.tsx
/components/workspace/case/ReadinessMeter.tsx
/components/workspace/case/InquiriesList.tsx
/components/workspace/case/CaseBriefSummary.tsx
/components/workspace/case/SourcesList.tsx
/components/workspace/case/RecentChat.tsx

/components/workspace/project/ProjectHomePage.tsx
/components/workspace/project/CaseList.tsx

/components/workspace/intelligence/TensionCard.tsx
/components/workspace/intelligence/BlindSpotCard.tsx
/components/workspace/intelligence/ExplorationCard.tsx

/components/workspace/actions/TensionResolutionView.tsx
/components/workspace/actions/BlindSpotModal.tsx
/components/workspace/actions/BriefContextModal.tsx

/components/ui/readiness-meter.tsx
/components/ui/action-card.tsx
```

### Files to Modify

```
/app/workspace/page.tsx - Use new HomePage
/app/workspace/projects/[projectId]/page.tsx - Use new ProjectHomePage
/app/workspace/cases/[caseId]/page.tsx - Add CaseHomePage as default view

/components/workspace/intelligence/IntelligenceCard.tsx - Enhance base component
```

### Files to Deprecate (Eventually)

```
/components/workspace/DashboardOverview.tsx - Replace with HomePage
/components/workspace/intelligence/ResearchCompleteCard.tsx - Replace with dynamic
/components/workspace/intelligence/AttentionNeededCard.tsx - Replace with dynamic
/components/workspace/intelligence/ConversationPromptCard.tsx - Replace with dynamic
/components/workspace/intelligence/ConnectionCard.tsx - Replace with dynamic
```

---

## Implementation Order

### Week 1: Foundation
1. ✓ Create `intelligence.ts` types
2. ✓ Create mock `useIntelligence` hook
3. ✓ Create mock `useCaseReadiness` hook
4. ✓ Create `ReadinessMeter` component
5. ✓ Create `RecommendedAction` component

### Week 2: Structure
1. ✓ Create `HomePage` with lorem ipsum data
2. ✓ Create `ProjectHomePage` with lorem ipsum data
3. ✓ Create `CaseHomePage` with lorem ipsum data
4. ✓ Create `CaseList` with expandable inquiries
5. ✓ Wire up routing to new components

### Week 3: Actions
1. ✓ Create `TensionResolutionView`
2. ✓ Create `BlindSpotModal`
3. ✓ Create `BriefContextModal`
4. ✓ Wire up action clicks to appropriate views

### Week 4: Integration
1. Define backend API endpoints
2. Update hooks to use real API
3. Test end-to-end flow
4. Polish and iterate

---

## Design Tokens

For consistency, use these across all new components:

```css
/* Spacing */
--space-section: 1.5rem;  /* Between sections */
--space-card: 1rem;       /* Inside cards */
--space-item: 0.5rem;     /* Between list items */

/* Colors (use existing theme) */
--color-blocking: var(--error-600);
--color-important: var(--warning-600);
--color-suggested: var(--accent-600);
--color-ready: var(--success-600);

/* Typography */
--text-section-header: 0.75rem uppercase tracking-wide text-neutral-500;
--text-title: 1.25rem font-semibold;
--text-description: 0.875rem text-neutral-600;
```

---

## Open Questions

1. **Backend support:** Do we have API endpoints for intelligence aggregation, or do we need to build them?

2. **Real-time updates:** Should intelligence items update in real-time (WebSocket) or on refresh?

3. **Dismissal persistence:** Where do we store dismissed intelligence items? Local storage or backend?

4. **Mobile:** These designs are desktop-focused. Do we need mobile variants now or later?

5. **Empty states:** What do we show when there are no actions, no cases, new user?

---

## Next Steps

1. Review this plan
2. Decide: Start with lorem ipsum (Phase 3) or types/hooks first (Phase 1)?
3. Assign timeline
4. Begin implementation
