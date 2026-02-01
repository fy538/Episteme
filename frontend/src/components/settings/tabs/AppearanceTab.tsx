/**
 * Appearance Tab - Theme and UI preferences
 */

'use client';

import * as React from 'react';
import { Label } from '@/components/ui/label';
import { Radio } from '@/components/ui/radio';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import type { UserPreferences } from '@/lib/api/preferences';

interface AppearanceTabProps {
  preferences: Partial<UserPreferences>;
  onChange: (updates: Partial<UserPreferences>) => void;
}

export function AppearanceTab({ preferences, onChange }: AppearanceTabProps) {
  return (
    <div className="space-y-6">
      {/* Theme */}
      <div>
        <Label className="text-base font-semibold">Theme</Label>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-3">
          Choose your preferred color scheme
        </p>
        <ThemeToggle />
      </div>

      {/* Font Size */}
      <div>
        <Label className="text-base font-semibold">Font Size</Label>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-3">
          Editor and content font size
        </p>
        <div className="space-y-2">
          {[
            { value: 'small', label: 'Small' },
            { value: 'medium', label: 'Medium' },
            { value: 'large', label: 'Large' },
          ].map((option) => (
            <Radio
              key={option.value}
              name="font_size"
              value={option.value}
              checked={preferences.font_size === option.value}
              onChange={(e) => onChange({ font_size: e.target.value as any })}
              label={option.label}
            />
          ))}
        </div>
      </div>

      {/* Density */}
      <div>
        <Label className="text-base font-semibold">Spacing Density</Label>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-3">
          How much space between UI elements
        </p>
        <div className="space-y-2">
          {[
            { value: 'compact', label: 'Compact', description: 'More information, less space' },
            { value: 'comfortable', label: 'Comfortable', description: 'Balanced spacing' },
            { value: 'relaxed', label: 'Relaxed', description: 'More breathing room' },
          ].map((option) => (
            <div key={option.value} className="flex items-start gap-2">
              <Radio
                name="density"
                value={option.value}
                checked={preferences.density === option.value}
                onChange={(e) => onChange({ density: e.target.value as any })}
              />
              <div>
                <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{option.label}</span>
                <span className="text-sm text-neutral-600 dark:text-neutral-400 ml-2">— {option.description}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
