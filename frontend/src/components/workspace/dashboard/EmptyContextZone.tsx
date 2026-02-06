/**
 * Empty Context Zone
 *
 * Shown in HomeContextZone when there's no content to display
 * (no continue state, no actions, no activity).
 * Provides gentle guidance rather than blank space.
 */

'use client';

import { cn } from '@/lib/utils';

interface EmptyContextZoneProps {
  className?: string;
}

export function EmptyContextZone({ className }: EmptyContextZoneProps) {
  return (
    <div className={cn('max-w-2xl mx-auto px-6 py-4 animate-slide-up', className)}>
      <div className="rounded-xl border border-dashed border-neutral-300 dark:border-neutral-700 bg-neutral-50/50 dark:bg-neutral-900/50 p-6 text-center">
        {/* Icon */}
        <div className="mb-3 flex justify-center">
          <div className="w-10 h-10 rounded-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center">
            <SparklesIcon className="w-5 h-5 text-neutral-400 dark:text-neutral-500" />
          </div>
        </div>

        {/* Message */}
        <p className="text-neutral-600 dark:text-neutral-400 mb-1">
          Ready when you are
        </p>
        <p className="text-sm text-neutral-500 dark:text-neutral-500">
          Start a conversation to begin analyzing a decision
        </p>
      </div>
    </div>
  );
}

// Sparkles icon
function SparklesIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 3L13.5 8.5L19 10L13.5 11.5L12 17L10.5 11.5L5 10L10.5 8.5L12 3Z" />
      <path d="M19 15L19.5 17L21.5 17.5L19.5 18L19 20L18.5 18L16.5 17.5L18.5 17L19 15Z" />
      <path d="M5 18L5.5 19.5L7 20L5.5 20.5L5 22L4.5 20.5L3 20L4.5 19.5L5 18Z" />
    </svg>
  );
}

export default EmptyContextZone;
