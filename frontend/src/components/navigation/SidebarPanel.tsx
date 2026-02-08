/**
 * SidebarPanel
 *
 * The 240px context-dependent panel that sits between the IconRail and main content.
 * Content swaps based on which rail section is active.
 * Supports collapse/expand with smooth width transition.
 */

'use client';

import { useRef, useEffect, useState } from 'react';
import { ConversationsPanelContent } from './panels/ConversationsPanelContent';
import { CasesPanelContent } from './panels/CasesPanelContent';
import { cn } from '@/lib/utils';
import type { PanelMode } from '@/lib/types/navigation';

/** Duration in ms for the panel content crossfade. Used by both the JS timeout and CSS transition. */
const CROSSFADE_MS = 100;

interface SidebarPanelProps {
  mode: PanelMode;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  className?: string;
}

export function SidebarPanel({ mode, isCollapsed, onToggleCollapse, className }: SidebarPanelProps) {
  // Track previous section for crossfade
  const [displaySection, setDisplaySection] = useState(mode.section);
  const [isCrossfading, setIsCrossfading] = useState(false);
  const prevSection = useRef(mode.section);

  useEffect(() => {
    if (prevSection.current !== mode.section) {
      // Trigger crossfade: fade out, swap, fade in
      setIsCrossfading(true);
      const timer = setTimeout(() => {
        setDisplaySection(mode.section);
        setIsCrossfading(false);
      }, CROSSFADE_MS);
      prevSection.current = mode.section;
      return () => clearTimeout(timer);
    }
  }, [mode.section]);

  return (
    <div
      className={cn(
        'h-full border-r border-neutral-200 dark:border-neutral-800',
        'bg-white dark:bg-neutral-950',
        'transition-[width] duration-200 ease-out overflow-hidden shrink-0',
        isCollapsed ? 'w-0 border-r-0' : 'w-60',
        className
      )}
    >
      <div
        className={cn(
          'w-60 h-full transition-opacity',
          isCollapsed && 'opacity-0',
          isCrossfading && 'opacity-0'
        )}
        style={{ transitionDuration: `${CROSSFADE_MS}ms` }}
      >
        <PanelContent mode={mode} displaySection={displaySection} />
      </div>
    </div>
  );
}

function PanelContent({
  mode,
  displaySection,
}: {
  mode: PanelMode;
  displaySection: string;
}) {
  // Use displaySection for rendering (handles crossfade timing)
  switch (displaySection) {
    case 'conversations':
      return (
        <ConversationsPanelContent
          activeThreadId={mode.section === 'conversations' && 'activeThreadId' in mode ? mode.activeThreadId : undefined}
        />
      );

    case 'cases':
      return (
        <CasesPanelContent
          activeCaseId={mode.section === 'cases' && 'activeCaseId' in mode ? mode.activeCaseId : undefined}
          activeProjectId={mode.section === 'cases' && 'activeProjectId' in mode ? mode.activeProjectId : undefined}
        />
      );

    case 'none':
      return null;

    default:
      return (
        <ConversationsPanelContent
          activeThreadId={mode.section === 'conversations' && 'activeThreadId' in mode ? mode.activeThreadId : undefined}
        />
      );
  }
}
