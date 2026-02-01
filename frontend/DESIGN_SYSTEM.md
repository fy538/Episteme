# Episteme Design System

A comprehensive design system for building consistent, beautiful UI across the Episteme platform.

## Overview

This design system provides:
- **Design Tokens**: Centralized color, typography, spacing, and other visual properties
- **Component Library**: Pre-built, accessible UI components
- **Guidelines**: Best practices for consistent UI/UX

---

## Design Tokens

All design tokens are defined in `tailwind.config.ts` and can be used via Tailwind utility classes.

### Colors

#### Brand Colors
- **Primary**: Slate scale for brand foundation (text, borders, backgrounds)
  - Use `bg-primary-600`, `text-primary-700`, `border-primary-200`
  - Main brand color: `primary-600` (#475569) - Professional slate

- **Accent**: Indigo scale for calls-to-action and important interactions
  - Use `bg-accent-600`, `text-accent-600`, `focus:ring-accent-500`
  - Main accent color: `accent-600` (#4f46e5) - Sophisticated indigo

#### Semantic Colors
- **Success**: Emerald scale for validated/approved states
  - Use `bg-success-600`, `text-success-700`, etc.
  - Main success color: `success-600` (#059669) - Professional green

- **Warning**: Amber scale for caution and untested states
  - Use `bg-warning-600`, `text-warning-700`, etc.
  - Main warning color: `warning-600` (#d97706) - Muted amber

- **Error**: Rose scale for risks and critical issues
  - Use `bg-error-600`, `text-error-700`, etc.
  - Main error color: `error-600` (#e11d48) - Professional red

- **Info**: Sky scale for informational elements
  - Use `bg-info-600`, `text-info-700`, etc.
  - Main info color: `info-600` (#0284c7) - Clear blue

#### Neutral Colors
- **Neutral**: Slate scale for text, borders, backgrounds
  - Use `bg-neutral-100`, `text-neutral-700`, `border-neutral-300`, etc.
  - Note: `neutral-*` is an alias for `primary-*` (both use slate)
  - Slate has subtle blue undertone for cohesive, sophisticated feel

#### Feature-Specific Colors
- **Evidence Types**:
  - Metric: `evidence.metric` (#3b82f6 - blue)
  - Benchmark: `evidence.benchmark` (#8b5cf6 - purple)
  - Fact: `evidence.fact` (#22c55e - green)
  - Claim: `evidence.claim` (#f59e0b - amber)
  - Quote: `evidence.quote` (#ec4899 - pink)

- **Status Colors** (for assumptions/investigations):
  - Untested: Yellow/amber tones
  - Investigating: Purple tones
  - Validated: Green tones

### Typography

#### Font Families
- **Sans**: `font-sans` - Inter (primary font)
- **Mono**: `font-mono` - Monospace for code

#### Type Scale
Refined scale with proper line-heights:
- `text-xs` - 12px (labels, captions)
- `text-sm` - 14px (body text, buttons)
- `text-base` - 16px (default body)
- `text-lg` - 18px (subheadings)
- `text-xl` - 20px (headings)
- `text-2xl` - 24px (page titles)
- `text-3xl` - 30px (hero headings)
- `text-4xl` - 36px (marketing)
- `text-5xl` - 48px (large displays)

#### Font Weights
- Regular: `font-normal` (400)
- Medium: `font-medium` (500) - for emphasis
- Semibold: `font-semibold` (600) - for headings
- Bold: `font-bold` (700) - for strong emphasis

### Spacing

Use Tailwind's spacing scale:
- `space-1` to `space-12` - common increments
- `space-18` (72px) - custom token
- `space-88` (352px) - custom token
- `space-128` (512px) - custom token

**Common patterns:**
- Padding inside cards: `p-6`
- Gap between elements: `gap-4`
- Margin between sections: `mb-6` or `mb-8`

### Border Radius
- `rounded-sm` - 4px (subtle)
- `rounded` - 6px (default)
- `rounded-md` - 8px (cards, inputs)
- `rounded-lg` - 12px (cards, modals)
- `rounded-xl` - 16px (large cards)
- `rounded-2xl` - 24px (hero sections)
- `rounded-full` - circular (badges, avatars)

### Shadows
- `shadow-sm` - Subtle depth (cards)
- `shadow` - Default shadow (dropdowns)
- `shadow-md` - Medium depth (modals)
- `shadow-lg` - High depth (overlays)
- `shadow-xl` - Maximum depth (popovers)

### Animations
- `animate-fade-in` - Fade in (200ms)
- `animate-slide-up` - Slide up (300ms)
- `animate-slide-down` - Slide down (300ms)
- `animate-scale-in` - Scale in (200ms)

---

## Component Library

### Button

**Usage:**
```tsx
import { Button } from '@/components/ui/button';

<Button>Default</Button>
<Button variant="outline">Outline</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="destructive">Delete</Button>
<Button variant="success">Confirm</Button>
<Button size="sm">Small</Button>
<Button size="lg">Large</Button>
```

**Variants:**
- `default` - Primary actions (blue background)
- `outline` - Secondary actions (border only)
- `ghost` - Tertiary actions (transparent)
- `destructive` - Dangerous actions (red)
- `success` - Positive actions (green)

**Sizes:**
- `sm` - Small (h-8, text-xs)
- `default` - Medium (h-10, text-sm)
- `lg` - Large (h-12, text-base)
- `icon` - Square icon button (9x9)

---

### Input

**Usage:**
```tsx
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

<div>
  <Label>Email</Label>
  <Input type="email" placeholder="you@example.com" />
</div>

<Input error placeholder="This field has an error" />
```

**Props:**
- `error?: boolean` - Shows error state (red border)

---

### Textarea

**Usage:**
```tsx
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';

<div>
  <Label>Description</Label>
  <Textarea placeholder="Enter description..." />
</div>

<Textarea error placeholder="This field has an error" />
```

---

### Label

**Usage:**
```tsx
import { Label } from '@/components/ui/label';

<Label>Field Name</Label>
<Label required>Required Field</Label>
```

**Props:**
- `required?: boolean` - Adds red asterisk

---

### Card

**Usage:**
```tsx
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui/card';

<Card>
  <CardHeader>
    <CardTitle>Card Title</CardTitle>
    <CardDescription>Card description text</CardDescription>
  </CardHeader>
  <CardContent>
    <p>Card content goes here</p>
  </CardContent>
  <CardFooter>
    <Button>Action</Button>
  </CardFooter>
</Card>
```

**Components:**
- `Card` - Container
- `CardHeader` - Top section with title/description
- `CardTitle` - Heading (h3)
- `CardDescription` - Subtitle
- `CardContent` - Main content area
- `CardFooter` - Bottom section for actions

---

### Badge

**Usage:**
```tsx
import { Badge } from '@/components/ui/badge';

<Badge>Default</Badge>
<Badge variant="success">Success</Badge>
<Badge variant="warning">Warning</Badge>
<Badge variant="error">Error</Badge>
<Badge variant="neutral">Neutral</Badge>
<Badge variant="outline">Outline</Badge>
```

**Variants:**
- `default` - Primary blue
- `success` - Green
- `warning` - Amber
- `error` - Red
- `neutral` - Gray
- `outline` - Border only

---

## Usage Guidelines

### 1. Color Usage

**Do:**
- Use semantic colors for their intended purpose
  - Primary (slate) for brand foundation - text, borders, neutral UI
  - Accent (indigo) for important actions, links, CTAs
  - Success (emerald) for validated/approved states
  - Warning (amber) for cautions and untested elements
  - Error (rose) for risks and critical issues
- Use neutral (slate) colors for text, borders, backgrounds
- Use evidence colors consistently (metric, fact, claim, quote, benchmark)

**Don't:**
- Mix old `gray-*` classes with new `neutral-*` classes
- Use raw hex colors in components
- Use primary colors for success states (use `success` instead)

### 2. Typography

**Hierarchy:**
1. Page title: `text-2xl font-semibold`
2. Section heading: `text-xl font-semibold`
3. Subsection: `text-lg font-medium`
4. Body: `text-base` or `text-sm`
5. Caption: `text-xs text-neutral-500`

**Do:**
- Use consistent heading levels
- Maintain line-height for readability
- Use `font-medium` or `font-semibold` for headings

**Don't:**
- Skip heading levels
- Use multiple font weights in body text
- Use all caps for long text

### 3. Spacing

**Common patterns:**
- Card padding: `p-6`
- Vertical stack: `space-y-4` or `gap-4`
- Horizontal group: `gap-2` or `gap-3`
- Section margin: `mb-6` or `mb-8`
- Page padding: `p-6` or `p-8`

**Do:**
- Use consistent spacing values (4, 8, 12, 16, 24px multiples)
- Use Tailwind's spacing scale
- Group related elements closely, separate sections widely

**Don't:**
- Mix `space-y-*` with manual `mb-*` on children
- Use inconsistent spacing (e.g., `gap-3` and `gap-5` in similar contexts)

### 4. Borders & Shadows

**Borders:**
- Cards: `border border-neutral-200`
- Dividers: `border-t border-neutral-200`
- Input focus: handled by components

**Shadows:**
- Cards: `shadow-sm`
- Dropdowns: `shadow-md`
- Modals: `shadow-lg`

### 5. Interactive States

**All interactive elements should have:**
- Hover state (lighter/darker background)
- Focus state (ring-2 ring-primary-500)
- Active state (visual feedback)
- Disabled state (opacity-50, cursor-not-allowed)
- Smooth transitions (transition-colors)

---

## Migration Guide

### Phase 1: Update Core Components (Week 1)

**Priority order:**
1. Replace all `gray-*` with `neutral-*`
2. Replace `blue-600/700` with `primary-600/700`
3. Update buttons to use new Button component variants
4. Replace custom inputs with Input component

**Example migration:**

**Before:**
```tsx
<input 
  className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
  placeholder="Search..."
/>
```

**After:**
```tsx
<Input placeholder="Search..." />
```

### Phase 2: Cards & Lists (Week 2)

**Replace custom card patterns with Card component:**

**Before:**
```tsx
<div className="rounded-lg border border-gray-200 bg-white p-6">
  <h3 className="text-lg font-semibold mb-2">Title</h3>
  <p className="text-sm text-gray-600">Description</p>
</div>
```

**After:**
```tsx
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
</Card>
```

### Phase 3: Badges & Status Indicators (Week 3)

**Replace custom badges with Badge component:**

**Before:**
```tsx
<span className="px-2.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
  Active
</span>
```

**After:**
```tsx
<Badge>Active</Badge>
```

### Phase 4: Forms (Week 4)

**Systematically update all forms:**
- Use Label + Input/Textarea combinations
- Add proper error states
- Consistent spacing and layout

---

## Best Practices

### Accessibility
- Always use semantic HTML
- Provide proper labels for inputs
- Ensure sufficient color contrast (WCAG AA)
- Support keyboard navigation
- Include focus indicators

### Performance
- Use Tailwind's utility classes (purged in production)
- Avoid inline styles when possible
- Use design tokens instead of custom values

### Consistency
- Use components from the library, not custom implementations
- Follow spacing patterns consistently
- Maintain visual hierarchy with typography scale
- Use semantic colors appropriately

### Code Quality
- Import components from `@/components/ui/*`
- Use the `cn()` utility for conditional classes
- Keep components focused and composable
- Document custom variants/extensions

---

## Tools & Utilities

### `cn()` Utility
Combines `clsx` and `tailwind-merge` for intelligent class merging:

```tsx
import { cn } from '@/lib/utils';

<div className={cn(
  'base-classes',
  condition && 'conditional-classes',
  className // from props
)} />
```

### Component Composition
Build complex UIs by composing primitives:

```tsx
<Card>
  <CardHeader>
    <div className="flex items-center justify-between">
      <CardTitle>Users</CardTitle>
      <Button size="sm">Add User</Button>
    </div>
  </CardHeader>
  <CardContent>
    {/* User list */}
  </CardContent>
</Card>
```

---

## Future Enhancements

### Planned Components
- [ ] Select/Dropdown
- [ ] Modal/Dialog
- [ ] Toast notifications
- [ ] Tabs
- [ ] Accordion
- [ ] Tooltip
- [ ] Popover
- [ ] Date picker
- [ ] Table
- [ ] Avatar
- [ ] Checkbox/Radio
- [ ] Switch/Toggle

### Planned Features
- [ ] Dark mode support
- [ ] Animation presets
- [ ] Form validation patterns
- [ ] Loading states
- [ ] Empty states
- [ ] Error states

---

## Resources

- **Tailwind CSS**: https://tailwindcss.com/docs
- **shadcn/ui**: https://ui.shadcn.com/ (inspiration)
- **Radix UI**: https://www.radix-ui.com/ (accessibility primitives)

---

## Questions?

Refer to this guide when building new features or refactoring existing ones. For questions or suggestions, discuss with the team.

**Remember:** Consistency is key. Use the design system, and the system will make your app beautiful.
