/**
 * ThinkingSection - Mode-aware meta-cognitive reflection display
 *
 * Adapts its style and content based on the current chat mode:
 * - casual: General Socratic questions
 * - case: Case-focused ("Which inquiry should you tackle first?")
 * - inquiry_focus: Specific ("What would increase your confidence here?")
 */

'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { theme, isTerminalTheme } from '@/lib/theme/companionTheme';
import type { ChatMode } from '@/lib/types/companion';

interface ThinkingSectionProps {
  content: string;
  isStreaming?: boolean;
  mode: ChatMode;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

const MODE_LABELS: Record<ChatMode, string> = {
  casual: 'THINKING',
  case: 'CASE_ANALYSIS',
  inquiry_focus: 'INQUIRY_FOCUS',
};

// Map chat mode to theme section
const getModeTheme = (mode: ChatMode) => {
  switch (mode) {
    case 'case':
      return theme.case;
    case 'inquiry_focus':
      return theme.inquiry;
    default:
      return theme.thinking;
  }
};

export function ThinkingSection({
  content,
  isStreaming = false,
  mode,
  collapsed = false,
  onToggleCollapse,
}: ThinkingSectionProps) {
  const [isManuallyCollapsed, setIsManuallyCollapsed] = useState(false);

  const shouldCollapse = collapsed || isManuallyCollapsed;
  const hasContent = content && content.trim().length > 0;
  const modeTheme = getModeTheme(mode);

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
    <section className={cn('border-b', modeTheme.border)}>
      {/* Header */}
      <button
        onClick={handleToggle}
        className={cn(
          'w-full px-3 py-2 flex items-center justify-between transition-colors',
          modeTheme.bgHover,
          isTerminalTheme && 'font-mono'
        )}
      >
        <div className="flex items-center gap-2">
          <span className={cn('text-xs', modeTheme.text)}>{'>'}</span>
          <span className={cn('text-xs tracking-wider font-medium uppercase', modeTheme.text)}>
            {MODE_LABELS[mode]}
          </span>
          {isStreaming && (
            <span className={cn('animate-pulse text-xs', modeTheme.text)}>_</span>
          )}
        </div>
        {hasContent && (
          <span className={cn('text-xs', modeTheme.textMuted)}>
            {shouldCollapse ? '[+]' : '[-]'}
          </span>
        )}
      </button>

      {/* Content */}
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
              <p className={cn(
                'text-xs truncate border-l-2 pl-2',
                modeTheme.border,
                modeTheme.text,
                'opacity-70',
                isTerminalTheme && 'font-mono'
              )}>
                {previewText}
                {previewText.length >= 120 && '...'}
              </p>
            ) : (
              // Full content
              <div className={cn('border p-2', modeTheme.border, modeTheme.bg)}>
                <div className={cn(
                  'text-xs leading-relaxed space-y-2',
                  modeTheme.text,
                  isTerminalTheme && 'font-mono'
                )}>
                  {paragraphs.map((paragraph, i) => (
                    <p key={i} className={cn('border-l-2 pl-2', modeTheme.border)}>
                      {paragraph}
                    </p>
                  ))}
                  {isStreaming && (
                    <span className={cn('inline-block animate-pulse', modeTheme.text)}>|</span>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : (
          // Empty state
          <div className="pb-3">
            {isStreaming ? (
              <div className={cn(
                'flex items-center gap-2 text-xs',
                modeTheme.text,
                isTerminalTheme && 'font-mono'
              )}>
                <span className="animate-pulse">...</span>
                <span>thinking</span>
              </div>
            ) : (
              <p className={cn(
                'text-xs',
                modeTheme.textSubtle,
                isTerminalTheme && 'font-mono'
              )}>
                [ awaiting context... ]
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
