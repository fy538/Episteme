/**
 * Appearance Tab — Theme, font size, and density preferences
 *
 * Uses SettingsCard grid for visual selection cards.
 * Fills in the previously empty font_size and density UI.
 */

'use client';

import * as React from 'react';
import { useTheme } from '@/components/theme-provider';
import { SettingsGroup, SettingsCard, SettingsCardGrid } from '../SettingsSection';
import type { UserPreferences } from '@/lib/api/preferences';

interface AppearanceTabProps {
  preferences: Partial<UserPreferences>;
  onChange: (updates: Partial<UserPreferences>) => void;
}

/* ─── Theme Options ─── */

const THEME_OPTIONS: Array<{
  value: 'light' | 'dark' | 'system';
  label: string;
  description: string;
  icon: React.ReactNode;
  preview: { bg: string; fg: string; accent: string };
}> = [
  {
    value: 'light',
    label: 'Light',
    description: 'Clean, bright interface',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
      </svg>
    ),
    preview: { bg: 'bg-white', fg: 'bg-neutral-200', accent: 'bg-accent-400' },
  },
  {
    value: 'dark',
    label: 'Dark',
    description: 'Easy on the eyes',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
      </svg>
    ),
    preview: { bg: 'bg-neutral-900', fg: 'bg-neutral-700', accent: 'bg-accent-500' },
  },
  {
    value: 'system',
    label: 'System',
    description: 'Follow OS preference',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
    preview: { bg: 'bg-gradient-to-r from-white to-neutral-900', fg: 'bg-neutral-400', accent: 'bg-accent-500' },
  },
];

/* ─── Font Size Options ─── */

const FONT_SIZE_OPTIONS: Array<{
  value: 'small' | 'medium' | 'large';
  label: string;
  description: string;
  sampleClass: string;
}> = [
  {
    value: 'small',
    label: 'Small',
    description: 'Compact text',
    sampleClass: 'text-xs',
  },
  {
    value: 'medium',
    label: 'Medium',
    description: 'Default size',
    sampleClass: 'text-sm',
  },
  {
    value: 'large',
    label: 'Large',
    description: 'Easier to read',
    sampleClass: 'text-base',
  },
];

/* ─── Density Options ─── */

const DENSITY_OPTIONS: Array<{
  value: 'compact' | 'comfortable' | 'relaxed';
  label: string;
  description: string;
}> = [
  {
    value: 'compact',
    label: 'Compact',
    description: 'Less spacing',
  },
  {
    value: 'comfortable',
    label: 'Comfortable',
    description: 'Default spacing',
  },
  {
    value: 'relaxed',
    label: 'Relaxed',
    description: 'More breathing room',
  },
];

export function AppearanceTab({ preferences, onChange }: AppearanceTabProps) {
  const { theme, setTheme } = useTheme();

  // Map 'system' from useTheme to what our options expect
  const currentTheme = theme === 'light' || theme === 'dark' ? theme : 'system';

  const handleThemeChange = (value: 'light' | 'dark' | 'system') => {
    setTheme(value);
    onChange({ theme: value === 'system' ? 'auto' : value });
  };

  return (
    <div className="space-y-8">
      {/* Theme */}
      <SettingsGroup title="Theme" description="Choose your preferred color scheme">
        <SettingsCardGrid columns={3}>
          {THEME_OPTIONS.map((option) => (
            <SettingsCard
              key={option.value}
              active={currentTheme === option.value}
              onClick={() => handleThemeChange(option.value)}
              icon={option.icon}
              title={option.label}
              description={option.description}
            >
              {/* Color preview strip */}
              <div className="flex gap-1 mt-2">
                <div className={`h-2 flex-1 rounded-full ${option.preview.bg} border border-neutral-200 dark:border-neutral-700`} />
                <div className={`h-2 flex-1 rounded-full ${option.preview.fg}`} />
                <div className={`h-2 flex-1 rounded-full ${option.preview.accent}`} />
              </div>
            </SettingsCard>
          ))}
        </SettingsCardGrid>
      </SettingsGroup>

      {/* Font Size */}
      <SettingsGroup title="Font Size" description="Adjust text size across the interface" divider>
        <SettingsCardGrid columns={3}>
          {FONT_SIZE_OPTIONS.map((option) => (
            <SettingsCard
              key={option.value}
              active={(preferences.font_size || 'medium') === option.value}
              onClick={() => onChange({ font_size: option.value })}
              title={option.label}
              description={option.description}
            >
              {/* Size preview */}
              <p className={`${option.sampleClass} font-medium text-neutral-600 dark:text-neutral-300 mt-2`}>
                Aa
              </p>
            </SettingsCard>
          ))}
        </SettingsCardGrid>
      </SettingsGroup>

      {/* Density */}
      <SettingsGroup title="Density" description="Control spacing and padding throughout the UI" divider>
        <SettingsCardGrid columns={3}>
          {DENSITY_OPTIONS.map((option) => (
            <SettingsCard
              key={option.value}
              active={(preferences.density || 'comfortable') === option.value}
              onClick={() => onChange({ density: option.value })}
              title={option.label}
              description={option.description}
            >
              {/* Density visual: horizontal bars with different gaps */}
              <div className={`flex flex-col mt-2 ${
                option.value === 'compact' ? 'gap-0.5' : option.value === 'comfortable' ? 'gap-1' : 'gap-1.5'
              }`}>
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="h-1 rounded-full bg-neutral-300 dark:bg-neutral-600"
                    style={{ width: `${80 - i * 15}%` }}
                  />
                ))}
              </div>
            </SettingsCard>
          ))}
        </SettingsCardGrid>
      </SettingsGroup>
    </div>
  );
}
