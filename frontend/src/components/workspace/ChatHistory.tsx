/**
 * Chat History - displays all chat threads for a case
 * Used in the "Chats" tab of the case workspace
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import type { ChatThread } from '@/lib/types/chat';

interface ChatHistoryProps {
  caseId: string;
  threads: ChatThread[];
  currentThreadId?: string;
  onSelectThread: (threadId: string) => void;
  onNewThread: (threadType?: string) => void;
  onDeleteThread?: (threadId: string) => void;
  onRenameThread?: (threadId: string, newTitle: string) => void;
}

export function ChatHistory({
  caseId,
  threads,
  currentThreadId,
  onSelectThread,
  onNewThread,
  onDeleteThread,
  onRenameThread,
}: ChatHistoryProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const filteredThreads = threads.filter(thread =>
    thread.title?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const threadTypes = [
    { value: 'general', label: 'General Discussion', icon: '💬', color: 'blue' },
    { value: 'research', label: 'Research Thread', icon: '🔬', color: 'purple' },
    { value: 'inquiry', label: 'Inquiry-Specific', icon: '❓', color: 'orange' },
    { value: 'document', label: 'Document Analysis', icon: '📄', color: 'green' },
  ];

  const getThreadTypeInfo = (type: string) => {
    return threadTypes.find(t => t.value === type) || threadTypes[0];
  };

  const handleStartEdit = (thread: ChatThread) => {
    setEditingThreadId(thread.id);
    setEditTitle(thread.title || '');
  };

  const handleSaveEdit = (threadId: string) => {
    if (onRenameThread && editTitle.trim()) {
      onRenameThread(threadId, editTitle.trim());
    }
    setEditingThreadId(null);
  };

  const handleCancelEdit = () => {
    setEditingThreadId(null);
    setEditTitle('');
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="p-6 border-b border-neutral-200">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl tracking-tight font-bold text-neutral-900">Chat Threads</h2>
          <Button onClick={() => onNewThread()}>
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Thread
          </Button>
        </div>

        {/* Search */}
        <Input
          type="text"
          placeholder="Search threads..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full"
        />
      </div>

      {/* Thread List */}
      <div className="flex-1 overflow-y-auto p-6">
        {filteredThreads.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-neutral-400 mb-4">
              <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <p className="text-neutral-600 mb-4">
              {searchTerm ? 'No threads found' : 'No chat threads yet'}
            </p>
            <Button onClick={() => onNewThread()}>
              Start Your First Thread
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredThreads.map(thread => {
              const typeInfo = getThreadTypeInfo(thread.thread_type || 'general');
              const isEditing = editingThreadId === thread.id;
              const isCurrent = currentThreadId === thread.id;

              return (
                <div
                  key={thread.id}
                  className={cn(
                    'p-4 rounded-lg border-2 transition-all',
                    isCurrent
                      ? 'border-accent-500 bg-accent-50'
                      : 'border-neutral-200 hover:border-neutral-300 bg-white'
                  )}
                >
                  <div className="flex items-start gap-3">
                    {/* Icon */}
                    <div className="text-2xl flex-shrink-0">
                      {typeInfo.icon}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      {isEditing ? (
                        <div className="flex gap-2">
                          <Input
                            type="text"
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') handleSaveEdit(thread.id);
                              if (e.key === 'Escape') handleCancelEdit();
                            }}
                            autoFocus
                            className="flex-1"
                          />
                          <Button
                            size="sm"
                            onClick={() => handleSaveEdit(thread.id)}
                          >
                            Save
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={handleCancelEdit}
                          >
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-neutral-900 truncate">
                              {thread.title || 'Untitled Chat'}
                            </h3>
                            {isCurrent && (
                              <span className="text-xs px-2 py-0.5 bg-accent-600 text-white rounded">
                                Active
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-3 mt-1">
                            <span className={cn(
                              'text-xs px-2 py-0.5 rounded',
                              `bg-${typeInfo.color}-100 text-${typeInfo.color}-700`
                            )}>
                              {typeInfo.label}
                            </span>
                            <span className="text-xs text-neutral-500">
                              {thread.message_count || 0} messages
                            </span>
                            <span className="text-xs text-neutral-400">
                              {new Date(thread.updated_at).toLocaleDateString()}
                            </span>
                          </div>
                        </>
                      )}
                    </div>

                    {/* Actions */}
                    {!isEditing && (
                      <div className="flex items-center gap-1 flex-shrink-0">
                        {!isCurrent && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => onSelectThread(thread.id)}
                            className="text-accent-600 hover:text-accent-700"
                          >
                            Open
                          </Button>
                        )}
                        {onRenameThread && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleStartEdit(thread)}
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </Button>
                        )}
                        {onDeleteThread && !isCurrent && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              if (confirm('Delete this thread? This cannot be undone.')) {
                                onDeleteThread(thread.id);
                              }
                            }}
                            className="text-error-600 hover:text-error-700"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </Button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Quick Create Buttons */}
      <div className="p-6 border-t border-neutral-200 bg-neutral-50">
        <p className="text-sm text-neutral-600 mb-3">Quick create:</p>
        <div className="grid grid-cols-2 gap-2">
          {threadTypes.map(type => (
            <button
              key={type.value}
              onClick={() => onNewThread(type.value)}
              className="flex items-center gap-2 px-4 py-3 text-sm rounded-lg border border-neutral-200 hover:border-accent-500 hover:bg-white transition-colors"
            >
              <span className="text-xl">{type.icon}</span>
              <span>{type.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
