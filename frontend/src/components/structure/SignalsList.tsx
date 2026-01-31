/**
 * Signals list component - shows extracted signals with actions
 */

'use client';

import { useState } from 'react';
import { signalsAPI } from '@/lib/api/signals';
import type { Signal } from '@/lib/types/signal';

const SIGNAL_COLORS: Record<string, string> = {
  Claim: 'bg-blue-100 text-blue-800 border-blue-200',
  Assumption: 'bg-purple-100 text-purple-800 border-purple-200',
  Question: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  Constraint: 'bg-red-100 text-red-800 border-red-200',
  Goal: 'bg-green-100 text-green-800 border-green-200',
  DecisionIntent: 'bg-indigo-100 text-indigo-800 border-indigo-200',
  EvidenceMention: 'bg-gray-100 text-gray-800 border-gray-200',
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
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          Signals
        </h3>
        <div className="text-sm text-gray-500 italic">
          No signals yet. Start chatting to extract structure from your thinking.
        </div>
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-700 mb-2">
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
                <span className="text-xs text-gray-500">
                  {(signal.confidence * 100).toFixed(0)}%
                </span>
                {signal.status === 'confirmed' && (
                  <span className="text-xs text-green-600">✓ Confirmed</span>
                )}
                {signal.status === 'rejected' && (
                  <span className="text-xs text-red-600">✗ Rejected</span>
                )}
              </div>

              {isEditing ? (
                <div>
                  <textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    className="w-full border rounded px-2 py-1 text-sm mb-2"
                    rows={3}
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleSaveEdit(signal)}
                      className="px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
                    >
                      Save
                    </button>
                    <button
                      onClick={handleCancelEdit}
                      className="px-2 py-1 bg-gray-200 text-gray-700 rounded text-xs hover:bg-gray-300"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <p className="text-gray-800 mb-2">
                    {signal.text}
                  </p>

                  {isSuggested && (
                    <div className="flex gap-2 mt-2">
                      <button
                        onClick={() => handleConfirm(signal)}
                        disabled={isActing}
                        className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs hover:bg-green-200 disabled:opacity-50"
                      >
                        ✓ Confirm
                      </button>
                      <button
                        onClick={() => handleReject(signal)}
                        disabled={isActing}
                        className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs hover:bg-red-200 disabled:opacity-50"
                      >
                        ✗ Reject
                      </button>
                      <button
                        onClick={() => handleStartEdit(signal)}
                        disabled={isActing}
                        className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs hover:bg-gray-200 disabled:opacity-50"
                      >
                        ✏️ Edit
                      </button>
                    </div>
                  )}

                  {signal.status === 'confirmed' && (
                    <button
                      onClick={() => handleStartEdit(signal)}
                      className="mt-2 px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs hover:bg-gray-200"
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
