# Settings Page Design: Comprehensive Configuration Hub

## Current State Analysis

### What Exists
- ✅ Modal-based settings (Profile + Chat Model)
- ✅ localStorage-only (no backend persistence)
- ✅ Model selection UI (but not connected to backend)

### Critical Gap
- ❌ **Model selection doesn't work** - Frontend saves to localStorage but backend ignores it
- ❌ No backend user preferences API
- ❌ Limited scope (only 2 settings)

---

## Design Philosophy: Progressive Disclosure

**Principle**: Don't overwhelm users with configuration. Surface essentials, hide advanced.

### Three Tiers of Settings

**Tier 1: Essential** (Always visible)
- Profile, workspace preferences, appearance

**Tier 2: Customization** (For power users)
- Skills, agent preferences, defaults

**Tier 3: Advanced** (Hidden until needed)
- API keys, integrations, debug options

---

## Proposed Settings Architecture

### Navigation Pattern: Tabbed Interface

```
┌─────────────────────────────────────────────────────────┐
│ Settings                                          [×]   │
├──────────────┬──────────────────────────────────────────┤
│              │                                          │
│ Profile      │  [Profile content]                       │
│ Workspace    │                                          │
│ AI & Agents  │                                          │
│ Skills       │                                          │
│ Appearance   │                                          │
│ Notifications│                                          │
│ Advanced     │                                          │
│              │                                          │
│              │                                          │
│              │                                          │
│              │                                          │
│              │  [Cancel] [Save Changes]                 │
└──────────────┴──────────────────────────────────────────┘
```

**Alternative**: Full-page settings (like Notion, Linear)
- Dedicated `/settings` route
- Better for complex configurations
- More room for explanations

---

## Settings Categories

### 1. Profile (Tier 1: Essential)

**Fields**:
- Name (text input)
- Email (email input, read-only if from auth)
- Avatar (upload, future)
- Bio (textarea, optional)
- Role (dropdown: Founder, PM, Engineer, Legal, Medical, etc.)

**Why Role?**
- Used for skill suggestions ("Legal role → suggest Legal skills")
- Personalized agent behavior
- Team context

**Backend Required**:
```python
class UserProfile(models.Model):
    user = models.OneToOneField(User)
    avatar_url = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    role = models.CharField(max_length=50)
```

---

### 2. Workspace Preferences (Tier 1: Essential)

**Subheading**: How you work with cases and inquiries

**Settings**:
- **Default case view**: Brief | Inquiry Dashboard | Documents
- **Auto-save delay**: Instant | 1s | 3s | 5s
- **Case creation**:
  - ☐ Auto-create inquiries from questions
  - ☐ Auto-detect assumptions
  - ☐ Auto-generate titles
- **Inquiry defaults**:
  - Default status: OPEN | INVESTIGATING
  - Evidence credibility threshold: 1-5 stars
- **Editor preferences**:
  - Font size: Small | Medium | Large
  - Line spacing: Compact | Normal | Relaxed
  - Show word count: ☑
  - Spell check: ☑

**Why These**:
- Directly affect daily workflow
- High usage frequency
- Personal preference (no "correct" answer)

---

### 3. AI & Agents (Tier 1-2: Essential to Customization)

**Subheading**: Configure how AI assists you

**Chat Model** (Existing, Enhanced):
- Model selection (keep current UI)
- ✨ NEW: Actually send to backend
- ✨ NEW: Show model capabilities/limits
- ✨ NEW: Per-case model override option

**Agent Behavior**:
- **Inflection detection**:
  - Sensitivity: Low (every 5 turns) | Medium (every 3 turns) | High (every turn)
  - Min confidence to suggest: 0.5 | 0.75 | 0.9
  - Auto-run agents: ☐ Never | ☐ High confidence only (>0.95)
- **Agent defaults**:
  - Default research depth: Quick | Thorough | Comprehensive
  - Critique style: Gentle | Balanced | Aggressive
  - Brief format: Executive | Technical | Stakeholder

**Signal Extraction**:
- Extraction threshold: 500 chars (current) | Custom
- Auto-extract: ☑ Always | ☐ Only when case linked

**Why These**:
- Control over automation level
- Personalize AI behavior
- Power user customization

---

### 4. Skills (Tier 2: Customization)

**Subheading**: Manage your personal and team skills

**Personal Skills**:
- List of personal skills with status (active/draft)
- [+ Create New Skill]
- Actions: Edit | Promote to Team | Archive

**Team Skills** (if in a team/project):
- Skills shared with your team
- Actions: View | Fork to Personal

**Organization Skills** (if in org):
- Read-only view of org-wide skills
- Actions: Fork to Personal | Request Edit

**Quick Actions**:
- Import from template
- Fork from public marketplace
- Create from current case

**Why Separate Tab**:
- Skills are configuration, not daily workflow
- Power users customize, most users use defaults
- Keeps main settings uncluttered

**Backend Required**:
- Use existing Skill models
- Add user → organization relationship
- Skills list API with filtering by scope

---

### 5. Appearance (Tier 1: Essential)

**Subheading**: Customize how Episteme looks

**Theme**:
- ○ Light (default)
- ○ Dark
- ○ Auto (system preference)

**Color Accent**:
- Default blue | Purple | Teal | Orange (changes primary-* tokens)

**Density**:
- Comfortable (current, p-6 spacing)
- Compact (p-4 spacing)
- Relaxed (p-8 spacing)

**Font**:
- Inter (default) | System | Custom (future)

**Why These**:
- Personal preference
- Accessibility (some users prefer dark mode, larger text)
- Common in modern apps

---

### 6. Notifications (Tier 2: Customization)

**Subheading**: Control what you get notified about

**In-App Notifications**:
- ☑ Inquiry resolved
- ☑ Evidence added to my inquiry
- ☑ Agent completed
- ☑ Case updated by team member

**Email Notifications**:
- ☐ Daily digest
- ☐ Weekly summary
- ☐ Urgent only (blocks, deadlines)

**Chat Notifications**:
- ☐ Slack integration (future)
- ☐ Email on @mentions

**Why These**:
- Stay informed without being overwhelmed
- Team collaboration awareness
- Background work completion alerts

---

### 7. Advanced (Tier 3: Hidden)

**Subheading**: Advanced configuration and debugging

**API Configuration**:
- API keys (read-only, set in backend)
- Model overrides (per-agent-type)
- Rate limits display

**Debug Options**:
- ☐ Show event IDs
- ☐ Show correlation IDs in UI
- ☐ Enable verbose logging
- ☐ Show AI prompts (for transparency)

**Data & Privacy**:
- Export all data (JSON)
- Delete account
- Data retention policy

**Experimental Features**:
- ☐ Enable skill marketplace
- ☐ Beta: Multi-agent chains
- ☐ Beta: Auto-promotion of signals

**Why Hidden**:
- Most users never need these
- Can be dangerous (API keys, deletions)
- Clutters main settings

---

## Recommended UX Pattern

### Option A: Modal with Tabs (Current, Enhanced)

**Pros**:
- Familiar pattern
- Lightweight
- Quick access

**Cons**:
- Limited space for complex settings
- Scrolling required
- Hard to show help text

### Option B: Dedicated Settings Page (Recommended)

**Pattern**: `/settings` route with left sidebar

```
┌────────────┬───────────────────────────────────────┐
│ Profile    │  Profile                              │
│ Workspace  │  ─────────                            │
│ AI & Agents│                                       │
│ Skills     │  Name: [____________]                 │
│ Appearance │  Email: [____________]                │
│ Notificatons│ Role: [Dropdown: Founder ▼]         │
│ Advanced   │                                       │
│            │  Avatar: [Upload]                     │
│            │                                       │
│            │  ─────────────────────────────────    │
│            │                                       │
│            │                                       │
│            │                [Cancel] [Save]        │
└────────────┴───────────────────────────────────────┘
```

**Pros**:
- More space for complex settings
- Better organization
- Room for help text/descriptions
- Can have dedicated URLs (settings/profile, settings/ai, etc.)

**Cons**:
- Requires routing
- More complex implementation
- User leaves workspace context

**Recommendation**: Start with **enhanced modal** (tabs), migrate to **dedicated page** when settings grow complex.

---

## Implementation Phases

### Phase 1: Backend Foundation (Required First)
1. Create `UserPreferences` model
2. Create preferences API (CRUD)
3. Connect model selection to chat API
4. Add skill scope filtering

### Phase 2: Enhanced Modal (Quick Win)
1. Add tabs to current modal
2. Expand settings:
   - Profile (existing +)
   - Workspace preferences
   - AI & Agents (existing + inflection settings)
   - Appearance (new)
3. Connect to backend API

### Phase 3: Skills Tab (Power Users)
1. Skills list view
2. Create/edit inline
3. Scope management (personal/team/org)

### Phase 4: Full Settings Page (Later)
1. Dedicated `/settings` route
2. Sidebar navigation
3. More room for complex options

---

## Key Settings to Add

### Immediate (High Value)

1. **Agent inflection sensitivity** - Control how often agents are suggested
2. **Auto-create inquiries** - Toggle from conversation analysis
3. **Default case view** - Start on brief vs dashboard
4. **Model selection that works** - Fix backend connection

### Short-term (Good UX)

5. **Theme** - Dark mode support
6. **Skills visibility** - Show/hide skills section
7. **Evidence threshold** - Min confidence to auto-suggest resolution
8. **Notification preferences** - Email on inquiry resolution

### Long-term (Polish)

9. **Keyboard shortcuts** - Customizable hotkeys
10. **Export/import** - Data portability
11. **Team management** - Invite users, permissions
12. **Billing** - Plans, usage, limits

---

## Settings Data Model

### Backend

```python
class UserPreferences(models.Model):
    user = models.OneToOneField(User, related_name='preferences')
    
    # Workspace
    default_case_view = models.CharField(
        max_length=20,
        choices=[('brief', 'Brief'), ('dashboard', 'Dashboard')],
        default='brief'
    )
    auto_save_delay_ms = models.IntegerField(default=1000)
    
    # AI/Agents
    chat_model = models.CharField(max_length=100, default='anthropic:claude-4-5-haiku-20251022')
    agent_check_interval = models.IntegerField(default=3)  # turns
    agent_min_confidence = models.FloatField(default=0.75)
    
    # Case creation
    auto_create_inquiries = models.BooleanField(default=True)
    auto_detect_assumptions = models.BooleanField(default=True)
    
    # Appearance
    theme = models.CharField(
        max_length=10,
        choices=[('light', 'Light'), ('dark', 'Dark'), ('auto', 'Auto')],
        default='light'
    )
    font_size = models.CharField(max_length=10, default='medium')
    
    # Notifications
    email_notifications = models.BooleanField(default=False)
    notify_on_inquiry_resolved = models.BooleanField(default=True)
    
    # Advanced
    show_debug_info = models.BooleanField(default=False)
```

### Frontend

```typescript
interface UserPreferences {
  // Workspace
  default_case_view: 'brief' | 'dashboard';
  auto_save_delay_ms: number;
  
  // AI
  chat_model: string;
  agent_check_interval: number;
  agent_min_confidence: number;
  
  // Features
  auto_create_inquiries: boolean;
  auto_detect_assumptions: boolean;
  
  // Appearance
  theme: 'light' | 'dark' | 'auto';
  font_size: 'small' | 'medium' | 'large';
  
  // Notifications
  email_notifications: boolean;
  notify_on_inquiry_resolved: boolean;
}
```

---

## Skills in Settings: Positioning

### What NOT to Do
```
❌ Settings > Skills (main tab)
   - Makes skills too prominent
   - Implies they're core workflow
   - Users feel obligated to configure
```

### What TO Do
```
✅ Settings > AI & Agents > Advanced > Skills
   or
✅ Settings > Advanced > Skills & Templates
```

**Presentation**:
- Collapsed by default
- "Skills (Optional)" label
- Help text: "Configure domain-specific templates for agents"
- Link to skill marketplace/templates

**Why**:
- Skills are powerful but optional
- Most users use org defaults
- Power users can find them
- Doesn't clutter main settings

---

## Mockup: Enhanced Settings Modal

```
┌──────────────────────────────────────────────────────────┐
│  Settings                                          [×]   │
├──────────────┬───────────────────────────────────────────┤
│              │                                           │
│  Profile     │  **Profile**                              │
│  Workspace  ◄│                                           │
│  AI & Agents │  Name: [Alice Chen_________________]      │
│  Appearance  │  Email: alice@startup.com (verified ✓)   │
│  Advanced    │  Role: [Founder ▼]                        │
│              │                                           │
│              │  ────────────────────────────────────     │
│              │                                           │
│              │  **Workspace Preferences**                │
│              │                                           │
│              │  Default case view:                       │
│              │  ○ Brief  ● Dashboard  ○ Documents        │
│              │                                           │
│              │  Auto-save delay: [1_] second(s)          │
│              │                                           │
│              │  Case creation:                           │
│              │  ☑ Auto-create inquiries from questions   │
│              │  ☑ Auto-detect assumptions                │
│              │  ☑ Auto-generate titles                   │
│              │                                           │
│              │  Evidence defaults:                       │
│              │  Min credibility for resolution: [3★▼]    │
│              │                                           │
│              │           [Cancel] [Save Changes]         │
│              │                                           │
└──────────────┴───────────────────────────────────────────┘
```

---

## AI & Agents Tab (Detailed)

```
**AI Model Selection**

Chat Model: [Dropdown: Claude 4.5 Haiku ▼]
├─ Claude 4.5 Haiku (Fast, low cost) ← Current
├─ Claude 4.5 Sonnet (Balanced)
├─ GPT-4o Mini (Fast, OpenAI)
└─ GPT-4o (Most capable, high cost)

────────────────────────────────────

**Agent Behavior**

Inflection Detection:
  Sensitivity: ○ Low (5 turns)  ● Medium (3 turns)  ○ High (every turn)
  Min confidence: [0.75_____] (higher = fewer suggestions)
  
  ☐ Auto-run agents (when confidence > 0.95) ⚠️ Experimental

Agent Defaults:
  Research depth: ○ Quick  ● Thorough  ○ Comprehensive
  Critique style: ○ Gentle  ● Balanced  ○ Aggressive
  
────────────────────────────────────

**Advanced: Per-Agent Models** (Collapsed by default)

[▶ Show advanced agent configuration]

When expanded:
  Research agent: [Claude 4.5 Sonnet ▼] (Override chat default)
  Critique agent: [Claude 4.5 Sonnet ▼]
  Brief agent: [GPT-4o Mini ▼]
  Signal extraction: [GPT-4o Mini ▼]
```

---

## Skills Tab (Hidden by Default)

```
**Skills & Templates** (Optional)

Personal Skills (2)
┌───────────────────────────────────────────────┐
│ Product Decision Framework          [Active] │
│ Created from: Product Launch Case            │
│ [Edit] [Promote to Team] [Archive]           │
├───────────────────────────────────────────────┤
│ My FDA Process                      [Draft]  │
│ Created: Jan 31, 2026                         │
│ [Edit] [Activate] [Delete]                    │
└───────────────────────────────────────────────┘

[+ Create New Skill] [Import from Template] [Browse Marketplace]

────────────────────────────────────

Team Skills (Shared) (3)
┌───────────────────────────────────────────────┐
│ Legal Framework                    [Active]  │
│ By: Bob (Lawyer)                              │
│ [View] [Fork to Personal]                     │
└───────────────────────────────────────────────┘

────────────────────────────────────

Organization Skills (5)
┌───────────────────────────────────────────────┐
│ FDA Regulatory Compliance         [Active]  │
│ Organization-wide                             │
│ [View Details] [Fork to Personal]             │
└───────────────────────────────────────────────┘

💡 Skills are domain-specific templates that enhance AI agents.
   They're optional—the system works great without them!
```

---

## Implementation Checklist

### Phase 1: Backend (Required)
- [ ] Create `UserPreferences` model
- [ ] Create preferences API (`/api/users/me/preferences/`)
- [ ] Add default preferences on user creation
- [ ] Connect chat model selection to chat API
- [ ] Add preferences to user serializer

### Phase 2: Enhanced Modal UI
- [ ] Add tab navigation to modal
- [ ] Migrate existing settings to Profile tab
- [ ] Add Workspace tab
- [ ] Add AI & Agents tab (enhanced)
- [ ] Add Appearance tab
- [ ] Connect to backend API

### Phase 3: Skills Integration
- [ ] Add Skills tab (collapsed by default)
- [ ] List user's skills by scope
- [ ] Add quick actions (edit, promote, fork)
- [ ] Link to skill detail/edit view

### Phase 4: Advanced Features
- [ ] Add Notifications tab
- [ ] Add Advanced tab
- [ ] Add debug options
- [ ] Add data export

---

## Quick Wins

Start with these high-impact settings:

1. **Fix model selection** (currently broken)
   - Send selected model to backend
   - Use in chat API calls

2. **Add agent sensitivity** (controls automation level)
   - Store in preferences
   - Use in inflection detection

3. **Add default case view** (dashboard vs brief)
   - Personalize landing experience
   - Store in preferences

4. **Add theme toggle** (dark mode)
   - Popular request
   - Good for extended use

---

## Files to Create/Modify

### Backend
- `backend/apps/auth_app/models.py` - Add UserPreferences model
- `backend/apps/auth_app/views.py` - Add preferences endpoint
- `backend/apps/auth_app/serializers.py` - Add preferences serializer

### Frontend
- `frontend/src/lib/api/preferences.ts` - Preferences API client
- `frontend/src/hooks/usePreferences.ts` - React Query hooks
- `frontend/src/components/settings/SettingsModal.tsx` - Enhance with tabs
- `frontend/src/components/settings/ProfileTab.tsx` - Profile settings
- `frontend/src/components/settings/WorkspaceTab.tsx` - Workspace settings
- `frontend/src/components/settings/AITab.tsx` - AI/Agent settings
- `frontend/src/components/settings/AppearanceTab.tsx` - Theme/font
- `frontend/src/components/settings/SkillsTab.tsx` - Skills management (optional)

---

## Summary

A comprehensive settings page should:
1. **Organize by user mental model** (Profile, Workspace, AI, etc.)
2. **Use progressive disclosure** (Essential → Customization → Advanced)
3. **Hide complexity** (Skills in advanced, not main tab)
4. **Be connected** (Backend persistence, not localStorage)
5. **Provide defaults** (Works great out of box)
6. **Enable power users** (Advanced options available)

Want me to implement the backend preferences API and enhanced settings UI?
