/**
 * Floating Action Button (FAB)
 * 
 * Context-aware primary action button that changes based on the active tab
 * Provides quick access to common actions with a radial menu
 * 
 * Keyboard shortcut: Cmd+Shift+A
 */

'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

type ActionId = 'inquiry' | 'document' | 'chat' | 'generate';

interface Action {
  id: ActionId;
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
  color?: string;
}

interface FloatingActionButtonProps {
  actions: Action[];
  primaryAction?: Action;
}

export function FloatingActionButton({ actions, primaryAction }: FloatingActionButtonProps) {
  const [isOpen, setIsOpen] = useState(false);

  // Keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'a') {
        e.preventDefault();
        setIsOpen(prev => !prev);
      }
      // Escape to close
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  const handleActionClick = (action: Action) => {
    action.onClick();
    setIsOpen(false);
  };

  const primary = primaryAction || actions[0];

  return (
    <>
      {/* Main FAB Button */}
      <div className="fixed bottom-8 right-8 z-40">
        {/* Secondary actions (radial menu) */}
        {isOpen && actions.length > 1 && (
          <div className="absolute bottom-16 right-0 flex flex-col-reverse gap-3 mb-2">
            {actions.map((action, index) => (
              <button
                key={action.id}
                onClick={() => handleActionClick(action)}
                className={cn(
                  'flex items-center gap-3 bg-white rounded-full shadow-lg hover:shadow-xl transition-all transform hover:scale-105',
                  'px-4 py-3 border border-neutral-200'
                )}
                style={{
                  animation: `slideIn 0.2s ease-out ${index * 0.05}s backwards`,
                }}
              >
                <span className="text-neutral-700">
                  {action.icon}
                </span>
                <span className="text-sm font-medium text-neutral-900">
                  {action.label}
                </span>
              </button>
            ))}
          </div>
        )}

        {/* Primary button */}
        <button
          onClick={() => {
            if (actions.length === 1) {
              handleActionClick(primary);
            } else {
              setIsOpen(!isOpen);
            }
          }}
          className={cn(
            'w-14 h-14 rounded-full shadow-lg hover:shadow-xl transition-all',
            'flex items-center justify-center',
            'bg-accent-600 hover:bg-accent-700 text-white',
            isOpen && 'rotate-45'
          )}
          aria-label="Quick actions"
        >
          {isOpen ? (
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            primary.icon
          )}
        </button>

        {/* Keyboard hint */}
        {!isOpen && (
          <div className="absolute -top-10 right-0 bg-neutral-900 text-white text-xs px-2 py-1 rounded opacity-0 hover:opacity-100 transition-opacity pointer-events-none">
            ⌘⇧A
          </div>
        )}
      </div>

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-black bg-opacity-10"
          onClick={() => setIsOpen(false)}
        />
      )}

      <style jsx>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </>
  );
}
