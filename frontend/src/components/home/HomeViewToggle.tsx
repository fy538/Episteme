/**
 * HomeViewToggle
 *
 * Small pill/segmented control for switching between Home and Brief views.
 * Used in the home page header. Has a sliding background indicator.
 */

'use client';

import { cn } from '@/lib/utils';

export type HomeViewMode = 'home' | 'brief';

interface HomeViewToggleProps {
  viewMode: HomeViewMode;
  onViewModeChange: (mode: HomeViewMode) => void;
}

const MODES: { id: HomeViewMode; label: string }[] = [
  { id: 'home', label: 'Home' },
  { id: 'brief', label: 'Brief' },
];

export function HomeViewToggle({ viewMode, onViewModeChange }: HomeViewToggleProps) {
  return (
    <div
      className={cn(
        'relative flex items-center p-0.5 rounded-lg',
        'bg-neutral-100 dark:bg-neutral-800',
        'border border-neutral-200/50 dark:border-neutral-700/50'
      )}
    >
      {/* Sliding background pill */}
      <div
        className={cn(
          'absolute top-0.5 bottom-0.5 rounded-md',
          'bg-white dark:bg-neutral-700',
          'shadow-sm',
          'transition-all duration-200 ease-out'
        )}
        style={{
          left: viewMode === 'home' ? '2px' : '50%',
          width: 'calc(50% - 2px)',
        }}
      />

      {MODES.map((mode) => (
        <button
          key={mode.id}
          onClick={() => onViewModeChange(mode.id)}
          className={cn(
            'relative z-10 px-3 py-1 text-xs font-medium rounded-md',
            'transition-colors duration-200',
            viewMode === mode.id
              ? 'text-neutral-900 dark:text-neutral-100'
              : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200'
          )}
        >
          {mode.label}
        </button>
      ))}
    </div>
  );
}
