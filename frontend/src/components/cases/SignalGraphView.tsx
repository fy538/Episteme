/**
 * SignalGraphView - Read-only visualization of signal relationships
 *
 * Displays claims, evidence, and assumptions in a connected graph,
 * highlighting validation status with colors.
 */

'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  ArrowsPointingOutIcon,
  ArrowsPointingInIcon,
  FunnelIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

interface Signal {
  id: string;
  type: 'claim' | 'assumption' | 'evidence' | 'question' | 'constraint' | 'goal';
  text: string;
  strength: number;
  validation_status?: 'validated' | 'unvalidated' | 'contradicted' | 'pending';
  linked_to?: string[]; // IDs of related signals
  inquiry_id?: string;
}

interface SignalGraphViewProps {
  signals: Signal[];
  onSignalClick?: (signal: Signal) => void;
  highlightedId?: string;
  compact?: boolean;
}

export function SignalGraphView({
  signals,
  onSignalClick,
  highlightedId,
  compact = false,
}: SignalGraphViewProps) {
  const [expandedView, setExpandedView] = useState(!compact);
  const [filter, setFilter] = useState<Signal['type'] | 'all'>('all');
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);

  // Filter signals
  const filteredSignals = useMemo(() => {
    if (filter === 'all') return signals;
    return signals.filter((s) => s.type === filter);
  }, [signals, filter]);

  // Group signals by type for visualization
  const groupedSignals = useMemo(() => {
    const groups: Record<Signal['type'], Signal[]> = {
      claim: [],
      assumption: [],
      evidence: [],
      question: [],
      constraint: [],
      goal: [],
    };

    filteredSignals.forEach((signal) => {
      groups[signal.type].push(signal);
    });

    return groups;
  }, [filteredSignals]);

  // Get connected signals for a given signal
  const getConnections = useCallback(
    (signal: Signal): Signal[] => {
      if (!signal.linked_to) return [];
      return signals.filter((s) => signal.linked_to?.includes(s.id));
    },
    [signals]
  );

  const handleSignalClick = (signal: Signal) => {
    setSelectedSignal(signal);
    onSignalClick?.(signal);
  };

  // Compact list view
  if (!expandedView) {
    return (
      <div className="border rounded-lg overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2 bg-neutral-50 border-b">
          <span className="text-sm font-medium text-neutral-700">
            Signal Network ({signals.length})
          </span>
          <Button variant="ghost" size="sm" onClick={() => setExpandedView(true)}>
            <ArrowsPointingOutIcon className="w-4 h-4" />
          </Button>
        </div>
        <div className="p-3">
          <div className="flex flex-wrap gap-2">
            {Object.entries(groupedSignals).map(([type, typeSignals]) => {
              if (typeSignals.length === 0) return null;
              return (
                <Badge
                  key={type}
                  variant="neutral"
                  className={`${getTypeColor(type as Signal['type'])} cursor-pointer`}
                  onClick={() => setFilter(type as Signal['type'])}
                >
                  {formatTypeName(type)} ({typeSignals.length})
                </Badge>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // Expanded graph view
  return (
    <div className="border rounded-lg overflow-hidden bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-neutral-50 border-b">
        <div className="flex items-center gap-3">
          <span className="font-medium text-neutral-900">Signal Network</span>
          <Badge variant="outline">{filteredSignals.length} signals</Badge>
        </div>
        <div className="flex items-center gap-2">
          {/* Filter dropdown */}
          <div className="flex items-center gap-1">
            <FunnelIcon className="w-4 h-4 text-neutral-400" />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as Signal['type'] | 'all')}
              className="text-sm border-none bg-transparent focus:outline-none"
            >
              <option value="all">All types</option>
              <option value="claim">Claims</option>
              <option value="assumption">Assumptions</option>
              <option value="evidence">Evidence</option>
              <option value="question">Questions</option>
              <option value="constraint">Constraints</option>
              <option value="goal">Goals</option>
            </select>
          </div>
          <Button variant="ghost" size="sm" onClick={() => setExpandedView(false)}>
            <ArrowsPointingInIcon className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 px-4 py-2 border-b bg-white text-xs">
        <span className="text-neutral-500">Status:</span>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-success-500" />
          <span>Validated</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-warning-500" />
          <span>Unvalidated</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-error-500" />
          <span>Contradicted</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-neutral-400" />
          <span>Pending</span>
        </div>
      </div>

      {/* Graph area */}
      <div className="p-4 min-h-[300px]">
        <div className="grid grid-cols-3 gap-4">
          {/* Claims column */}
          <SignalColumn
            title="Claims"
            signals={groupedSignals.claim}
            highlightedId={highlightedId}
            selectedSignal={selectedSignal}
            onSignalClick={handleSignalClick}
          />

          {/* Assumptions column */}
          <SignalColumn
            title="Assumptions"
            signals={groupedSignals.assumption}
            highlightedId={highlightedId}
            selectedSignal={selectedSignal}
            onSignalClick={handleSignalClick}
          />

          {/* Evidence column */}
          <SignalColumn
            title="Evidence"
            signals={groupedSignals.evidence}
            highlightedId={highlightedId}
            selectedSignal={selectedSignal}
            onSignalClick={handleSignalClick}
          />
        </div>

        {/* Additional types */}
        {(groupedSignals.question.length > 0 ||
          groupedSignals.constraint.length > 0 ||
          groupedSignals.goal.length > 0) && (
          <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t">
            <SignalColumn
              title="Questions"
              signals={groupedSignals.question}
              highlightedId={highlightedId}
              selectedSignal={selectedSignal}
              onSignalClick={handleSignalClick}
            />
            <SignalColumn
              title="Constraints"
              signals={groupedSignals.constraint}
              highlightedId={highlightedId}
              selectedSignal={selectedSignal}
              onSignalClick={handleSignalClick}
            />
            <SignalColumn
              title="Goals"
              signals={groupedSignals.goal}
              highlightedId={highlightedId}
              selectedSignal={selectedSignal}
              onSignalClick={handleSignalClick}
            />
          </div>
        )}
      </div>

      {/* Selected signal detail */}
      {selectedSignal && (
        <div className="px-4 py-3 border-t bg-neutral-50">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <Badge className={getTypeColor(selectedSignal.type)}>
                  {formatTypeName(selectedSignal.type)}
                </Badge>
                <Badge
                  variant="outline"
                  className={getStatusColor(selectedSignal.validation_status)}
                >
                  {formatStatus(selectedSignal.validation_status)}
                </Badge>
              </div>
              <p className="text-sm text-neutral-700">{selectedSignal.text}</p>
              {getConnections(selectedSignal).length > 0 && (
                <div className="mt-2">
                  <p className="text-xs text-neutral-500 mb-1">Connected to:</p>
                  <div className="flex flex-wrap gap-1">
                    {getConnections(selectedSignal).map((conn) => (
                      <button
                        key={conn.id}
                        onClick={() => handleSignalClick(conn)}
                        className="text-xs px-2 py-0.5 bg-neutral-200 hover:bg-neutral-300 rounded"
                      >
                        {conn.text.substring(0, 30)}...
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <button
              onClick={() => setSelectedSignal(null)}
              className="p-1 text-neutral-400 hover:text-neutral-600"
            >
              <XMarkIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function SignalColumn({
  title,
  signals,
  highlightedId,
  selectedSignal,
  onSignalClick,
}: {
  title: string;
  signals: Signal[];
  highlightedId?: string;
  selectedSignal: Signal | null;
  onSignalClick: (signal: Signal) => void;
}) {
  if (signals.length === 0) {
    return (
      <div className="text-center py-4">
        <p className="text-xs text-neutral-400">{title}</p>
        <p className="text-xs text-neutral-300 mt-1">No signals</p>
      </div>
    );
  }

  return (
    <div>
      <p className="text-xs font-medium text-neutral-500 mb-2 text-center">{title}</p>
      <div className="space-y-2">
        {signals.map((signal) => (
          <SignalNode
            key={signal.id}
            signal={signal}
            isHighlighted={signal.id === highlightedId}
            isSelected={selectedSignal?.id === signal.id}
            onClick={() => onSignalClick(signal)}
          />
        ))}
      </div>
    </div>
  );
}

function SignalNode({
  signal,
  isHighlighted,
  isSelected,
  onClick,
}: {
  signal: Signal;
  isHighlighted: boolean;
  isSelected: boolean;
  onClick: () => void;
}) {
  const statusColor = getStatusBgColor(signal.validation_status);

  return (
    <button
      onClick={onClick}
      className={`
        w-full text-left p-2 rounded-lg border transition-all text-xs
        ${isHighlighted ? 'ring-2 ring-accent-500 ring-offset-1' : ''}
        ${isSelected ? 'border-accent-500 bg-accent-50' : 'border-neutral-200 hover:border-neutral-300'}
        ${statusColor}
      `}
    >
      <div className="flex items-start gap-1.5">
        <div
          className={`w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0 ${getStatusDotColor(
            signal.validation_status
          )}`}
        />
        <p className="line-clamp-2">{signal.text}</p>
      </div>
      {signal.inquiry_id && (
        <p className="text-[10px] text-accent-600 mt-1">Linked to inquiry</p>
      )}
    </button>
  );
}

// Helper functions

function formatTypeName(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function formatStatus(status?: string): string {
  if (!status) return 'Pending';
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function getTypeColor(type: Signal['type']): string {
  const colors: Record<Signal['type'], string> = {
    claim: 'bg-purple-100 text-purple-700',
    assumption: 'bg-warning-100 text-warning-700',
    evidence: 'bg-success-100 text-success-700',
    question: 'bg-accent-100 text-accent-700',
    constraint: 'bg-error-100 text-error-700',
    goal: 'bg-blue-100 text-blue-700',
  };
  return colors[type] || 'bg-neutral-100 text-neutral-700';
}

function getStatusColor(status?: string): string {
  switch (status) {
    case 'validated':
      return 'border-success-500 text-success-700';
    case 'unvalidated':
      return 'border-warning-500 text-warning-700';
    case 'contradicted':
      return 'border-error-500 text-error-700';
    default:
      return 'border-neutral-300 text-neutral-600';
  }
}

function getStatusBgColor(status?: string): string {
  switch (status) {
    case 'validated':
      return 'bg-success-50';
    case 'contradicted':
      return 'bg-error-50';
    default:
      return 'bg-white';
  }
}

function getStatusDotColor(status?: string): string {
  switch (status) {
    case 'validated':
      return 'bg-success-500';
    case 'unvalidated':
      return 'bg-warning-500';
    case 'contradicted':
      return 'bg-error-500';
    default:
      return 'bg-neutral-400';
  }
}
