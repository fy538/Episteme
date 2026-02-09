/**
 * useNavigationState Hook
 *
 * Core navigation state for the sidebar architecture.
 *
 * The sidebar has two tabs (Decisions / Threads). The active tab is:
 *   1. Auto-derived from the URL pathname (e.g. /chat → threads, /cases → decisions)
 *   2. Manually overridable by the user clicking a tab
 *   3. Override resets on the next URL navigation
 *
 * Panel collapse state is persisted in localStorage.
 */

'use client';

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import type { SidebarTab, RailSection, PanelMode } from '@/lib/types/navigation';

const STORAGE_KEY = 'episteme_nav_panel_collapsed';
const TAB_STORAGE_KEY = 'episteme_nav_default_tab';

/** Regex patterns for extracting route params from pathname */
const CHAT_THREAD_RE = /^\/chat\/([^/]+)/;
const CASE_ID_RE = /^\/cases\/([^/]+)/;
const PROJECT_ID_RE = /^\/projects\/([^/]+)/;

/** Derive the sidebar tab from the current pathname */
function deriveTab(pathname: string): SidebarTab {
  if (pathname.startsWith('/chat')) return 'threads';
  // Home, cases, inquiries, projects all map to decisions
  if (pathname === '/') return 'decisions';
  if (pathname.startsWith('/cases')) return 'decisions';
  if (pathname.startsWith('/inquiries')) return 'decisions';
  if (pathname.startsWith('/projects')) return 'decisions';
  return 'decisions'; // default
}

/** Map SidebarTab to the legacy RailSection for backwards compat */
function tabToRailSection(tab: SidebarTab): RailSection {
  return tab === 'threads' ? 'conversations' : 'cases';
}

/** Derive the panel mode from the pathname */
function derivePanelMode(pathname: string): PanelMode {
  // Home shows decisions panel
  if (pathname === '/') return { section: 'cases' };

  if (pathname.startsWith('/chat')) {
    const match = pathname.match(CHAT_THREAD_RE);
    return match
      ? { section: 'conversations', activeThreadId: match[1] }
      : { section: 'conversations' };
  }

  if (pathname.startsWith('/cases')) {
    const match = pathname.match(CASE_ID_RE);
    return match
      ? { section: 'cases', activeCaseId: match[1] }
      : { section: 'cases' };
  }

  if (pathname.startsWith('/inquiries')) {
    return { section: 'cases' };
  }

  if (pathname.startsWith('/projects')) {
    const match = pathname.match(PROJECT_ID_RE);
    return match
      ? { section: 'cases', activeProjectId: match[1] }
      : { section: 'cases' };
  }

  return { section: 'conversations' };
}

export interface UseNavigationStateReturn {
  // State
  /** Active sidebar tab — the source of truth for which panel content to show */
  activeTab: SidebarTab;
  /** @deprecated Use activeTab. Derived for backwards compatibility. */
  railSection: RailSection;
  panelMode: PanelMode;
  isPanelCollapsed: boolean;
  isTransitioning: boolean;
  /** Whether the overlay sidebar is open (used on narrow/mobile screens) */
  isOverlayOpen: boolean;

  // Actions
  /** Manually switch the sidebar tab (overrides URL-derived tab until next navigation) */
  setActiveTab: (tab: SidebarTab) => void;
  setPanelCollapsed: (collapsed: boolean) => void;
  togglePanel: () => void;
  /** Open the sidebar as a floating overlay (for narrow/mobile screens) */
  openOverlay: () => void;
  /** Close the overlay sidebar */
  closeOverlay: () => void;

  // Derived
  activeCaseId: string | null;
  activeThreadId: string | null;

  // Navigation helpers
  navigateToConversation: (threadId: string) => void;
  navigateToCase: (caseId: string) => void;
  navigateToHome: () => void;
  navigateToSearch: () => void;
}

export function useNavigationState(): UseNavigationStateReturn {
  const pathname = usePathname();
  const router = useRouter();

  // Derive tab and panel mode from URL
  const urlDerivedTab = deriveTab(pathname);
  const panelMode = derivePanelMode(pathname);

  // Active tab state: URL-derived by default, manually overridable
  const [tabOverride, setTabOverride] = useState<SidebarTab | null>(null);
  const prevPathnameRef = useRef(pathname);

  // Reset tab override on pathname change (URL navigation takes precedence)
  useEffect(() => {
    if (prevPathnameRef.current !== pathname) {
      setTabOverride(null);
      prevPathnameRef.current = pathname;
    }
  }, [pathname]);

  // Effective active tab: override > URL-derived
  const activeTab = tabOverride ?? urlDerivedTab;

  // Legacy railSection derived from activeTab
  const railSection = tabToRailSection(activeTab);

  // Manual tab switch (sets override, doesn't navigate)
  const setActiveTab = useCallback((tab: SidebarTab) => {
    setTabOverride(tab);
    // Persist preference for ambiguous routes (like home)
    if (typeof window !== 'undefined') {
      localStorage.setItem(TAB_STORAGE_KEY, tab);
    }
  }, []);

  // Panel collapse state (persisted)
  const [isPanelCollapsed, setIsPanelCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem(STORAGE_KEY) === 'true';
  });

  // Overlay sidebar state (for narrow/mobile screens)
  const [isOverlayOpen, setIsOverlayOpen] = useState(false);

  // Transition state
  const [isTransitioning, setIsTransitioning] = useState(false);
  const prevTabRef = useRef<SidebarTab>(activeTab);

  // Detect tab changes and trigger transition animation
  useEffect(() => {
    if (prevTabRef.current !== activeTab) {
      setIsTransitioning(true);
      const timer = setTimeout(() => setIsTransitioning(false), 200);
      prevTabRef.current = activeTab;
      return () => clearTimeout(timer);
    }
  }, [activeTab]);

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

  // Derived values
  const activeCaseId = useMemo(() => {
    if (panelMode.section === 'cases' && 'activeCaseId' in panelMode) {
      return panelMode.activeCaseId ?? null;
    }
    return null;
  }, [panelMode]);

  const activeThreadId = useMemo(() => {
    if (panelMode.section === 'conversations' && 'activeThreadId' in panelMode) {
      return panelMode.activeThreadId ?? null;
    }
    return null;
  }, [panelMode]);

  // Navigation helpers
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
    activeTab,
    railSection,
    panelMode,
    isPanelCollapsed,
    isTransitioning,
    isOverlayOpen,
    setActiveTab,
    setPanelCollapsed,
    togglePanel,
    openOverlay,
    closeOverlay,
    activeCaseId,
    activeThreadId,
    navigateToConversation,
    navigateToCase,
    navigateToHome,
    navigateToSearch,
  };
}
