/**
 * ExplorationMapView — Renders a map of exploration areas with status.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { theme } from '@/lib/theme/companionTheme';
import type { ExplorationStatus, ExplorationMapContent, StructureViewProps } from './types';

const STATUS_COLORS: Record<ExplorationStatus, string> = {
  explored: 'border-emerald-500/30',
  partially_explored: 'border-amber-500/30',
  unexplored: 'border-zinc-700/30',
};

export const ExplorationMapView = memo(function ExplorationMapView({
  content,
}: StructureViewProps<ExplorationMapContent>) {
  const areas = content.areas ?? [];

  return (
    <div className="space-y-1.5">
      {content.center && (
        <p className={cn('text-xs font-medium', theme.thinking.text)}>{content.center}</p>
      )}
      {areas.map((area, i) => (
        <div
          key={i}
          className={cn(
            'pl-2 border-l-2 py-0.5',
            area.status ? (STATUS_COLORS[area.status] ?? 'border-zinc-700/30') : 'border-zinc-700/30',
          )}
        >
          <div className={cn('text-xs font-medium', theme.thinking.text)}>{area.label}</div>
          {area.summary && (
            <p className={cn('text-[10px]', theme.thinking.textMuted)}>{area.summary}</p>
          )}
        </div>
      ))}
    </div>
  );
});
