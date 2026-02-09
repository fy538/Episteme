/**
 * Workspace Tab — Case view defaults and auto-save preferences
 *
 * Uses SettingsCard grid for default view selection,
 * SettingsRow for inline controls.
 */

'use client';

import * as React from 'react';
import { Input } from '@/components/ui/input';
import { SettingsGroup, SettingsRow, SettingsCard, SettingsCardGrid } from '../SettingsSection';
import type { UserPreferences } from '@/lib/api/preferences';

interface WorkspaceTabProps {
  preferences: Partial<UserPreferences>;
  onChange: (updates: Partial<UserPreferences>) => void;
}

const CASE_VIEW_OPTIONS = [
  {
    value: 'brief' as const,
    label: 'Brief',
    description: 'Editable document view',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
  {
    value: 'dashboard' as const,
    label: 'Inquiry Dashboard',
    description: 'Investigation overview',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
      </svg>
    ),
  },
  {
    value: 'documents' as const,
    label: 'Documents',
    description: 'Document tree view',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
      </svg>
    ),
  },
];

export function WorkspaceTab({ preferences, onChange }: WorkspaceTabProps) {
  return (
    <div className="space-y-8">
      {/* Default Case View */}
      <SettingsGroup title="Default Case View" description="Choose which view to show when opening a case">
        <SettingsCardGrid columns={3}>
          {CASE_VIEW_OPTIONS.map((option) => (
            <SettingsCard
              key={option.value}
              active={preferences.default_case_view === option.value}
              onClick={() => onChange({ default_case_view: option.value })}
              icon={option.icon}
              title={option.label}
              description={option.description}
            />
          ))}
        </SettingsCardGrid>
      </SettingsGroup>

      {/* Auto-save */}
      <SettingsGroup title="Auto-save" description="Configure automatic saving behavior" divider>
        <SettingsRow
          label="Auto-save delay"
          description="How long to wait before auto-saving (1000 = 1 second)"
        >
          <div className="flex items-center gap-2">
            <Input
              type="number"
              min="0"
              max="5000"
              step="500"
              value={preferences.auto_save_delay_ms || 1000}
              onChange={(e) => onChange({ auto_save_delay_ms: parseInt(e.target.value) })}
              className="w-24"
            />
            <span className="text-xs text-neutral-500 dark:text-neutral-400">ms</span>
          </div>
        </SettingsRow>
      </SettingsGroup>

    </div>
  );
}
