/**
 * Action Chips
 *
 * Quick action chips displayed below the chat input on the home page.
 * These provide contextual suggestions for what the user might want to do.
 */

'use client';

import { cn } from '@/lib/utils';
import type { ContinueState } from '@/lib/types/intelligence';

interface ActionChipsProps {
  continueState: ContinueState | null;
  hasProjects?: boolean;
  onChipClick: (action: string, data?: Record<string, unknown>) => void;
  className?: string;
}

export function ActionChips({ continueState, hasProjects = true, onChipClick, className }: ActionChipsProps) {
  // Build chip array for staggered animations
  const chips: Array<{
    key: string;
    icon: React.ReactNode;
    label: string;
    action: string;
    data?: Record<string, unknown>;
    variant?: 'default' | 'primary';
  }> = [];

  if (!hasProjects) {
    // Simplified chips for new users with no projects
    chips.push(
      { key: 'explore', icon: <SparklesIcon />, label: 'Start exploring', action: 'explore', variant: 'primary' },
      { key: 'learn', icon: <BookIcon />, label: 'How it works', action: 'learn' }
    );
  } else {
    // Normal chips for users with projects
    if (continueState) {
      chips.push({
        key: 'continue',
        icon: <ArrowRightIcon />,
        label: `Continue: ${continueState.title}`,
        action: 'continue',
        data: continueState as unknown as Record<string, unknown>,
        variant: 'primary',
      });
    }

    chips.push(
      { key: 'explore', icon: <LightbulbIcon />, label: 'Explore a new angle', action: 'explore' },
      { key: 'new_case', icon: <PlusIcon />, label: 'Start new case', action: 'new_case' },
      { key: 'research', icon: <SearchIcon />, label: 'Research', action: 'research' }
    );
  }

  return (
    <div className={cn('flex flex-wrap justify-center gap-2 pb-6', className)}>
      {chips.map((chip, index) => (
        <div
          key={chip.key}
          className="animate-scale-in"
          style={{ animationDelay: `${200 + index * 50}ms` }}
        >
          <ActionChip
            icon={chip.icon}
            label={chip.label}
            onClick={() => onChipClick(chip.action, chip.data)}
            variant={chip.variant}
          />
        </div>
      ))}
    </div>
  );
}

interface ActionChipProps {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  variant?: 'default' | 'primary';
}

function ActionChip({ icon, label, onClick, variant = 'default' }: ActionChipProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all',
        'border hover:shadow-sm active:scale-[0.98]',
        variant === 'primary'
          ? 'bg-accent-50 dark:bg-accent-900/30 border-accent-200 dark:border-accent-800 text-accent-700 dark:text-accent-300 hover:bg-accent-100 dark:hover:bg-accent-900/50'
          : 'bg-white dark:bg-neutral-900 border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300 hover:border-neutral-300 dark:hover:border-neutral-600 hover:bg-neutral-50 dark:hover:bg-neutral-800'
      )}
    >
      <span className="w-4 h-4">{icon}</span>
      <span className="whitespace-nowrap">{label}</span>
    </button>
  );
}

// Icons
function ArrowRightIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M12 5l7 7-7 7" />
    </svg>
  );
}

function LightbulbIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 18h6M10 22h4M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0018 8 6 6 0 006 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 018.91 14" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <circle cx="11" cy="11" r="8" />
      <path d="M21 21l-4.35-4.35" />
    </svg>
  );
}

function SparklesIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3L13.5 8.5L19 10L13.5 11.5L12 17L10.5 11.5L5 10L10.5 8.5L12 3Z" />
      <path d="M19 15L19.5 17L21.5 17.5L19.5 18L19 20L18.5 18L16.5 17.5L18.5 17L19 15Z" />
    </svg>
  );
}

function BookIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
    </svg>
  );
}

export default ActionChips;
