# Navigation & Information Architecture Analysis for Episteme

**Date:** 2026-02-07
**Purpose:** Competitive analysis of sidebar/navigation patterns across apps most similar to Episteme's hybrid AI research workspace.

---

## Table of Contents

1. [Notion](#1-notion)
2. [Linear](#2-linear)
3. [ChatGPT / Claude.ai](#3-chatgpt--claudeai)
4. [Cursor / VS Code](#4-cursor--vs-code)
5. [Coda / Airtable](#5-coda--airtable)
6. [Dovetail](#6-dovetail)
7. [Mem.ai / Granola / Lex](#7-memai--granola--lex)
8. [Slack / Discord](#8-slack--discord)
9. [Best Practices & Design System Guidelines](#9-best-practices--design-system-guidelines)
10. [Synthesis: Episteme's Current Architecture & Recommendations](#10-synthesis-epistemes-current-architecture--recommendations)

---

## 1. Notion

### Sidebar Structure (Top to Bottom)

**Zone 1 -- Workspace Switcher (Top Bar)**
- Workspace name displayed at the very top of the sidebar.
- Click opens a dropdown listing all workspaces the user belongs to, plus options to create/join workspaces.
- This is the highest-level context switch in the entire app.

**Zone 2 -- Utility Row (Fixed, Never Changes)**
- **Search** (Cmd+K): Opens the universal search/command palette.
- **Home**: Returns to a "recent pages" feed -- not a dashboard, but a chronological list of recently accessed pages across the workspace.
- **Inbox**: Notifications, mentions, page updates.
- **Notion AI**: Opens the AI assistant panel (sometimes inline, sometimes as a sidebar overlay).
- These four items are _always_ present regardless of which page the user is viewing.

**Zone 3 -- Favorites**
- Appears after the user favorites their first page.
- Flat list of starred pages from _anywhere_ in the workspace.
- User-personal: each user sees only their own favorites.
- Pages in Favorites are not grouped by teamspace or hierarchy -- they are a shortcut layer that cuts across the organizational structure.
- Can be reordered via drag-and-drop.

**Zone 4 -- Teamspaces**
- Each teamspace is a collapsible section header (e.g., "Engineering", "Marketing", "Design").
- Clicking the teamspace name reveals/hides the top-level pages within that teamspace.
- Pages nest infinitely: every page can contain sub-pages, shown as an indented tree with expand/collapse chevron toggles.
- Each level of nesting is indented approximately 12-16px, with a rotation animation on the chevron.
- Private teamspaces are invisible unless you are a member.
- Teamspace settings (icon, description, members) are accessible via a "..." menu on hover.

**Zone 5 -- Shared**
- Contains pages shared with select individuals but not belonging to any teamspace.
- Useful for ad-hoc collaboration pages.

**Zone 6 -- Private**
- Personal pages visible only to the individual user.
- Default location for new pages created from the sidebar.
- Cannot be seen by other workspace members.

**Zone 7 -- Bottom Utility (Fixed)**
- **Settings & Members**: Opens workspace settings.
- **Templates**: Template gallery.
- **Trash**: Deleted pages.
- These are pinned to the bottom and always visible.

### How It Changes Across Contexts

The sidebar is **globally persistent** -- it does NOT change when you navigate into a page, database, or any other view. The full workspace tree is always visible. The active page is highlighted with a blue/accent background in the tree. There is no "contextual sidebar" that swaps content based on what you are viewing.

### How Conversation/Chat History Is Surfaced

Notion AI has no persistent conversation history in the sidebar. AI is accessed contextually:
- Via the AI button in the utility row (opens a chat overlay).
- Via `/ai` slash commands inline within a page.
- Via text selection -> "Ask AI" in the context menu.
Conversations with AI are ephemeral -- they exist only during the current session and are not saved as navigable objects.

### "Back to Home" Pattern

Click "Home" in the utility row. This returns to a reverse-chronological feed of recently viewed pages. There is no "dashboard" in the traditional sense.

### Collapse Behavior

- The entire sidebar collapses via Cmd+\ or by clicking the `<<` toggle.
- When collapsed, the sidebar is **fully hidden** (not reduced to an icon rail).
- Hovering near the left edge reveals it as a floating overlay.
- The sidebar width is resizable by dragging its right edge (elastic behavior).

### Strengths
- Infinite nesting handles arbitrarily complex information hierarchies.
- Favorites provide personal shortcuts that transcend organizational structure.
- Teamspaces create team-level scoping without losing workspace context.
- The sidebar is completely customizable: drag-and-drop reordering, collapsible toggles, configurable visibility per section.
- Drag-and-drop reordering of sections themselves (e.g., move Favorites above/below Teamspaces).

### Weaknesses
- Deep nesting quickly becomes cluttered; progressive indentation eats horizontal space in a 240-280px sidebar.
- No visual distinction between a "page" and a "database" at the sidebar level beyond a tiny icon difference.
- Navigation can become overwhelming in large workspaces with 5+ teamspaces and hundreds of pages.
- Favorites is a flat list that does not scale beyond ~15-20 items.
- When collapsed, there is no icon rail -- you lose all navigation context until you hover.

---

## 2. Linear

### Sidebar Structure (Top to Bottom)

**Zone 1 -- Workspace Switcher**
- Workspace logo and name at the top.
- Click opens a dropdown to switch between workspaces or access workspace settings.

**Zone 2 -- Global Personal Navigation (Fixed)**
- **Inbox**: Notifications, assigned issues, mentions. Shows unread count badge.
- **My Issues**: All issues assigned to the current user across all teams.
- These are user-personal views that span the entire workspace.

**Zone 3 -- Workspace-Level Views**
- **Initiatives**: High-level goals that span multiple projects and teams.
- **Projects**: All projects across teams (with status grouping: Planned, In Progress, Completed, Cancelled).
- **Views**: Saved custom filter views that the user has created.
- These provide cross-team overviews.

**Zone 4 -- Team Sections (Repeating)**
Each team (e.g., "Engineering", "Design") is a collapsible group. Under each team:
- **Issues**: Hovering reveals a flyout sub-menu with views: Active, Backlog, Upcoming.
- **Projects**: Team-specific projects.
- **Cycles** (if enabled): Sprint-like time-boxed periods. Hovering reveals flyout: Current Cycle, Upcoming, Past.
- **Triage** (if enabled): Incoming unprocessed issues.

Sub-teams (introduced March 2025) allow nesting teams within teams, creating a hierarchy like: Engineering > Frontend > React Team. This mirrors organizational structure in the sidebar.

**Zone 5 -- Bottom Utility**
- **Settings**: Workspace and personal settings.
- User avatar/profile.

### How It Changes Across Contexts

The sidebar is **globally persistent** -- it does NOT change regardless of which view, issue, or project you are viewing. Clicking into a specific issue opens it as a detail view in the main content area, but the sidebar remains unchanged. The active item gets a highlighted background.

### Personalization (December 2024 Update)

Users can now:
- Reorder sidebar items via drag-and-drop.
- Hide items behind a "More" menu to reduce clutter.
- Customize notification display (count badge vs. dot vs. hidden).
- Right-click context menus on sidebar items for quick actions.
- Choose which teams appear expanded vs. collapsed by default.

### How Conversation/Chat History Is Surfaced

Linear has no chat interface. AI is used behind the scenes for:
- Auto-triage of incoming issues.
- Issue summarization.
- Writing assistance (auto-generating descriptions, comments).
- Smart search (natural language queries via Cmd+K).

### "Back to Home" Pattern

There is no explicit "Home" page. The primary landing views are Inbox or My Issues, both always one click away from the sidebar. The Cmd+K command palette serves as the universal escape hatch and navigation tool.

### Collapse Behavior

The sidebar does not collapse to an icon rail. It can be toggled on/off entirely, or resized.

### Keyboard Navigation

Linear is keyboard-first:
- `G then I` = Go to Inbox
- `G then V` = Go to current cycle
- `G then B` = Go to backlog
- `C` = Create issue
- `Cmd+K` = Command palette (search + commands)

### Strengths
- Clean visual hierarchy with minimal nesting (max 2 levels: Team > Section).
- Personalization lets each user optimize their own sidebar.
- Hover flyouts for sub-views (Active, Backlog, Upcoming) avoid cluttering the tree.
- Keyboard shortcuts are extensive and consistent (G+modifier for navigation, C for creation).
- Sub-teams allow organizational hierarchy without deep visual nesting.
- The "Initiatives" layer provides workspace-level goal tracking above projects.

### Weaknesses
- Team sections multiply in large organizations (10+ teams make the sidebar very long).
- No visual differentiation between different object types in the sidebar.
- Flyout sub-menus require mouse precision and are not discoverable.
- No cross-team view of issues (except via My Issues or custom Views).

---

## 3. ChatGPT / Claude.ai

### ChatGPT

**Sidebar Structure (Top to Bottom)**

**Zone 1 -- Action Bar (Top)**
- "New chat" button (prominent, always visible).
- Model selector dropdown (GPT-4o, GPT-4, etc.).
- "ChatGPT" logo that doubles as a home link.

**Zone 2 -- Projects Section**
- Projects appear as folder-like workspaces with custom name and color.
- Each project contains:
  - Grouped conversations (multiple chat threads).
  - Uploaded files that serve as persistent context.
  - Project-specific instructions (custom system prompt).
- Clicking a project opens a project view showing all its chats and files.
- Projects are shareable (as of October 2025) -- team members can contribute.
- Projects appear _above_ individual conversations in the sidebar.

**Zone 3 -- Conversation History**
- Recent conversations listed in reverse chronological groups:
  - "Today"
  - "Yesterday"
  - "Previous 7 Days"
  - "Previous 30 Days"
- Limited number shown initially; scrolling reveals older conversations.
- Each conversation shows its auto-generated or manually-edited title.
- Active conversation is highlighted.
- Hover reveals a "..." menu for rename, archive, delete, share.

**Zone 4 -- Pinned GPTs**
- Recent and pinned custom GPT models displayed below conversations.
- Quick switching between preferred GPT configurations.

**Zone 5 -- Bottom**
- Settings icon (gear).
- User profile/account.
- Settings icon is consistently positioned at the bottom.

**Sidebar Behavior:**
- The sidebar now operates in **floating mode** (as of the 2025 redesign): it hovers over content rather than pushing it aside.
- **Soft dismiss**: clicking outside the sidebar or selecting an item closes it.
- This preserves maximum screen real estate for the conversation.
- An infinite scroll flyout provides seamless browsing of older conversations.

### Claude.ai

**Sidebar Structure (Top to Bottom)**

**Zone 1 -- Action Bar (Top)**
- "New chat" button.
- Model/tone selector: dropdown for choosing tone (Formal/Casual) and length (Short/Detailed).

**Zone 2 -- Projects Section**
- Projects are displayed as a dedicated section, visually separated from individual conversations.
- Each project functions as a **knowledge container**:
  - Contains multiple conversation threads.
  - Contains uploaded reference documents (PDFs, spreadsheets, text files).
  - Documents uploaded once are available across all conversations within the project.
  - Has project-specific custom instructions.
- Clicking a project opens a project view listing:
  - All chats within the project.
  - Uploaded documents with previews.
  - Project instructions/settings.
- This is the most sophisticated organizational structure among AI chat tools.

**Zone 3 -- Conversation History**
- Individual conversations listed chronologically below projects.
- Flat list, manually renameable.
- No automatic grouping by date (unlike ChatGPT).
- Each conversation is a simple text link.

**Zone 4 -- Bottom**
- Settings.
- User profile.

### Context Behavior (Both Tools)

**Home Screen:**
- Sidebar shows the full conversation/project list.
- Main area displays a centered input with suggested prompts, quick actions, or recent activity.
- The input is the hero element, positioned prominently.

**In a Conversation:**
- Sidebar remains visible with the full conversation list.
- Active thread is highlighted.
- Main area fills entirely with the chat thread.
- Claude shows "Artifacts" (code, documents, visualizations) in a right-side panel.

**In a Project:**
- Main area shows the project view (chats + documents + instructions).
- Sidebar maintains the full workspace view (does not scope to just that project).

### "Back to Home" Pattern

- Click the product logo (ChatGPT icon / Claude icon) or "New chat" to return to the home/new conversation view.
- ChatGPT also shows a small home icon.

### Strengths
- Simplicity: the sidebar is essentially a list of conversations with lightweight grouping.
- New chat is always one click away.
- ChatGPT's floating sidebar preserves screen real estate.
- Claude's Projects solve the "many scattered conversations" problem effectively by bundling related chats with reference documents.
- Projects as shared knowledge bases enable team collaboration.

### Weaknesses
- Flat conversation lists do not scale beyond ~50 conversations without search.
- No tagging, filtering, or multi-level organization beyond projects.
- No way to see structured content (briefs, documents, analyses) alongside conversation history in the sidebar.
- Limited visual hierarchy: every conversation looks identical in the list.
- No activity indicators or status markers on conversations.
- Search is the only way to find old conversations in a large history.

---

## 4. Cursor / VS Code

### VS Code's Three-Tier Layout

**Tier 1 -- Activity Bar (Icon Rail)**
- Narrow vertical strip (~48px) on the far left (or right, configurable).
- Contains icon-only buttons for top-level modes:
  - **Explorer** (file icon): File tree, open editors, outline.
  - **Search** (magnifying glass): Global search input and results.
  - **Source Control** (branch icon): Git changes, branches, commits.
  - **Run & Debug** (play icon): Debug configurations, breakpoints.
  - **Extensions** (blocks icon): Marketplace, installed extensions.
- Extensions can add their own Activity Bar icons.
- **Only one item is active at a time.** The active item has a highlighted state: typically a left border indicator (a 2px accent-colored bar) plus a brighter icon.
- The Activity Bar also contains a **Settings gear** at the very bottom, and optionally a **user account icon**.

**Tier 2 -- Primary Sidebar (~300px)**
- Appears immediately to the right of the Activity Bar.
- **Content changes entirely** based on which Activity Bar icon is selected:
  - Explorer selected: File tree (hierarchical, expandable), Open Editors list, Outline view of current file.
  - Search selected: Search input field, file filter, results tree with file grouping.
  - Source Control selected: Changed files list, commit message input, branch switcher.
  - Extensions selected: Extension marketplace search, installed extensions list.
- Each sidebar mode has its own internal sub-views (called "Views") that can be shown/hidden and reordered.
- View Containers with multiple views show a "..." button in the sidebar toolbar to toggle individual views.
- When a View Container has only one view, the toolbar consolidates to show that view's actions directly.

**Tier 3 -- Secondary Sidebar (Optional, Right Side)**
- VS Code supports a secondary sidebar on the opposite side.
- Users can drag views from the primary sidebar or bottom panel into the secondary sidebar.
- Useful for side-by-side panels (e.g., file explorer on left, terminal on right).

### Cursor's Extension of This Pattern

Cursor inherits VS Code's Activity Bar + Sidebar but adds AI-specific panels:

**AI Chat Panel (Default: Left Side in Cursor 2.0+)**
- Toggled via Cmd+L.
- Contains:
  - Model selector dropdown (Claude, GPT-4, etc.).
  - Conversation thread with code diffs inline.
  - File context chips showing which files are referenced.
  - "Agent" tab for autonomous multi-step operations.
- In Cursor 2.0 (December 2025), the chat moved to the LEFT side by default, and the file explorer moved to the RIGHT. This was controversial -- many users preferred the previous layout.
- Users can customize placement: drag the chat panel to top, right, or bottom positions.

**The "Three-Panel" Default Layout:**
- Left: AI Chat panel (or Activity Bar + Sidebar).
- Center: Code editor.
- Right: File explorer (or secondary sidebar).
- This creates a strong spatial model: AI interaction on left, work in center, file navigation on right.

**Agent Tab:**
- A dedicated tab within the AI panel for agent-mode interactions.
- Shows the agent's plan, current step, file modifications, and terminal commands.
- Plans and runs become first-class sidebar objects.

### Context Behavior

The Activity Bar is **globally persistent**. Clicking a different icon swaps the entire Primary Sidebar content. This is the canonical "mode switching" pattern. Within each mode, the sidebar has its own internal hierarchy (tree views, sections, toolbars).

The key insight: **the Activity Bar provides O(1) access to any mode**, and each mode gets a fully optimized sidebar UI without competing for space.

### Collapse Behavior

- The Activity Bar can be hidden entirely via View menu.
- The Primary Sidebar can be toggled independently (Cmd+B).
- Individual views within the sidebar can be shown/hidden.
- The sidebar can collapse to show only the Activity Bar (~48px) without showing any panel content.

### Strengths
- The Activity Bar is an excellent pattern for mode switching: small footprint, always visible, provides a visual inventory of available modes.
- Completely context-dependent sidebar content means each mode gets its own optimized UI.
- Users build strong spatial memory: "file tree is always in the same position."
- Highly extensible: any tool/extension can add an Activity Bar icon and sidebar panel.
- The three-tier system (rail + primary panel + secondary panel) handles complex information needs.

### Weaknesses
- Mode switching means losing sight of one context when viewing another (cannot see file tree and search results simultaneously without the secondary sidebar).
- The Activity Bar becomes crowded with many extensions installed.
- The Cursor 2.0 layout change (chat left, explorer right) broke users' muscle memory.
- Fixed panel layout can be rigid on smaller screens.
- The distinction between Primary Sidebar, Secondary Sidebar, and Bottom Panel creates cognitive overhead for new users.

---

## 5. Coda / Airtable

### Coda

**Two-Level Navigation System:**

**Level 1 -- Workspace Level (Left Sidebar)**
- Shows the full list of workspaces you belong to.
- Current workspace is expanded, showing:
  - Folders within the workspace.
  - Docs within each folder (or at workspace root).
- Each doc is a link; clicking enters the doc context.
- The sidebar at this level is similar to a file manager.

**Level 2 -- Doc Level (Page List Sidebar)**
- Once inside a doc, the left panel becomes the **"page list"**: a tree of pages and subpages within that document.
- Pages can nest infinitely under other pages (subpages).
- The page list can be collapsed by clicking the page icon in the upper-left corner.
- When hidden, hovering over the left edge reveals it as an overlay.
- Pages can be reordered via drag-and-drop.
- Pages can be hidden from the list to reduce visual noise.

**2025 UI Refresh:**
- **Breadcrumbs** added: a hierarchical path showing where you are within a doc's page structure (e.g., "Workspace > Doc > Page > Subpage").
- **Home icon**: dedicated icon to jump back to workspace level.
- These address the "lost in a complex doc" problem.

**Within a Page:**
- Pages can contain rich content: text, tables, views, buttons, formulas, embedded data.
- Tables support multiple view types: Grid, Card, Calendar, Detail, Kanban.
- Detail views have their own internal left-hand navigation bar for switching between rows.
- Views are created inline within pages, not as separate sidebar items.

**Context Behavior:**
- Navigating from workspace-level to doc-level is a **distinct context switch**: the sidebar content completely changes from "folder/doc list" to "page tree."
- Breadcrumbs and back buttons provide the path back to workspace level.
- Within a doc, the sidebar shows only that doc's page tree.

### Airtable

**Multi-Level Navigation Hierarchy:**

**Level 1 -- Home Screen**
- Left sidebar shows:
  - Workspace list (collapsible).
  - "All workspaces" view.
  - "Starred" section for favorited bases.
- Main area shows bases organized by workspace.
- "Recently opened" section at the top of the main area.
- Sidebar can be collapsed by clicking the sidebar toggle.

**Level 2 -- Inside a Base**
- The navigation changes significantly:
  - **Table tabs** appear as horizontal tabs at the TOP of the screen (not in the sidebar). Each tab represents a table within the base.
  - **View sidebar** appears in the top-left area:
    - "My views" section: personal views.
    - "All views" section: all shared views.
    - Each view has a type icon (Grid, Kanban, Calendar, Gallery, Form, Timeline).
    - Creating a new view opens a type selector.
  - The left sidebar from the home screen is no longer visible.

**Level 3 -- Interface Designer**
- When in Interface mode, the left sidebar becomes a completely different navigation:
  - Interface pages listed vertically.
  - Interface groups for organizing pages.
  - Page settings and layout options.
- This is a separate editing mode for building end-user dashboards.

**Context Behavior:**
- There are significant context switches between Home -> Base -> Interface.
- Each level has its own sidebar content.
- The top bar provides breadcrumbs and a home button (Airtable logo) for navigation between levels.
- There is no universal sidebar that spans all contexts.

### Strengths (Both)
- Strong separation between workspace-level and document-level navigation.
- Multiple view types for the same data give users flexibility without cluttering navigation.
- Coda's page tree within a document is clean and intuitive.
- Airtable's Interface Designer provides a separate clean navigation layer for end-users vs. builders.
- Coda's 2025 breadcrumbs solve the "where am I?" problem effectively.

### Weaknesses
- Context switches between levels can be disorienting.
- Airtable has inconsistent navigation between Base view, Interface view, and Automations view.
- Coda's two-level system means you lose workspace context when inside a doc.
- Neither provides a way to see cross-document information simultaneously.
- Airtable's view sidebar is cramped and can get very long with many views.

---

## 6. Dovetail

### Dovetail 3.0 Navigation (Redesigned Late 2024)

**Global Vertical Sidebar (Left, Always Present)**

The sidebar operates **collapsed by default** to maximize workspace focus. Users expand it via:
- The hamburger menu (three-line icon) in the top left.
- Pressing the `[` key.

When expanded, the sidebar contains:

**Top Section -- Primary Actions:**
- **Home**: Unified view merging previous "Your work" and "Browse" tabs. Shows:
  - Recent work items.
  - Full workspace folder tree.
  - Admin-pinned projects and folders at top.
  - Personal favorites.
- **Search**: Workspace-wide search.
- **New** (create button): Create new projects, channels, folders.

**Middle Section -- Workspace:**
- **Projects**: All research projects, organized in folders.
- **Dashboards**: Cross-project analytics views.
- **Channels**: Continuous feedback streams (support tickets, survey responses) that are auto-analyzed by AI. Channels are a distinct concept from projects.

**Bottom Section -- Favorites:**
- User-personal favorites list.
- Can favorite folders, projects, and channels.
- One-click access to frequently used resources.

**Fixed Bottom:**
- **Settings**.
- **More** (additional options).

### Within a Project -- Horizontal Navigation

This is a key design decision: within projects, Dovetail moved from a vertical sidebar to a **horizontal header navigation** to simplify the interface and provide more room for content. The horizontal nav shows the research workflow progression:

- **Data**: Raw research data (notes, images, audio, video).
- **Analysis**: Tagging, coding, charts, pattern identification.
- **Insights** (now called "Docs" in 3.0): Summarized findings.

This left-to-right flow maps the research workflow: collect data -> analyze it -> produce insights.

### Insights/Docs Evolution

Insights have evolved into **"Docs"** which function independently from individual projects:
- Can analyze across projects.
- Centralize reports at workspace or folder level.
- Powered by generative AI for summaries and cross-project analysis.
- Displayed in a newspaper-style layout (grid or list toggle) with large images, excerpts, author avatars, and publish dates.

### Sidebar Collapse Behavior

When working inside a project, the sidebar auto-collapses to give maximum room for content. This means the horizontal project nav (Data/Analysis/Docs) and the main content area get the full width.

### Views Within Data/Analysis

Data, highlights, and insights can be viewed in multiple layouts:
- Grid view.
- Board view (groups by field, like Kanban).
- Table view.

### Strengths
- The Data -> Analysis -> Insights horizontal flow maps perfectly to a research workflow progression.
- Global sidebar with favorites provides consistent top-level navigation.
- Collapsed-by-default sidebar maximizes content space.
- Labels on all navigation actions (not just icons) reduce cognitive load.
- Cross-project search for insights/docs breaks down silos.
- Channels as a separate concept for always-on feedback streams is clever.
- The Home tab unifying "Your work" and "Browse" reduces tab-switching.

### Weaknesses
- Users report confusion with the project organization system.
- Heavy reliance on manual tagging for navigation and discovery.
- Semantic search sometimes interferes with simple keyword search.
- Navigating between old reports and folders creates friction.
- The auto-collapsing sidebar requires re-expanding when switching between projects.

---

## 7. Mem.ai / Granola / Lex

### Mem.ai

**Three-Panel Layout:**

**Left Sidebar (~240px):**
- **Home**: Timeline view showing mems (notes) as cards in reverse chronological order.
- **Upcoming meetings**: Calendar-linked upcoming meetings.
- **Creative mems**: AI-curated mems for creative work.
- **Shared mems**: Notes shared by/with others.
- **Collections**: Lightweight groupings (not folders -- more like tags).

**Center Panel:**
- The current note editor (clean, distraction-free writing surface).
- Or search results when searching.

**Right Sidebar -- "Heads Up" Panel:**
- **Related mems**: Automatically surfaced by AI based on the content of the current note.
- **Referenced by**: Mems that link to the current note.
- **Mentions**: Mems containing words from your tags.
- **Hover previews**: Hovering over a related mem shows a content preview.
- This panel is the core of Mem's value proposition: AI does the organizing.

**Navigation Philosophy:**
Mem deliberately rejects hierarchical organization. There are:
- **No folders.**
- **No required tags.**
- **No manual filing.**
Instead, navigation is primarily through:
- Search (Cmd+K).
- The reverse-chronological timeline.
- AI-surfaced relationships in the right sidebar.
- Command palette (Cmd+/) for quick actions.

**Strengths:**
- Extremely low organizational overhead; AI handles the connections.
- Clean writing surface without organizational distractions.
- The "Heads Up" right sidebar provides context without the user having to search.
- Hover previews on related mems enable quick reconnaissance.

**Weaknesses:**
- Lack of explicit structure can be disorienting for users who want to organize.
- Finding specific notes relies entirely on search accuracy and AI quality.
- No project-level grouping for multi-note research efforts.
- The "magic" of AI surfacing can feel unpredictable.

### Granola

**Clean Split-Screen Layout:**

**Left Sidebar (~240px):**
Organized by relationship type (this is the key differentiator):
- **Companies**: Meeting notes grouped by company/organization.
- **People**: Notes grouped by individual contact.
- **Team**: Shared notes within your team.
- **Folders**: Manual grouping for notes.
- **Shared with me**: Notes others have shared.
- **Recent meetings**: Quick access to latest notes.

Clicking a company or person shows all meeting notes associated with that entity, creating an automatic CRM-like view.

**Center Panel:**
- Meeting note editor (looks like Apple Notes or Google Docs).
- Rich text with formatting, headers, bullet points.
- Markdown-style editing.

**Right Panel -- AI Sidebar:**
- AI-generated meeting notes (collapsible).
- Live transcript during active meetings.
- Toggled via Cmd+J.
- After the meeting: AI summary, action items, key decisions.

**Navigation Philosophy:**
Organization is automatic, based on:
- Meeting participants (extracted from calendar events).
- Company associations.
- Recurring meeting detection.
Zero learning curve: notes are automatically filed by relationship.

**Strengths:**
- Automatic organization by relationship is powerful for meeting-centric work.
- The Companies/People/Team sidebar creates natural browsing paths.
- Minimal navigation required -- most access is through the relationship hierarchy.
- AI sidebar with transcript is contextual and non-intrusive.

**Weaknesses:**
- Narrow use case (meetings only).
- No support for non-meeting research or analysis.
- Relationship-based navigation doesn't work for solo work or document creation.

### Lex

**Minimalist Two-Panel Layout:**

**Left Panel -- Document Browser (~200px):**
- Flat list of documents, optionally organized in folders.
- Each document shows title and last-edited timestamp.
- Minimal chrome: no icons, no status indicators, no metadata.
- Designed to feel like a notebook table of contents.
- Can be collapsed to give the editor full width.

**Center Panel -- Writing Canvas:**
- Clean, distraction-free editor similar to iA Writer or Bear.
- Large serif typography (focused on reading/writing experience).
- No toolbar visible by default; formatting via keyboard shortcuts or `/` commands.

**Right Panel -- "Ask Lex" AI Sidebar:**
- Toggled on/off (not always visible).
- Contains pre-loaded prompt buttons:
  - "Get feedback on my draft"
  - "Get feedback on my article idea"
  - "Sharpen my introduction"
  - "Identify weak arguments"
  - "Help me overcome writer's block"
- Free-form chat input for custom questions.
- Responses appear in the sidebar as a conversation thread.
- Does not maintain persistent conversation history across sessions.

**Navigation Philosophy:**
Keyboard-first with `/` commands for AI interaction inline. The document list is intentionally simple to keep focus on writing. The AI sidebar is an overlay that does not disrupt the writing flow.

**Strengths:**
- Excellent focus on single-task (writing/thinking).
- AI assistance is ambient but not intrusive.
- Pre-loaded prompts reduce the cognitive overhead of "what should I ask the AI?"
- The document list is refreshingly simple.
- Keyboard-first navigation keeps writers in flow.

**Weaknesses:**
- No project-level organization.
- Not designed for multi-document research workflows.
- No way to reference multiple documents in AI conversation.
- Document list doesn't scale beyond ~50-100 documents.
- No collaboration features in the sidebar.

---

## 8. Slack / Discord

### Slack (2024-2025 Redesign)

**Top-Level Tab Navigation:**
Slack uses a horizontal tab bar at the top of the sidebar (above the channel list) with the following default tabs:

- **Home**: Shows all channels, DMs, and apps in a single view. This is the "base camp."
- **DMs**: Dedicated tab showing only direct message conversations with most recent message preview.
- **Activity**: Unified feed combining threads, mentions, reactions, and app notifications. Has sub-tabs within: All, Threads, Mentions, Reactions.
- **Files**: Consolidates canvases, lists, and third-party files in one location with type filters.

Behind the **More** menu:
- **Later**: Saved messages and reminders.
- **Tools** (formerly Automations): Apps, workflows, channel templates.
- **Agentforce** and **Sales** (if Salesforce is integrated).

Users can customize which tabs are visible or hidden.

**Within the Home Tab -- Sidebar Content:**

- **Directories** link at the top: Opens a separate page for People (including user groups), Channels, and External Connections.
- **Custom Sections**: Users create named groups (e.g., "Engineering", "Social", "Project X") and drag channels, DMs, and apps into them. Sections can be:
  - Collapsed/expanded independently.
  - Reordered via drag-and-drop.
  - Set to show all items or only unread items.
  - Created on Standard plan and above.
- **Create button**: Replaces the old draft message option. Can create: message, huddle, canvas, channel.

**Tab Peeking (New Feature):**
Hovering over the Activity tab icon shows a preview of its content without switching tabs.

**Workspace Switching:**
- When signed into multiple workspaces, an "All workspaces" view provides a unified sidebar across all of them.
- Users can filter to a specific workspace to focus.

### Discord

**Tier 1 -- Server Rail (Icon Rail, ~72px)**
- Narrow vertical strip on the far left.
- Contains circular server icons stacked vertically.
- Top-to-bottom order:
  - **Home/DMs button** (Discord logo) at the very top.
  - **Separator line**.
  - **Server icons** in user-defined order.
  - **Server folders**: Users can drag one server icon onto another to create a collapsible folder of servers (appears as a stacked icon that expands on click).
  - **Separator line**.
  - **Add a Server** button (green + icon).
  - **Explore Public Servers** button (compass icon).
- The active server has a **white pill indicator** on the left edge.
- Servers with unread messages show a **small white dot** on the left edge.
- Servers with mentions show a **red badge** with the mention count on the server icon.

**Tier 2 -- Channel Panel (~240px)**
- Immediately to the right of the server rail.
- Content **changes entirely** based on which server is selected.
- Structure within a server:
  - **Server name** (clickable for server settings dropdown) at the top.
  - **Server boost status bar** (if applicable).
  - **Text/voice channels** organized into **Categories** (collapsible groups like "General", "Development", "Voice Channels").
  - Categories are the top-level organizational unit.
  - Channels nest under categories but **cannot nest further** (only 2 levels: Category > Channel).
  - Each channel shows: `#` icon for text, speaker icon for voice, plus the channel name.
  - Active channel has a **white text** treatment; inactive channels are grey.
  - Channels with unread messages are **bold white**.

**Home/DMs View (when Home is selected on the rail):**
- Channel panel shows:
  - **Find or start a conversation** search bar.
  - **Friends** link.
  - **Nitro** link.
  - **Shop** link.
  - **Direct Messages** header with list of recent DM conversations.

### Context Switching

Clicking a different server icon on the rail **immediately swaps the entire channel panel** to show that server's channels. This is instant, with clear visual feedback:
- The previous server's pill indicator disappears.
- The new server's pill indicator appears.
- The channel panel animates to the new server's content.

This creates strong **spatial memory**: users remember where their servers are positioned on the rail and develop muscle memory for switching.

### Strengths (Both)
- Discord's two-tier rail + panel is one of the clearest implementations of mode switching via an icon rail. Spatial memory is strong.
- Slack's custom sections provide flexible user-defined organization without imposing structure.
- Both maintain consistent top-level navigation regardless of current view.
- Discord's server folders help manage rail overflow elegantly.
- Slack's tab peeking provides context without full context switches.
- Discord's unread indicators (dot, bold, badge) provide three levels of urgency at a glance.

### Weaknesses
- Discord's channel panel can get very long with many categories and channels.
- Slack's 2024 redesign moved familiar features (People, Channels, External Connections moved from tabs to a Directories page), causing "where did that go?" confusion.
- Neither handles structured content well -- they are conversation-first tools.
- Slack's tab system adds a third navigation level (tabs > sections > items) which can be cognitively heavy.
- Discord has no search within the server rail (you must scroll to find servers).

---

## 9. Best Practices & Design System Guidelines

### shadcn/ui Sidebar Component

The shadcn/ui sidebar (which Episteme could leverage, given it already uses shadcn components) provides:

**Three Layout Variants:**
- **Sidebar**: Standard fixed panel alongside content.
- **Floating**: Independent panel that overlays content.
- **Inset**: Content area wraps around the sidebar.

**Three Collapsible Modes:**
- **Offcanvas**: Slides completely away.
- **Icon**: Collapses to an icon rail (showing only icons, no labels).
- **None**: Permanently expanded, not collapsible.

**Subcomponent System:**
- `SidebarProvider`: State management wrapper.
- `SidebarHeader` / `SidebarFooter`: Fixed top/bottom areas.
- `SidebarContent`: Scrollable middle area.
- `SidebarGroup`: Named sections within content.
- `SidebarMenu` / `SidebarMenuButton`: Navigation items.
- `SidebarMenuSub`: Nested items (collapsible sub-menus).
- `SidebarRail`: A thin strip that can toggle the sidebar.
- `useSidebar` hook: Controls open/closed state.
- Default keyboard toggle: Cmd+B.

### Vercel Web Interface Guidelines

Key principles relevant to Episteme:
- **Persist all navigation state in URLs**: Filters, tabs, pagination, expanded panels should all be URL-addressable for deep-linking and browser history.
- **Semantic navigation elements**: Use `<a>` and `<Link>` for proper browser behavior (Cmd+Click to open in new tab, middle-click, right-click context menu).
- **Deliberate optical alignment**: All elements should feel visually aligned even if not mathematically so.
- **Avoid excessive scrollbars**: Fix overflow issues rather than adding scroll containers.

### General Sidebar Best Practices (Aggregated)

**Dimensions:**
- Expanded width: 240-300px.
- Collapsed (icon rail) width: 48-64px.
- Sidebar should occupy ~15% of viewport width when expanded.

**Visual Design:**
- Combine icons with text labels for comprehension.
- Use familiar iconography aligned with common UX patterns.
- Highlight hover and active states with color changes or subtle shadows.
- Active state should use a left-edge accent indicator (colored bar) plus background highlight.

**Information Hierarchy:**
- Organize links from general to specific.
- Order by usefulness, relevance, or frequency of use.
- Keep navigation shallow -- maximum 2-3 levels.
- Use clear, descriptive (but short) labels.

**Interaction:**
- Keep the sidebar persistent (fixed) -- do not scroll it with the page.
- Enable expand/collapse of sub-menus with chevron indicators.
- Support keyboard navigation (tab through items, arrow keys for tree navigation).
- Provide a keyboard shortcut to toggle sidebar visibility.

**Context-Awareness:**
- Static menus that don't adapt to user actions hinder navigation.
- Contextual sidebars that show relevant options based on current page enhance usability.
- Use breadcrumbs to improve navigation success rate.

### Three Dominant Patterns for Chat + Structured Content Hybrids

**Pattern A: "Chat-First with Project Containers" (ChatGPT, Claude.ai)**
- Sidebar is primarily a conversation list with lightweight folder/project grouping.
- Projects are containers that bundle conversations + documents.
- Works well when conversation is the primary interaction mode and structure emerges from it.
- Fails when users need to navigate complex hierarchies of structured objects.

**Pattern B: "Structure-First with Embedded AI" (Notion, Coda, Dovetail)**
- Sidebar is a hierarchical tree of structured objects (pages, databases, projects).
- AI is accessed contextually within objects (inline, slash commands, side panel).
- Works well when structured content is the primary artifact and AI assists within it.
- Fails when conversation itself is the main work product.

**Pattern C: "Mode-Switching with Contextual Panels" (VS Code/Cursor, Slack/Discord)**
- An icon rail or top-level tabs switch between completely different sidebar contexts.
- Each mode has its own optimized sidebar UI.
- Works well when the app has genuinely different operational modes.
- Fails when users need to see information from multiple modes simultaneously.

---

## 10. Synthesis: Episteme's Current Architecture & Recommendations

### Current Episteme Navigation Architecture

Based on the codebase analysis, Episteme has two distinct navigation contexts:

**Context A: Home / Dashboard View** (`Home.tsx` + `DashboardSidebar.tsx`)

Layout: `[DashboardSidebar | Main Content (Home Feed or Chat)]`

The `DashboardSidebar` implements a 5-zone collapsible left navigation:

| Zone | Expanded (w-64 = 256px) | Collapsed (w-14 = 56px) |
|------|--------------------------|-------------------------|
| 1. Workspace Header | "E" logo + "Episteme" text + collapse toggle | "E" logo + expand toggle |
| 2. Search | Full search bar with Cmd+K hint | Search icon |
| 3. Primary Nav | Home, Cases, Inquiries (icon + label) | Icons only with active indicator |
| 4. Project Tree | "Projects" header + create button, then `ProjectNavItem` tree with nested `CaseNavItem` entries (expandable) | Folder icons only |
| 5. Bottom Utility | Settings button + user avatar + name | Settings icon + avatar circle |

Key details:
- Active nav items show a 3px accent-colored left border indicator (`bg-accent-500`).
- Case items show status icons: green check (ready), yellow alert (has issues), or empty circle (in progress).
- Case items show compact timestamps (time today, day name this week, M/D for older).
- Project tree nodes have chevron expand/collapse toggles with rotation animation.
- Scroll fade masks (gradient overlays) at top/bottom of the project tree zone.

When the user sends a message from the home hero input, the home content fades out with a scale+blur animation and a full `ChatPanel` takes over the main content area, with an optional `CompanionPanel` on the right.

**Context B: Case Workspace View** (`cases/[caseId]/page.tsx` + `WorkspaceLayout.tsx`)

Layout: `[Header (breadcrumbs + mode badge) | CaseNavigation (left) | Center View (brief/inquiry/readiness/dashboard) | Right Panel (CompanionPanel + ChatPanel)]`

The `WorkspaceLayout` is a fixed three-column layout:
- Left: 256px (`w-64`) `CaseNavigation` sidebar.
- Center: Flex-1 adaptive view (switches between Brief, Inquiry, Readiness Checklist, Investigation Dashboard).
- Right: Variable-width panel containing `CompanionPanel` (stacked above) + `ChatPanel` (below).

The `CaseNavigation` sidebar shows:
- "Cases" header + "New Case" button.
- "Recent Cases" section (cases without a project).
- Project-grouped cases (expandable project headers with cases nested underneath).
- Settings button at the bottom.

The `CompanionPanel` (right sidebar) uses a **priority-ranked slot system**:
- Sidebar mode: 3 slots (vertical, each scrollable).
- Bottom mode: 2 slots (horizontal strip, compact).
- Sections compete for visibility based on recency, content density, mode relevance, and user interaction.
- Available sections: Thinking, Status, Session Receipts, Case State, Action Hints, Signals.
- Slot 1 renders expanded; slots 2+ render as compact previews.
- Overflow sections shown as "+N more" with expand-on-click.

### Where Episteme Sits in the Taxonomy

Episteme is a **hybrid** that needs elements of all three patterns:

1. **Chat is a primary interaction mode** (like ChatGPT/Claude): Users start conversations, and structured objects emerge from those conversations.
2. **Structured objects (cases, inquiries, briefs, documents) are first-class** (like Notion/Dovetail): Research has structure that outlasts any single conversation.
3. **There are distinct operational modes** (like VS Code/Linear): Dashboard/home, active conversation, case workspace, inquiry research, brief editing, readiness checking -- these are genuinely different activities.

This makes Episteme's navigation challenge harder than any single comparison app.

### Gap Analysis: What's Missing

| Need | Current State | Gap |
|------|--------------|-----|
| Mode switching between dashboard and case workspace | Two completely different layouts (`DashboardSidebar` vs `CaseNavigation`) with no shared navigation shell | No continuity between contexts; sidebar resets entirely |
| Chat history across conversations | No persistent chat history sidebar; each conversation exists only within its case context | Users cannot browse or search past conversations |
| Relationship between home chat and case chats | Home chat creates a new thread; case workspace has its own thread per case | No way to see "conversations that led to this case" or navigate between them |
| Cross-cutting navigation | `DashboardSidebar` shows Home/Cases/Inquiries but `CaseNavigation` only shows cases | Inquiries are only accessible from the dashboard sidebar, not from within a case workspace |
| AI companion context persistence | CompanionPanel resets per page load; signals are polled per thread | No persistent companion state across navigation |
| Breadcrumb / "where am I?" | Case workspace has a `ModeHeader` with breadcrumbs, but home view has none | Inconsistent wayfinding between contexts |

### Architectural Patterns Most Applicable to Episteme

**1. The VS Code/Cursor Activity Bar Pattern (Highest Relevance)**

Consider a narrow icon rail (~48-56px) on the far left for top-level mode switching:
- Home (dashboard icon)
- Chat History (message bubbles icon)
- Cases (document icon)
- Projects (folder icon)
- Search (magnifying glass)
- Settings (gear, bottom-pinned)

The sidebar panel (~240px) to the right of the rail would change content per mode:
- Home mode: Welcome/feed content in the main area, sidebar shows recent activity.
- Chat History mode: Sidebar lists all conversations (like Claude.ai), main area shows selected conversation.
- Cases mode: Sidebar shows project tree with nested cases (current `DashboardSidebar` zone 4), main area shows case workspace.
- Projects mode: Sidebar shows project list with metadata, main area shows project overview.

This solves the "two completely different sidebars" problem by unifying them under a single shell.

**2. Claude.ai's Projects as Knowledge Containers**

Episteme's "Cases" already serve a similar role to Claude's Projects. The sidebar should make this relationship explicit:
- Each case in the sidebar tree should show its associated conversations (expandable).
- Conversations should link back to their parent case.
- The case detail view should have a "Conversations" tab or section.

**3. Dovetail's Horizontal Workflow Progression**

For case detail views, consider a horizontal progression header (like Dovetail's Data -> Analysis -> Insights):
- **Brief** (the case brief / decision document)
- **Research** (inquiries and investigation)
- **Evidence** (supporting documents and data)
- **Readiness** (decision readiness checklist)

This replaces the current view-switching logic (`ws.viewMode === 'brief' ? ... : ws.viewMode === 'readiness' ? ...`) with explicit horizontal tabs.

**4. Linear's Keyboard-First Navigation**

Episteme already has a `CommandPalette` but it's scoped to the case workspace. Consider making it global and extending it:
- Navigation commands: "Go to Cases", "Go to Project X", "Open Case Y".
- Creation commands: "New Case", "New Inquiry", "New Project".
- AI commands: "Detect assumptions", "Generate research".
- Context commands: "Back to brief", "View readiness".

**5. Slack's Custom Sections / Notion's Favorites**

Allow users to create a "Favorites" or "Pinned" section in the sidebar for quick access to frequently-used cases, inquiries, or projects, cutting across the organizational hierarchy.

**6. Discord's Unread/Status Indicators on the Rail**

If using an icon rail, add subtle indicators:
- A dot for cases with new signals or companion activity.
- A badge for unread inquiry results.
- A colored ring for cases with readiness issues (tensions, blind spots).

### Summary Comparison Table

| App | Pattern | Sidebar Tiers | Collapses To | Chat in Sidebar | Context Switch Method | Most Relevant to Episteme |
|-----|---------|--------------|-------------|----------------|----------------------|--------------------------|
| Notion | Single sidebar, page tree | 1 (nested sections) | Hidden (overlay on hover) | No (inline AI) | None -- global sidebar | Favorites, infinite nesting, teamspaces |
| Linear | Single sidebar, customizable | 1 (team sections) | Hidden | No | None -- global sidebar | Personalization, keyboard-first, sub-teams |
| ChatGPT | Single sidebar, conversation list | 1 (projects + flat) | Floating overlay | Yes (primary) | None -- conversation list | Projects as containers, floating sidebar |
| Claude.ai | Single sidebar, conversation list | 1 (projects + flat) | Hidden | Yes (primary) | Project view vs. chat view | Projects as knowledge containers, document bundling |
| VS Code/Cursor | Icon rail + sidebar panel | 2 (rail + panel) | Icon rail | Right-side panel | Activity Bar icon clicks | **Mode switching, icon rail, contextual panels** |
| Coda | Two-level (workspace then doc) | 1 per level | Hidden (overlay) | No | Level transition | Breadcrumbs, page tree within doc |
| Airtable | Multi-level | 1 per level | Collapsible | No | Top-bar breadcrumbs | View types for same data |
| Dovetail | Global sidebar + horizontal header | 1 + horizontal | Collapsed by default | No | Horizontal Data/Analysis/Insights | **Horizontal workflow progression, global sidebar + project nav** |
| Mem.ai | Three-panel (left + right) | 1 per side | Hideable | No (AI surfaces) | Minimal | AI-surfaced related content in right sidebar |
| Granola | Left sidebar + collapsible AI | 1 | Hideable | Collapsible AI panel | By entity (Company/Person) | Relationship-based organization |
| Lex | Minimal doc list + AI sidebar | 1 + right AI panel | Hideable | Right-side AI panel | None | Clean AI sidebar with pre-loaded prompts |
| Slack | Tabs + custom sections | 2 (tabs + sections) | N/A | N/A (is chat) | Tab switching | Custom sections, tab peeking |
| Discord | Icon rail + channel panel | 2 (rail + panel) | N/A | N/A (is chat) | Server rail icon clicks | **Icon rail pattern, status indicators, server folders** |

### Recommended Hybrid Architecture for Episteme

Based on this analysis, the strongest candidate architecture for Episteme combines:

```
[Icon Rail (48px)] [Sidebar Panel (240px)] [Main Content Area] [Right Panel (optional, 320px)]
```

**Icon Rail (always visible):**
- Home
- Conversations (chat history)
- Cases
- Projects
- Search (or keep as Cmd+K only)
- ---separator---
- Settings (bottom)
- User avatar (bottom)

**Sidebar Panel (context-dependent, collapsible):**
Changes entirely based on rail selection:
- Home: Quick stats, action items, recent activity feed.
- Conversations: Chronological conversation list (like Claude.ai) with project/case grouping.
- Cases: Project tree with nested cases (current DashboardSidebar zone 4), with status indicators and timestamps.
- Projects: Project list with case counts, progress indicators.

**Main Content Area:**
- Home: Hero input + personalized feed (current behavior).
- Conversation: Full chat thread.
- Case: Horizontal tabbed workspace (Brief | Research | Evidence | Readiness).
- Project: Project overview with case grid.

**Right Panel (contextual, collapsible):**
- During chat: CompanionPanel with priority-ranked sections.
- During case editing: Structure sidebar with signals and suggestions.
- On home: Hidden or minimal.

This architecture provides:
1. **Persistent wayfinding** via the icon rail (always know where you are).
2. **Context-optimized content** via the swappable sidebar panel.
3. **Strong spatial memory** (cases are always in the same rail position).
4. **Graceful scaling** as new modes are added (just add an icon to the rail).
5. **Compatibility with the existing CompanionPanel** architecture on the right side.
