/**
 * Profile Tab - User profile and notification settings
 */

'use client';

import * as React from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
  return (
    <div className="space-y-8">
      {/* Profile Section */}
      <section>
        <h3 className="text-base font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Profile</h3>
        <div className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="settings-name" className="text-neutral-900 dark:text-neutral-100">Name</Label>
            <Input
              id="settings-name"
              type="text"
              value={userName}
              onChange={(e) => onUserNameChange(e.target.value)}
              placeholder="Your name"
            />
          </div>

          <div className="space-y-1">
            <Label htmlFor="settings-email" className="text-neutral-900 dark:text-neutral-100">Email</Label>
            <Input
              id="settings-email"
              type="email"
              value={userEmail}
              onChange={(e) => onUserEmailChange(e.target.value)}
              placeholder="your.email@example.com"
            />
            <p className="text-xs text-neutral-500 dark:text-neutral-400">
              Used for notifications and account recovery
            </p>
          </div>
        </div>
      </section>

      {/* Notifications Section */}
      <section className="border-t border-neutral-200 dark:border-neutral-700 pt-6">
        <h3 className="text-base font-semibold text-neutral-900 dark:text-neutral-100 mb-1">Notifications</h3>
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
          Control what you get notified about
        </p>
        <div className="space-y-3">
          <label className="flex items-center gap-3 cursor-pointer p-3 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors">
            <input
              type="checkbox"
              checked={preferences.email_notifications ?? false}
              onChange={(e) => onPreferenceChange({ email_notifications: e.target.checked })}
              className="w-4 h-4 rounded border-neutral-300 dark:border-neutral-600 text-primary-600"
            />
            <div>
              <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                Email notifications
              </span>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                Receive updates via email
              </p>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer p-3 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors">
            <input
              type="checkbox"
              checked={preferences.notify_on_inquiry_resolved ?? true}
              onChange={(e) => onPreferenceChange({ notify_on_inquiry_resolved: e.target.checked })}
              className="w-4 h-4 rounded border-neutral-300 dark:border-neutral-600 text-primary-600"
            />
            <div>
              <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                Inquiry resolved
              </span>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                Notify when an inquiry reaches resolution
              </p>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer p-3 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors">
            <input
              type="checkbox"
              checked={preferences.notify_on_agent_complete ?? true}
              onChange={(e) => onPreferenceChange({ notify_on_agent_complete: e.target.checked })}
              className="w-4 h-4 rounded border-neutral-300 dark:border-neutral-600 text-primary-600"
            />
            <div>
              <span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                Agent completed
              </span>
              <p className="text-xs text-neutral-500 dark:text-neutral-400">
                Notify when a background agent finishes its task
              </p>
            </div>
          </label>
        </div>
      </section>
    </div>
  );
}
