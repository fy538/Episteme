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

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'profile', label: 'Profile', icon: '👤' },
  { id: 'workspace', label: 'Workspace', icon: '⚙️' },
  { id: 'ai', label: 'AI & Agents', icon: '🤖' },
  { id: 'appearance', label: 'Appearance', icon: '🎨' },
  { id: 'advanced', label: 'Advanced', icon: '🔧' },
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
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex overflow-hidden">
        {/* Left Sidebar - Tabs */}
        <div className="w-48 bg-neutral-50 border-r border-neutral-200 p-4">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4 px-2">
            Settings
          </h2>
          <nav className="space-y-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-white text-primary-700 shadow-sm'
                    : 'text-neutral-700 hover:bg-white/50'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Right Content Area */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-neutral-200">
            <h3 className="text-xl font-semibold text-neutral-900">
              {TABS.find(t => t.id === activeTab)?.label}
            </h3>
            <button
              onClick={onClose}
              className="text-neutral-400 hover:text-neutral-600 transition-colors"
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
          <div className="flex items-center justify-end gap-3 p-6 border-t border-neutral-200 bg-neutral-50">
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
