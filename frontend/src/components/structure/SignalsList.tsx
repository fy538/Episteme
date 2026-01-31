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

  export function SignalsList({ signals }: { signals: Signal[] }) {
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
        {signals.map(signal => (
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
            </div>
            <p className="text-gray-800 leading-snug">{signal.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
