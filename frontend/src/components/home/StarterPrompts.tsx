/**
 * StarterPrompts — Clickable scenario cards for first-time users.
 *
 * Displayed below the hero input when no projects or cases exist.
 * Each card triggers the same flow as typing + Enter: creates a
 * thread, stores the message in sessionStorage, and navigates to
 * /chat/[threadId].
 */

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';

interface StarterPromptsProps {
  onSelect: (prompt: string) => void;
}

const STARTER_PROMPTS = [
  {
    icon: '\u2696\ufe0f', // balance scale
    text: 'Help me think through whether to accept a job offer I received',
  },
  {
    icon: '\ud83d\udcca', // bar chart
    text: "I need to compare options for my team's next quarter priorities",
  },
  {
    icon: '\ud83d\udd0d', // magnifying glass
    text: 'What are the blind spots in my plan to launch a new product?',
  },
];

export const StarterPrompts = memo(function StarterPrompts({ onSelect }: StarterPromptsProps) {
  return (
    <div className="space-y-2">
      <p className="text-xs text-neutral-400 dark:text-neutral-500">
        Try a scenario
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        {STARTER_PROMPTS.map((prompt) => (
          <button
            key={prompt.text}
            type="button"
            onClick={() => onSelect(prompt.text)}
            aria-label={`Try: ${prompt.text}`}
            className={cn(
              'flex flex-col items-start text-left rounded-lg border p-3 min-h-[56px]',
              'bg-neutral-50 dark:bg-neutral-900/50',
              'border-neutral-200 dark:border-neutral-800',
              'hover:border-accent-300 dark:hover:border-accent-700',
              'hover:bg-accent-50/30 dark:hover:bg-accent-900/10',
              'transition-all duration-150 cursor-pointer',
            )}
          >
            <span className="text-sm mb-1" aria-hidden="true">{prompt.icon}</span>
            <span className="text-xs font-medium text-neutral-700 dark:text-neutral-300 leading-snug line-clamp-2">
              {prompt.text}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
});
