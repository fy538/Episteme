/**
 * Navigation type definitions for the sidebar architecture.
 *
 * Three-mode progressive zoom sidebar:
 *   - home: All projects + scratch threads
 *   - project: Scoped to one project (landscape, threads, cases, sources)
 *   - case: Scoped to one case (plan, inquiries, assumptions, criteria)
 */

// --- Sidebar Mode (new primary system) ---

/** The three sidebar modes representing progressive zoom levels. */
export type SidebarMode =
  | { mode: 'home' }
  | { mode: 'project'; projectId: string }
  | { mode: 'case'; caseId: string; projectId?: string };

/** Direction of sidebar transition animation. */
export type TransitionDirection = 'forward' | 'back' | null;

// --- Navigation State ---

export interface NavigationState {
  /** Current sidebar mode — derived from URL */
  sidebarMode: SidebarMode;
  /** Direction of last mode transition (for slide animation) */
  transitionDirection: TransitionDirection;
  /** Whether the context panel is collapsed */
  isPanelCollapsed: boolean;
  /** Whether a mode transition animation is in progress */
  isTransitioning: boolean;
}

