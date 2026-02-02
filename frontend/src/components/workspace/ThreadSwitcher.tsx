/**
 * Thread Switcher - switches between multiple chat threads for a case
 * Shows in the ChatPanel header
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { ChatThread } from '@/lib/types/chat';

interface ThreadSwitcherProps {
  caseId: string;
  threads: ChatThread[];
  currentThreadId: string;
  onSwitchThread: (threadId: string) => void;
  onNewThread: (threadType?: string) => void;
}

export function ThreadSwitcher({
  caseId,
  threads,
  currentThreadId,
  onSwitchThread,
  onNewThread,
}: ThreadSwitcherProps) {
  const [isOpen, setIsOpen] = useState(false);

  const currentThread = threads.find(t => t.id === currentThreadId);

  const threadTypes = [
    { value: 'general', label: 'General', icon: '💬' },
    { value: 'research', label: 'Research', icon: '🔬' },
    { value: 'inquiry', label: 'Inquiry', icon: '❓' },
    { value: 'document', label: 'Document', icon: '📄' },
  ];

  const getThreadTypeIcon = (type: string) => {
    return threadTypes.find(t => t.value === type)?.icon || '💬';
  };

  if (!isOpen) {
    return (
      <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-200">
        <button
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2 text-sm font-medium text-neutral-900 hover:text-accent-600 transition-colors"
        >
          <span>{getThreadTypeIcon(currentThread?.thread_type || 'general')}</span>
          <span className="truncate max-w-[180px]">
            {currentThread?.title || 'Chat'}
          </span>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onNewThread()}
          className="text-accent-600 hover:text-accent-700"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </Button>
      </div>
    );
  }

  return (
    <div className="border-b border-neutral-200 bg-white">
      <div className="px-4 py-2">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-neutral-900">Chat Threads</h3>
          <button
            onClick={() => setIsOpen(false)}
            className="text-neutral-400 hover:text-neutral-600"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="max-h-64 overflow-y-auto space-y-1">
          {threads.map(thread => (
            <button
              key={thread.id}
              onClick={() => {
                onSwitchThread(thread.id);
                setIsOpen(false);
              }}
              className={cn(
                'w-full text-left px-3 py-2 rounded-lg transition-colors',
                thread.id === currentThreadId
                  ? 'bg-accent-50 text-accent-900'
                  : 'hover:bg-neutral-50 text-neutral-700'
              )}
            >
              <div className="flex items-start gap-2">
                <span className="text-lg flex-shrink-0">
                  {getThreadTypeIcon(thread.thread_type || 'general')}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">
                    {thread.title || 'Untitled Chat'}
                  </p>
                  <p className="text-xs text-neutral-500">
                    {thread.message_count || 0} messages
                  </p>
                </div>
                {thread.id === currentThreadId && (
                  <svg className="w-4 h-4 text-accent-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>
            </button>
          ))}
        </div>

        <div className="mt-3 pt-3 border-t border-neutral-200">
          <p className="text-xs text-neutral-500 mb-2">Create new thread:</p>
          <div className="grid grid-cols-2 gap-2">
            {threadTypes.map(type => (
              <button
                key={type.value}
                onClick={() => {
                  onNewThread(type.value);
                  setIsOpen(false);
                }}
                className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-neutral-200 hover:border-accent-500 hover:bg-accent-50 transition-colors"
              >
                <span>{type.icon}</span>
                <span>{type.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
