/**
 * Navigation type definitions for the two-tier sidebar architecture.
 *
 * Rail sections represent the top-level navigation modes.
 * Panel modes represent the contextual content shown in the sidebar panel.
 *
 * Consolidated to 2 primary sections:
 *   - conversations: Chat threads + hero input landing
 *   - cases: Cases grouped by project
 */

// --- Rail ---

export type RailSection = 'conversations' | 'cases';

// --- Panel ---

export type PanelMode =
  | { section: 'conversations'; activeThreadId?: string }
  | { section: 'cases'; activeCaseId?: string; activeProjectId?: string }
  | { section: 'none' };

// --- Navigation State ---

export interface NavigationState {
  /** Currently active rail section (derived from URL) */
  railSection: RailSection;
  /** Panel content mode (derived from rail section + route params) */
  panelMode: PanelMode;
  /** Whether the context panel is collapsed */
  isPanelCollapsed: boolean;
  /** Whether a rail transition animation is in progress */
  isTransitioning: boolean;
  /** Previous rail section (for animation direction) */
  previousRailSection: RailSection | null;
}

// --- Rail Item ---

export interface RailItem {
  id: RailSection;
  label: string;
  href: string;
  icon: 'conversations' | 'cases';
}

export const RAIL_ITEMS: RailItem[] = [
  { id: 'conversations', label: 'Chat', href: '/chat', icon: 'conversations' },
  { id: 'cases', label: 'Cases', href: '/cases', icon: 'cases' },
];
