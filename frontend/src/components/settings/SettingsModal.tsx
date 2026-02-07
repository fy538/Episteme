/**
 * Enhanced Settings Modal with tabs and backend persistence
 * 
 * Organized into: Profile, Workspace, AI & Agents, Appearance, Advanced
 * Skills positioned in Advanced (collapsed, optional)
 */

'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { useUserPreferences, useUpdatePreferences } from '@/hooks/usePreferences';
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

type TabId = 'profile' | 'workspace' | 'ai' | 'appearance' | 'advanced';

// SVG icons for tabs
const TabIcons: Record<TabId, React.ReactNode> = {
  profile: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
  ),
  workspace: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
    </svg>
  ),
  ai: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  ),
  appearance: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
    </svg>
  ),
  advanced: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
};

const TABS: { id: TabId; label: string }[] = [
  { id: 'profile', label: 'Profile' },
  { id: 'workspace', label: 'Workspace' },
  { id: 'ai', label: 'AI & Behavior' },
  { id: 'appearance', label: 'Appearance' },
  { id: 'advanced', label: 'Advanced' },
];

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [activeTab, setActiveTab] = React.useState<TabId>('profile');
  const [userName, setUserName] = React.useState('');
  const [userEmail, setUserEmail] = React.useState('');
  
  // Fetch preferences from backend
  const { data: preferences, isLoading } = useUserPreferences();
  const updatePreferences = useUpdatePreferences();
  
  // Local state for preference changes (optimistic updates)
  const [localPreferences, setLocalPreferences] = React.useState<Partial<UserPreferences>>({});

  React.useEffect(() => {
    // Load from localStorage for backward compatibility
    const savedName = localStorage.getItem('episteme_user_name');
    const savedEmail = localStorage.getItem('episteme_user_email');
    
    if (savedName) setUserName(savedName);
    if (savedEmail) setUserEmail(savedEmail);
  }, []);

  React.useEffect(() => {
    // Initialize local preferences from backend
    if (preferences) {
      setLocalPreferences(preferences);
    }
  }, [preferences]);

  const handlePreferenceChange = (updates: Partial<UserPreferences>) => {
    setLocalPreferences(prev => ({ ...prev, ...updates }));
  };

  const handleSave = async () => {
    // Save user profile to localStorage (for now)
    localStorage.setItem('episteme_user_name', userName);
    localStorage.setItem('episteme_user_email', userEmail);
    
    // Save preferences to backend
    try {
      await updatePreferences.mutateAsync(localPreferences);
      onClose();
    } catch (error) {
      console.error('Failed to save preferences:', error);
      // TODO: Show error toast
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="bg-white dark:bg-neutral-900 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex overflow-hidden animate-scale-in">
        {/* Left Sidebar - Tabs */}
        <div className="w-48 bg-neutral-50 dark:bg-neutral-800 border-r border-neutral-200 dark:border-neutral-700 p-4">
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4 px-2">
            Settings
          </h2>
          <nav className="space-y-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${
                  activeTab === tab.id
                    ? 'bg-white dark:bg-neutral-700 text-primary-700 dark:text-primary-300 shadow-sm'
                    : 'text-neutral-700 dark:text-neutral-300 hover:bg-white/50 dark:hover:bg-neutral-700/50'
                }`}
              >
                {TabIcons[tab.id]}
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Right Content Area */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-neutral-200 dark:border-neutral-700">
            <h3 className="text-xl font-display font-semibold tracking-tight text-neutral-900 dark:text-neutral-100">
              {TABS.find(t => t.id === activeTab)?.label}
            </h3>
            <button
              onClick={onClose}
              className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors"
              aria-label="Close"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {isLoading ? (
              <div className="flex items-center gap-2 text-sm text-neutral-600">
                <span className="inline-flex gap-1">
                  <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce [animation-delay:-0.2s]" />
                  <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" />
                  <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce [animation-delay:0.2s]" />
                </span>
                <span>Loading preferences...</span>
              </div>
            ) : (
              <>
                {activeTab === 'profile' && (
                  <ProfileTab
                    userName={userName}
                    userEmail={userEmail}
                    onUserNameChange={setUserName}
                    onUserEmailChange={setUserEmail}
                    preferences={localPreferences}
                    onPreferenceChange={handlePreferenceChange}
                  />
                )}
                
                {activeTab === 'workspace' && (
                  <WorkspaceTab
                    preferences={localPreferences}
                    onChange={handlePreferenceChange}
                  />
                )}
                
                {activeTab === 'ai' && (
                  <AITab
                    preferences={localPreferences}
                    onChange={handlePreferenceChange}
                  />
                )}
                
                {activeTab === 'appearance' && (
                  <AppearanceTab
                    preferences={localPreferences}
                    onChange={handlePreferenceChange}
                  />
                )}
                
                {activeTab === 'advanced' && (
                  <AdvancedTab
                    preferences={localPreferences}
                    onChange={handlePreferenceChange}
                  />
                )}
              </>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 p-6 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={updatePreferences.isPending}
            >
              {updatePreferences.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
