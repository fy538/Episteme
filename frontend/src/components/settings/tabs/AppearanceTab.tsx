/**
 * Appearance Tab - Theme preferences
 */

'use client';

import * as React from 'react';
import { Label } from '@/components/ui/label';
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
        <Label className="text-base font-semibold text-neutral-900 dark:text-neutral-100">Theme</Label>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-3">
          Choose your preferred color scheme
        </p>
        <ThemeToggle />
      </div>
    </div>
  );
}
