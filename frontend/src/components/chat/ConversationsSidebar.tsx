/**
 * Conversations sidebar - list, create, rename threads
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import type { ChatThread } from '@/lib/types/chat';

export function ConversationsSidebar({
  threads,
  selectedThreadId,
  isLoading,
  onSelect,
  onCreate,
  onRename,
}: {
  threads: ChatThread[];
  selectedThreadId: string | null;
  isLoading?: boolean;
  onSelect: (threadId: string) => void;
  onCreate: () => void;
  onRename: (threadId: string, title: string) => Promise<void>;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [titleDraft, setTitleDraft] = useState('');

  function startEditing(thread: ChatThread) {
    setEditingId(thread.id);
    setTitleDraft(thread.title || 'Untitled Conversation');
  }

  async function saveRename(threadId: string) {
    const trimmed = titleDraft.trim();
    if (!trimmed) return;
    await onRename(threadId, trimmed);
    setEditingId(null);
  }

  return (
    <div className="w-72 border-r border-gray-200 p-4 overflow-y-auto bg-gray-50">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Conversations</h2>
        <Button size="sm" onClick={onCreate}>
          New
        </Button>
      </div>

      {isLoading && (
        <p className="text-sm text-gray-500">Loading...</p>
      )}

      {!isLoading && threads.length === 0 && (
        <p className="text-sm text-gray-500">No conversations yet.</p>
      )}

      <div className="space-y-2">
        {threads.map(thread => {
          const isSelected = thread.id === selectedThreadId;
          const title = thread.title || 'Untitled Conversation';
          const isEditing = editingId === thread.id;

          return (
            <div
              key={thread.id}
              className={`rounded border px-3 py-2 text-sm ${
                isSelected ? 'border-blue-500 bg-white' : 'border-transparent bg-white/60'
              }`}
            >
              {isEditing ? (
                <div className="space-y-2">
                  <input
                    value={titleDraft}
                    onChange={e => setTitleDraft(e.target.value)}
                    className="w-full px-2 py-1 border border-gray-300 rounded"
                  />
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => saveRename(thread.id)}>
                      Save
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setEditingId(null)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between gap-2">
                  <button
                    onClick={() => onSelect(thread.id)}
                    className="text-left flex-1"
                    title={title}
                  >
                    {title}
                  </button>
                  <button
                    onClick={() => startEditing(thread)}
                    className="text-xs text-gray-500 hover:text-gray-800"
                    aria-label="Rename conversation"
                  >
                    Rename
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
