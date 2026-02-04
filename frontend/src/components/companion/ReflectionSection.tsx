/**
 * ReflectionSection - Displays streaming meta-cognitive reflection
 *
 * Always present, expands when streaming, contracts when idle.
 */

'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';

interface ReflectionSectionProps {
  content: string;
  isStreaming?: boolean;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function ReflectionSection({
  content,
  isStreaming = false,
  collapsed = false,
  onToggleCollapse,
}: ReflectionSectionProps) {
  const [isManuallyCollapsed, setIsManuallyCollapsed] = useState(false);

  const shouldCollapse = collapsed || isManuallyCollapsed;
  const hasContent = content && content.trim().length > 0;

  const handleToggle = () => {
    if (onToggleCollapse) {
      onToggleCollapse();
    } else {
      setIsManuallyCollapsed(!isManuallyCollapsed);
    }
  };

  // Split content into paragraphs
  const paragraphs = content ? content.split('\n\n').filter((p) => p.trim()) : [];
  const previewText = paragraphs[0]?.substring(0, 120) || '';

  return (
    <section className="border-b border-cyan-900/30">
      {/* Terminal Header */}
      <button
        onClick={handleToggle}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-cyan-950/20 transition-colors font-mono"
      >
        <div className="flex items-center gap-2">
          <span className="text-cyan-400 text-[10px]">{'>'}</span>
          <span className="text-[10px] tracking-wider font-medium text-cyan-400 uppercase">
            META_ANALYSIS
          </span>
          {isStreaming && (
            <span className="text-cyan-400 animate-pulse text-[10px]">_</span>
          )}
        </div>
        {hasContent && (
          <span className="text-cyan-600 text-[10px]">
            {shouldCollapse ? '[▼]' : '[▲]'}
          </span>
        )}
      </button>

      {/* Terminal Content */}
      <div
        className={cn(
          'overflow-hidden transition-all duration-300 px-3',
          shouldCollapse ? 'max-h-8' : 'max-h-96'
        )}
      >
        {hasContent ? (
          <div className="pb-3">
            {shouldCollapse ? (
              // Collapsed preview
              <p className="text-[11px] text-cyan-500/70 truncate font-mono border-l-2 border-cyan-900/50 pl-2">
                {previewText}
                {previewText.length >= 120 && '...'}
              </p>
            ) : (
              // Full content - terminal box
              <div className="border border-cyan-900/30 bg-cyan-950/10 p-2">
                <div className="text-[11px] leading-relaxed text-cyan-300 space-y-2 font-mono">
                  {paragraphs.map((paragraph, i) => (
                    <p key={i} className="border-l-2 border-cyan-900/50 pl-2">
                      {paragraph}
                    </p>
                  ))}
                  {isStreaming && (
                    <span className="inline-block text-cyan-400 animate-pulse">▊</span>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : (
          // Empty state
          <div className="pb-3">
            {isStreaming ? (
              <div className="flex items-center gap-2 text-[11px] text-cyan-600 font-mono">
                <span className="animate-pulse">◐</span>
                <span>ANALYZING...</span>
              </div>
            ) : (
              <p className="text-[11px] text-cyan-700 font-mono">
                [ awaiting input... ]
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
