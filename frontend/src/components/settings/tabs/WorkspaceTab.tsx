/**
 * Workspace Tab - Workspace and case preferences
 */

'use client';

import * as React from 'react';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import type { UserPreferences } from '@/lib/api/preferences';

interface WorkspaceTabProps {
  preferences: Partial<UserPreferences>;
  onChange: (updates: Partial<UserPreferences>) => void;
}

export function WorkspaceTab({ preferences, onChange }: WorkspaceTabProps) {
  return (
    <div className="space-y-6">
      {/* Default View */}
      <div>
        <Label className="text-base font-semibold text-neutral-900 dark:text-neutral-100">Default Case View</Label>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-3">
          Choose which view to show when opening a case
        </p>
        <div className="space-y-2">
          {[
            { value: 'brief', label: 'Brief', description: 'Editable document view' },
            { value: 'dashboard', label: 'Inquiry Dashboard', description: 'Investigation overview' },
            { value: 'documents', label: 'Documents', description: 'Document tree view' },
          ].map((option) => (
            <label
              key={option.value}
              className={`block p-3 border-2 rounded-lg cursor-pointer transition-all ${
                preferences.default_case_view === option.value
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                  : 'border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600'
              }`}
            >
              <div className="flex items-start">
                <input
                  type="radio"
                  name="default_case_view"
                  value={option.value}
                  checked={preferences.default_case_view === option.value}
                  onChange={(e) => onChange({ default_case_view: e.target.value as 'brief' | 'dashboard' | 'documents' })}
                  className="mt-1 mr-3"
                />
                <div>
                  <p className="font-medium text-neutral-900 dark:text-neutral-100">{option.label}</p>
                  <p className="text-sm text-neutral-600 dark:text-neutral-400">{option.description}</p>
                </div>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Auto-save Delay */}
      <div>
        <Label htmlFor="auto-save-delay" className="text-neutral-900 dark:text-neutral-100">Auto-save Delay</Label>
        <div className="flex items-center gap-2 mt-2">
          <Input
            id="auto-save-delay"
            type="number"
            min="0"
            max="5000"
            step="500"
            value={preferences.auto_save_delay_ms || 1000}
            onChange={(e) => onChange({ auto_save_delay_ms: parseInt(e.target.value) })}
            className="w-24"
          />
          <span className="text-sm text-neutral-600 dark:text-neutral-400">milliseconds</span>
        </div>
        <p className="text-xs text-neutral-500 dark:text-neutral-500 mt-1">
          How long to wait before auto-saving (1000 = 1 second)
        </p>
      </div>

      {/* Evidence Defaults */}
      <div>
        <Label htmlFor="evidence-credibility" className="text-neutral-900 dark:text-neutral-100">Evidence Credibility Threshold</Label>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-2">
          Minimum star rating for resolution suggestions
        </p>
        <Select
          id="evidence-credibility"
          value={preferences.evidence_min_credibility || 3}
          onChange={(e) => onChange({ evidence_min_credibility: parseInt(e.target.value) })}
          className="w-full max-w-xs"
        >
          {[1, 2, 3, 4, 5].map((stars) => (
            <option key={stars} value={stars}>
              {stars} star{stars > 1 ? 's' : ''} minimum
            </option>
          ))}
        </Select>
      </div>
    </div>
  );
}
