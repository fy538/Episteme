/**
 * ConversationStructureSection — Renders the organic companion structure.
 *
 * Displays the flexible conversation structure (decision tree, checklist,
 * comparison, etc.) with established facts, open questions, and eliminated
 * options as contextual tracking.
 *
 * View components are split into structure-views/ for maintainability.
 */

'use client';

import { useId, useState } from 'react';
import { cn } from '@/lib/utils';
import { theme, isTerminalTheme } from '@/lib/theme/companionTheme';
import { StateBar, StructureContent, TrackingLists } from './structure-views';
import type { ConversationStructure, StructureType } from '@/lib/types/companion';

interface ConversationStructureSectionProps {
  structure: ConversationStructure;
  collapsed?: boolean;
  /** Show a subtle updating indicator (e.g. while the assistant is responding) */
  isUpdating?: boolean;
}

const STRUCTURE_LABELS: Record<StructureType, string> = {
  assumption_surface: 'Assumptions',
  angle_map: 'Angles',
  decision_tree: 'Decision Tree',
  checklist: 'Checklist',
  comparison: 'Comparison',
  exploration_map: 'Exploration Map',
  flow: 'Flow',
  constraint_list: 'Constraints',
  pros_cons: 'Pros & Cons',
  concept_map: 'Concept Map',
};

const STRUCTURE_ICONS: Record<StructureType, string> = {
  assumption_surface: '\u25c7',
  angle_map: '\u2736',
  decision_tree: '\u2442',
  checklist: '\u2611',
  comparison: '\u2261',
  exploration_map: '\u2299',
  flow: '\u2192',
  constraint_list: '\u2234',
  pros_cons: '\u00b1',
  concept_map: '\u2b21',
};

export function ConversationStructureSection({
  structure,
  collapsed = false,
  isUpdating = false,
}: ConversationStructureSectionProps) {
  const [isExpanded, setIsExpanded] = useState(!collapsed);
  const contentId = useId();

  const icon = STRUCTURE_ICONS[structure.structure_type] || '\u2022';
  const label = STRUCTURE_LABELS[structure.structure_type] || structure.structure_type;

  return (
    <section
      className={cn('border-b', theme.thinking.border)}
      role="region"
      aria-label="Conversation structure"
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
        aria-controls={contentId}
        className={cn(
          'w-full px-3 py-2 flex items-center gap-2 text-left',
          'hover:bg-white/5 transition-colors',
          isTerminalTheme && 'font-mono'
        )}
      >
        <span className={cn('text-xs', theme.thinking.text)} aria-hidden="true">
          {icon}
        </span>
        <span className={cn('text-xs tracking-wider font-medium uppercase flex-1', theme.thinking.text)}>
          {label}
        </span>
        {isUpdating && (
          <span
            className={cn('text-[10px] animate-pulse', theme.thinking.textMuted)}
            aria-label="Structure is updating"
          >
            updating...
          </span>
        )}
        <span className={cn('text-xs tabular-nums', theme.thinking.textMuted)}>
          v{structure.version}
        </span>
        <span className={cn('text-xs', theme.thinking.textMuted)} aria-hidden="true">
          {isExpanded ? '\u25b4' : '\u25be'}
        </span>
      </button>

      {isExpanded && (
        <div id={contentId} className="px-3 pb-3 space-y-3">
          {/* State Bar — quick overview */}
          <StateBar structure={structure} />

          {/* Structure Content */}
          <StructureContent
            type={structure.structure_type}
            content={structure.content}
          />

          {/* Tracking Lists */}
          <TrackingLists
            established={structure.established}
            openQuestions={structure.open_questions}
            eliminated={structure.eliminated}
          />
        </div>
      )}
    </section>
  );
}
