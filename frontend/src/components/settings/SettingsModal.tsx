/**
 * App Settings Modal — User preferences
 *
 * Uses SettingsShell for consistent layout + Framer Motion transitions.
 * 5 tabs: Profile, Workspace, AI & Behavior, Appearance, Advanced
 */

'use client';

import * as React from 'react';
import { useUserPreferences, useUpdatePreferences } from '@/hooks/usePreferences';
import { SettingsShell, type SettingsTab } from './SettingsShell';
import { ProfileTab } from './tabs/ProfileTab';
import { WorkspaceTab } from './tabs/WorkspaceTab';
import { AITab } from './tabs/AITab';
import { AppearanceTab } from './tabs/AppearanceTab';
import { AdvancedTab } from './tabs/AdvancedTab';
import type { UserPreferences } from '@/lib/api/preferences';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const TABS: SettingsTab[] = [
  {
    id: 'profile',
    label: 'Profile',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    ),
  },
  {
    id: 'workspace',
    label: 'Workspace',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
    ),
  },
  {
    id: 'ai',
    label: 'AI & Behavior',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    id: 'appearance',
    label: 'Appearance',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
      </svg>
    ),
  },
  {
    id: 'advanced',
    label: 'Advanced',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
];

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [activeTab, setActiveTab] = React.useState('profile');
  const [userName, setUserName] = React.useState('');
  const [userEmail, setUserEmail] = React.useState('');

  const { data: preferences, isLoading } = useUserPreferences();
  const updatePreferences = useUpdatePreferences();

  const [localPreferences, setLocalPreferences] = React.useState<Partial<UserPreferences>>({});

  React.useEffect(() => {
    const savedName = localStorage.getItem('episteme_user_name');
    const savedEmail = localStorage.getItem('episteme_user_email');
    if (savedName) setUserName(savedName);
    if (savedEmail) setUserEmail(savedEmail);
  }, []);

  React.useEffect(() => {
    if (preferences) {
      setLocalPreferences(preferences);
    }
  }, [preferences]);

  const handlePreferenceChange = (updates: Partial<UserPreferences>) => {
    setLocalPreferences(prev => ({ ...prev, ...updates }));
  };

  const handleSave = async () => {
    localStorage.setItem('episteme_user_name', userName);
    localStorage.setItem('episteme_user_email', userEmail);

    try {
      await updatePreferences.mutateAsync(localPreferences);
      onClose();
    } catch (error) {
      console.error('Failed to save preferences:', error);
    }
  };

  const renderTabContent = () => {
    if (isLoading) {
      return (
        <div className="flex items-center gap-2 text-sm text-neutral-500 py-8">
          <span className="inline-flex gap-1">
            <span className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce [animation-delay:-0.2s]" />
            <span className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce" />
            <span className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce [animation-delay:0.2s]" />
          </span>
          Loading preferences...
        </div>
      );
    }

    switch (activeTab) {
      case 'profile':
        return (
          <ProfileTab
            userName={userName}
            userEmail={userEmail}
            onUserNameChange={setUserName}
            onUserEmailChange={setUserEmail}
            preferences={localPreferences}
            onPreferenceChange={handlePreferenceChange}
          />
        );
      case 'workspace':
        return <WorkspaceTab preferences={localPreferences} onChange={handlePreferenceChange} />;
      case 'ai':
        return <AITab preferences={localPreferences} onChange={handlePreferenceChange} />;
      case 'appearance':
        return <AppearanceTab preferences={localPreferences} onChange={handlePreferenceChange} />;
      case 'advanced':
        return <AdvancedTab preferences={localPreferences} onChange={handlePreferenceChange} />;
      default:
        return null;
    }
  };

  return (
    <SettingsShell
      isOpen={isOpen}
      onClose={onClose}
      onSave={handleSave}
      isSaving={updatePreferences.isPending}
      title="Settings"
      tabs={TABS}
      activeTab={activeTab}
      onTabChange={setActiveTab}
    >
      {renderTabContent()}
    </SettingsShell>
  );
}
