/**
 * Keyboard Shortcut Components
 * Visual display of keyboard shortcuts
 */

'use client';

import { cn } from '@/lib/utils';

interface KeyboardShortcutProps {
  keys: string[];
  className?: string;
}

export function KeyboardShortcut({ keys, className }: KeyboardShortcutProps) {
  return (
    <div className={cn('inline-flex items-center gap-1', className)}>
      {keys.map((key, index) => (
        <kbd
          key={index}
          className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 font-mono text-xs font-semibold text-neutral-700 dark:text-neutral-300 bg-neutral-100 dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-700 rounded shadow-sm"
        >
          {key}
        </kbd>
      ))}
    </div>
  );
}

// Hook for registering keyboard shortcuts
import { useEffect } from 'react';

export function useKeyboardShortcut(
  keys: string[],
  callback: () => void,
  options: {
    enabled?: boolean;
    preventDefault?: boolean;
  } = {}
) {
  const { enabled = true, preventDefault = true } = options;

  useEffect(() => {
    if (!enabled) return;

    function handleKeyDown(event: KeyboardEvent) {
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
      const modKey = isMac ? event.metaKey : event.ctrlKey;

      // Parse shortcut (e.g., ["Cmd", "K"] or ["Cmd", "Shift", "P"])
      const needsMod = keys.includes('Cmd') || keys.includes('Ctrl');
      const needsShift = keys.includes('Shift');
      const needsAlt = keys.includes('Alt');
      const key = keys[keys.length - 1].toLowerCase();

      const matches =
        (!needsMod || modKey) &&
        (!needsShift || event.shiftKey) &&
        (!needsAlt || event.altKey) &&
        event.key.toLowerCase() === key;

      if (matches) {
        if (preventDefault) {
          event.preventDefault();
        }
        callback();
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [keys, callback, enabled, preventDefault]);
}

// Keyboard shortcuts help modal
export function KeyboardShortcutsHelp({ shortcuts }: {
  shortcuts: Array<{
    keys: string[];
    description: string;
    category?: string;
  }>;
}) {
  // Group by category
  const grouped = shortcuts.reduce((acc, shortcut) => {
    const category = shortcut.category || 'General';
    if (!acc[category]) acc[category] = [];
    acc[category].push(shortcut);
    return acc;
  }, {} as Record<string, typeof shortcuts>);

  return (
    <div className="space-y-6">
      {Object.entries(grouped).map(([category, items]) => (
        <div key={category}>
          <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 mb-3">
            {category}
          </h3>
          <dl className="space-y-2">
            {items.map((item, index) => (
              <div
                key={index}
                className="flex items-center justify-between py-2 border-b border-neutral-100 dark:border-neutral-800 last:border-0"
              >
                <dt className="text-sm text-neutral-700 dark:text-neutral-300">
                  {item.description}
                </dt>
                <dd>
                  <KeyboardShortcut keys={item.keys} />
                </dd>
              </div>
            ))}
          </dl>
        </div>
      ))}
    </div>
  );
}
