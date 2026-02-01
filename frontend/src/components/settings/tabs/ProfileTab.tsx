/**
 * Profile Tab - User profile settings
 */

'use client';

import * as React from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import type { UserPreferences } from '@/lib/api/preferences';

interface ProfileTabProps {
  userName: string;
  userEmail: string;
  onUserNameChange: (value: string) => void;
  onUserEmailChange: (value: string) => void;
}

export function ProfileTab({
  userName,
  userEmail,
  onUserNameChange,
  onUserEmailChange,
}: ProfileTabProps) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-neutral-900 mb-4">Profile</h3>
        <div className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="settings-name">Name</Label>
            <Input
              id="settings-name"
              type="text"
              value={userName}
              onChange={(e) => onUserNameChange(e.target.value)}
              placeholder="Your name"
            />
          </div>
          
          <div className="space-y-1">
            <Label htmlFor="settings-email">Email</Label>
            <Input
              id="settings-email"
              type="email"
              value={userEmail}
              onChange={(e) => onUserEmailChange(e.target.value)}
              placeholder="your.email@example.com"
            />
            <p className="text-xs text-neutral-500">
              Used for notifications and account recovery
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
