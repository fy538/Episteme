/**
 * ConceptMapView — Renders nodes and their connections.
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { theme } from '@/lib/theme/companionTheme';
import type { ConceptMapContent, StructureViewProps } from './types';

export const ConceptMapView = memo(function ConceptMapView({
  content,
}: StructureViewProps<ConceptMapContent>) {
  const nodes = content.nodes ?? [];
  const connections = content.connections ?? [];

  return (
    <div className="space-y-1.5">
      {content.title && (
        <p className={cn('text-xs font-medium', theme.thinking.text)}>{content.title}</p>
      )}
      {nodes.map((node, i) => (
        <div key={i} className="flex items-start gap-1.5">
          <span className="text-blue-400 text-xs">{'\u25c6'}</span>
          <div>
            <span className={cn('text-xs font-medium', theme.thinking.text)}>{node.label}</span>
            {node.description && (
              <p className={cn('text-[10px]', theme.thinking.textMuted)}>{node.description}</p>
            )}
          </div>
        </div>
      ))}
      {connections.length > 0 && (
        <div className="pt-1 space-y-0.5">
          {connections.map((conn, i) => (
            <p key={i} className={cn('text-[10px]', theme.thinking.textMuted)}>
              {conn.from} {'\u2192'} {conn.to}: {conn.relation}
            </p>
          ))}
        </div>
      )}
    </div>
  );
});
