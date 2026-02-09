/**
 * SessionReceiptsSection - Timeline of session accomplishments
 *
 * Shows a chronological list of what was achieved during the session:
 * - Case created
 * - Inquiry resolved
 * - Research completed
 */

'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { theme, isTerminalTheme } from '@/lib/theme/companionTheme';
import type { SessionReceipt, SessionReceiptType } from '@/lib/types/companion';

interface SessionReceiptsSectionProps {
  receipts: SessionReceipt[];
  onReceiptClick?: (receipt: SessionReceipt) => void;
}

const RECEIPT_ICONS: Record<SessionReceiptType, string> = {
  case_created: '+',
  inquiry_resolved: '!',
  research_completed: '?',
};

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  return date.toLocaleDateString();
}

// Get theme colors for receipt type
function getReceiptTheme(type: SessionReceiptType) {
  return theme.receipts[type] || theme.receipts.case_created;
}

export function SessionReceiptsSection({
  receipts,
  onReceiptClick,
}: SessionReceiptsSectionProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (receipts.length === 0) {
    return null;
  }

  return (
    <section className={cn('border-b', theme.thinking.border)}>
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        aria-expanded={!collapsed}
        className={cn(
          'w-full px-3 py-2 flex items-center justify-between transition-colors',
          theme.thinking.bgHover,
          isTerminalTheme && 'font-mono'
        )}
      >
        <div className="flex items-center gap-2">
          <span className={cn('text-xs', theme.thinking.text)} aria-hidden="true">{'>'}</span>
          <span className={cn('text-xs tracking-wider font-medium uppercase', theme.thinking.text)}>
            SESSION
          </span>
          <span className={cn('text-xs', theme.thinking.textMuted)}>
            ({receipts.length} item{receipts.length !== 1 ? 's' : ''})
          </span>
        </div>
        <span className={cn('text-xs', theme.thinking.textMuted)} aria-hidden="true">
          {collapsed ? '[+]' : '[-]'}
        </span>
      </button>

      {/* Timeline */}
      {!collapsed && (
        <div className={cn('px-3 pb-3', isTerminalTheme && 'font-mono')}>
          <div className={cn('border-l-2 pl-3 space-y-2', theme.thinking.border)}>
            {receipts.map((receipt) => {
              const receiptTheme = getReceiptTheme(receipt.type);
              const icon = RECEIPT_ICONS[receipt.type];

              return (
                <button
                  key={receipt.id}
                  onClick={() => onReceiptClick?.(receipt)}
                  className={cn(
                    'w-full text-left border p-2 text-xs transition-colors',
                    theme.thinking.border,
                    theme.thinking.bg,
                    'hover:brightness-110',
                    onReceiptClick && 'cursor-pointer'
                  )}
                  disabled={!onReceiptClick}
                >
                  <div className="flex items-start gap-2">
                    {/* Timeline dot */}
                    <span className={cn('font-bold', receiptTheme.text)}>
                      {icon}
                    </span>

                    <div className="flex-1 min-w-0">
                      {/* Title */}
                      <div className={cn('font-medium truncate', receiptTheme.text)}>
                        {receipt.title}
                      </div>

                      {/* Detail (if present) */}
                      {receipt.detail && (
                        <div className={cn('truncate mt-0.5', theme.thinking.textMuted)}>
                          {receipt.detail}
                        </div>
                      )}

                      {/* Timestamp */}
                      <div className={cn('mt-1', theme.thinking.textSubtle)}>
                        {formatTimestamp(receipt.timestamp)}
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}
