/**
 * Floating action menu - appears near text selection
 * Enables inline inquiry creation, assumption marking, and grounding-aware actions
 */

'use client';

import { useEffect, useState } from 'react';
import type { GroundingStatus, BriefAnnotation } from '@/lib/types/case';

export interface SectionContext {
  sectionId: string;
  groundingStatus: GroundingStatus;
  annotations: BriefAnnotation[];
}

interface FloatingActionMenuProps {
  visible: boolean;
  x: number;
  y: number;
  onCreateInquiry: () => void;
  onMarkAssumption: () => void;
  onFindEvidence?: () => void;
  onResolveTension?: (annotationId: string) => void;
  onClose: () => void;
  sectionContext?: SectionContext | null;
}

export function FloatingActionMenu({
  visible,
  x,
  y,
  onCreateInquiry,
  onMarkAssumption,
  onFindEvidence,
  onResolveTension,
  onClose,
  sectionContext,
}: FloatingActionMenuProps) {
  const [position, setPosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    // Adjust position to stay within viewport
    const menuWidth = 200;
    const menuHeight = 160;
    const padding = 10;

    let adjustedX = x;
    let adjustedY = y - menuHeight - padding; // Above selection by default

    // Keep within horizontal bounds
    if (adjustedX + menuWidth > window.innerWidth) {
      adjustedX = window.innerWidth - menuWidth - padding;
    }
    if (adjustedX < padding) {
      adjustedX = padding;
    }

    // Keep within vertical bounds
    if (adjustedY < padding) {
      adjustedY = y + padding; // Below selection if can't fit above
    }

    setPosition({ x: adjustedX, y: adjustedY });
  }, [x, y]);

  useEffect(() => {
    if (!visible) return;

    function handleClickOutside(e: MouseEvent) {
      const target = e.target as HTMLElement;
      if (!target.closest('[data-floating-menu]')) {
        onClose();
      }
    }

    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        onClose();
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [visible, onClose]);

  if (!visible) return null;

  // Determine grounding-aware actions based on section context
  const isUngrounded = sectionContext && (
    sectionContext.groundingStatus === 'empty' || sectionContext.groundingStatus === 'weak'
  );
  const tensions = sectionContext?.annotations.filter(a => a.annotation_type === 'tension') ?? [];
  const hasTensions = tensions.length > 0;

  return (
    <div
      data-floating-menu
      className="fixed z-50 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-lg py-1 min-w-[180px]"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
      }}
    >
      <button
        onClick={() => {
          onCreateInquiry();
          onClose();
        }}
        className="w-full px-4 py-2 text-left text-sm hover:bg-accent-50 dark:hover:bg-accent-900/20 transition-colors flex items-center gap-2"
      >
        <svg className="w-4 h-4 text-accent-600 dark:text-accent-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="font-medium text-neutral-800 dark:text-neutral-200">Create Inquiry</span>
      </button>

      <button
        onClick={() => {
          onMarkAssumption();
          onClose();
        }}
        className="w-full px-4 py-2 text-left text-sm hover:bg-yellow-50 dark:hover:bg-yellow-900/20 transition-colors flex items-center gap-2"
      >
        <svg className="w-4 h-4 text-yellow-600 dark:text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span className="font-medium text-neutral-800 dark:text-neutral-200">Mark as Assumption</span>
      </button>

      {/* Grounding-aware contextual actions */}
      {isUngrounded && onFindEvidence && (
        <>
          <div className="border-t border-neutral-200 dark:border-neutral-700 my-1" />
          <button
            onClick={() => {
              onFindEvidence();
              onClose();
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-emerald-50 dark:hover:bg-emerald-900/20 transition-colors flex items-center gap-2"
          >
            <svg className="w-4 h-4 text-emerald-600 dark:text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <span className="font-medium text-neutral-800 dark:text-neutral-200">Find Evidence</span>
          </button>
        </>
      )}

      {hasTensions && onResolveTension && (
        <>
          {!isUngrounded && <div className="border-t border-neutral-200 dark:border-neutral-700 my-1" />}
          <button
            onClick={() => {
              onResolveTension(tensions[0].id);
              onClose();
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors flex items-center gap-2"
          >
            <svg className="w-4 h-4 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span className="font-medium text-neutral-800 dark:text-neutral-200">
              Resolve Tension{tensions.length > 1 ? ` (${tensions.length})` : ''}
            </span>
          </button>
        </>
      )}

      <div className="border-t border-neutral-200 dark:border-neutral-700 mt-1 pt-1">
        <div className="px-4 py-1 text-xs text-neutral-500 dark:text-neutral-400">
          ESC to close
        </div>
      </div>
    </div>
  );
}
