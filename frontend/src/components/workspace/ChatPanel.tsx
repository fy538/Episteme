/**
 * ChatPanel - Unified chat component for all contexts
 *
 * Supports two display variants:
 * - "panel" (default): Sidebar chat panel (collapsible, compact header)
 * - "full": Full-screen chat (fills parent, breadcrumbs header, no collapse)
 *
 * Features: unified streaming, mode-aware header, case analysis auto-trigger.
 * Companion content (thinking, action hints, signals) is rendered separately
 * in CompanionPanel.
 *
 * Used by:
 * - Home.tsx (variant="full") — casual chat
 * - CaseWorkspace page (variant="panel") — case chat sidebar
 * - FloatingChatPanel (variant="panel", hideCollapse) — canvas floating chat
 */

'use client';

import { useRouter } from 'next/navigation';
import { MessageList } from '@/components/chat/MessageList';
import { MessageInput } from '@/components/chat/MessageInput';
import { ChatModeHeader } from '@/components/chat/ChatModeHeader';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { CaseCreationPreview } from '@/components/cases/CaseCreationPreview';
import { CaseAssemblyAnimation } from '@/components/cases/CaseAssemblyAnimation';
import { documentsAPI } from '@/lib/api/documents';
import { chatAPI } from '@/lib/api/chat';
import { useState as useToastState } from 'react';
import { useChatPanelState } from '@/hooks/useChatPanelState';
import type { StreamingCallbacks } from '@/lib/types/streaming';
import type { ModeContext } from '@/lib/types/companion';

interface ChatPanelProps {
  threadId: string;
  contextLabel?: string;
  onCreateCase?: () => void;
  hideCollapse?: boolean;
  briefId?: string;
  onIntegrationPreview?: (result: Record<string, unknown>) => void;
  /** Callbacks for unified stream events forwarded to parent */
  streamCallbacks?: StreamingCallbacks;
  /** Current chat mode context (case, inquiry_focus, casual) */
  mode?: ModeContext;
  /** Exit inquiry focus mode */
  onExitFocus?: () => void;
  /** Display variant: "panel" (sidebar) or "full" (full-screen) */
  variant?: 'panel' | 'full';
  /** Auto-send this message on mount (used by Home hero input handoff) */
  initialMessage?: string;
  /** Called after initialMessage has been sent */
  onInitialMessageSent?: () => void;
}

export function ChatPanel({
  threadId,
  contextLabel = 'AI Chat',
  onCreateCase,
  hideCollapse = false,
  briefId,
  onIntegrationPreview,
  streamCallbacks,
  mode,
  onExitFocus,
  variant = 'panel',
  initialMessage,
  onInitialMessageSent,
}: ChatPanelProps) {
  const router = useRouter();
  const state = useChatPanelState({
    threadId,
    onCreateCase,
    streamCallbacks,
    mode,
    initialMessage,
    onInitialMessageSent,
  });

  const isFull = variant === 'full';
  const [briefToast, setBriefToast] = useToastState<string | null>(null);

  async function handleAddToBrief(messageId: string, content: string) {
    if (!briefId) {
      console.warn('No brief available in this context');
      return;
    }
    try {
      const result = await documentsAPI.integrateContent(briefId, content, 'general', messageId);
      onIntegrationPreview?.(result);
      setBriefToast('Content added to brief');
      setTimeout(() => setBriefToast(null), 3000);
    } catch (error) {
      console.error('Failed to integrate content:', error);
      setBriefToast('Failed to add to brief');
      setTimeout(() => setBriefToast(null), 3000);
    }
  }

  async function handleCreateEvidence(content: string) {
    // TODO: Implement evidence creation via API
    console.log('Create evidence from:', content);
  }

  // Determine if we should show mode-aware header vs static label
  const showModeHeader = mode && mode.mode !== 'casual';

  // Panel variant: collapsed sidebar
  if (!isFull && state.isCollapsed && !hideCollapse) {
    return (
      <div className="w-16 flex flex-col items-center py-4 bg-neutral-50 animate-fade-in">
        <button
          onClick={() => state.setIsCollapsed(false)}
          className="p-2 hover:bg-neutral-200 rounded-lg transition-colors"
          aria-label="Expand chat"
        >
          <svg className="w-5 h-5 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
      </div>
    );
  }

  return (
    <div className={isFull ? 'flex flex-col h-full bg-white' : 'flex flex-col h-full bg-white'}>
      {/* Header — variant-aware */}
      {isFull ? (
        <div className="border-b border-neutral-200 p-4">
          <Breadcrumbs items={[{ label: 'Chat' }]} />
        </div>
      ) : (
        <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200">
          <h3 className="text-sm font-medium text-neutral-900">
            {showModeHeader ? 'Chat' : contextLabel}
          </h3>
          {!hideCollapse && (
            <button
              onClick={() => state.setIsCollapsed(true)}
              className="p-1 hover:bg-neutral-100 rounded transition-colors"
              aria-label="Collapse chat"
            >
              <svg className="w-4 h-4 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          )}
        </div>
      )}

      {/* Mode-aware context header */}
      {showModeHeader && mode && (
        <ChatModeHeader
          mode={mode}
          onExitFocus={onExitFocus}
        />
      )}

      {/* Error banner */}
      {state.error && (
        <div className={isFull
          ? 'bg-error-50 border-l-4 border-error-500 p-4 mx-4 mt-4'
          : 'bg-red-50 border-l-4 border-red-500 p-3 mx-3 mt-2'
        }>
          <div className="flex items-start">
            <div className="flex-1">
              <p className={isFull ? 'text-sm text-error-700' : 'text-xs text-red-700'}>{state.error}</p>
              {state.lastFailedMessage && (
                <button
                  onClick={state.handleRetry}
                  className={isFull
                    ? 'mt-2 text-sm font-medium text-error-700 hover:text-error-900 underline'
                    : 'mt-1 text-xs font-medium text-red-700 hover:text-red-900 underline'
                  }
                >
                  Retry message
                </button>
              )}
            </div>
            <button
              onClick={state.clearError}
              className={isFull
                ? 'ml-4 text-error-700 hover:text-error-900'
                : 'ml-2 text-red-700 hover:text-red-900 text-xs'
              }
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Brief integration toast */}
      {briefToast && (
        <div className="mx-3 mb-1 px-3 py-1.5 bg-accent-50 border border-accent-200 rounded text-xs text-accent-700 text-center animate-in fade-in slide-in-from-top-1">
          {briefToast}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto">
          <MessageList
            messages={state.messages}
            isWaitingForResponse={state.isWaitingForResponse}
            isStreaming={state.isStreaming}
            ttft={state.ttft}
            onAddToBrief={briefId ? handleAddToBrief : undefined}
            onCreateEvidence={handleCreateEvidence}
          />
        </div>

        {/* Case suggestion */}
        {state.showCaseSuggestion && state.caseAnalysis && (
          <CaseCreationPreview
            analysis={state.caseAnalysis}
            onConfirm={async (edits) => {
              state.setCreatingCase(true);
              try {
                const result = await chatAPI.createCaseFromAnalysis(threadId, state.caseAnalysis, edits);
                state.setShowCaseSuggestion(false);
                state.setShowAssembly(true);
                setTimeout(() => {
                  router.push(`/cases/${result.case.id}`);
                }, 3000);
              } catch (error) {
                console.error('Failed to create case:', error);
                state.setCreatingCase(false);
              }
            }}
            onDismiss={() => state.setShowCaseSuggestion(false)}
            isCreating={state.creatingCase}
          />
        )}

        {/* Assembly animation */}
        {state.showAssembly && <CaseAssemblyAnimation onComplete={() => {}} />}
      </div>

      {/* Input */}
      <MessageInput
        onSend={state.sendMessage}
        disabled={state.isLoading}
        isProcessing={state.isLoading || state.isWaitingForResponse}
        isStreaming={state.isStreaming}
        onStop={state.stopGeneration}
      />
    </div>
  );
}
