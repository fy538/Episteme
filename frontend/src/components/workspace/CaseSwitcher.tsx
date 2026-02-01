/**
 * Case Switcher - quick navigation between cases
 * Similar to Cursor's file switcher
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import type { Case } from '@/lib/types/case';

interface CaseSwitcherProps {
  cases: Case[];
  currentCaseId?: string;
  onCaseSelect?: (caseId: string) => void;
}

export function CaseSwitcher({ cases, currentCaseId, onCaseSelect }: CaseSwitcherProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  // Filter cases by search
  const filteredCases = search.trim()
    ? cases.filter(c =>
        c.title.toLowerCase().includes(search.toLowerCase())
      )
    : cases;

  // Sort: current first, then by updated_at
  const sortedCases = [...filteredCases].sort((a, b) => {
    if (a.id === currentCaseId) return -1;
    if (b.id === currentCaseId) return 1;
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
  });

  // Keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Cmd/Ctrl+P to open
      if ((e.metaKey || e.ctrlKey) && e.key === 'p') {
        e.preventDefault();
        setIsOpen(true);
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
      setSearch('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Arrow key navigation
  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => Math.min(prev + 1, sortedCases.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const selectedCase = sortedCases[selectedIndex];
        if (selectedCase) {
          handleSelectCase(selectedCase.id);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        setIsOpen(false);
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, sortedCases, selectedIndex]);

  function handleSelectCase(caseId: string) {
    if (onCaseSelect) {
      onCaseSelect(caseId);
    } else {
      router.push(`/workspace/cases/${caseId}`);
    }
    setIsOpen(false);
  }

  const currentCase = cases.find(c => c.id === currentCaseId);

  return (
    <>
      {/* Trigger Button */}
      <Button
        variant="outline"
        size="sm"
        onClick={() => setIsOpen(true)}
        className="min-w-[200px] justify-between"
      >
        <span className="truncate">
          {currentCase ? currentCase.title : 'Select Case'}
        </span>
        <div className="flex items-center gap-1 text-neutral-500">
          <kbd className="px-1.5 py-0.5 text-xs bg-neutral-100 rounded">⌘</kbd>
          <kbd className="px-1.5 py-0.5 text-xs bg-neutral-100 rounded">P</kbd>
        </div>
      </Button>

      {/* Modal */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-50 flex items-start justify-center pt-[20vh]"
          onClick={() => setIsOpen(false)}
        >
          <div
            className="bg-white rounded-lg shadow-2xl w-full max-w-2xl mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Search Input */}
            <div className="p-4 border-b border-neutral-200">
              <Input
                ref={inputRef}
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search cases..."
                aria-label="Search cases"
              />
            </div>

            {/* Cases List */}
            <div className="max-h-[400px] overflow-y-auto py-2">
              {sortedCases.length === 0 ? (
                <div className="py-8 text-center text-neutral-500 text-sm">
                  No cases found
                </div>
              ) : (
                sortedCases.map((caseItem, index) => (
                  <button
                    key={caseItem.id}
                    onClick={() => handleSelectCase(caseItem.id)}
                    className={cn(
                      'w-full px-4 py-3 flex items-center justify-between transition-colors',
                      index === selectedIndex
                        ? 'bg-accent-50 text-accent-900'
                        : 'text-neutral-900 hover:bg-neutral-50'
                    )}
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className="text-left flex-1 min-w-0">
                        <div className="font-medium truncate">{caseItem.title}</div>
                        <div className="text-xs text-neutral-500 flex items-center gap-2 mt-1">
                          <span className={cn(
                            'px-1.5 py-0.5 rounded text-xs',
                            caseItem.status === 'active' && 'bg-success-100 text-success-700',
                            caseItem.status === 'draft' && 'bg-warning-100 text-warning-700',
                            caseItem.status === 'archived' && 'bg-neutral-100 text-neutral-700'
                          )}>
                            {caseItem.status}
                          </span>
                          {caseItem.id === currentCaseId && (
                            <span className="text-accent-600 font-medium">• Current</span>
                          )}
                        </div>
                      </div>
                    </div>

                    <svg className="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                ))
              )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-neutral-200 bg-neutral-50 text-xs text-neutral-600 flex items-center justify-between">
              <span>Use ↑↓ to navigate, Enter to select, Esc to close</span>
              <span className="text-neutral-500">{sortedCases.length} cases</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
