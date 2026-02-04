/**
 * DecisionNode - Central node representing the case/decision
 *
 * Shows:
 * - Decision question prominently
 * - Status
 * - User's stated confidence (if set) - as their assessment, not system's
 *
 * No computed confidence scores or progress bars.
 */

'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

interface DecisionNodeData {
  title: string;
  userConfidence?: number | null; // User's self-stated confidence (0-100)
  status: string;
  onClick: () => void;
}

function DecisionNodeComponent({ data, selected }: NodeProps<DecisionNodeData>) {
  const { title, userConfidence, status, onClick } = data;

  return (
    <div
      onClick={onClick}
      className={`
        relative cursor-pointer transition-all duration-200
        ${selected ? 'scale-105' : 'hover:scale-102'}
      `}
    >
      {/* Subtle glow effect */}
      <div className="absolute inset-0 rounded-2xl blur-xl opacity-20 bg-indigo-400" />

      {/* Main node */}
      <div
        className={`
          relative bg-white rounded-2xl shadow-lg
          px-6 py-4 min-w-[280px] max-w-[400px]
          border-2 border-indigo-300
          ${selected ? 'ring-2 ring-indigo-400 ring-offset-2' : ''}
        `}
      >
        {/* Status badge */}
        <div className="absolute -top-2 -right-2">
          <span className={`
            px-2 py-0.5 rounded-full text-xs font-medium
            ${status === 'active' ? 'bg-green-100 text-green-700' : ''}
            ${status === 'draft' ? 'bg-neutral-100 text-neutral-600' : ''}
            ${status === 'archived' ? 'bg-neutral-200 text-neutral-500' : ''}
          `}>
            {status}
          </span>
        </div>

        {/* Icon */}
        <div className="flex items-center gap-3 mb-2">
          <div className={`
            w-10 h-10 rounded-xl flex items-center justify-center
            bg-gradient-to-br from-indigo-500 to-purple-600
          `}>
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <span className="text-xs text-neutral-400 uppercase tracking-wide">Decision</span>
        </div>

        {/* Title - the decision question */}
        <h3 className="text-lg font-semibold text-neutral-900 leading-snug">
          {title}
        </h3>

        {/* User's confidence (if they've stated it) */}
        {userConfidence !== null && userConfidence !== undefined && (
          <div className="mt-3 flex items-center gap-2">
            <span className="text-xs text-neutral-500">Your confidence:</span>
            <span className={`text-sm font-medium ${getUserConfidenceColor(userConfidence)}`}>
              {userConfidence}
            </span>
          </div>
        )}

        {/* Click hint */}
        <p className="text-xs text-neutral-400 mt-3 text-center">
          Click to view brief
        </p>
      </div>

      {/* Output handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-indigo-500 !border-2 !border-white"
      />
    </div>
  );
}

// Helper for user confidence display color
function getUserConfidenceColor(confidence: number): string {
  if (confidence >= 70) return 'text-green-600';
  if (confidence >= 40) return 'text-amber-600';
  return 'text-red-600';
}

export const DecisionNode = memo(DecisionNodeComponent);
