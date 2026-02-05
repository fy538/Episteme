/**
 * ChecklistItem - Individual readiness checklist item
 *
 * Displays item with checkbox, description, and optional context.
 * Shows AI explanation when expanded.
 */

'use client';

import { Checkbox } from '@/components/ui/checkbox';
import type { ReadinessChecklistItemData } from './ReadinessChecklist';

interface ChecklistItemProps {
  item: ReadinessChecklistItemData;
  isExpanded: boolean;
  onToggle: () => void;
  onExpand: () => void;
  onDelete: () => void;
  // Optional props for hierarchical display
  showProgress?: boolean;
  progressText?: string;
  isChild?: boolean;
}

export function ChecklistItem({
  item,
  isExpanded,
  onToggle,
  onExpand,
  onDelete,
  showProgress = false,
  progressText,
  isChild = false,
}: ChecklistItemProps) {
  const hasContext = item.why_important || item.completion_note;

  return (
    <div className="border border-neutral-200 dark:border-neutral-800 rounded-lg p-3 bg-white dark:bg-neutral-950">
      <div className="flex items-start gap-3">
        <Checkbox
          checked={item.is_complete}
          onChange={onToggle}
          className="mt-1"
        />

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <button
              onClick={hasContext ? onExpand : undefined}
              className={`text-left flex-1 ${hasContext ? 'cursor-pointer' : 'cursor-default'}`}
            >
              <div>
                <span
                  className={`text-sm ${isChild ? 'text-sm' : 'font-medium'} ${
                    item.is_complete
                      ? 'line-through text-neutral-500 dark:text-neutral-500'
                      : 'text-neutral-900 dark:text-neutral-100'
                  }`}
                >
                  {item.description}
                </span>
                {showProgress && progressText && (
                  <div className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                    {progressText}
                  </div>
                )}
              </div>
            </button>

            {hasContext && (
              <button
                onClick={onExpand}
                className="flex-shrink-0 p-1 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded transition-colors"
                aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
              >
                <svg
                  className={`w-4 h-4 text-neutral-400 transition-transform ${
                    isExpanded ? 'rotate-180' : ''
                  }`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>
            )}
          </div>

          {/* Expanded context */}
          {isExpanded && hasContext && (
            <div className="mt-3 space-y-2">
              {item.why_important && !item.is_complete && (
                <div className="text-xs text-neutral-600 dark:text-neutral-400 pl-3 border-l-2 border-accent-500">
                  <span className="font-medium text-neutral-700 dark:text-neutral-300">
                    Why this matters:{' '}
                  </span>
                  {item.why_important}
                </div>
              )}

              {item.completion_note && item.is_complete && (
                <div className="text-xs text-neutral-600 dark:text-neutral-400 pl-3 border-l-2 border-green-500">
                  <span className="font-medium text-green-700 dark:text-green-400">
                    Completed:{' '}
                  </span>
                  {item.completion_note}
                </div>
              )}
            </div>
          )}

          {/* Metadata row */}
          <div className="flex items-center gap-3 mt-2">
            {item.created_by_ai && (
              <span className="text-xs text-neutral-500 dark:text-neutral-500 flex items-center gap-1">
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 10V3L4 14h7v7l9-11h-7z"
                  />
                </svg>
                AI suggested
              </span>
            )}

            {item.linked_inquiry && (
              <span className="text-xs text-accent-600 dark:text-accent-400 flex items-center gap-1">
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
                  />
                </svg>
                Linked to inquiry
              </span>
            )}

            <button
              onClick={onDelete}
              className="ml-auto text-xs text-neutral-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
