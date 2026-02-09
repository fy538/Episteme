/**
 * SpotlightSearch - Enhanced ⌘K with unified semantic search
 *
 * Features:
 * - Empty state: Recent items + Quick actions
 * - With query: Semantic search across all content
 * - Grouped results: "In this case" / "Other cases"
 * - Type filters via Tab key
 * - Rich result cards with metadata
 * - Keyboard navigation
 */

'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import {
  unifiedSearch,
  getResultTypeIcon,
  getResultTypeLabel,
  getResultPath,
  type SearchResult,
  type SearchResultType,
  type UnifiedSearchResponse,
} from '@/lib/api/search';

interface SpotlightSearchProps {
  isOpen: boolean;
  onClose: () => void;
  contextCaseId?: string;
  contextCaseName?: string;
}

const RESULT_TYPES: SearchResultType[] = ['inquiry', 'case', 'document'];

// Quick actions for empty state
interface QuickAction {
  id: string;
  label: string;
  icon: React.ReactNode;
  action: () => void;
  shortcut?: string;
}

export function SpotlightSearch({
  isOpen,
  onClose,
  contextCaseId,
  contextCaseName,
}: SpotlightSearchProps) {
  const router = useRouter();
  const pathname = usePathname();
  const inputRef = useRef<HTMLInputElement>(null);

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<UnifiedSearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [activeFilter, setActiveFilter] = useState<SearchResultType | 'all'>('all');

  // Debounce search
  const searchTimeoutRef = useRef<NodeJS.Timeout>();
  // Track if component is mounted to avoid state updates after unmount
  const isMountedRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
      setQuery('');
      setSelectedIndex(0);
      setActiveFilter('all');
      setError(null);
      // Load recent items
      performSearch('');
    }
  }, [isOpen]);

  // Perform search
  const performSearch = useCallback(async (searchQuery: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await unifiedSearch(
        searchQuery,
        { case_id: contextCaseId },
        {
          types: activeFilter === 'all' ? undefined : [activeFilter],
          top_k: 15,
        }
      );
      if (isMountedRef.current) {
        setResults(response);
        setSelectedIndex(0);
      }
    } catch (err) {
      console.error('Search failed:', err);
      if (isMountedRef.current) {
        setError('Search failed. Please try again.');
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [contextCaseId, activeFilter]);

  // Handle query change with debounce (300ms for better UX)
  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    // Longer debounce (300ms) reduces flicker while typing
    searchTimeoutRef.current = setTimeout(() => {
      performSearch(query);
    }, 300);

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [query, performSearch]);

  // Re-search when filter changes (no debounce needed)
  useEffect(() => {
    if (isOpen && query.trim()) {
      performSearch(query);
    }
  }, [activeFilter]);

  // Get all results flattened for keyboard navigation
  const getAllResults = useCallback((): (SearchResult | QuickAction)[] => {
    if (!results) return [];

    const items: (SearchResult | QuickAction)[] = [];

    // If no query, show recent items
    if (!query.trim()) {
      // Quick actions first
      items.push(...getQuickActions());
      // Then recent items
      items.push(...results.recent);
    } else {
      // In-context results first
      items.push(...results.in_context);
      // Then other results
      items.push(...results.other);
    }

    return items;
  }, [results, query]);

  const allItems = getAllResults();

  // Quick actions
  function getQuickActions(): QuickAction[] {
    return [
      {
        id: 'action-new-case',
        label: 'Create new case',
        icon: <PlusIcon />,
        action: () => {
          router.push('/cases?new=true');
          onClose();
        },
        shortcut: '⌘N',
      },
      {
        id: 'action-home',
        label: 'Go Home',
        icon: <GridIcon />,
        action: () => {
          router.push('/');
          onClose();
        },
      },
    ];
  }

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, allItems.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const item = allItems[selectedIndex];
        if (item) {
          handleSelect(item);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      } else if (e.key === 'Tab') {
        e.preventDefault();
        // Cycle through filters
        const currentIdx = activeFilter === 'all' ? -1 : RESULT_TYPES.indexOf(activeFilter);
        const nextIdx = (currentIdx + 1) % (RESULT_TYPES.length + 1);
        setActiveFilter(nextIdx === RESULT_TYPES.length ? 'all' : RESULT_TYPES[nextIdx]);
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, allItems, selectedIndex, activeFilter, onClose]);

  // Handle item selection
  function handleSelect(item: SearchResult | QuickAction) {
    if ('action' in item) {
      // Quick action
      item.action();
    } else {
      // Search result - navigate
      const path = getResultPath(item);
      router.push(path);
      onClose();
    }
  }

  // Scroll selected item into view
  useEffect(() => {
    const element = document.querySelector(`[data-spotlight-idx="${selectedIndex}"]`);
    element?.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 dark:bg-black/70 z-50 flex items-start justify-center pt-[15vh] animate-fade-in">
      {/* Backdrop */}
      <div className="absolute inset-0" onClick={onClose} />

      {/* Spotlight Panel */}
      <div className="relative bg-white dark:bg-neutral-900 rounded-xl shadow-2xl max-w-2xl w-full mx-4 overflow-hidden border border-neutral-200 dark:border-neutral-700 animate-scale-in">
        {/* Search Input */}
        <div className="border-b border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center px-4 py-3 gap-3">
            <SearchIcon className="w-5 h-5 text-neutral-400" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={contextCaseName ? `Search in "${contextCaseName}" or everywhere...` : 'Search everything...'}
              className="flex-1 outline-none text-neutral-900 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-500 bg-transparent"
            />
            {isLoading && (
              <div className="w-4 h-4 border-2 border-neutral-300 border-t-accent-500 rounded-full animate-spin" />
            )}
            <kbd className="hidden sm:inline-block px-2 py-1 text-xs font-medium text-neutral-500 bg-neutral-100 dark:bg-neutral-800 rounded">
              ESC
            </kbd>
          </div>

          {/* Type Filters */}
          <div className="flex items-center gap-1 px-4 pb-2 overflow-x-auto">
            <FilterPill
              active={activeFilter === 'all'}
              onClick={() => setActiveFilter('all')}
            >
              All
            </FilterPill>
            {RESULT_TYPES.map((type) => (
              <FilterPill
                key={type}
                active={activeFilter === type}
                onClick={() => setActiveFilter(type)}
              >
                {getResultTypeIcon(type)} {getResultTypeLabel(type)}
              </FilterPill>
            ))}
            <span className="text-xs text-neutral-400 ml-2">Tab ↹</span>
          </div>
        </div>

        {/* Results */}
        <div className="max-h-[60vh] overflow-y-auto">
          {/* Loading Skeletons - show while searching with query */}
          {isLoading && query.trim() ? (
            <div className="py-2">
              <div className="px-4 py-2">
                <div className="h-3 w-20 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse" />
              </div>
              {[...Array(4)].map((_, idx) => (
                <SearchResultSkeleton key={idx} />
              ))}
            </div>
          ) : !query.trim() ? (
            // Empty state - Recent + Quick actions
            <div className="py-2">
              {/* Quick Actions */}
              <div className="px-4 py-2">
                <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                  Quick Actions
                </span>
              </div>
              {getQuickActions().map((action, idx) => (
                <ResultRow
                  key={action.id}
                  index={idx}
                  isSelected={selectedIndex === idx}
                  onClick={() => handleSelect(action)}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-neutral-500 dark:text-neutral-400">{action.icon}</span>
                    <span className="font-medium text-neutral-900 dark:text-neutral-100">{action.label}</span>
                  </div>
                  {action.shortcut && (
                    <kbd className="px-2 py-0.5 text-xs text-neutral-500 bg-neutral-100 dark:bg-neutral-800 rounded">
                      {action.shortcut}
                    </kbd>
                  )}
                </ResultRow>
              ))}

              {/* Recent Items */}
              {results && results.recent.length > 0 && (
                <>
                  <div className="px-4 py-2 mt-2">
                    <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                      Recent
                    </span>
                  </div>
                  {results.recent.map((result, idx) => {
                    const itemIdx = getQuickActions().length + idx;
                    return (
                      <SearchResultRow
                        key={result.id}
                        result={result}
                        index={itemIdx}
                        isSelected={selectedIndex === itemIdx}
                        onClick={() => handleSelect(result)}
                      />
                    );
                  })}
                </>
              )}
            </div>
          ) : results && (results.in_context.length > 0 || results.other.length > 0) ? (
            // Search results
            <div className="py-2">
              {/* In-context results */}
              {results.in_context.length > 0 && (
                <>
                  <div className="px-4 py-2">
                    <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                      {contextCaseName ? `In "${contextCaseName}"` : 'In This Context'}
                    </span>
                  </div>
                  {results.in_context.map((result, idx) => (
                    <SearchResultRow
                      key={result.id}
                      result={result}
                      index={idx}
                      isSelected={selectedIndex === idx}
                      onClick={() => handleSelect(result)}
                      showCase={false}
                    />
                  ))}
                </>
              )}

              {/* Other results */}
              {results.other.length > 0 && (
                <>
                  <div className="px-4 py-2 mt-2">
                    <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                      Other Cases
                    </span>
                  </div>
                  {results.other.map((result, idx) => {
                    const itemIdx = results.in_context.length + idx;
                    return (
                      <SearchResultRow
                        key={result.id}
                        result={result}
                        index={itemIdx}
                        isSelected={selectedIndex === itemIdx}
                        onClick={() => handleSelect(result)}
                        showCase={true}
                      />
                    );
                  })}
                </>
              )}
            </div>
          ) : error ? (
            // Error state
            <div className="px-4 py-12 text-center">
              <p className="text-error-600 dark:text-error-400">
                {error}
              </p>
              <button
                onClick={() => performSearch(query)}
                className="mt-2 text-sm text-accent-600 hover:text-accent-700 dark:text-accent-400"
              >
                Try again
              </button>
            </div>
          ) : query.trim() && !isLoading ? (
            // No results
            <div className="px-4 py-12 text-center">
              <p className="text-neutral-500 dark:text-neutral-400">
                No results found for "{query}"
              </p>
              <p className="text-sm text-neutral-400 dark:text-neutral-500 mt-1">
                Try different keywords or check your filters
              </p>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="border-t border-neutral-200 dark:border-neutral-700 px-4 py-2 text-xs text-neutral-500 dark:text-neutral-400 flex items-center justify-between bg-neutral-50 dark:bg-neutral-800/50">
          <span>↑↓ Navigate · ⏎ Select · Tab Filter</span>
          {results && results.total_count > 0 && (
            <span>{results.total_count} results</span>
          )}
        </div>
      </div>
    </div>
  );
}

// Helper Components

interface ResultRowProps {
  index: number;
  isSelected: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

function ResultRow({ index, isSelected, onClick, children }: ResultRowProps) {
  return (
    <button
      data-spotlight-idx={index}
      onClick={onClick}
      className={`w-full px-4 py-2.5 flex items-center justify-between transition-colors ${
        isSelected
          ? 'bg-accent-50 dark:bg-accent-900/30'
          : 'hover:bg-neutral-50 dark:hover:bg-neutral-800'
      }`}
    >
      {children}
    </button>
  );
}

interface SearchResultRowProps {
  result: SearchResult;
  index: number;
  isSelected: boolean;
  onClick: () => void;
  showCase?: boolean;
}

function SearchResultRow({ result, index, isSelected, onClick, showCase = true }: SearchResultRowProps) {
  const icon = getResultTypeIcon(result.type);
  const typeLabel = getResultTypeLabel(result.type);

  return (
    <button
      data-spotlight-idx={index}
      onClick={onClick}
      className={`w-full px-4 py-2.5 flex items-start gap-3 text-left transition-colors ${
        isSelected
          ? 'bg-accent-50 dark:bg-accent-900/30'
          : 'hover:bg-neutral-50 dark:hover:bg-neutral-800'
      }`}
    >
      {/* Icon */}
      <span className="text-lg flex-shrink-0 mt-0.5">{icon}</span>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-neutral-900 dark:text-neutral-100 truncate">
            {result.title}
          </span>
          <span className="text-xs px-1.5 py-0.5 bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 rounded flex-shrink-0">
            {typeLabel}
          </span>
        </div>
        <div className="text-sm text-neutral-500 dark:text-neutral-400 truncate mt-0.5">
          {result.subtitle}
          {showCase && result.case_title && (
            <span className="ml-2 text-neutral-400 dark:text-neutral-500">
              · {result.case_title}
            </span>
          )}
        </div>
      </div>

      {/* Score indicator for high relevance */}
      {result.score >= 0.8 && (
        <span className="text-xs text-accent-600 dark:text-accent-400 flex-shrink-0">
          Best match
        </span>
      )}
    </button>
  );
}

function SearchResultSkeleton() {
  return (
    <div className="w-full px-4 py-2.5 flex items-start gap-3">
      {/* Icon skeleton */}
      <div className="w-5 h-5 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse flex-shrink-0" />

      {/* Content skeleton */}
      <div className="flex-1 min-w-0 space-y-2">
        <div className="flex items-center gap-2">
          <div className="h-4 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse w-3/4" />
          <div className="h-4 w-12 bg-neutral-200 dark:bg-neutral-700 rounded animate-pulse flex-shrink-0" />
        </div>
        <div className="h-3 bg-neutral-100 dark:bg-neutral-800 rounded animate-pulse w-1/2" />
      </div>
    </div>
  );
}

interface FilterPillProps {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

function FilterPill({ active, onClick, children }: FilterPillProps) {
  return (
    <button
      onClick={onClick}
      className={`px-2.5 py-1 text-xs rounded-full whitespace-nowrap transition-colors ${
        active
          ? 'bg-accent-100 dark:bg-accent-900/50 text-accent-700 dark:text-accent-300 font-medium'
          : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'
      }`}
    >
      {children}
    </button>
  );
}

// Icons

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
  );
}

function GridIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
    </svg>
  );
}
