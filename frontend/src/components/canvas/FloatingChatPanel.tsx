/**
 * FloatingChatPanel - Floating chat panel for the canvas workspace
 *
 * Wraps ChatPanel in the same floating panel pattern as AICopilotPanel:
 * - Absolute positioned, top-right, w-96
 * - Gradient header with close button
 * - Height constrained to viewport
 * - hideCollapse since the floating panel has its own close
 *
 * Shares the same thread as the classic case workspace so
 * conversation persists across view switches.
 */

'use client';

import { ChatPanel } from '@/components/workspace/ChatPanel';
import type { StreamingCallbacks } from '@/lib/types/streaming';

interface FloatingChatPanelProps {
  isOpen: boolean;
  onClose: () => void;
  threadId: string;
  caseId: string;
  caseName: string;
  briefId?: string;
  /** Callbacks for forwarding unified stream events (reflection, action hints) to parent */
  streamCallbacks?: StreamingCallbacks;
}

export function FloatingChatPanel({
  isOpen,
  onClose,
  threadId,
  caseId,
  caseName,
  briefId,
  streamCallbacks,
}: FloatingChatPanelProps) {
  if (!isOpen) return null;

  return (
    <div
      className="absolute top-4 right-4 w-96 bg-white rounded-xl shadow-2xl border border-neutral-200 overflow-hidden z-50 flex flex-col animate-slide-in-right"
      style={{ height: 'calc(100vh - 120px)' }}
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-500 to-indigo-600 px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2 text-white">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <span className="font-medium text-sm">Chat</span>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-white/80 hover:text-white rounded transition-colors"
          aria-label="Close chat"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Chat panel (fills remaining space) */}
      <div className="flex-1 overflow-hidden">
        <ChatPanel
          threadId={threadId}
          hideCollapse={true}
          briefId={briefId}
          mode={{ mode: 'case', caseId, caseName }}
          streamCallbacks={streamCallbacks}
        />
      </div>
    </div>
  );
}

/**
 * Floating trigger button for the chat panel (matches AICopilotTrigger pattern)
 */
export function ChatPanelTrigger({
  onClick,
}: {
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="p-3 rounded-xl shadow-lg border bg-white text-blue-600 border-blue-200 hover:border-blue-400 transition-all hover:scale-105"
      title="Chat (C)"
    >
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    </button>
  );
}
