/**
 * Profile Tab — User profile and notification preferences
 *
 * Uses SettingsGroup + SettingsRow for consistent layout.
 * Switch component for animated toggles.
 */

'use client';

import * as React from 'react';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { SettingsGroup, SettingsRow } from '../SettingsSection';
import type { UserPreferences } from '@/lib/api/preferences';

interface ProfileTabProps {
  userName: string;
  userEmail: string;
  onUserNameChange: (value: string) => void;
  onUserEmailChange: (value: string) => void;
  preferences?: Partial<UserPreferences>;
  onPreferenceChange?: (updates: Partial<UserPreferences>) => void;
}

export function ProfileTab({
  userName,
  userEmail,
  onUserNameChange,
  onUserEmailChange,
  preferences = {},
  onPreferenceChange = () => {},
}: ProfileTabProps) {
  // Generate initials for avatar
  const initials = userName
    ? userName
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : '?';

  return (
    <div className="space-y-8">
      {/* Profile Section */}
      <SettingsGroup title="Profile" description="Your personal information">
        {/* Avatar + Name row */}
        <div className="flex items-center gap-4 py-3 px-4 -mx-4">
          <div className="flex-shrink-0 w-14 h-14 rounded-full bg-gradient-to-br from-accent-500 to-accent-700 flex items-center justify-center text-white font-semibold text-lg shadow-md">
            {initials}
          </div>
          <div className="flex-1 min-w-0 space-y-3">
            <div>
              <label htmlFor="settings-name" className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">
                Name
              </label>
              <Input
                id="settings-name"
                type="text"
                value={userName}
                onChange={(e) => onUserNameChange(e.target.value)}
                placeholder="Your name"
                className="mt-1"
              />
            </div>
            <div>
              <label htmlFor="settings-email" className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">
                Email
              </label>
              <Input
                id="settings-email"
                type="email"
                value={userEmail}
                onChange={(e) => onUserEmailChange(e.target.value)}
                placeholder="your.email@example.com"
                className="mt-1"
              />
              <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                Used for notifications and account recovery
              </p>
            </div>
          </div>
        </div>
      </SettingsGroup>

      {/* Notifications Section */}
      <SettingsGroup title="Notifications" description="Control what you get notified about" divider>
        <SettingsRow
          label="Email notifications"
          description="Receive updates via email"
        >
          <Switch
            checked={preferences.email_notifications ?? false}
            onCheckedChange={(checked) => onPreferenceChange({ email_notifications: checked })}
          />
        </SettingsRow>

        <SettingsRow
          label="Inquiry resolved"
          description="Notify when an inquiry reaches resolution"
        >
          <Switch
            checked={preferences.notify_on_inquiry_resolved ?? true}
            onCheckedChange={(checked) => onPreferenceChange({ notify_on_inquiry_resolved: checked })}
          />
        </SettingsRow>

        <SettingsRow
          label="Agent completed"
          description="Notify when a background agent finishes its task"
        >
          <Switch
            checked={preferences.notify_on_agent_complete ?? true}
            onCheckedChange={(checked) => onPreferenceChange({ notify_on_agent_complete: checked })}
          />
        </SettingsRow>
      </SettingsGroup>
    </div>
  );
}
