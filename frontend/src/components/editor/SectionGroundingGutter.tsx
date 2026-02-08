/**
 * SectionGroundingGutter — Left-margin gutter for the brief editor.
 *
 * Renders colored grounding dots aligned with section marker anchors in the
 * editor DOM. Clicking a dot sets the active section, driving the context
 * panel in the left sidebar.
 */

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { cn } from '@/lib/utils';
import { GROUNDING_CONFIG } from '@/lib/constants/grounding';
import type { BriefSection } from '@/lib/types/case';

interface SectionPosition {
  sectionId: string;
  top: number;
}

interface SectionGroundingGutterProps {
  sections: BriefSection[];
  activeSectionId: string | null;
  editorContainerRef: React.RefObject<HTMLDivElement | null>;
  onSectionClick: (sectionId: string) => void;
  className?: string;
}

export function SectionGroundingGutter({
  sections,
  activeSectionId,
  editorContainerRef,
  onSectionClick,
  className,
}: SectionGroundingGutterProps) {
  const [positions, setPositions] = useState<SectionPosition[]>([]);
  const gutterRef = useRef<HTMLDivElement>(null);

  // Build a map from section_id (marker ID) to BriefSection
  const sectionMap = useRef(new Map<string, BriefSection>());
  useEffect(() => {
    const map = new Map<string, BriefSection>();
    const collect = (sects: BriefSection[]) => {
      for (const s of sects) {
        map.set(s.section_id, s);
        if (s.subsections?.length) collect(s.subsections);
      }
    };
    collect(sections);
    sectionMap.current = map;
  }, [sections]);

  // Measure positions of section marker elements in the editor
  const measurePositions = useCallback(() => {
    const container = editorContainerRef.current;
    if (!container) return;

    const markers = container.querySelectorAll<HTMLElement>('[data-section-id]');
    const containerRect = container.getBoundingClientRect();
    const scrollTop = container.scrollTop;

    const measured: SectionPosition[] = [];
    markers.forEach((el) => {
      const sectionId = el.getAttribute('data-section-id');
      if (!sectionId) return;

      const rect = el.getBoundingClientRect();
      // Position relative to the scrollable container
      const top = rect.top - containerRect.top + scrollTop;
      measured.push({ sectionId, top });
    });

    setPositions(measured);
  }, [editorContainerRef]);

  // Re-measure on mount, sections change, and scroll
  useEffect(() => {
    measurePositions();

    const container = editorContainerRef.current;
    if (!container) return;

    // Re-measure on scroll
    container.addEventListener('scroll', measurePositions, { passive: true });

    // Re-measure on resize
    const observer = new ResizeObserver(measurePositions);
    observer.observe(container);

    return () => {
      container.removeEventListener('scroll', measurePositions);
      observer.disconnect();
    };
  }, [measurePositions, editorContainerRef]);

  // Also re-measure when sections data changes (grounding may have updated)
  useEffect(() => {
    // Small delay to let DOM update after section markers render
    const timer = setTimeout(measurePositions, 100);
    return () => clearTimeout(timer);
  }, [sections, measurePositions]);

  if (positions.length === 0) return null;

  return (
    <div
      ref={gutterRef}
      className={cn('relative w-10 flex-shrink-0', className)}
      aria-label="Section grounding indicators"
    >
      {positions.map(({ sectionId, top }) => {
        const section = sectionMap.current.get(sectionId);
        if (!section) return null;

        const config = GROUNDING_CONFIG[section.grounding_status];
        const isActive = activeSectionId === sectionId;
        const annotationCount = section.annotations.length;
        const hasBlocking = section.annotations.some(a => a.priority === 'blocking');

        return (
          <button
            key={sectionId}
            className={cn(
              'absolute left-1/2 -translate-x-1/2 flex items-center gap-0.5',
              'transition-all duration-150',
              isActive && 'scale-125',
            )}
            style={{ top: `${top + 8}px` }} // +8px to align with heading text
            onClick={() => onSectionClick(sectionId)}
            title={`${section.heading}: ${config.label}`}
          >
            {/* Grounding dot */}
            <div
              className={cn(
                'w-2.5 h-2.5 rounded-full transition-colors',
                config.dotBg,
                isActive && 'ring-2 ring-offset-1 ring-accent-400 dark:ring-accent-500',
              )}
            />

            {/* Annotation count badge */}
            {annotationCount > 0 && (
              <span
                className={cn(
                  'text-[9px] font-bold leading-none min-w-[14px] h-[14px] flex items-center justify-center rounded-full',
                  hasBlocking
                    ? 'bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400'
                    : 'bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400',
                )}
              >
                {annotationCount}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
