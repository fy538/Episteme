/**
 * Command Palette - Cmd/Ctrl+K for quick actions and navigation
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import Fuse from 'fuse.js';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

export interface Command {
  id: string;
  label: string;
  category: 'navigation' | 'actions' | 'ai' | 'search';
  keywords: string[];
  action: () => void | Promise<void>;
  shortcut?: string;
  icon?: React.ReactNode;
}

interface CommandPaletteProps {
  commands: Command[];
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ commands, isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Fuzzy search
  const fuse = useRef(
    new Fuse(commands, {
      keys: ['label', 'keywords'],
      threshold: 0.3,
    })
  );

  const filteredCommands = query.trim()
    ? fuse.current.search(query).map((result) => result.item)
    : commands;

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, filteredCommands.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const cmd = filteredCommands[selectedIndex];
        if (cmd) {
          cmd.action();
          onClose();
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, filteredCommands, selectedIndex, onClose]);

  // Scroll selected item into view
  useEffect(() => {
    const element = document.querySelector(`[data-command-idx="${selectedIndex}"]`);
    element?.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center pt-[20vh]">
      {/* Backdrop click to close */}
      <div className="absolute inset-0" onClick={onClose} />

      {/* Palette */}
      <div className="relative bg-white rounded-lg shadow-2xl max-w-2xl w-full mx-4">
        {/* Search Input */}
        <div className="border-b border-neutral-200">
          <div className="flex items-center px-4 py-3">
            <svg className="w-5 h-5 text-neutral-400 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type a command or search..."
              className="flex-1 outline-none text-neutral-900 placeholder-neutral-400"
            />
            <kbd className="hidden sm:inline-block px-2 py-1 text-xs font-medium text-neutral-500 bg-neutral-100 rounded">
              ESC
            </kbd>
          </div>
        </div>

        {/* Results */}
        <div className="max-h-96 overflow-y-auto">
          {filteredCommands.length === 0 ? (
            <div className="px-4 py-8 text-center text-neutral-500">
              No commands found for "{query}"
            </div>
          ) : (
            <div className="py-2">
              {filteredCommands.map((cmd, idx) => (
                <Button
                  key={cmd.id}
                  variant="ghost"
                  data-command-idx={idx}
                  onClick={() => {
                    cmd.action();
                    onClose();
                  }}
                  className={`w-full px-4 py-3 h-auto flex items-center justify-between rounded-none transition-colors ${
                    idx === selectedIndex
                      ? 'bg-accent-50 text-accent-900'
                      : 'text-neutral-900 hover:bg-neutral-50'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {cmd.icon && <span className="text-neutral-500">{cmd.icon}</span>}
                    <div className="text-left">
                      <div className="font-medium">{cmd.label}</div>
                      <div className="text-xs text-neutral-500">{cmd.category}</div>
                    </div>
                  </div>
                  {cmd.shortcut && (
                    <kbd className="px-2 py-1 text-xs font-medium text-neutral-500 bg-neutral-100 rounded">
                      {cmd.shortcut}
                    </kbd>
                  )}
                </Button>
              ))}
            </div>
          )}
        </div>

        {/* Footer hint */}
        <div className="border-t border-neutral-200 px-4 py-2 text-xs text-neutral-500 flex items-center justify-between">
          <span>Navigate with ↑↓ arrows</span>
          <span>Press Enter to select</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Hook to manage command palette state with keyboard shortcut
 */
export function useCommandPalette() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Cmd+K or Ctrl+K — toggle (for keyboard users)
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
    }

    // Programmatic open via custom event (always opens, never toggles)
    function handleOpenCommand() {
      setIsOpen(true);
    }

    document.addEventListener('keydown', handleKeyDown);
    window.addEventListener('episteme:open-command-palette', handleOpenCommand);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('episteme:open-command-palette', handleOpenCommand);
    };
  }, []);

  return { isOpen, setIsOpen };
}
