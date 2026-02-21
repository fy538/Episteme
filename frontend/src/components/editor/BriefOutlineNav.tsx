/**
 * BriefOutlineNav — Compact outline sidebar for the unified brief view.
 *
 * Shows section headings with grounding status dots and annotation badges.
 * Supports click-to-scroll, active section highlighting, and drag-to-reorder.
 */

'use client';

import { useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { GROUNDING_CONFIG, SECTION_TYPE_LABELS } from '@/lib/constants/grounding';
import type { BriefSection, SectionType } from '@/lib/types/case';

interface BriefOutlineNavProps {
  sections: BriefSection[];
  activeSectionId: string | null;
  onSectionClick: (sectionId: string) => void;
  onReorderSections?: (order: Array<{ id: string; order: number }>) => void;
  onAddSection?: () => void;
  className?: string;
}

export function BriefOutlineNav({
  sections,
  activeSectionId,
  onSectionClick,
  onReorderSections,
  onAddSection,
  className,
}: BriefOutlineNavProps) {
  // Drag state
  const [dragSourceId, setDragSourceId] = useState<string | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);

  const handleDragStart = useCallback((e: React.DragEvent, sectionId: string) => {
    setDragSourceId(sectionId);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', sectionId);
  }, []);

  const handleDragEnd = useCallback(() => {
    setDragSourceId(null);
    setDragOverId(null);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, sectionId: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (sectionId !== dragSourceId) {
      setDragOverId(sectionId);
    }
  }, [dragSourceId]);

  const handleDrop = useCallback((e: React.DragEvent, targetId: string) => {
    e.preventDefault();
    setDragOverId(null);

    if (!dragSourceId || dragSourceId === targetId || !onReorderSections) {
      setDragSourceId(null);
      return;
    }

    const currentOrder = sections.map(s => s.id);
    const sourceIdx = currentOrder.indexOf(dragSourceId);
    const targetIdx = currentOrder.indexOf(targetId);

    if (sourceIdx === -1 || targetIdx === -1) {
      setDragSourceId(null);
      return;
    }

    const newOrder = [...currentOrder];
    newOrder.splice(sourceIdx, 1);
    newOrder.splice(targetIdx, 0, dragSourceId);

    const reorderPayload = newOrder.map((id, idx) => ({ id, order: idx }));
    onReorderSections(reorderPayload);

    setDragSourceId(null);
  }, [dragSourceId, sections, onReorderSections]);

  return (
    <div className={cn('flex flex-col', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500">
          Outline
        </h3>
        {onAddSection && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onAddSection}
            className="h-6 w-6 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
            title="Add section"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 5v14M5 12h14" strokeLinecap="round" />
            </svg>
          </Button>
        )}
      </div>

      {/* Section list */}
      <div className="space-y-0.5 px-1">
        {sections.map((section) => {
          const config = GROUNDING_CONFIG[section.grounding_status];
          const isActive = activeSectionId === section.section_id;
          const annotationCount = section.annotations.length;
          const hasBlocking = section.annotations.some(a => a.priority === 'blocking');
          const isDragging = dragSourceId === section.id;
          const isDragOver = dragOverId === section.id;

          return (
            <button
              key={section.id}
              onClick={() => onSectionClick(section.section_id)}
              draggable={!!onReorderSections}
              onDragStart={(e) => handleDragStart(e, section.id)}
              onDragEnd={handleDragEnd}
              onDragOver={(e) => handleDragOver(e, section.id)}
              onDragLeave={() => setDragOverId(null)}
              onDrop={(e) => handleDrop(e, section.id)}
              className={cn(
                'w-full text-left px-2 py-1.5 rounded-md flex items-center gap-2 transition-all text-xs group',
                isActive
                  ? 'bg-accent-50 dark:bg-accent-900/20 text-accent-700 dark:text-accent-300'
                  : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800',
                isDragging && 'opacity-40',
                isDragOver && 'ring-1 ring-accent-400',
                section.is_locked && 'opacity-50',
              )}
            >
              {/* Grounding dot */}
              <div
                className={cn('w-2 h-2 rounded-full flex-shrink-0', config.dotBg)}
                title={config.label}
              />

              {/* Heading */}
              <span className="truncate flex-1 min-w-0 leading-tight">
                {section.heading}
              </span>

              {/* Annotation badge */}
              {annotationCount > 0 && (
                <span
                  className={cn(
                    'text-xs font-bold min-w-[14px] h-[14px] flex items-center justify-center rounded-full flex-shrink-0',
                    hasBlocking
                      ? 'bg-error-100 dark:bg-error-900/40 text-error-600 dark:text-error-400'
                      : 'bg-warning-100 dark:bg-warning-900/40 text-warning-600 dark:text-warning-400',
                  )}
                >
                  {annotationCount}
                </span>
              )}

              {/* Lock icon for locked sections */}
              {section.is_locked && (
                <svg className="w-3 h-3 text-neutral-400 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0110 0v4" />
                </svg>
              )}
            </button>
          );
        })}
      </div>

      {/* Empty state */}
      {sections.length === 0 && (
        <p className="px-3 py-4 text-xs text-neutral-400 dark:text-neutral-500 text-center">
          No sections yet
        </p>
      )}
    </div>
  );
}
