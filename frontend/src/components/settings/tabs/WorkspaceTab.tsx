/**
 * Workspace Tab - Workspace and case preferences
 */

'use client';

import * as React from 'react';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
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
        <Label className="text-base font-semibold">Default Case View</Label>
        <p className="text-sm text-neutral-600 mb-3">
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
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-neutral-200 hover:border-neutral-300'
              }`}
            >
              <div className="flex items-start">
                <input
                  type="radio"
                  name="default_case_view"
                  value={option.value}
                  checked={preferences.default_case_view === option.value}
                  onChange={(e) => onChange({ default_case_view: e.target.value as any })}
                  className="mt-1 mr-3"
                />
                <div>
                  <p className="font-medium text-neutral-900">{option.label}</p>
                  <p className="text-sm text-neutral-600">{option.description}</p>
                </div>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Auto-save Delay */}
      <div>
        <Label htmlFor="auto-save-delay">Auto-save Delay</Label>
        <div className="flex items-center gap-2">
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
          <span className="text-sm text-neutral-600">milliseconds</span>
        </div>
        <p className="text-xs text-neutral-500 mt-1">
          How long to wait before auto-saving (1000 = 1 second)
        </p>
      </div>

      {/* Case Creation Toggles */}
      <div>
        <Label className="text-base font-semibold">Case Creation</Label>
        <p className="text-sm text-neutral-600 mb-3">
          Auto-create items when cases are created from conversations
        </p>
        <div className="space-y-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={preferences.auto_create_inquiries ?? true}
              onChange={(e) => onChange({ auto_create_inquiries: e.target.checked })}
              className="rounded border-neutral-300"
            />
            <span className="text-sm text-neutral-900">
              Auto-create inquiries from questions
            </span>
          </label>
          
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={preferences.auto_detect_assumptions ?? true}
              onChange={(e) => onChange({ auto_detect_assumptions: e.target.checked })}
              className="rounded border-neutral-300"
            />
            <span className="text-sm text-neutral-900">
              Auto-detect assumptions
            </span>
          </label>
          
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={preferences.auto_generate_titles ?? true}
              onChange={(e) => onChange({ auto_generate_titles: e.target.checked })}
              className="rounded border-neutral-300"
            />
            <span className="text-sm text-neutral-900">
              Auto-generate titles for cases and inquiries
            </span>
          </label>
        </div>
      </div>

      {/* Evidence Defaults */}
      <div>
        <Label htmlFor="evidence-credibility">Evidence Credibility Threshold</Label>
        <p className="text-sm text-neutral-600 mb-2">
          Minimum star rating for resolution suggestions
        </p>
        <select
          id="evidence-credibility"
          value={preferences.evidence_min_credibility || 3}
          onChange={(e) => onChange({ evidence_min_credibility: parseInt(e.target.value) })}
          className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm"
        >
          {[1, 2, 3, 4, 5].map((stars) => (
            <option key={stars} value={stars}>
              {stars} star{stars > 1 ? 's' : ''} minimum
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
