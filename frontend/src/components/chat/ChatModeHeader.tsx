/**
 * ChatModeHeader - Shows the current chat mode context
 *
 * Displays:
 * - casual: Just the thread title
 * - case: "Case: [caseName]"
 * - inquiry_focus: "Case > Inquiry: [inquiryTitle]" with exit button
 */

'use client';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { theme } from '@/lib/theme/companionTheme';
import type { ModeContext, ChatMode } from '@/lib/types/companion';

interface ChatModeHeaderProps {
  mode: ModeContext;
  threadTitle?: string;
  onExitFocus?: () => void;
  onExitCase?: () => void;
  onViewCase?: () => void;
  onViewInquiry?: () => void;
  className?: string;
}

// Map mode to theme section - using semantic colors for header (not terminal)
const getModeStyles = (mode: ChatMode) => {
  switch (mode) {
    case 'case':
      return {
        bg: 'bg-warning-50 dark:bg-warning-900/20',
        border: 'border-warning-200 dark:border-warning-800',
        text: 'text-warning-700 dark:text-warning-400',
        icon: 'text-warning-500',
      };
    case 'inquiry_focus':
      return {
        bg: 'bg-accent-50 dark:bg-accent-900/20',
        border: 'border-accent-200 dark:border-accent-800',
        text: 'text-accent-700 dark:text-accent-400',
        icon: 'text-accent-500',
      };
    default:
      return {
        bg: 'bg-neutral-100 dark:bg-primary-800',
        border: 'border-neutral-200 dark:border-neutral-700',
        text: 'text-neutral-600 dark:text-neutral-400',
        icon: 'text-neutral-500',
      };
  }
};

export function ChatModeHeader({
  mode,
  threadTitle,
  onExitFocus,
  onExitCase,
  onViewCase,
  onViewInquiry,
  className,
}: ChatModeHeaderProps) {
  const styles = getModeStyles(mode.mode);
  const caseStyles = getModeStyles('case');

  // Don't render for casual mode without explicit content
  if (mode.mode === 'casual' && !threadTitle) {
    return null;
  }

  return (
    <div
      className={cn(
        'px-4 py-2 border-b flex items-center justify-between',
        styles.bg,
        styles.border,
        className
      )}
    >
      <div className="flex items-center gap-2 min-w-0">
        {mode.mode === 'casual' && (
          <>
            <span className="text-sm text-neutral-500">Chat:</span>
            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300 truncate">
              {threadTitle || 'New Chat'}
            </span>
          </>
        )}

        {mode.mode === 'case' && (
          <>
            <span className={cn('text-lg', styles.icon)}>+</span>
            <button
              onClick={onViewCase}
              className={cn(
                'text-sm font-medium truncate hover:underline',
                styles.text,
                onViewCase && 'cursor-pointer'
              )}
              disabled={!onViewCase}
            >
              {mode.caseName}
            </button>
          </>
        )}

        {mode.mode === 'inquiry_focus' && (
          <>
            {/* Case breadcrumb */}
            <span className={cn('text-lg', caseStyles.icon)}>+</span>
            <button
              onClick={onViewCase}
              className={cn(
                'text-sm hover:underline truncate max-w-32',
                caseStyles.text
              )}
              title={mode.caseName}
            >
              {mode.caseName}
            </button>

            {/* Separator */}
            <span className="text-neutral-400 dark:text-neutral-600">&gt;</span>

            {/* Inquiry */}
            <span className={cn('text-lg', styles.icon)}>@</span>
            <button
              onClick={onViewInquiry}
              className={cn(
                'text-sm font-medium truncate hover:underline',
                styles.text,
                onViewInquiry && 'cursor-pointer'
              )}
              disabled={!onViewInquiry}
            >
              {mode.inquiryTitle}
            </button>
          </>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {mode.mode === 'inquiry_focus' && onExitFocus && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onExitFocus}
            className={cn('text-xs', styles.text)}
          >
            Exit Focus
          </Button>
        )}

        {mode.mode === 'case' && onExitCase && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onExitCase}
            className={cn('text-xs', styles.text)}
          >
            Exit Case
          </Button>
        )}
      </div>
    </div>
  );
}
