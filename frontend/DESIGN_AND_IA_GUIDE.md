# Episteme Design System & IA Guide

> Single source of truth for frontend design and navigation

---

## Quick Start

```bash
cd frontend
npm run dev
```

**Try:**
- Cmd+K - Command palette (navigate anywhere)
- Cmd+P - Case switcher (in workspace)
- Notice the refined slate + indigo colors

---

## Design System

### Colors

**Primary (Slate):** Brand foundation - text, borders, backgrounds  
**Accent (Indigo):** CTAs, links, focus rings  
**Success (Emerald):** Validated, approved  
**Warning (Amber):** Caution, untested  
**Error (Rose):** Risks, critical  

### Components

```tsx
import { Button, Input, Textarea, Label, Card, Badge } from '@/components/ui/...';

<Button>Primary</Button>
<Button variant="outline">Secondary</Button>
<Input placeholder="..." />
<Label>Field Name</Label>
<Card><CardHeader><CardTitle>Title</CardTitle></CardHeader></Card>
```

---

## Navigation

### Routes
- `/chat` - Conversations
- `/workspace/cases/[id]` - Case workspace (unified)
- `/cases/[id]/documents/[docId]` - Documents

### Keyboard Shortcuts
- `Cmd+K` - Command palette (global)
- `Cmd+P` - Case switcher (workspace)

### Components
- `Breadcrumbs` - Navigation trail
- `GlobalHeader` - Consistent shell
- `CaseSwitcher` - Quick switching
- `GlobalCommandPalette` - Cmd+K navigation

---

## Implementation Notes

**Phase 1-3:** Design system migrated (68 files)  
**Color scheme:** Refined to professional slate + indigo  
**IA:** Unified routes, breadcrumbs, shortcuts  
**Status:** Production-ready ✅
