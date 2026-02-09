/**
 * Navigation type definitions for the sidebar architecture.
 *
 * Sidebar tabs represent the top-level navigation modes (Decisions / Threads).
 * Panel modes represent the contextual content shown in the sidebar panel.
 *
 * Consolidated to 2 primary sections:
 *   - decisions (cases): Cases grouped by project
 *   - threads (conversations): Chat threads
 */

// --- Sidebar Tab ---

/** The two tabs shown in the sidebar panel header. */
export type SidebarTab = 'decisions' | 'threads';

/** @deprecated Use SidebarTab instead. Kept for migration compatibility. */
export type RailSection = 'conversations' | 'cases';

// --- Panel ---

export type PanelMode =
  | { section: 'conversations'; activeThreadId?: string }
  | { section: 'cases'; activeCaseId?: string; activeProjectId?: string }
  | { section: 'none' };

// --- Navigation State ---

export interface NavigationState {
  /** Currently active sidebar tab */
  activeTab: SidebarTab;
  /** @deprecated Use activeTab. Derived from URL for backwards compat. */
  railSection: RailSection;
  /** Panel content mode (derived from tab + route params) */
  panelMode: PanelMode;
  /** Whether the context panel is collapsed */
  isPanelCollapsed: boolean;
  /** Whether a tab transition animation is in progress */
  isTransitioning: boolean;
}
