/**
 * Chat panel for workspace - Cursor-style AI companion
 * Always accessible, collapsible, context-aware
 */

'use client';

import { useState, useEffect, useRef, startTransition } from 'react';
import { MessageList } from '@/components/chat/MessageList';
import { MessageInput } from '@/components/chat/MessageInput';
import { CaseCreationPreview } from '@/components/cases/CaseCreationPreview';
import { CaseAssemblyAnimation } from '@/components/cases/CaseAssemblyAnimation';
import { chatAPI } from '@/lib/api/chat';
import { signalsAPI } from '@/lib/api/signals';
import type { Message } from '@/lib/types/chat';
import type { Signal } from '@/lib/types/signal';

interface ChatPanelProps {
  threadId: string;
  contextLabel?: string;  // e.g., "Chat about: Market Entry Case"
  onCreateInquiry?: (signalIds: string[]) => void;
  onCreateCase?: () => void;
  hideCollapse?: boolean;  // For standalone chat mode
  briefId?: string;  // Current brief for "Add to Brief" action
  onIntegrationPreview?: (result: Record<string, unknown>) => void;
}

export function ChatPanel({ 
  threadId, 
  contextLabel = 'AI Chat',
  onCreateInquiry,
  onCreateCase,
  hideCollapse = false,
  briefId,
  onIntegrationPreview,
}: ChatPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [signalsExpanded, setSignalsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [pendingSince, setPendingSince] = useState<number | null>(null);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [ttft, setTtft] = useState<number | null>(null);
  const [showCaseSuggestion, setShowCaseSuggestion] = useState(false);
  const [caseAnalysis, setCaseAnalysis] = useState<any>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [creatingCase, setCreatingCase] = useState(false);
  const [showAssembly, setShowAssembly] = useState(false);
  const conversationTurns = useRef(0);

  // Load messages
  useEffect(() => {
    async function loadMessages() {
      setIsLoading(true);
      try {
        const msgs = await chatAPI.getMessages(threadId);
        setMessages(msgs);
      } catch (error) {
        console.error('Failed to load messages:', error);
      } finally {
        setIsLoading(false);
      }
    }
    loadMessages();
  }, [threadId]);

  // Load signals
  useEffect(() => {
    async function loadSignals() {
      try {
        const sigs = await signalsAPI.getByThread(threadId);
        setSignals(sigs);
      } catch (error) {
        console.error('Failed to load signals:', error);
      }
    }
    loadSignals();
    const interval = setInterval(loadSignals, 15000);
    return () => clearInterval(interval);
  }, [threadId]);

  async function handleSendMessage(content: string) {
    setIsLoading(true);
    setIsWaitingForResponse(true);
    const requestStart = Date.now();
    setPendingSince(requestStart);
    setTtft(null);
    
    const controller = new AbortController();
    setAbortController(controller);
    
    try {
      const now = new Date().toISOString();
      const tempUserId = `local-user-${Date.now()}`;
      const tempAssistantId = `local-assistant-${Date.now()}`;

      const optimisticUserMessage: Message = {
        id: tempUserId,
        thread: threadId,
        role: 'user',
        content,
        event_id: '',
        metadata: {},
        created_at: now,
      };

      const optimisticAssistantMessage: Message = {
        id: tempAssistantId,
        thread: threadId,
        role: 'assistant',
        content: '',
        event_id: '',
        metadata: { streaming: true },
        created_at: now,
      };

      setMessages(prev => [...prev, optimisticUserMessage, optimisticAssistantMessage]);
      setIsStreaming(true);

      let firstTokenReceived = false;

      try {
        await chatAPI.sendMessageStream(
          threadId,
          content,
          (delta) => {
            if (!firstTokenReceived) {
              const ttftMs = Date.now() - requestStart;
              setTtft(ttftMs);
              firstTokenReceived = true;
            }
            
            startTransition(() => {
              setMessages(prev =>
                prev.map(msg =>
                  msg.id === tempAssistantId
                    ? { ...msg, content: `${msg.content}${delta}` }
                    : msg
                )
              );
            });
          },
          async (messageId) => {
            setIsWaitingForResponse(false);
            setIsStreaming(false);
            setPendingSince(null);
            
            // Track conversation turns for case suggestion
            conversationTurns.current += 1;
            
            // Trigger analysis after 4 turns
            if (conversationTurns.current >= 4 && onCreateCase && !showCaseSuggestion && !analyzing) {
              triggerCaseAnalysis();
            }
            
            async function triggerCaseAnalysis() {
              setAnalyzing(true);
              try {
                const analysis = await chatAPI.analyzeForCase(threadId);
                setCaseAnalysis(analysis);
                setShowCaseSuggestion(true);
              } catch (error) {
                console.error('Failed to analyze for case:', error);
              } finally {
                setAnalyzing(false);
              }
            }
            
            if (messageId) {
              setMessages(prev =>
                prev.map(msg => {
                  if (msg.id === tempAssistantId) {
                    return { ...msg, id: messageId, metadata: { ...msg.metadata, streaming: false } };
                  }
                  return msg;
                })
              );
            }
          },
          controller.signal
        );
      } catch (error) {
        if (error instanceof Error && error.name !== 'AbortError') {
          // Stream error occurred
          setMessages(prev => prev.filter(m => m.id !== tempAssistantId));
        }
        setIsWaitingForResponse(false);
        setIsStreaming(false);
        setPendingSince(null);
      }
    } catch (error) {
      console.error('Send error:', error);
    } finally {
      setIsLoading(false);
      setAbortController(null);
    }
  }

  function handleStop() {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
      setIsStreaming(false);
      setIsWaitingForResponse(false);
    }
  }

  async function handleAddToBrief(messageId: string, content: string) {
    if (!briefId) {
      alert('No brief available in this context');
      return;
    }

    try {
      const { documentsAPI } = await import('@/lib/api/documents');
      const result = await documentsAPI.integrateContent(
        briefId,
        content,
        'general',
        messageId
      );
      
      onIntegrationPreview?.(result);
    } catch (error) {
      console.error('Failed to integrate content:', error);
      alert('Failed to integrate content. Please try again.');
    }
  }

  async function handleCreateEvidence(content: string) {
    // TODO: Implement evidence creation
    console.log('Create evidence from:', content);
    alert('Evidence creation coming soon!');
  }

  if (isCollapsed && !hideCollapse) {
    return (
      <div className="w-16 flex flex-col items-center py-4 bg-neutral-50 border-l border-neutral-200">
        <button
          onClick={() => setIsCollapsed(false)}
          className="p-2 hover:bg-neutral-200 rounded-lg transition-colors"
          aria-label="Expand chat"
        >
          <svg className="w-5 h-5 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        
        {signals.length > 0 && (
          <div className="mt-4 px-2 py-1 bg-accent-100 text-accent-700 rounded-full text-xs font-medium">
            {signals.length}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="w-96 flex flex-col h-full bg-white">
      {/* Chat Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200">
        <h3 className="text-sm font-medium text-neutral-900">{contextLabel}</h3>
        {!hideCollapse && (
          <button
            onClick={() => setIsCollapsed(true)}
            className="p-1 hover:bg-neutral-100 rounded transition-colors"
            aria-label="Collapse chat"
          >
            <svg className="w-4 h-4 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto">
          <MessageList
            messages={messages}
            isWaitingForResponse={isWaitingForResponse}
            isStreaming={isStreaming}
            ttft={ttft}
            onAddToBrief={briefId ? handleAddToBrief : undefined}
            onCreateEvidence={handleCreateEvidence}
          />
        </div>

        {/* Smart case suggestion with preview */}
        {showCaseSuggestion && caseAnalysis && (
          <CaseCreationPreview
            analysis={caseAnalysis}
            onConfirm={async (edits) => {
              setCreatingCase(true);
              try {
                const result = await chatAPI.createCaseFromAnalysis(
                  threadId,
                  caseAnalysis,
                  edits
                );
                
                setShowCaseSuggestion(false);
                setShowAssembly(true);
                
                // After assembly animation, navigate
                setTimeout(() => {
                  window.location.href = `/workspace/cases/${result.case.id}`;
                }, 3000);
              } catch (error) {
                console.error('Failed to create case:', error);
                setCreatingCase(false);
              }
            }}
            onDismiss={() => setShowCaseSuggestion(false)}
            isCreating={creatingCase}
          />
        )}
        
        {/* Assembly animation */}
        {showAssembly && (
          <CaseAssemblyAnimation
            onComplete={() => {
              // Animation completes, navigation happens via setTimeout above
            }}
          />
        )}
      </div>

      {/* Message Input */}
      <MessageInput
        onSend={handleSendMessage}
        disabled={isLoading}
        isProcessing={isLoading}
        isStreaming={isStreaming}
        onStop={handleStop}
      />

      {/* Collapsible Signals */}
      {signals.length > 0 && (
        <div className="border-t border-neutral-200">
          <button
            onClick={() => setSignalsExpanded(!signalsExpanded)}
            className="w-full flex items-center justify-between px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
          >
            <span>Signals ({signals.length})</span>
            <svg
              className={`w-4 h-4 transition-transform ${signalsExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {signalsExpanded && (
            <div className="px-4 py-3 max-h-48 overflow-y-auto bg-neutral-50">
              <div className="space-y-2">
                {signals.map(signal => (
                  <div key={signal.id} className="text-xs p-2 bg-white border border-neutral-200 rounded">
                    <span className="font-medium text-neutral-700">{signal.signal_type}:</span>
                    <span className="text-neutral-600 ml-1">{signal.content}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
