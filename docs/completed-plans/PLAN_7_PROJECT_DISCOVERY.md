# Plan 7: Project Discovery + Onboarding Flow

## Goal
Give users a proper entry point — a project list/dashboard with search, filtering, and first-time onboarding. Currently there's **no `/projects` list page** — users can only access projects through detail pages. New users have zero guidance on where to start.

---

## Architecture Overview

```
User opens app
        ↓
/projects → ProjectsListPage
        ↓
[Zero projects?] → First-run onboarding empty state
[Has projects?]  → Grid of ProjectCards with search + sort
        ↓
Click ProjectCard → /projects/[projectId] (existing detail page)
Click "+ New Project" → NewProjectModal → createProject() → navigate to detail
```

---

## Current State

| Component | File | Status |
|-----------|------|--------|
| Projects API (frontend) | `frontend/src/lib/api/projects.ts` | Has `listProjects()`, `getProject()`, `deleteProject()` — **NO `createProject()` or `updateProject()`** |
| Project type | `frontend/src/lib/types/project.ts` | Minimal: id, title, description, is_archived, total_documents, timestamps |
| ProjectSerializer | `backend/apps/projects/serializers.py` | Basic fields: id, title, description, user, total_cases, total_documents, is_archived, timestamps |
| ProjectViewSet | `backend/apps/projects/views.py` | Standard CRUD, filters `is_archived=False` |
| ProjectService | `backend/apps/projects/services.py` | `create_project()` exists |
| Cases list page | `frontend/src/app/(app)/cases/page.tsx` | Grid + search + filter — **pattern to follow** |
| Project detail page | `frontend/src/app/(app)/projects/[projectId]/page.tsx` | Exists, title is static (not editable) |

**Key gap:** No way for users to create a project from the frontend, no projects list page, no onboarding.

---

## Implementation Steps

### Step 1: Add `createProject()` and `updateProject()` to Frontend API

**File: `frontend/src/lib/api/projects.ts`**

Add the missing API methods, following the same pattern as existing `listProjects` and `deleteProject`:

```typescript
export const projectsAPI = {
  // ... existing methods ...

  async createProject(data: { title: string; description?: string }): Promise<Project> {
    return apiClient.post<Project>('/projects/', data);
  },

  async updateProject(projectId: string, data: { title?: string; description?: string }): Promise<Project> {
    return apiClient.patch<Project>(`/projects/${projectId}/`, data);
  },
};
```

The backend `ProjectViewSet` already handles POST and PATCH via `CreateProjectSerializer` — no backend changes needed for this step.

---

### Step 2: Extend Project Type with Computed Fields

**File: `frontend/src/lib/types/project.ts`**

Extend the `Project` interface with fields we'll add to the serializer:

```typescript
export interface Project {
  id: string;
  title: string;
  description?: string;
  is_archived?: boolean;
  total_documents?: number;
  total_cases?: number;                      // NEW
  case_count_by_status?: {                   // NEW
    active: number;
    draft: number;
    archived: number;
  };
  has_hierarchy?: boolean;                   // NEW — does a READY hierarchy exist?
  latest_activity?: string;                  // NEW — ISO datetime of most recent update
  created_at: string;
  updated_at: string;
}
```

---

### Step 3: Enhance `ProjectSerializer` with Computed Fields

**File: `backend/apps/projects/serializers.py`**

Add `SerializerMethodField`s to give the frontend richer data for project cards:

```python
class ProjectSerializer(serializers.ModelSerializer):
    case_count_by_status = serializers.SerializerMethodField()
    has_hierarchy = serializers.SerializerMethodField()
    latest_activity = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'description', 'user',
            'total_cases', 'total_documents', 'is_archived',
            'case_count_by_status', 'has_hierarchy', 'latest_activity',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'total_cases', 'total_documents',
            'case_count_by_status', 'has_hierarchy', 'latest_activity',
            'created_at', 'updated_at',
        ]

    def get_case_count_by_status(self, obj):
        """Count cases grouped by status."""
        from apps.cases.models import Case
        qs = Case.objects.filter(project=obj).values('status').annotate(
            count=models.Count('id')
        )
        result = {'active': 0, 'draft': 0, 'archived': 0}
        for row in qs:
            if row['status'] in result:
                result[row['status']] = row['count']
        return result

    def get_has_hierarchy(self, obj):
        """Whether project has a READY cluster hierarchy."""
        from apps.graph.models import ClusterHierarchy, HierarchyStatus
        return ClusterHierarchy.objects.filter(
            project=obj, is_current=True, status=HierarchyStatus.READY
        ).exists()

    def get_latest_activity(self, obj):
        """Most recent update timestamp across project entities."""
        # Use project's own updated_at as a simple proxy
        # Could extend to check latest document or case update
        return obj.updated_at.isoformat() if obj.updated_at else None
```

**Performance note:** `get_case_count_by_status` does one query per project. For the list page, optimize the `ProjectViewSet.get_queryset()` to annotate counts:

```python
# In ProjectViewSet.get_queryset():
from django.db.models import Count, Q

queryset = Project.objects.filter(user=request.user, is_archived=False).annotate(
    active_case_count=Count('cases', filter=Q(cases__status='active')),
    draft_case_count=Count('cases', filter=Q(cases__status='draft')),
)
```

Then update the serializer method to use annotated values when available, falling back to the query approach.

---

### Step 4: Create Projects List Page

**File (NEW): `frontend/src/app/(app)/projects/page.tsx`**

Grid layout with search, mirroring the cases list page pattern:

```typescript
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Spinner } from '@/components/ui/spinner';
import { PageTitle } from '@/components/ui/headings';
import { projectsAPI } from '@/lib/api/projects';
import { ProjectCard } from '@/components/home/ProjectCard';
import { NewProjectModal } from '@/components/home/NewProjectModal';
import type { Project } from '@/lib/types/project';

export default function ProjectsListPage() {
    const router = useRouter();
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [showNewModal, setShowNewModal] = useState(false);

    useEffect(() => {
        async function load() {
            try {
                const data = await projectsAPI.listProjects();
                setProjects(data);
            } catch (error) {
                console.error('Failed to load projects:', error);
            } finally {
                setLoading(false);
            }
        }
        load();
    }, []);

    const filtered = projects
        .filter(p => p.title.toLowerCase().includes(search.toLowerCase()))
        .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());

    if (loading) {
        return (
            <div className="flex h-full items-center justify-center">
                <Spinner size="lg" className="text-accent-600" />
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-neutral-50 dark:bg-primary-950">
            <main className="flex-1 overflow-y-auto p-8">
                <div className="max-w-7xl mx-auto space-y-6">
                    {/* Header */}
                    <div className="flex items-center justify-between">
                        <div>
                            <PageTitle>Projects</PageTitle>
                            <p className="text-primary-600 dark:text-primary-400 mt-1">
                                {filtered.length} {filtered.length === 1 ? 'project' : 'projects'}
                            </p>
                        </div>
                        <Button onClick={() => setShowNewModal(true)}>
                            + New Project
                        </Button>
                    </div>

                    {/* Search */}
                    <Input
                        placeholder="Search projects..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="max-w-md"
                    />

                    {/* Grid or empty state */}
                    {filtered.length === 0 ? (
                        /* Empty state — see Step 6 */
                        <FirstRunOnboarding onCreateProject={() => setShowNewModal(true)} />
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {filtered.map(project => (
                                <ProjectCard
                                    key={project.id}
                                    project={project}
                                    onClick={() => router.push(`/projects/${project.id}`)}
                                />
                            ))}
                        </div>
                    )}
                </div>
            </main>

            <NewProjectModal
                isOpen={showNewModal}
                onClose={() => setShowNewModal(false)}
                onCreated={(project) => {
                    setShowNewModal(false);
                    router.push(`/projects/${project.id}`);
                }}
            />
        </div>
    );
}
```

---

### Step 5: Create ProjectCard Component

**File (NEW): `frontend/src/components/home/ProjectCard.tsx`**

Shows project summary in a card. Follows the case card pattern from `cases/page.tsx`:

```typescript
interface ProjectCardProps {
    project: Project;
    onClick: () => void;
}
```

**Displays:**
- Title (bold, 2-line clamp)
- Description (truncated, subtle text)
- Stats row: `{total_documents} docs · {total_cases} cases`
- Hierarchy badge: green dot if `has_hierarchy`, gray if not ("Mapped" vs "Unmapped")
- Last activity: relative time (`updated_at`)
- Hover: border accent color, slight shadow lift

**Visual structure:**
```
┌─────────────────────────────────┐
│  🟢 Mapped                     │
│                                 │
│  Project Title Here             │
│  Description text truncated...  │
│                                 │
│  12 docs · 3 cases              │
│  Updated 2 hours ago            │
└─────────────────────────────────┘
```

---

### Step 6: Create NewProjectModal

**File (NEW): `frontend/src/components/home/NewProjectModal.tsx`**

Simple creation modal following the `PremortemModal` pattern:

```typescript
interface NewProjectModalProps {
    isOpen: boolean;
    onClose: () => void;
    onCreated: (project: Project) => void;
}
```

**Form:**
- Title (text input, required, max 500 chars)
- Description (textarea, optional)
- Submit button: "Create Project"
- Cancel button: "Cancel"

**Behavior:**
- On submit: `projectsAPI.createProject({ title, description })`
- On success: call `onCreated(project)` → parent navigates to new project
- Error state: show inline error message
- Escape key closes modal
- Backdrop click closes modal

**Pattern to follow:** `frontend/src/components/cases/PremortemModal.tsx` — same modal overlay, button layout, keyboard handling, error state.

---

### Step 7: First-Run Onboarding Empty State

In the projects list page (Step 4), when `projects.length === 0` and no search is active:

```typescript
function FirstRunOnboarding({ onCreateProject }: { onCreateProject: () => void }) {
    return (
        <div className="text-center py-16 border border-dashed border-neutral-300 dark:border-neutral-700 rounded-lg">
            {/* Welcome illustration / icon */}
            <svg className="w-16 h-16 mx-auto text-accent-400 mb-6" ...>
                {/* Folder/lightbulb icon */}
            </svg>

            <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
                Welcome to Episteme
            </h2>
            <p className="text-neutral-600 dark:text-neutral-400 mb-8 max-w-md mx-auto">
                Create a project to start organizing your research and investigations.
            </p>

            {/* 3-step explainer */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-2xl mx-auto mb-8 text-left">
                {[
                    { step: '1', title: 'Create a project', desc: 'Group related documents and research under a shared context.' },
                    { step: '2', title: 'Upload documents', desc: 'Add your source material. Episteme will cluster and map themes.' },
                    { step: '3', title: 'Investigate decisions', desc: 'Start cases to explore questions, test assumptions, and reach decisions.' },
                ].map(item => (
                    <div key={item.step} className="flex items-start gap-3">
                        <span className="w-7 h-7 rounded-full bg-accent-600 text-white text-sm font-bold flex items-center justify-center shrink-0">
                            {item.step}
                        </span>
                        <div>
                            <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200">{item.title}</p>
                            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">{item.desc}</p>
                        </div>
                    </div>
                ))}
            </div>

            <Button onClick={onCreateProject}>
                Create Your First Project
            </Button>
        </div>
    );
}
```

When projects exist but search has no matches, show simpler empty state: "No projects match your search."

---

### Step 8: Inline Editing on Project Detail Page

**File: `frontend/src/app/(app)/projects/[projectId]/page.tsx`**

Add click-to-edit behavior for title and description:

1. Wrap title in a component that toggles between `<h1>` and `<input>` on click
2. On blur or Enter → call `projectsAPI.updateProject(projectId, { title: newTitle })`
3. On Escape → revert to original value
4. Same pattern for description (textarea instead of input)
5. Show subtle edit icon on hover to indicate editability

This is a small UX improvement — no new components needed, just local state management in the existing page.

---

## Key Files to Modify

| File | Change |
|------|--------|
| `frontend/src/lib/api/projects.ts` | Add `createProject()`, `updateProject()` |
| `frontend/src/lib/types/project.ts` | Extend Project interface with computed fields |
| `backend/apps/projects/serializers.py` | Add `case_count_by_status`, `has_hierarchy`, `latest_activity` |
| `backend/apps/projects/views.py` | Optimize queryset with annotations |
| `frontend/src/app/(app)/projects/page.tsx` | NEW — projects list page |
| `frontend/src/components/home/ProjectCard.tsx` | NEW — card component |
| `frontend/src/components/home/NewProjectModal.tsx` | NEW — creation modal |
| `frontend/src/app/(app)/projects/[projectId]/page.tsx` | Add inline title/description editing |

**Not modified (reused as-is):**
- `backend/apps/projects/services.py` — `create_project()` already exists
- `PageTitle`, `Button`, `Input`, `Spinner` — existing UI components
- `(app)` layout — handles auth, no changes needed

---

## Edge Cases

1. **Zero projects, first-time user:** Show onboarding empty state with 3-step guide
2. **Archived projects:** Already filtered out by backend (`is_archived=False`)
3. **Long titles:** `line-clamp-2` in ProjectCard, max 500 chars on input
4. **Concurrent updates:** `updateProject` uses PATCH — only sends changed fields
5. **Failed creation:** Show inline error in modal, don't close
6. **Rapid search typing:** Local filter is synchronous, no debounce needed

---

## Testing

1. **Frontend:** ProjectCard renders with correct stats for mock data
2. **Frontend:** NewProjectModal creates project and navigates on success
3. **Frontend:** Empty state shows onboarding when zero projects
4. **Backend:** ProjectSerializer returns `case_count_by_status`, `has_hierarchy` correctly
5. **Integration:** Create project → upload doc → verify card shows "1 doc" count
6. **Inline edit:** Click title → edit → blur → verify PATCH saves
