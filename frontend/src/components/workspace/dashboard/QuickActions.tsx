/**
 * Quick Actions
 *
 * Quick action buttons for common tasks.
 */

'use client';

import { cn } from '@/lib/utils';

interface QuickAction {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}

interface QuickActionsProps {
  actions: QuickAction[];
  className?: string;
}

export function QuickActions({ actions, className }: QuickActionsProps) {
  return (
    <div className={cn('grid grid-cols-3 gap-3', className)}>
      {actions.map((action, index) => (
        <QuickActionCard key={index} {...action} />
      ))}
    </div>
  );
}

function QuickActionCard({ icon, label, onClick }: QuickAction) {
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-center justify-center gap-2 p-4 rounded-xl border border-neutral-200 dark:border-neutral-800 hover:border-accent-300 dark:hover:border-accent-700 hover:bg-accent-50 dark:hover:bg-accent-900/20 transition-colors group"
    >
      <div className="text-neutral-600 dark:text-neutral-400 group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors">
        {icon}
      </div>
      <span className="text-sm font-medium text-primary-900 dark:text-primary-50 group-hover:text-accent-600 dark:group-hover:text-accent-400 transition-colors">
        {label}
      </span>
    </button>
  );
}

// Pre-built icons for common quick actions
export function ChatIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-6 h-6', className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z" />
    </svg>
  );
}

export function PlusIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-6 h-6', className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

export function UploadIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-6 h-6', className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-6 h-6', className)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8" />
      <path d="M21 21l-4.35-4.35" strokeLinecap="round" />
    </svg>
  );
}

export default QuickActions;
