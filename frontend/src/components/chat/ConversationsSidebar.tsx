/**
 * Conversations sidebar - list, create, rename threads
 */

'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { ConversationsSkeleton } from '@/components/ui/skeleton';
import { NoConversationsEmpty, NoSearchResultsEmpty } from '@/components/ui/empty-state';
import { SettingsModal } from '@/components/settings/SettingsModal';
import { SwipeableItem } from '@/components/ui/swipeable-item';
import { KeyboardShortcut } from '@/components/ui/keyboard-shortcut';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { useKeyboardShortcut } from '@/components/ui/keyboard-shortcut';
import type { ChatThread } from '@/lib/types/chat';
import type { Project } from '@/lib/types/project';

export function ConversationsSidebar({
  projects,
  threads,
  selectedThreadId,
  isLoading,
  onSelect,
  onCreate,
  onRename,
  onDelete,
  onArchive,
  searchTerm,
  onSearchChange,
  showArchived,
  onToggleArchived,
}: {
  projects: Project[];
  threads: ChatThread[];
  selectedThreadId: string | null;
  isLoading?: boolean;
  onSelect: (threadId: string) => void;
  onCreate: () => void;
  onRename: (threadId: string, title: string) => Promise<void>;
  onDelete: (threadId: string) => Promise<void>;
  onArchive: (threadId: string, archived: boolean) => Promise<void>;
  searchTerm: string;
  onSearchChange: (value: string) => void;
  showArchived: boolean;
  onToggleArchived: () => void;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [titleDraft, setTitleDraft] = useState('');
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const prefersReducedMotion = useReducedMotion();

  // Keyboard shortcuts
  useKeyboardShortcut(['Cmd', 'N'], onCreate, { enabled: true });

  function startEditing(thread: ChatThread) {
    setEditingId(thread.id);
    setTitleDraft(thread.title || 'New Chat');
  }

  async function saveRename(threadId: string) {
    const trimmed = titleDraft.trim();
    if (!trimmed) return;
    await onRename(threadId, trimmed);
    setEditingId(null);
  }

  async function handleDelete(thread: ChatThread) {
    const ok = window.confirm(`Delete "${thread.title || 'New Chat'}"?`);
    if (!ok) return;
    await onDelete(thread.id);
  }

  async function handleArchive(thread: ChatThread) {
    await onArchive(thread.id, !thread.archived);
  }

  const noProjectTitle = 'No Project';
  const activeThreads = threads.filter(thread => !thread.archived);
  const archivedThreads = threads.filter(thread => thread.archived);

  const groupThreads = (list: ChatThread[]) => {
    const grouped: { label: string; items: ChatThread[] }[] = [];

    projects.forEach(project => {
      const items = list.filter(t => t.project === project.id);
      if (items.length > 0) {
        grouped.push({ label: project.title, items });
      }
    });

    const noProjectItems = list.filter(t => !t.project);
    if (noProjectItems.length > 0) {
      grouped.push({ label: noProjectTitle, items: noProjectItems });
    }

    return grouped;
  };

  const filteredThreads = threads.filter(thread =>
    (thread.title || 'New Chat').toLowerCase().includes(searchTerm.toLowerCase())
  );
  const filteredActiveThreads = filteredThreads.filter(t => !t.archived);
  const filteredArchivedThreads = filteredThreads.filter(t => t.archived);

  const activeGroups = groupThreads(filteredActiveThreads);
  const archivedGroups = groupThreads(filteredArchivedThreads);

  // Show skeleton during initial load
  if (isLoading) {
    return <ConversationsSkeleton />;
  }

  return (
    <div className="w-72 border-r border-neutral-200 dark:border-neutral-800 p-4 overflow-y-auto bg-neutral-50 dark:bg-primary-900">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Conversations</h2>
        <div className="flex items-center gap-2">
          <KeyboardShortcut keys={['⌘', 'N']} className="hidden lg:flex" />
          <Button size="sm" onClick={onCreate}>
            New
          </Button>
        </div>
      </div>

      <div className="mb-3 space-y-2">
        <Input
          value={searchTerm}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search conversations..."
          aria-label="Search conversations"
        />
        <Checkbox
          checked={showArchived}
          onChange={onToggleArchived}
          label="Show archived"
          className="text-xs"
        />
      </div>

      {threads.length === 0 && !searchTerm && (
        <NoConversationsEmpty onCreate={onCreate} />
      )}

      {threads.length > 0 && filteredThreads.length === 0 && searchTerm && (
        <NoSearchResultsEmpty query={searchTerm} />
      )}

      <div className="space-y-4">
        {activeGroups.map(group => (
          <div key={group.label}>
            <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
              {group.label}
            </h3>
            <AnimatePresence mode="popLayout">
              <div className="space-y-2">
                {group.items.map((thread, index) => {
                  const isSelected = thread.id === selectedThreadId;
                  const title = thread.title || 'New Chat';
                  const isEditing = editingId === thread.id;
                  const isArchived = !!thread.archived;

                  const conversationContent = (
                    <div
                      className={`rounded border px-3 py-2 text-sm ${
                        isSelected ? 'border-accent-500 bg-white' : 'border-transparent bg-white/60'
                      }`}
                    >
                    {isEditing ? (
                      <div className="space-y-2">
                        <Input
                          value={titleDraft}
                          onChange={e => setTitleDraft(e.target.value)}
                          aria-label="Rename conversation"
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
                      <div className="space-y-1">
                        <div className="flex items-center justify-between gap-2 group">
                          <button
                            onClick={() => onSelect(thread.id)}
                            className="text-left flex-1 truncate"
                            title={title}
                          >
                            {title}
                          </button>
                          <div className="relative opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setMenuOpenId(menuOpenId === thread.id ? null : thread.id);
                              }}
                              className="p-1 hover:bg-neutral-200 rounded"
                              aria-label="Options"
                            >
                              <svg className="w-4 h-4 text-neutral-600" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                              </svg>
                            </button>
                            {menuOpenId === thread.id && (
                              <div className="absolute right-0 mt-1 w-32 bg-white border border-neutral-200 rounded-md shadow-lg z-10">
                                <button
                                  onClick={() => { startEditing(thread); setMenuOpenId(null); }}
                                  className="w-full text-left px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-50 transition-colors"
                                >
                                  Rename
                                </button>
                                <button
                                  onClick={() => { handleArchive(thread); setMenuOpenId(null); }}
                                  className="w-full text-left px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-50 transition-colors"
                                >
                                  {isArchived ? 'Unarchive' : 'Archive'}
                                </button>
                                <button
                                  onClick={() => { handleDelete(thread); setMenuOpenId(null); }}
                                  className="w-full text-left px-3 py-2 text-sm text-error-600 hover:bg-error-50 transition-colors"
                                >
                                  Delete
                                </button>
                                {!thread.project && (
                                  <button
                                    onClick={() => { setMenuOpenId(null); }}
                                    className="w-full text-left px-3 py-2 text-sm text-accent-600 hover:bg-accent-50 transition-colors border-t border-neutral-100"
                                  >
                                    Link to Project →
                                  </button>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                        
                        {/* Project Badge */}
                        {thread.project && (
                          <div className="mt-1">
                            <Badge variant="neutral" className="text-xs">
                              {projects.find(p => p.id === thread.project)?.title || 'Project'}
                            </Badge>
                          </div>
                        )}
                      </div>
                    )}
                    </div>
                  );

                  // Wrap in swipeable container for mobile gestures
                  const content = (
                    <SwipeableItem
                      onSwipeLeft={() => handleDelete(thread)}
                      onSwipeRight={() => handleArchive(thread)}
                      rightAction={{
                        icon: (
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        ),
                        color: '#e11d48',
                        label: 'Delete',
                      }}
                      leftAction={{
                        icon: (
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                          </svg>
                        ),
                        color: '#0891b2',
                        label: isArchived ? 'Unarchive' : 'Archive',
                      }}
                    >
                      {conversationContent}
                    </SwipeableItem>
                  );

                  // Wrap in motion if animations are enabled
                  if (prefersReducedMotion) {
                    return <div key={thread.id}>{content}</div>;
                  }

                  return (
                    <motion.div
                      key={thread.id}
                      layout
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20, height: 0 }}
                      transition={{
                        duration: 0.2,
                        delay: index < 5 ? index * 0.03 : 0, // Stagger first 5
                        layout: { duration: 0.2 },
                      }}
                    >
                      {content}
                    </motion.div>
                  );
                })}
              </div>
            </AnimatePresence>
          </div>
        ))}
      </div>

      {showArchived && (
        <div className="mt-6">
          <h3 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
            Archived
          </h3>
          <div className="space-y-4">
            {archivedGroups.map(group => (
              <div key={group.label}>
                <h4 className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wide mb-2">
                  {group.label}
                </h4>
                <div className="space-y-2">
                  {group.items.map(thread => {
                    const isSelected = thread.id === selectedThreadId;
                    const title = thread.title || 'New Chat';
                    const isEditing = editingId === thread.id;

                    return (
                      <div
                        key={thread.id}
                        className={`rounded border px-3 py-2 text-sm ${
                          isSelected ? 'border-accent-500 bg-white' : 'border-transparent bg-white/60'
                        }`}
                      >
                        {isEditing ? (
                          <div className="space-y-2">
                            <Input
                              value={titleDraft}
                              onChange={e => setTitleDraft(e.target.value)}
                              aria-label="Rename conversation"
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
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => startEditing(thread)}
                                className="text-xs text-neutral-500 hover:text-neutral-800"
                                aria-label="Rename conversation"
                              >
                                Rename
                              </button>
                              <button
                                onClick={() => handleArchive(thread)}
                                className="text-xs text-neutral-500 hover:text-neutral-800"
                                aria-label="Unarchive conversation"
                              >
                                Unarchive
                              </button>
                              <button
                                onClick={() => handleDelete(thread)}
                                className="text-xs text-error-600 hover:text-error-800"
                                aria-label="Delete conversation"
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Settings Button - Bottom Left */}
      <div className="mt-auto pt-4 border-t border-neutral-200">
        <button
          onClick={() => setSettingsOpen(true)}
          className="w-full flex items-center gap-3 px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="font-medium">Settings</span>
        </button>
      </div>

      {/* Settings Modal */}
      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}
