/**
 * Guided first actions - helps new users get started
 * Shows for 30 seconds or until first action
 */

'use client';

import { useEffect } from 'react';

interface GuidedFirstActionsProps {
  show: boolean;
  onDismiss: () => void;
}

export function GuidedFirstActions({ show, onDismiss }: GuidedFirstActionsProps) {
  useEffect(() => {
    if (!show) return;

    // Auto-dismiss after 30 seconds
    const timer = setTimeout(() => {
      onDismiss();
    }, 30000);

    return () => clearTimeout(timer);
  }, [show, onDismiss]);

  if (!show) return null;

  return (
    <div className="fixed bottom-6 right-24 z-40 max-w-sm animate-slide-in">
      <div className="bg-white border-2 border-accent-500 rounded-lg shadow-2xl p-5">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-accent-600" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
              <path
                fillRule="evenodd"
                d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z"
                clipRule="evenodd"
              />
            </svg>
            <h4 className="font-semibold text-neutral-900">Get Started</h4>
          </div>
          <button
            onClick={onDismiss}
            className="text-neutral-400 hover:text-neutral-600 transition-colors"
            aria-label="Dismiss"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>

        <div className="space-y-3">
          <div className="flex items-start gap-3 p-3 hover:bg-blue-50 rounded-lg cursor-pointer transition-colors">
            <span className="text-2xl">💬</span>
            <div>
              <p className="text-sm font-medium text-neutral-900">Chat with AI</p>
              <p className="text-xs text-neutral-600">Ask anything about your decision</p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 hover:bg-blue-50 rounded-lg cursor-pointer transition-colors">
            <span className="text-2xl">⚠️</span>
            <div>
              <p className="text-sm font-medium text-neutral-900">Investigate Assumptions</p>
              <p className="text-xs text-neutral-600">Click yellow highlights to validate claims</p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 hover:bg-blue-50 rounded-lg cursor-pointer transition-colors">
            <span className="text-2xl">🔍</span>
            <div>
              <p className="text-sm font-medium text-neutral-900">Start Researching</p>
              <p className="text-xs text-neutral-600">Open an inquiry to gather evidence</p>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-neutral-200">
          <p className="text-xs text-neutral-500 text-center">
            Auto-dismisses in 30s or after your first action
          </p>
        </div>
      </div>
    </div>
  );
}
