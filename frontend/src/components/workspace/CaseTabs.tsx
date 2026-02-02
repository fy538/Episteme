/**
 * Tab interface for case workspace
 * 
 * Provides navigation between Brief, Inquiries, Documents, and Chats views
 */

'use client';

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { cn } from '@/lib/utils';

type TabId = 'brief' | 'inquiries' | 'documents' | 'chats';

interface Tab {
  id: TabId;
  label: string;
  icon: React.ReactNode;
  count?: number;
}

interface CaseTabsProps {
  caseId: string;
  activeTab?: TabId;
  counts?: {
    inquiries?: number;
    documents?: number;
    chats?: number;
  };
}

export function CaseTabs({ caseId, activeTab = 'brief', counts }: CaseTabsProps) {
  const router = useRouter();

  const tabs: Tab[] = [
    {
      id: 'brief',
      label: 'Brief',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
    },
    {
      id: 'inquiries',
      label: 'Inquiries',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      count: counts?.inquiries,
    },
    {
      id: 'documents',
      label: 'Documents',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
      ),
      count: counts?.documents,
    },
    {
      id: 'chats',
      label: 'Chats',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      ),
      count: counts?.chats,
    },
  ];

  const handleTabClick = (tabId: TabId) => {
    router.push(`/workspace/cases/${caseId}?tab=${tabId}`);
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey) {
        switch (e.key) {
          case '1':
            e.preventDefault();
            handleTabClick('brief');
            break;
          case '2':
            e.preventDefault();
            handleTabClick('inquiries');
            break;
          case '3':
            e.preventDefault();
            handleTabClick('documents');
            break;
          case '4':
            e.preventDefault();
            handleTabClick('chats');
            break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [caseId]);

  return (
    <div className="border-b border-neutral-200 bg-white">
      <nav className="flex space-x-1 px-6" aria-label="Tabs">
        {tabs.map((tab, index) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => handleTabClick(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                isActive
                  ? 'border-accent-600 text-accent-600'
                  : 'border-transparent text-neutral-600 hover:text-neutral-900 hover:border-neutral-300'
              )}
              aria-current={isActive ? 'page' : undefined}
            >
              {tab.icon}
              <span>{tab.label}</span>
              {tab.count !== undefined && tab.count > 0 && (
                <span
                  className={cn(
                    'ml-1 rounded-full px-2 py-0.5 text-xs font-medium',
                    isActive
                      ? 'bg-accent-100 text-accent-700'
                      : 'bg-neutral-100 text-neutral-600'
                  )}
                >
                  {tab.count}
                </span>
              )}
              {/* Keyboard shortcut hint */}
              <span className="hidden lg:block ml-1 text-xs text-neutral-400">
                ⌘{index + 1}
              </span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}

// Hook to use tab state
export function useActiveTab(): TabId {
  const searchParams = useSearchParams();
  const tab = searchParams?.get('tab') as TabId;
  return tab || 'brief';
}
