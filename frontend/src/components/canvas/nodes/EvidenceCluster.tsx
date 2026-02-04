/**
 * EvidenceCluster - Compact visualization of evidence items
 *
 * Shows evidence as colored dots:
 * - Green: Supporting
 * - Red: Contradicting
 * - Gray: Neutral
 */

'use client';

import { memo, useState } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

interface Signal {
  id: string;
  signal_type: string;
  content: string;
  direction?: 'supporting' | 'contradicting' | 'neutral';
}

interface EvidenceClusterData {
  signals: Signal[];
  inquiryId: string;
}

function EvidenceClusterComponent({ data, selected }: NodeProps<EvidenceClusterData>) {
  const { signals } = data;
  const [expanded, setExpanded] = useState(false);

  // Categorize signals
  const supporting = signals.filter(s => s.direction === 'supporting' || s.signal_type === 'claim');
  const contradicting = signals.filter(s => s.direction === 'contradicting');
  const neutral = signals.filter(s => !s.direction || s.direction === 'neutral');

  const total = signals.length;

  if (total === 0) return null;

  return (
    <div className="relative">
      {/* Input handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-2 !h-2 !bg-neutral-300 !border-2 !border-white"
      />

      {/* Compact view */}
      {!expanded && (
        <button
          onClick={() => setExpanded(true)}
          className={`
            flex items-center gap-1 px-3 py-2
            bg-white/80 backdrop-blur rounded-lg shadow-sm
            border border-neutral-200
            hover:bg-white hover:shadow transition-all
            ${selected ? 'ring-2 ring-indigo-300 ring-offset-1' : ''}
          `}
        >
          {/* Evidence dots */}
          <div className="flex items-center gap-0.5">
            {supporting.slice(0, 5).map((_, i) => (
              <div key={`s-${i}`} className="w-2 h-2 rounded-full bg-green-500" />
            ))}
            {contradicting.slice(0, 3).map((_, i) => (
              <div key={`c-${i}`} className="w-2 h-2 rounded-full bg-red-500" />
            ))}
            {neutral.slice(0, 3).map((_, i) => (
              <div key={`n-${i}`} className="w-2 h-2 rounded-full bg-neutral-400" />
            ))}
          </div>

          {/* Count if more than shown */}
          {total > 8 && (
            <span className="text-xs text-neutral-500 ml-1">+{total - 8}</span>
          )}
        </button>
      )}

      {/* Expanded view */}
      {expanded && (
        <div
          className={`
            bg-white rounded-xl shadow-lg border border-neutral-200
            p-3 min-w-[200px] max-w-[280px]
            ${selected ? 'ring-2 ring-indigo-300 ring-offset-1' : ''}
          `}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-neutral-600">
              {total} Evidence Items
            </span>
            <button
              onClick={() => setExpanded(false)}
              className="text-xs text-neutral-400 hover:text-neutral-600"
            >
              Collapse
            </button>
          </div>

          {/* Summary */}
          <div className="flex items-center gap-3 text-xs mb-3">
            {supporting.length > 0 && (
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <span className="text-green-700">{supporting.length} supporting</span>
              </div>
            )}
            {contradicting.length > 0 && (
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-red-500" />
                <span className="text-red-700">{contradicting.length} contradicting</span>
              </div>
            )}
            {neutral.length > 0 && (
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-neutral-400" />
                <span className="text-neutral-600">{neutral.length} neutral</span>
              </div>
            )}
          </div>

          {/* Evidence list preview */}
          <div className="space-y-1.5 max-h-32 overflow-y-auto">
            {signals.slice(0, 5).map((signal) => (
              <div
                key={signal.id}
                className={`
                  text-xs px-2 py-1 rounded
                  ${signal.direction === 'supporting' ? 'bg-green-50 text-green-800' : ''}
                  ${signal.direction === 'contradicting' ? 'bg-red-50 text-red-800' : ''}
                  ${!signal.direction || signal.direction === 'neutral' ? 'bg-neutral-50 text-neutral-700' : ''}
                `}
              >
                <span className="line-clamp-1">{signal.content}</span>
              </div>
            ))}
            {signals.length > 5 && (
              <p className="text-xs text-neutral-400 text-center">
                +{signals.length - 5} more
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export const EvidenceCluster = memo(EvidenceClusterComponent);
