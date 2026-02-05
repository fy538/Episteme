/**
 * Advanced Tab - Debug options and experimental features
 */

'use client';

import * as React from 'react';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { UserPreferences } from '@/lib/api/preferences';

interface AdvancedTabProps {
  preferences: Partial<UserPreferences>;
  onChange: (updates: Partial<UserPreferences>) => void;
}

export function AdvancedTab({ preferences, onChange }: AdvancedTabProps) {
  const [showSkills, setShowSkills] = React.useState(false);

  return (
    <div className="space-y-6">
      {/* Skills Section (Collapsed by default) */}
      <div className="border border-neutral-200 dark:border-neutral-700 rounded-lg overflow-hidden">
        <button
          onClick={() => setShowSkills(!showSkills)}
          className="w-full p-4 flex items-center justify-between text-left hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
        >
          <div>
            <h3 className="text-base font-semibold text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
              Skills & Templates
              <Badge variant="neutral" className="text-xs">
                Optional
              </Badge>
            </h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
              Configure domain-specific templates for AI agents
            </p>
          </div>
          <svg
            className={`w-5 h-5 text-neutral-400 dark:text-neutral-500 transition-transform ${
              showSkills ? 'rotate-180' : ''
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {showSkills && (
          <div className="p-4 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50">
            <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-3">
              Skills are powerful but optional. Most users work great with organization defaults.
            </p>
            <div className="flex gap-2">
              <Button size="sm" variant="outline">
                View My Skills
              </Button>
              <Button size="sm" variant="ghost">
                Browse Templates
              </Button>
            </div>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-3">
              Skills auto-inject domain knowledge into agents when activated for a case.
            </p>
          </div>
        )}
      </div>

      {/* Debug Options */}
      <section>
        <Label className="text-base font-semibold text-neutral-900 dark:text-neutral-100">Debug Options</Label>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
          For troubleshooting and transparency
        </p>
        <div className="space-y-3">
          <label className="flex items-center gap-3 cursor-pointer p-3 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors">
            <input
              type="checkbox"
              checked={preferences.show_debug_info ?? false}
              onChange={(e) => onChange({ show_debug_info: e.target.checked })}
              className="w-4 h-4 rounded border-neutral-300 dark:border-neutral-600 text-primary-600"
            />
            <div>
              <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                Show event IDs and correlation IDs
              </span>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                Display technical identifiers for debugging
              </p>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer p-3 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors">
            <input
              type="checkbox"
              checked={preferences.show_ai_prompts ?? false}
              onChange={(e) => onChange({ show_ai_prompts: e.target.checked })}
              className="w-4 h-4 rounded border-neutral-300 dark:border-neutral-600 text-primary-600"
            />
            <div>
              <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                Show AI prompts (transparency mode)
              </span>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                See the prompts sent to AI models
              </p>
            </div>
          </label>
        </div>
      </section>

      {/* Danger Zone */}
      <section className="border-t border-neutral-200 dark:border-neutral-700 pt-6">
        <Label className="text-base font-semibold text-error-600 dark:text-error-400">Danger Zone</Label>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
          Irreversible actions
        </p>
        <div className="p-4 border border-error-200 dark:border-error-900 rounded-lg bg-error-50 dark:bg-error-900/20">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-error-900 dark:text-error-200">
                Reset all preferences
              </p>
              <p className="text-xs text-error-700 dark:text-error-400">
                Restore all settings to their defaults
              </p>
            </div>
            <Button variant="outline" size="sm" className="border-error-300 text-error-700 hover:bg-error-100 dark:border-error-700 dark:text-error-300 dark:hover:bg-error-900/40">
              Reset
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
