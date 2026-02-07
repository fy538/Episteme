/**
 * FloatingThinking - Auto-appearing reflection panel for canvas view
 *
 * Shows AI thinking/reflection content as a small floating panel in the
 * top-left of the canvas. Auto-appears when reflection is streaming,
 * auto-fades 5s after streaming stops.
 *
 * Positioned top-left to avoid overlap with chat/copilot panels (top-right).
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';

interface FloatingThinkingProps {
  content: string;
  isStreaming: boolean;
  /** Auto-hide delay in ms after streaming stops (default: 5000) */
  autoHideDelay?: number;
}

export function FloatingThinking({
  content,
  isStreaming,
  autoHideDelay = 5000,
}: FloatingThinkingProps) {
  const [visible, setVisible] = useState(false);
  const [fading, setFading] = useState(false);
  const fadeTimerRef = useRef<NodeJS.Timeout | null>(null);
  const hasContent = content.trim().length > 0;

  // Show when streaming starts or content appears
  useEffect(() => {
    if (isStreaming || hasContent) {
      setVisible(true);
      setFading(false);
      // Clear any pending fade timer
      if (fadeTimerRef.current) {
        clearTimeout(fadeTimerRef.current);
        fadeTimerRef.current = null;
      }
    }
  }, [isStreaming, hasContent]);

  // Auto-fade after streaming stops
  useEffect(() => {
    if (!isStreaming && hasContent && visible) {
      fadeTimerRef.current = setTimeout(() => {
        setFading(true);
        // After fade animation, hide entirely
        setTimeout(() => {
          setVisible(false);
          setFading(false);
        }, 500);
      }, autoHideDelay);
    }

    return () => {
      if (fadeTimerRef.current) {
        clearTimeout(fadeTimerRef.current);
        fadeTimerRef.current = null;
      }
    };
  }, [isStreaming, hasContent, visible, autoHideDelay]);

  if (!visible || !hasContent) return null;

  // Show only first paragraph as preview
  const paragraphs = content.split('\n\n').filter(p => p.trim());
  const preview = paragraphs[0]?.substring(0, 200) || '';
  const hasMore = paragraphs.length > 1 || (paragraphs[0]?.length || 0) > 200;

  return (
    <div
      className={cn(
        'absolute top-4 left-4 z-40 w-72 transition-all duration-500',
        fading ? 'opacity-0 translate-y-[-8px]' : 'opacity-100 translate-y-0'
      )}
    >
      <div className="bg-white/95 backdrop-blur-sm rounded-lg shadow-lg border border-neutral-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-2 px-3 py-1.5 bg-neutral-50 border-b border-neutral-200">
          <div className="flex items-center gap-1.5">
            <span className="text-amber-500 text-xs">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                />
              </svg>
            </span>
            <span className="text-[10px] font-medium text-neutral-500 uppercase tracking-wider">
              Thinking
            </span>
          </div>
          {isStreaming && (
            <span className="animate-pulse text-amber-500 text-xs ml-auto">
              <svg className="w-3 h-3" viewBox="0 0 8 8">
                <circle cx="4" cy="4" r="3" fill="currentColor" />
              </svg>
            </span>
          )}
          {!isStreaming && (
            <button
              onClick={() => {
                setFading(true);
                setTimeout(() => {
                  setVisible(false);
                  setFading(false);
                }, 300);
              }}
              className="ml-auto text-neutral-400 hover:text-neutral-600 transition-colors"
              aria-label="Dismiss thinking"
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Content */}
        <div className="px-3 py-2 max-h-32 overflow-y-auto">
          <p className="text-xs text-neutral-600 leading-relaxed">
            {preview}
            {hasMore && <span className="text-neutral-400">...</span>}
            {isStreaming && (
              <span className="inline-block w-1.5 h-3 bg-amber-400 animate-pulse ml-0.5 align-text-bottom" />
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
