/**
 * useNavigationState Hook
 *
 * Core navigation state for the two-tier sidebar architecture.
 * The rail section is derived from the current URL pathname (router is source of truth).
 * Panel collapse state is persisted in localStorage.
 */

'use client';

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import type { RailSection, PanelMode } from '@/lib/types/navigation';

const STORAGE_KEY = 'episteme_nav_panel_collapsed';

/** Regex patterns for extracting route params from pathname */
const CHAT_THREAD_RE = /^\/chat\/([^/]+)/;
const CASE_ID_RE = /^\/cases\/([^/]+)/;
const PROJECT_ID_RE = /^\/projects\/([^/]+)/;

/** Derive the active rail section from the current pathname */
function deriveRailSection(pathname: string): RailSection {
  // Home and chat routes all map to conversations
  if (pathname === '/') return 'conversations';
  if (pathname.startsWith('/chat')) return 'conversations';
  // Cases, inquiries, projects all map to cases
  if (pathname.startsWith('/cases')) return 'cases';
  if (pathname.startsWith('/inquiries')) return 'cases';
  if (pathname.startsWith('/projects')) return 'cases';
  return 'conversations'; // default to conversations
}

/** Derive the panel mode from the pathname */
function derivePanelMode(pathname: string): PanelMode {
  // Home and /chat both show conversations panel
  if (pathname === '/') return { section: 'conversations' };

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
  railSection: RailSection;
  panelMode: PanelMode;
  isPanelCollapsed: boolean;
  isTransitioning: boolean;
  /** Whether the overlay sidebar is open (used on narrow/mobile screens) */
  isOverlayOpen: boolean;

  // Actions
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

  // Derive rail section and panel mode from URL
  const railSection = deriveRailSection(pathname);
  const panelMode = derivePanelMode(pathname);

  // Panel collapse state (persisted)
  const [isPanelCollapsed, setIsPanelCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem(STORAGE_KEY) === 'true';
  });

  // Overlay sidebar state (for narrow/mobile screens)
  const [isOverlayOpen, setIsOverlayOpen] = useState(false);

  // Transition state
  const [isTransitioning, setIsTransitioning] = useState(false);
  const prevRailRef = useRef<RailSection>(railSection);

  // Detect rail section changes and trigger transition animation
  useEffect(() => {
    if (prevRailRef.current !== railSection) {
      setIsTransitioning(true);
      const timer = setTimeout(() => setIsTransitioning(false), 200);
      prevRailRef.current = railSection;
      return () => clearTimeout(timer);
    }
  }, [railSection]);

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
    railSection,
    panelMode,
    isPanelCollapsed,
    isTransitioning,
    isOverlayOpen,
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
