/**
 * Appearance Tab - Theme and UI preferences
 */

'use client';

import * as React from 'react';
import { Label } from '@/components/ui/label';
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
        <p className="text-sm text-neutral-600 mb-3">
          Choose your preferred color scheme
        </p>
        <div className="grid grid-cols-3 gap-3">
          {[
            { value: 'light', label: 'Light', icon: '☀️' },
            { value: 'dark', label: 'Dark', icon: '🌙' },
            { value: 'auto', label: 'Auto', icon: '🔄' },
          ].map((option) => (
            <label
              key={option.value}
              className={`p-4 border-2 rounded-lg cursor-pointer text-center transition-all ${
                preferences.theme === option.value
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-neutral-200 hover:border-neutral-300'
              }`}
            >
              <input
                type="radio"
                name="theme"
                value={option.value}
                checked={preferences.theme === option.value}
                onChange={(e) => onChange({ theme: e.target.value as any })}
                className="sr-only"
              />
              <div className="text-2xl mb-2">{option.icon}</div>
              <p className="text-sm font-medium text-neutral-900">{option.label}</p>
            </label>
          ))}
        </div>
        {preferences.theme === 'dark' && (
          <div className="mt-3 p-3 bg-primary-50 border border-primary-200 rounded-md">
            <p className="text-sm text-primary-900">
              💡 Dark mode coming soon! Your preference will be saved.
            </p>
          </div>
        )}
      </div>

      {/* Font Size */}
      <div>
        <Label className="text-base font-semibold">Font Size</Label>
        <p className="text-sm text-neutral-600 mb-3">
          Editor and content font size
        </p>
        <div className="space-y-2">
          {[
            { value: 'small', label: 'Small', example: 'text-sm' },
            { value: 'medium', label: 'Medium', example: 'text-base' },
            { value: 'large', label: 'Large', example: 'text-lg' },
          ].map((option) => (
            <label
              key={option.value}
              className={`block p-3 border rounded-md cursor-pointer ${
                preferences.font_size === option.value
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-neutral-200 hover:bg-neutral-50'
              }`}
            >
              <input
                type="radio"
                name="font_size"
                value={option.value}
                checked={preferences.font_size === option.value}
                onChange={(e) => onChange({ font_size: e.target.value as any })}
                className="mr-2"
              />
              <span className="text-sm font-medium text-neutral-900">{option.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Density */}
      <div>
        <Label className="text-base font-semibold">Spacing Density</Label>
        <p className="text-sm text-neutral-600 mb-3">
          How much space between UI elements
        </p>
        <div className="space-y-2">
          {[
            { value: 'compact', label: 'Compact', description: 'More information, less space' },
            { value: 'comfortable', label: 'Comfortable', description: 'Balanced spacing' },
            { value: 'relaxed', label: 'Relaxed', description: 'More breathing room' },
          ].map((option) => (
            <label
              key={option.value}
              className={`block p-3 border rounded-md cursor-pointer ${
                preferences.density === option.value
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-neutral-200 hover:bg-neutral-50'
              }`}
            >
              <input
                type="radio"
                name="density"
                value={option.value}
                checked={preferences.density === option.value}
                onChange={(e) => onChange({ density: e.target.value as any })}
                className="mr-2"
              />
              <div className="inline">
                <span className="text-sm font-medium text-neutral-900">{option.label}</span>
                <span className="text-sm text-neutral-600 ml-2">— {option.description}</span>
              </div>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
