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
- Toggle dark mode in Settings
- Notice the refined slate + indigo colors

---

## Design System

### Colors - "Analytical Precision"

**Primary (Charcoal):** Brand foundation - neutral, objective  
**Accent (Teal):** CTAs, links, focus rings - analytical clarity  
**Success (Emerald):** Validated, approved  
**Warning (Amber):** Caution, untested  
**Error (Rose):** Risks, critical  

**Philosophy:** Maximum objectivity for evidence-based decision-making  

### Components (23 total)

**Form Controls:**
```tsx
import { Button, Input, Textarea, Label, Checkbox, Radio, Select, Switch } from '@/components/ui/...';

<Button>Primary</Button>
<Input placeholder="..." />
<Checkbox label="Accept terms" />
<Radio name="option" label="Option 1" />
<Select><option>Choose...</option></Select>
<Switch label="Enable feature" />
```

**Layout:**
```tsx
import { Card, Breadcrumbs, Dialog } from '@/components/ui/...';

<Card><CardHeader><CardTitle>Title</CardTitle></CardHeader></Card>
<Breadcrumbs items={[...]} />
<Dialog isOpen={open} onClose={...}>Content</Dialog>
```

**Feedback & Data:**
```tsx
import { Badge, Spinner, Tooltip, Table, Toast } from '@/components/ui/...';

<Badge variant="success">Active</Badge>
<Spinner size="sm" />
<Tooltip content="Help text"><Button>?</Button></Tooltip>
<Table><TableHeader><TableHead>Name</TableHead></TableHeader></Table>

// Toast notifications
const { addToast } = useToast();
addToast({ title: 'Success', variant: 'success' });
```

**Theme:**
```tsx
import { ThemeToggle, useTheme } from '@/components/...';

<ThemeToggle />  // Light | Dark | System toggle
const { theme, setTheme } = useTheme();
```

---

## Navigation

### Routes
- `/` - Landing page (redirects to `/workspace` if authenticated)
- `/login` - Authentication (redirects to `/workspace` after login)
- `/workspace` - Primary hub/dashboard
- `/chat` - Conversations and chat interface
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

**Components:** 23 total (all major UI patterns covered)  
**Color scheme:** Professional slate + indigo  
**Dark mode:** Fully implemented ✅  
**IA:** Unified routes, breadcrumbs, shortcuts  
**Forms:** Checkbox, Radio, Select, Switch  
**Data:** Table component  
**Notifications:** Toast system  
**Status:** Production-ready ✅
