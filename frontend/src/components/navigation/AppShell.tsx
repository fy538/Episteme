/**
 * AppShell
 *
 * Unified layout wrapper for all authenticated app routes.
 * Provides the sidebar panel (with integrated tabs) and main content area.
 *
 * Layout (desktop ≥1024px):
 *   [SidebarPanel 240px] [Main Content flex-1]
 *
 * Responsive behavior:
 *   < lg (1024px): Panel auto-collapses, floating toggle appears to open overlay
 *   < md (768px):  Same overlay pattern, no separate treatment needed
 *
 * Overlay pattern: On narrow screens, a floating button in the top-left opens
 * the sidebar as an overlay drawer (slides over content with scrim backdrop).
 * Clicking the backdrop or navigating closes it. Inspired by Linear/Notion.
 */

'use client';

import { type ReactNode, useEffect, useState } from 'react';
import { SidebarPanel } from './SidebarPanel';
import { useNavigation } from './NavigationProvider';
import { useGlobalKeyboardShortcuts } from '@/hooks/useGlobalKeyboard';
import { cn } from '@/lib/utils';

interface AppShellProps {
  children: ReactNode;
  className?: string;
}

/** Hook to track a media query */
function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const mql = window.matchMedia(query);
    setMatches(mql.matches);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, [query]);

  return matches;
}

export function AppShell({ children, className }: AppShellProps) {
  const nav = useNavigation();
  const isSmallScreen = useMediaQuery('(max-width: 1023px)');

  // Activate global keyboard shortcuts (Cmd+B for panel toggle)
  // On narrow screens, Cmd+B toggles the overlay drawer instead of the inline panel
  useGlobalKeyboardShortcuts({
    onTogglePanel: isSmallScreen
      ? () => (nav.isOverlayOpen ? nav.closeOverlay() : nav.openOverlay())
      : nav.togglePanel,
  });

  // Auto-collapse panel on small screens (don't persist — it's viewport-driven)
  useEffect(() => {
    if (isSmallScreen && !nav.isPanelCollapsed) {
      nav.setPanelCollapsed(true);
    }
  }, [isSmallScreen]); // eslint-disable-line react-hooks/exhaustive-deps

  // Close overlay when screen becomes large again
  useEffect(() => {
    if (!isSmallScreen && nav.isOverlayOpen) {
      nav.closeOverlay();
    }
  }, [isSmallScreen]); // eslint-disable-line react-hooks/exhaustive-deps

  // Close overlay on Escape key
  useEffect(() => {
    if (!nav.isOverlayOpen) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        nav.closeOverlay();
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [nav.isOverlayOpen, nav.closeOverlay]);

  // Whether to show the floating sidebar toggle:
  // - On narrow screens (<1024px): panel is auto-collapsed, show toggle to open overlay
  // - On desktop (≥1024px): show toggle when user has manually collapsed the panel via ⌘B
  const isPanelHidden = isSmallScreen || nav.isPanelCollapsed;
  const showFloatingToggle = isPanelHidden && !nav.isOverlayOpen;

  return (
    <div className={cn('flex h-screen bg-white dark:bg-neutral-950', className)}>
      {/* Desktop panel (only on large screens) */}
      {!isSmallScreen && (
        <SidebarPanel
          isCollapsed={nav.isPanelCollapsed}
          onToggleCollapse={nav.togglePanel}
        />
      )}

      {/* ─── Overlay drawer (narrow/mobile screens) ─── */}
      {isSmallScreen && (
        <>
          {/* Scrim backdrop */}
          <div
            className={cn(
              'fixed inset-0 z-40 bg-black/20 backdrop-blur-[2px] transition-opacity duration-200',
              nav.isOverlayOpen
                ? 'opacity-100 pointer-events-auto'
                : 'opacity-0 pointer-events-none'
            )}
            onClick={nav.closeOverlay}
            aria-hidden="true"
          />

          {/* Sliding drawer — just the sidebar panel (no separate rail) */}
          <div
            className={cn(
              'fixed top-0 left-0 z-50 h-full',
              'transition-transform duration-200 ease-[cubic-bezier(0.32,0.72,0,1)]',
              nav.isOverlayOpen
                ? 'translate-x-0'
                : '-translate-x-full'
            )}
          >
            {/* Panel inside overlay */}
            <SidebarPanel
              isCollapsed={false}
              onToggleCollapse={() => nav.closeOverlay()}
            />

            {/* Close button at the drawer edge */}
            <button
              onClick={nav.closeOverlay}
              className="absolute top-3 right-[-36px] w-7 h-7 rounded-full bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 shadow-md flex items-center justify-center text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200 transition-all opacity-0 data-[open=true]:opacity-100 delay-100"
              data-open={nav.isOverlayOpen}
              aria-label="Close sidebar"
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        </>
      )}

      {/* ─── Main content area ─── */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        {/* Floating toggle button — appears when sidebar is hidden */}
        {showFloatingToggle && (
          <button
            onClick={isSmallScreen ? nav.openOverlay : nav.togglePanel}
            className={cn(
              'absolute top-3 left-3 z-30',
              'w-8 h-8 rounded-lg',
              'bg-white dark:bg-neutral-900',
              'border border-neutral-200 dark:border-neutral-700',
              'shadow-sm hover:shadow-md',
              'flex items-center justify-center',
              'text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200',
              'transition-all duration-200',
              // Subtle entrance animation
              'animate-in fade-in slide-in-from-left-2 duration-200'
            )}
            aria-label="Open sidebar"
            title="Open sidebar (⌘B)"
          >
            <SidebarToggleIcon className="w-4 h-4" />
          </button>
        )}

        {children}
      </main>
    </div>
  );
}

// ─── Icons ──────────────────────────────────────────────────

/** Hamburger-to-sidebar icon — three horizontal lines */
function SidebarToggleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 7h18M3 12h18M3 17h18" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
