/**
 * SignalsSection - Interactive list of extracted signals
 *
 * Shows signals grouped by type with:
 * - Expandable/collapsible list
 * - Status indicators (pending, validated, etc.)
 * - Quick actions for validation
 * - Badge showing total count
 */

'use client';

import { useState, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { SignalItem } from './SignalItem';
import type { CompanionSignal } from '@/lib/types/companion';

interface SignalsSectionProps {
  signals: CompanionSignal[];
  onSignalClick?: (signal: CompanionSignal) => void;
  onValidateSignal?: (signal: CompanionSignal) => void;
  onValidateAll?: (signals: CompanionSignal[]) => void;
  onDismissSignal?: (signal: CompanionSignal) => void;
}

type SignalGroup = {
  type: string;
  signals: CompanionSignal[];
  prefix: string;
  color: string;
  priority: number;
};

const typeConfig: Record<string, { prefix: string; color: string; priority: number }> = {
  Assumption: { prefix: 'ASM', color: 'text-amber-400', priority: 1 },
  Question: { prefix: 'QRY', color: 'text-blue-400', priority: 2 },
  Claim: { prefix: 'CLM', color: 'text-purple-400', priority: 3 },
  Evidence: { prefix: 'EVD', color: 'text-green-400', priority: 4 },
  Goal: { prefix: 'GOL', color: 'text-indigo-400', priority: 5 },
  Constraint: { prefix: 'CNS', color: 'text-red-400', priority: 6 },
  DecisionIntent: { prefix: 'DEC', color: 'text-pink-400', priority: 7 },
};

export function SignalsSection({
  signals,
  onSignalClick,
  onValidateSignal,
  onValidateAll,
  onDismissSignal,
}: SignalsSectionProps) {
  const [expanded, setExpanded] = useState(true);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['Assumption']));

  // Group signals by type
  const groups = useMemo(() => {
    const grouped = signals.reduce((acc, signal) => {
      const type = signal.type;
      if (!acc[type]) {
        acc[type] = [];
      }
      acc[type].push(signal);
      return acc;
    }, {} as Record<string, CompanionSignal[]>);

    return Object.entries(grouped)
      .map(([type, signals]) => ({
        type,
        signals,
        prefix: typeConfig[type]?.prefix || 'UNK',
        color: typeConfig[type]?.color || 'text-cyan-600',
        priority: typeConfig[type]?.priority || 99,
      }))
      .sort((a, b) => a.priority - b.priority);
  }, [signals]);

  // Count unvalidated assumptions
  const pendingAssumptions = useMemo(
    () =>
      signals.filter(
        (s) => s.type === 'Assumption' && s.validationStatus === 'pending'
      ),
    [signals]
  );

  const toggleGroup = (type: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  if (signals.length === 0) {
    return null;
  }

  return (
    <section className="border-b border-cyan-900/30">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-cyan-950/20 transition-colors font-mono"
      >
        <div className="flex items-center gap-2">
          <span className="text-cyan-400 text-[10px]">{'>'}</span>
          <span className="text-[10px] uppercase tracking-wider font-medium text-cyan-400">
            SIGNAL_BUFFER
          </span>
          <span className="px-1 py-0.5 text-[9px] font-medium bg-cyan-950/50 text-cyan-500 border border-cyan-900/50">
            [{signals.length.toString().padStart(2, '0')}]
          </span>
        </div>
        <span className="text-cyan-600 text-[10px]">
          {expanded ? '[▲]' : '[▼]'}
        </span>
      </button>

      {/* Content */}
      {expanded && (
        <div className="px-3 pb-3 space-y-2">
          {/* Validate all button */}
          {pendingAssumptions.length >= 2 && onValidateAll && (
            <button
              onClick={() => onValidateAll(pendingAssumptions)}
              className="w-full px-2 py-1.5 text-[10px] text-left border border-amber-800/50 bg-amber-950/20 text-amber-400 hover:bg-amber-950/40 transition-colors font-mono"
            >
              <span className="font-medium tracking-wider">
                [VALIDATE_{pendingAssumptions.length}_ASSUMPTIONS]
              </span>
              <span className="text-amber-500 ml-1">→</span>
            </button>
          )}

          {/* Signal groups */}
          {groups.map((group) => (
            <div key={group.type} className="space-y-0.5">
              {/* Group header */}
              <button
                onClick={() => toggleGroup(group.type)}
                className="w-full px-2 py-1 flex items-center justify-between hover:bg-cyan-950/20 transition-colors font-mono"
              >
                <div className="flex items-center gap-2">
                  <span className={cn('text-[9px] font-medium tracking-wider', group.color)}>
                    [{group.prefix}]
                  </span>
                  <span className="text-[10px] text-cyan-500">
                    {group.type}s
                  </span>
                  <span className="text-[9px] text-cyan-700">
                    ({group.signals.length})
                  </span>
                </div>
                <span className="text-cyan-700 text-[9px]">
                  {expandedGroups.has(group.type) ? '▲' : '▼'}
                </span>
              </button>

              {/* Group signals */}
              {expandedGroups.has(group.type) && (
                <div className="pl-2 space-y-0.5">
                  {group.signals.map((signal, idx) => (
                    <SignalItem
                      key={signal.id}
                      signal={signal}
                      index={idx}
                      compact
                      onClick={() => onSignalClick?.(signal)}
                      onValidate={() => onValidateSignal?.(signal)}
                      onDismiss={() => onDismissSignal?.(signal)}
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
