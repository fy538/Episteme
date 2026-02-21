/**
 * useNavigationState Hook
 *
 * Core navigation state for the three-mode sidebar architecture.
 *
 * The sidebar has three modes that match progressive zoom levels:
 *   - home: All projects + scratch threads (/, /chat, /chat/:id)
 *   - project: Scoped to one project (/projects/:id)
 *   - case: Scoped to one case (/cases/:id)
 *
 * The mode is derived from the URL pathname. Transition direction
 * (forward/back) is computed for slide animations.
 *
 * Panel collapse state is persisted in localStorage.
 */

'use client';

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import type {
  SidebarMode,
  TransitionDirection,
} from '@/lib/types/navigation';

const STORAGE_KEY = 'episteme_nav_panel_collapsed';

/** Regex patterns for extracting route params from pathname */
const CHAT_THREAD_RE = /^\/chat\/([^/]+)/;
const CASE_ID_RE = /^\/cases\/([^/]+)/;
const PROJECT_ID_RE = /^\/projects\/([^/]+)/;

// --- Mode depth for computing transition direction ---
const MODE_DEPTH: Record<SidebarMode['mode'], number> = {
  home: 0,
  project: 1,
  case: 2,
};

/** Derive the sidebar mode from the current pathname */
function deriveSidebarMode(pathname: string): SidebarMode {
  // Case page: /cases/:id (or /cases/:id/anything)
  const caseMatch = pathname.match(CASE_ID_RE);
  if (caseMatch) return { mode: 'case', caseId: caseMatch[1] };

  // Project page: /projects/:id (or /projects/:id/anything)
  const projectMatch = pathname.match(PROJECT_ID_RE);
  if (projectMatch) return { mode: 'project', projectId: projectMatch[1] };

  // Everything else: home (/, /chat, /chat/:id, /projects, /inquiries, etc.)
  return { mode: 'home' };
}

/** Compute transition direction between two sidebar modes */
function computeTransitionDirection(
  prev: SidebarMode,
  next: SidebarMode
): TransitionDirection {
  if (prev.mode === next.mode) {
    // Same mode — no transition (or lateral move within same level)
    return null;
  }
  const prevDepth = MODE_DEPTH[prev.mode];
  const nextDepth = MODE_DEPTH[next.mode];
  return nextDepth > prevDepth ? 'forward' : 'back';
}

export interface UseNavigationStateReturn {
  // --- New primary API ---

  /** Current sidebar mode — the source of truth for which sidebar content to show */
  sidebarMode: SidebarMode;
  /** Direction of last mode transition (for slide animation) */
  transitionDirection: TransitionDirection;

  // --- Common state ---

  isPanelCollapsed: boolean;
  isTransitioning: boolean;
  /** Whether the overlay sidebar is open (used on narrow/mobile screens) */
  isOverlayOpen: boolean;

  // --- Actions ---

  setPanelCollapsed: (collapsed: boolean) => void;
  togglePanel: () => void;
  /** Open the sidebar as a floating overlay (for narrow/mobile screens) */
  openOverlay: () => void;
  /** Close the overlay sidebar */
  closeOverlay: () => void;

  // --- Derived ---

  activeCaseId: string | null;
  activeProjectId: string | null;
  activeThreadId: string | null;
  /** Which project sub-page is active: 'home' | 'explore' | 'sources' | 'cases' | 'chat' | null */
  activeProjectSubPage: string | null;

  // --- Navigation helpers ---

  navigateToConversation: (threadId: string) => void;
  navigateToCase: (caseId: string) => void;
  navigateToProject: (projectId: string) => void;
  navigateToHome: () => void;
  navigateToSearch: () => void;

  // --- Override ---

  /** Override sidebar mode with data-driven value (e.g., thread → project) */
  setSidebarModeOverride: (mode: SidebarMode | null) => void;
}

export function useNavigationState(): UseNavigationStateReturn {
  const pathname = usePathname();
  const router = useRouter();

  // Derive sidebar mode from URL
  const urlSidebarMode = deriveSidebarMode(pathname);

  // Data-driven override (e.g., thread belongs to a project → show project sidebar)
  const [sidebarModeOverride, setSidebarModeOverride] = useState<SidebarMode | null>(null);

  // Clear override when URL-derived mode changes (user navigated to a different route)
  useEffect(() => {
    setSidebarModeOverride(null);
  }, [urlSidebarMode.mode]);

  // Effective sidebar mode: override takes precedence over URL-derived
  const sidebarMode = sidebarModeOverride ?? urlSidebarMode;

  // Track previous mode for transition direction
  const prevModeRef = useRef<SidebarMode>(sidebarMode);
  const [transitionDirection, setTransitionDirection] = useState<TransitionDirection>(null);

  // Transition state
  const [isTransitioning, setIsTransitioning] = useState(false);

  // Detect mode changes and compute transition direction
  useEffect(() => {
    const prev = prevModeRef.current;
    const next = sidebarMode;

    if (prev.mode !== next.mode) {
      const dir = computeTransitionDirection(prev, next);
      setTransitionDirection(dir);
      setIsTransitioning(true);
      const timer = setTimeout(() => setIsTransitioning(false), 200);
      prevModeRef.current = next;
      return () => clearTimeout(timer);
    }

    // Same mode but different ID (e.g., switching cases) — update ref without animating
    prevModeRef.current = next;
  }, [sidebarMode]);

  // Panel collapse state (persisted)
  const [isPanelCollapsed, setIsPanelCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem(STORAGE_KEY) === 'true';
  });

  // Overlay sidebar state (for narrow/mobile screens)
  const [isOverlayOpen, setIsOverlayOpen] = useState(false);

  // Persist panel collapse state
  const setPanelCollapsed = useCallback((collapsed: boolean) => {
    setIsPanelCollapsed(collapsed);
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, String(collapsed));
    }
  }, []);

  const togglePanel = useCallback(() => {
    setPanelCollapsed(!isPanelCollapsed);
  }, [isPanelCollapsed, setPanelCollapsed]);

  const openOverlay = useCallback(() => {
    setIsOverlayOpen(true);
  }, []);

  const closeOverlay = useCallback(() => {
    setIsOverlayOpen(false);
  }, []);

  // Close overlay on route change
  useEffect(() => {
    setIsOverlayOpen(false);
  }, [pathname]);

  // --- Derived values ---

  const activeCaseId = useMemo(() => {
    return sidebarMode.mode === 'case' ? sidebarMode.caseId : null;
  }, [sidebarMode]);

  const activeProjectId = useMemo(() => {
    if (sidebarMode.mode === 'project') return sidebarMode.projectId;
    if (sidebarMode.mode === 'case') return sidebarMode.projectId ?? null;
    return null;
  }, [sidebarMode]);

  const activeThreadId = useMemo(() => {
    const match = pathname.match(CHAT_THREAD_RE);
    return match ? match[1] : null;
  }, [pathname]);

  /** Which project sub-page is active (home, explore, sources, cases, chat). */
  const activeProjectSubPage = useMemo(() => {
    if (sidebarMode.mode !== 'project') return null;
    // Extract sub-path after /projects/[id]/
    const match = pathname.match(/^\/projects\/[^/]+\/([^/]+)/);
    return match ? match[1] : 'home';
  }, [pathname, sidebarMode]);

  // --- Navigation helpers ---

  const navigateToConversation = useCallback(
    (threadId: string) => {
      router.push(`/chat/${threadId}`);
    },
    [router]
  );

  const navigateToCase = useCallback(
    (caseId: string) => {
      router.push(`/cases/${caseId}`);
    },
    [router]
  );

  const navigateToProject = useCallback(
    (projectId: string) => {
      router.push(`/projects/${projectId}`);
    },
    [router]
  );

  const navigateToHome = useCallback(() => {
    router.push('/');
  }, [router]);

  const navigateToSearch = useCallback(() => {
    // Open the command palette via custom event (not a synthetic keyboard event)
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('episteme:open-command-palette'));
    }
  }, []);

  return {
    sidebarMode,
    transitionDirection,

    isPanelCollapsed,
    isTransitioning,
    isOverlayOpen,

    setPanelCollapsed,
    togglePanel,
    openOverlay,
    closeOverlay,

    activeCaseId,
    activeProjectId,
    activeThreadId,
    activeProjectSubPage,

    navigateToConversation,
    navigateToCase,
    navigateToProject,
    navigateToHome,
    navigateToSearch,

    setSidebarModeOverride,
  };
}
