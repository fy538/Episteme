/**
 * Settings Primitives — Shared building blocks for all settings UIs
 *
 * SettingsGroup: Section heading with title + description
 * SettingsRow: Label+description left, control right
 * SettingsCard: Selectable card for radio-style choices
 * SettingsDangerZone: Red-bordered container for destructive actions
 */

'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

/* ─── SettingsGroup ─── */

interface SettingsGroupProps {
  title: string;
  description?: string;
  divider?: boolean;
  children: React.ReactNode;
}

export function SettingsGroup({ title, description, divider = false, children }: SettingsGroupProps) {
  return (
    <section className={cn(divider && 'border-t border-neutral-200 dark:border-neutral-700 pt-6')}>
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 uppercase tracking-wide">
          {title}
        </h3>
        {description && (
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
            {description}
          </p>
        )}
      </div>
      <div className="space-y-1">
        {children}
      </div>
    </section>
  );
}

/* ─── SettingsRow ─── */

interface SettingsRowProps {
  label: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}

export function SettingsRow({ label, description, children, className }: SettingsRowProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-between gap-4 py-3 px-4 -mx-4 rounded-lg',
        'hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors',
        className
      )}
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
          {label}
        </p>
        {description && (
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
            {description}
          </p>
        )}
      </div>
      <div className="flex-shrink-0">
        {children}
      </div>
    </div>
  );
}

/* ─── SettingsCard ─── */

interface SettingsCardProps {
  active?: boolean;
  onClick?: () => void;
  icon?: React.ReactNode;
  title: string;
  description?: string;
  meta?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}

export function SettingsCard({
  active = false,
  onClick,
  icon,
  title,
  description,
  meta,
  children,
  className,
}: SettingsCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'w-full text-left p-4 rounded-xl border-2 transition-all duration-150',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2',
        active
          ? 'border-accent-500 bg-accent-50 dark:bg-accent-900/20 shadow-sm'
          : 'border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600 hover:bg-neutral-50 dark:hover:bg-neutral-800/50',
        className
      )}
    >
      <div className="flex items-start gap-3">
        {icon && (
          <div
            className={cn(
              'flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center',
              active
                ? 'bg-accent-100 dark:bg-accent-800/40 text-accent-600 dark:text-accent-400'
                : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400'
            )}
          >
            {icon}
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className={cn(
              'text-sm font-medium',
              active
                ? 'text-accent-900 dark:text-accent-100'
                : 'text-neutral-900 dark:text-neutral-100'
            )}>
              {title}
            </p>
            {meta}
          </div>
          {description && (
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
              {description}
            </p>
          )}
          {children}
        </div>
        {/* Active indicator */}
        <div className="flex-shrink-0 mt-1">
          <div
            className={cn(
              'w-4 h-4 rounded-full border-2 flex items-center justify-center transition-colors',
              active
                ? 'border-accent-500 bg-accent-500'
                : 'border-neutral-300 dark:border-neutral-600'
            )}
          >
            {active && (
              <svg className="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={3}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}

/* ─── SettingsCardGrid ─── */

interface SettingsCardGridProps {
  columns?: 2 | 3;
  children: React.ReactNode;
}

export function SettingsCardGrid({ columns = 3, children }: SettingsCardGridProps) {
  return (
    <div className={cn(
      'grid gap-3',
      columns === 2 ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-1 sm:grid-cols-3'
    )}>
      {children}
    </div>
  );
}

/* ─── SettingsDangerZone ─── */

interface SettingsDangerZoneProps {
  children: React.ReactNode;
}

export function SettingsDangerZone({ children }: SettingsDangerZoneProps) {
  return (
    <section className="border-t border-neutral-200 dark:border-neutral-700 pt-6">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-error-600 dark:text-error-400 uppercase tracking-wide">
          Danger Zone
        </h3>
      </div>
      <div className="rounded-xl border border-error-200 dark:border-error-800/50 bg-error-50/50 dark:bg-error-900/10 p-4 space-y-3">
        {children}
      </div>
    </section>
  );
}

/* ─── DangerAction ─── */

interface DangerActionProps {
  title: string;
  description: string;
  buttonLabel: string;
  onAction?: () => void;
  variant?: 'warning' | 'destructive';
}

export function DangerAction({ title, description, buttonLabel, onAction, variant = 'destructive' }: DangerActionProps) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-error-900 dark:text-error-200">{title}</p>
        <p className="text-xs text-error-700 dark:text-error-400">{description}</p>
      </div>
      <Button
        variant={variant === 'warning' ? 'outline' : 'destructive'}
        size="sm"
        onClick={onAction}
        className={variant === 'warning' ? 'border-warning-300 text-warning-700 hover:bg-warning-50 dark:border-warning-700 dark:text-warning-300' : ''}
      >
        {buttonLabel}
      </Button>
    </div>
  );
}
