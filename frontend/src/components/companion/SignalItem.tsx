/**
 * SignalItem - Individual signal display with status and actions
 */

'use client';

import { cn } from '@/lib/utils';
import type { CompanionSignal, SignalValidationStatus } from '@/lib/types/companion';

interface SignalItemProps {
  signal: CompanionSignal;
  index?: number;
  onClick?: () => void;
  onValidate?: () => void;
  onDismiss?: () => void;
  compact?: boolean;
}

const statusIcons: Record<SignalValidationStatus, string> = {
  pending: '○',
  validating: '◐',
  validated: '✓',
  refuted: '✗',
  partially_true: '◑',
  dismissed: '−',
};

const statusColors: Record<SignalValidationStatus, string> = {
  pending: 'text-cyan-700',
  validating: 'text-cyan-400',
  validated: 'text-green-400',
  refuted: 'text-red-400',
  partially_true: 'text-amber-400',
  dismissed: 'text-cyan-900',
};

export function SignalItem({
  signal,
  index = 0,
  onClick,
  onValidate,
  onDismiss,
  compact = false,
}: SignalItemProps) {
  const status = signal.validationStatus;
  const isValidatable = signal.type === 'Assumption' && status === 'pending';
  const hexAddr = `0x${index.toString(16).padStart(2, '0').toUpperCase()}`;

  return (
    <div
      className={cn(
        'group transition-all duration-200 font-mono border-l-2',
        compact ? 'p-1.5 pl-2' : 'p-2 pl-3',
        onClick && 'cursor-pointer',
        status === 'dismissed'
          ? 'opacity-40 border-cyan-900'
          : 'hover:bg-cyan-950/20 border-cyan-900/50'
      )}
      onClick={onClick}
    >
      <div className="flex items-start gap-2">
        {/* Hex address + Status */}
        <div className="flex items-center gap-1 pt-0.5">
          <span className="text-[9px] text-cyan-700">
            {hexAddr}
          </span>
          <span
            className={cn(
              'text-[10px] transition-colors',
              statusColors[status],
              status === 'validating' && 'animate-pulse'
            )}
          >
            {statusIcons[status]}
          </span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p
            className={cn(
              'text-[10px] leading-relaxed',
              status === 'dismissed'
                ? 'text-cyan-800 line-through'
                : 'text-cyan-400'
            )}
          >
            {signal.text}
          </p>

          {/* Meta info */}
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[9px] text-cyan-700">
              conf: {Math.round(signal.confidence * 100)}%
            </span>
            {signal.validationResult && (
              <span
                className={cn(
                  'text-[9px] font-medium tracking-wider',
                  signal.validationResult.verdict === 'true'
                    ? 'text-green-400'
                    : signal.validationResult.verdict === 'false'
                    ? 'text-red-400'
                    : 'text-amber-400'
                )}
              >
                {signal.validationResult.verdict === 'true'
                  ? '[VALID]'
                  : signal.validationResult.verdict === 'false'
                  ? '[REFUTED]'
                  : '[PARTIAL]'}
              </span>
            )}
          </div>

          {/* Validation result summary */}
          {signal.validationResult && !compact && (
            <p className="text-[10px] text-cyan-600 mt-1 leading-relaxed pl-2 border-l border-cyan-900/50">
              {signal.validationResult.summary}
            </p>
          )}
        </div>

        {/* Quick actions - show on hover */}
        {!compact && (isValidatable || status === 'pending') && (
          <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
            {isValidatable && onValidate && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onValidate();
                }}
                className="text-[9px] px-1.5 py-0.5 border border-cyan-800 bg-cyan-950/30 text-cyan-400 hover:bg-cyan-950/50"
              >
                RESEARCH
              </button>
            )}
            {onDismiss && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDismiss();
                }}
                className="text-[9px] px-1.5 py-0.5 text-cyan-700 hover:text-cyan-500"
              >
                [X]
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
