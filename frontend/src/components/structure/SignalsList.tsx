/**
 * Signals list component - shows extracted signals with actions
 */

'use client';

import { useState } from 'react';
import { signalsAPI } from '@/lib/api/signals';
import { Textarea } from '@/components/ui/textarea';
import type { Signal } from '@/lib/types/signal';

const SIGNAL_COLORS: Record<string, string> = {
  Claim: 'bg-warning-100 text-warning-800 border-warning-200',
  Assumption: 'bg-purple-100 text-purple-800 border-purple-200',
  Question: 'bg-warning-100 text-warning-800 border-warning-200',
  Constraint: 'bg-error-100 text-error-800 border-error-200',
  Goal: 'bg-success-100 text-success-800 border-success-200',
  DecisionIntent: 'bg-accent-100 text-accent-800 border-accent-200',
  EvidenceMention: 'bg-neutral-100 text-neutral-800 border-neutral-200',
};

export function SignalsList({ 
  signals, 
  onRefresh 
}: { 
  signals: Signal[];
  onRefresh?: () => void;
}) {
  const [actingOnId, setActingOnId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

  const handleConfirm = async (signal: Signal) => {
    setActingOnId(signal.id);
    try {
      await signalsAPI.confirm(signal.id);
      onRefresh?.();
    } catch (error) {
      console.error('Failed to confirm signal:', error);
    } finally {
      setActingOnId(null);
    }
  };

  const handleReject = async (signal: Signal) => {
    setActingOnId(signal.id);
    try {
      await signalsAPI.reject(signal.id);
      onRefresh?.();
    } catch (error) {
      console.error('Failed to reject signal:', error);
    } finally {
      setActingOnId(null);
    }
  };

  const handleStartEdit = (signal: Signal) => {
    setEditingId(signal.id);
    setEditText(signal.text);
  };

  const handleSaveEdit = async (signal: Signal) => {
    try {
      await signalsAPI.edit(signal.id, editText);
      setEditingId(null);
      onRefresh?.();
    } catch (error) {
      console.error('Failed to edit signal:', error);
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditText('');
  };

  if (signals.length === 0) {
    return (
      <div>
        <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">
          Signals
        </h3>
        <div className="text-sm text-neutral-500 dark:text-neutral-400 italic">
          No signals yet. Start chatting to extract structure from your thinking.
        </div>
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-2">
        Signals Extracted ({signals.length})
      </h3>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {signals.map(signal => {
          const isEditing = editingId === signal.id;
          const isActing = actingOnId === signal.id;
          const isSuggested = signal.status === 'suggested';
          
          return (
            <div
              key={signal.id}
              className="p-2 rounded border text-sm bg-white"
            >
              <div className="flex items-center gap-2 mb-1">
                <span className={`px-2 py-0.5 rounded text-xs font-medium border ${
                  SIGNAL_COLORS[signal.type] || SIGNAL_COLORS.Claim
                }`}>
                  {signal.type}
                </span>
                <span className="text-xs text-neutral-500 dark:text-neutral-400">
                  {(signal.confidence * 100).toFixed(0)}%
                </span>
                {signal.status === 'confirmed' && (
                  <span className="text-xs text-success-600 dark:text-success-400">✓ Confirmed</span>
                )}
                {signal.status === 'rejected' && (
                  <span className="text-xs text-error-600 dark:text-error-400">✗ Rejected</span>
                )}
              </div>

              {isEditing ? (
                <div>
                  <Textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    aria-label="Edit signal text"
                    className="mb-2"
                    rows={3}
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleSaveEdit(signal)}
                      className="px-2 py-1 bg-accent-600 text-white rounded text-xs hover:bg-accent-700 transition-colors"
                    >
                      Save
                    </button>
                    <button
                      onClick={handleCancelEdit}
                      className="px-2 py-1 bg-neutral-200 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-200 rounded text-xs hover:bg-neutral-300 dark:hover:bg-neutral-600 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <p className="text-neutral-800 dark:text-neutral-200 mb-2">
                    {signal.text}
                  </p>

                  {isSuggested && (
                    <div className="flex gap-2 mt-2">
                      <button
                        onClick={() => handleConfirm(signal)}
                        disabled={isActing}
                        className="px-2 py-1 bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-400 rounded text-xs hover:bg-success-200 dark:hover:bg-success-900/50 disabled:opacity-50 transition-colors"
                      >
                        ✓ Confirm
                      </button>
                      <button
                        onClick={() => handleReject(signal)}
                        disabled={isActing}
                        className="px-2 py-1 bg-error-100 dark:bg-error-900/30 text-error-700 dark:text-error-400 rounded text-xs hover:bg-error-200 dark:hover:bg-error-900/50 disabled:opacity-50 transition-colors"
                      >
                        ✗ Reject
                      </button>
                      <button
                        onClick={() => handleStartEdit(signal)}
                        disabled={isActing}
                        className="px-2 py-1 bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 rounded text-xs hover:bg-neutral-200 dark:hover:bg-neutral-700 disabled:opacity-50 transition-colors"
                      >
                        ✏️ Edit
                      </button>
                    </div>
                  )}

                  {signal.status === 'confirmed' && (
                    <button
                      onClick={() => handleStartEdit(signal)}
                      className="mt-2 px-2 py-1 bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 rounded text-xs hover:bg-neutral-200 dark:hover:bg-neutral-700 transition-colors"
                    >
                      ✏️ Edit
                    </button>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
