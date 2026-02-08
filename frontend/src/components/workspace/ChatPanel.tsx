/**
 * ChatPanel - Unified chat component for all contexts
 *
 * Supports two display variants:
 * - "panel" (default): Sidebar chat panel (collapsible, compact header)
 * - "full": Full-screen chat (fills parent, Claude-style centered layout)
 *
 * Full variant layout:
 * - Messages + input centered in a max-width column with side borders
 * - Borders absorb width reduction first, then sidebar collapses, then content narrows
 * - Input pinned to bottom, matching content width
 *
 * Features: unified streaming, mode-aware header, inline action cards for case creation.
 * Companion content (thinking, action hints, signals) is rendered separately
 * in CompanionPanel.
 *
 * Used by:
 * - /chat/[threadId] page (variant="full") — casual chat
 * - CaseWorkspace page (variant="panel") — case chat sidebar
 */

'use client';

import { useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { MessageList } from '@/components/chat/MessageList';
import { MessageInput } from '@/components/chat/MessageInput';
import { ChatModeHeader } from '@/components/chat/ChatModeHeader';
import { documentsAPI } from '@/lib/api/documents';
import { evidenceAPI } from '@/lib/api/evidence';
import { chatAPI } from '@/lib/api/chat';
import { useState } from 'react';
import { useChatPanelState } from '@/hooks/useChatPanelState';
import type { InlineCardActions } from '@/components/chat/cards/InlineActionCardRenderer';
import type { StreamingCallbacks } from '@/lib/types/streaming';
import type { ModeContext } from '@/lib/types/companion';
import type { InlineActionCard } from '@/lib/types/chat';

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
  /** Pre-fill chat input with this message (from deep-linking, e.g., "chat about" buttons) */
  prefillMessage?: string | null;
  /** Called after prefillMessage has been consumed */
  onPrefillConsumed?: () => void;
  /** Source context for "chat about" deep links (sent as part of message context) */
  chatSource?: { source_type: string; source_id: string } | null;
  /** Handle accepting a plan diff proposal from inline card */
  onAcceptPlanDiff?: (proposedContent: Record<string, unknown>, diffSummary: string, diffData: Record<string, unknown>) => void;
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
  prefillMessage,
  onPrefillConsumed,
  chatSource,
  onAcceptPlanDiff,
}: ChatPanelProps) {
  const router = useRouter();
  const state = useChatPanelState({
    threadId,
    onCreateCase,
    streamCallbacks,
    mode,
    chatSource,
    initialMessage,
    onInitialMessageSent,
  });

  const isFull = variant === 'full';
  const [briefToast, setBriefToast] = useState<string | null>(null);

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
    // Create evidence as a user observation linked to the active inquiry
    const inquiryId = mode?.mode === 'inquiry_focus' ? mode.inquiryId : undefined;
    if (!inquiryId) {
      setBriefToast('Focus on an inquiry to save evidence');
      setTimeout(() => setBriefToast(null), 3000);
      return;
    }
    try {
      await evidenceAPI.createForInquiry({
        inquiry_id: inquiryId,
        evidence_text: content,
        direction: 'neutral',
      });
      setBriefToast('Evidence saved to inquiry');
      setTimeout(() => setBriefToast(null), 3000);
    } catch (error) {
      console.error('Failed to create evidence:', error);
      setBriefToast('Failed to save evidence');
      setTimeout(() => setBriefToast(null), 3000);
    }
  }

  // --- Inline card action handlers ---

  // When the subtle suggestion card's "Structure as a case" is clicked:
  // Run the full analysis, then show a case_preview card with results.
  async function handleCreateCase(suggestedTitle?: string) {
    state.setCreatingCase(true);
    try {
      // Use the latest user message as focus context for the analysis
      const userMessages = state.messages.filter(m => m.role === 'user');
      const lastUserMessage = userMessages[userMessages.length - 1];
      const userFocus = lastUserMessage?.content;

      const analysis = await chatAPI.analyzeForCase(threadId, userFocus);

      // Add a case_preview card after the latest assistant message
      const assistantMessages = state.messages.filter(m => m.role === 'assistant');
      const lastAssistant = assistantMessages[assistantMessages.length - 1];
      if (lastAssistant) {
        const previewCard: InlineActionCard = {
          id: `case-preview-${Date.now()}`,
          type: 'case_preview',
          afterMessageId: lastAssistant.id,
          data: {
            suggestedTitle: analysis.suggested_title,
            positionDraft: analysis.position_draft,
            keyQuestions: analysis.key_questions,
            assumptions: analysis.assumptions,
            confidence: analysis.confidence,
            correlationId: analysis.correlation_id,
            decisionCriteria: analysis.success_criteria,
            assumptionTestStrategies: analysis.assumption_test_strategies,
            analysis,
          },
          createdAt: new Date().toISOString(),
        };
        state.addInlineCard(previewCard);
      }
    } catch (error) {
      console.error('Failed to analyze for case:', error);
    } finally {
      state.setCreatingCase(false);
    }
  }

  // When the preview card's "Create This Case" is clicked:
  async function handleCreateCaseFromPreview(analysis: Record<string, unknown>, title: string) {
    state.setCreatingCase(true);
    try {
      const result = await chatAPI.createCaseFromAnalysis(threadId, analysis, { title });
      router.push(`/cases/${result.case.id}`);
    } catch (error) {
      console.error('Failed to create case:', error);
      state.setCreatingCase(false);
    }
  }

  // When the preview card's "Adjust" is clicked:
  // Send a message to continue the shaping conversation
  function handleAdjustCasePreview() {
    state.sendMessage("I'd like to adjust the case structure. Can we refine the framing?");
  }

  // Memoize inline card actions to prevent re-renders
  const inlineCardActions: InlineCardActions = useMemo(() => ({
    onCreateCase: handleCreateCase,
    onCreateCaseFromPreview: handleCreateCaseFromPreview,
    onAdjustCasePreview: handleAdjustCasePreview,
    onAcceptPlanDiff: onAcceptPlanDiff,
    isCreatingCase: state.creatingCase,
    onDismissCard: state.dismissCard,
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [threadId, state.messages.length, onAcceptPlanDiff, state.creatingCase]);

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

  // --- Panel variant (sidebar) ---
  if (!isFull) {
    return (
      <div className="flex flex-col h-full bg-white">
        {/* Panel header */}
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

        {showModeHeader && mode && (
          <ChatModeHeader mode={mode} onExitFocus={onExitFocus} />
        )}

        {state.error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-3 mx-3 mt-2">
            <div className="flex items-start">
              <div className="flex-1">
                <p className="text-xs text-red-700">{state.error}</p>
                {state.lastFailedMessage && (
                  <button onClick={state.handleRetry} className="mt-1 text-xs font-medium text-red-700 hover:text-red-900 underline">
                    Retry message
                  </button>
                )}
              </div>
              <button onClick={state.clearError} className="ml-2 text-red-700 hover:text-red-900 text-xs">✕</button>
            </div>
          </div>
        )}

        <div className="flex-1 overflow-hidden flex flex-col">
          <div className="flex-1 overflow-y-auto">
            <MessageList
              messages={state.messages}
              isWaitingForResponse={state.isWaitingForResponse}
              isStreaming={state.isStreaming}
              ttft={state.ttft}
              onAddToBrief={briefId ? handleAddToBrief : undefined}
              onCreateEvidence={handleCreateEvidence}
              inlineCards={state.inlineCards}
              inlineCardActions={inlineCardActions}
            />
          </div>
        </div>

        <MessageInput
          onSend={state.sendMessage}
          disabled={state.isLoading}
          isProcessing={state.isLoading || state.isWaitingForResponse}
          isStreaming={state.isStreaming}
          onStop={state.stopGeneration}
          prefillValue={prefillMessage}
          onPrefillConsumed={onPrefillConsumed}
        />
      </div>
    );
  }

  // --- Full variant (Claude-style centered layout) ---
  return (
    <div className="flex flex-col h-full bg-white dark:bg-neutral-950">
      {/* Mode-aware context header */}
      {showModeHeader && mode && (
        <ChatModeHeader mode={mode} onExitFocus={onExitFocus} />
      )}

      {/* Error banner */}
      {state.error && (
        <div className="flex justify-center">
          <div className="w-full max-w-3xl px-4">
            <div className="bg-error-50 border-l-4 border-error-500 p-4 mt-3">
              <div className="flex items-start">
                <div className="flex-1">
                  <p className="text-sm text-error-700">{state.error}</p>
                  {state.lastFailedMessage && (
                    <button onClick={state.handleRetry} className="mt-2 text-sm font-medium text-error-700 hover:text-error-900 underline">
                      Retry message
                    </button>
                  )}
                </div>
                <button onClick={state.clearError} className="ml-4 text-error-700 hover:text-error-900">✕</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Brief integration toast */}
      {briefToast && (
        <div className="flex justify-center">
          <div className="w-full max-w-3xl px-4">
            <div className="px-3 py-1.5 bg-accent-50 border border-accent-200 rounded text-xs text-accent-700 text-center animate-in fade-in slide-in-from-top-1 mt-2">
              {briefToast}
            </div>
          </div>
        </div>
      )}

      {/* Structure as Case — subtle prompt after first exchange (user + assistant) in casual mode */}
      {state.messages.some(m => m.role === 'user') && state.messages.some(m => m.role === 'assistant') && (!mode || mode.mode === 'casual') && (
        <div className="flex justify-center">
          <div className="w-full max-w-2xl px-6">
            <button
              onClick={() => handleCreateCase()}
              disabled={state.creatingCase}
              className="flex items-center gap-1.5 px-2 py-1 text-xs text-neutral-400 hover:text-neutral-600 dark:text-neutral-500 dark:hover:text-neutral-300 transition-colors"
            >
              {state.creatingCase ? (
                <>
                  <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <span>Analyzing…</span>
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" />
                  </svg>
                  <span>Structure as Case</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Messages — scrollable, centered column (narrower than input for visual hierarchy) */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-2xl px-6 min-h-full">
          <MessageList
            messages={state.messages}
            isWaitingForResponse={state.isWaitingForResponse}
            isStreaming={state.isStreaming}
            ttft={state.ttft}
            onAddToBrief={briefId ? handleAddToBrief : undefined}
            onCreateEvidence={handleCreateEvidence}
            inlineCards={state.inlineCards}
            inlineCardActions={inlineCardActions}
            variant="full"
          />
        </div>
      </div>

      {/* Input — pinned to bottom, same centered width as messages */}
      <div className="bg-white dark:bg-neutral-950">
        <div className="mx-auto w-full max-w-3xl px-6 pb-4 pt-2">
          <MessageInput
            onSend={state.sendMessage}
            disabled={state.isLoading}
            isProcessing={state.isLoading || state.isWaitingForResponse}
            isStreaming={state.isStreaming}
            onStop={state.stopGeneration}
            mode={mode?.mode || 'casual'}
            variant="full"
            prefillValue={prefillMessage}
            onPrefillConsumed={onPrefillConsumed}
          />
        </div>
      </div>
    </div>
  );
}
