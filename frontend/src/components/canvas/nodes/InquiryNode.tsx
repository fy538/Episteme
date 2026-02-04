/**
 * InquiryNode - Node representing an inquiry/question to validate
 *
 * Shows:
 * - Inquiry title
 * - Status (open, investigating, resolved)
 * - Evidence count (not confidence percentage)
 * - Blocked indicator if dependencies exist
 *
 * No computed confidence scores - just status and evidence counts.
 */

'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import type { Inquiry } from '@/lib/types/case';

interface InquiryNodeData {
  inquiry: Inquiry;
  onClick: () => void;
  isBlocked?: boolean;
  isResolved?: boolean;
  evidenceCount?: { supporting: number; contradicting: number };
}

function InquiryNodeComponent({ data, selected }: NodeProps<InquiryNodeData>) {
  const { inquiry, onClick, isBlocked, isResolved, evidenceCount } = data;

  const statusConfig = getStatusConfig(inquiry.status, isBlocked);

  return (
    <div
      onClick={onClick}
      className={`
        relative cursor-pointer transition-all duration-200
        ${selected ? 'scale-105' : 'hover:scale-102'}
        ${isBlocked ? 'opacity-75' : ''}
      `}
    >
      {/* Input handle */}
      <Handle
        type="target"
        position={Position.Top}
        className={`!w-2.5 !h-2.5 !border-2 !border-white ${statusConfig.handleColor}`}
      />

      {/* Main node */}
      <div
        className={`
          relative bg-white rounded-xl shadow-md
          px-4 py-3 min-w-[180px] max-w-[220px]
          border-2 transition-all
          ${statusConfig.borderColor}
          ${selected ? 'ring-2 ring-offset-2 ' + statusConfig.ringColor : ''}
        `}
        style={{
          borderStyle: isBlocked ? 'dashed' : 'solid',
        }}
      >
        {/* Status indicator */}
        <div className="flex items-center gap-2 mb-2">
          <div className={`w-2 h-2 rounded-full ${statusConfig.dotColor}`} />
          <span className={`text-xs font-medium ${statusConfig.textColor}`}>
            {statusConfig.label}
          </span>
          {isBlocked && (
            <span className="text-xs text-amber-600 ml-auto">Blocked</span>
          )}
        </div>

        {/* Title */}
        <h4 className="text-sm font-medium text-neutral-800 leading-snug line-clamp-2">
          {inquiry.title}
        </h4>

        {/* Evidence counts (instead of confidence bar) */}
        {evidenceCount && (evidenceCount.supporting > 0 || evidenceCount.contradicting > 0) && (
          <div className="mt-2 flex items-center gap-2 text-xs">
            {evidenceCount.supporting > 0 && (
              <span className="text-green-600">{evidenceCount.supporting} supporting</span>
            )}
            {evidenceCount.supporting > 0 && evidenceCount.contradicting > 0 && (
              <span className="text-neutral-300">|</span>
            )}
            {evidenceCount.contradicting > 0 && (
              <span className="text-red-600">{evidenceCount.contradicting} contradicting</span>
            )}
          </div>
        )}

        {/* Fallback: total evidence count */}
        {!evidenceCount && inquiry.related_signals_count != null && inquiry.related_signals_count > 0 && (
          <div className="mt-2 text-xs text-neutral-400">
            {inquiry.related_signals_count} evidence items
          </div>
        )}

        {/* Resolved conclusion hint */}
        {isResolved && inquiry.conclusion && (
          <div className="mt-2 text-xs text-green-600 line-clamp-1">
            Resolved
          </div>
        )}
      </div>

      {/* Output handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        className={`!w-2.5 !h-2.5 !border-2 !border-white ${statusConfig.handleColor}`}
      />
    </div>
  );
}

// Status configuration
function getStatusConfig(status: string, isBlocked?: boolean) {
  if (isBlocked) {
    return {
      label: 'Blocked',
      dotColor: 'bg-amber-500',
      borderColor: 'border-amber-300',
      textColor: 'text-amber-600',
      handleColor: '!bg-amber-500',
      ringColor: 'ring-amber-300',
    };
  }

  switch (status) {
    case 'resolved':
      return {
        label: 'Resolved',
        dotColor: 'bg-green-500',
        borderColor: 'border-green-400',
        textColor: 'text-green-600',
        handleColor: '!bg-green-500',
        ringColor: 'ring-green-300',
      };
    case 'investigating':
      return {
        label: 'Investigating',
        dotColor: 'bg-blue-500 animate-pulse',
        borderColor: 'border-blue-400',
        textColor: 'text-blue-600',
        handleColor: '!bg-blue-500',
        ringColor: 'ring-blue-300',
      };
    case 'open':
    default:
      return {
        label: 'Open',
        dotColor: 'bg-neutral-400',
        borderColor: 'border-neutral-300',
        textColor: 'text-neutral-600',
        handleColor: '!bg-neutral-400',
        ringColor: 'ring-neutral-300',
      };
  }
}

export const InquiryNode = memo(InquiryNodeComponent);
