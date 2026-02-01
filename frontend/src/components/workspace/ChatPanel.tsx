/**
 * Chat panel for workspace - Cursor-style AI companion
 * Always accessible, collapsible, context-aware
 */

'use client';

import { useState, useEffect, useRef, startTransition } from 'react';
import { MessageList } from '@/components/chat/MessageList';
import { MessageInput } from '@/components/chat/MessageInput';
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
  onIntegrationPreview?: (result: any) => void;
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
            
            // Suggest case creation after 4 turns (user has sent 4 messages)
            if (conversationTurns.current >= 4 && onCreateCase && !showCaseSuggestion) {
              setShowCaseSuggestion(true);
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
      } catch (error: any) {
        if (error.name !== 'AbortError') {
          console.error('Stream error:', error);
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
      <div className="w-16 flex flex-col items-center py-4 bg-gray-50 border-l border-gray-200">
        <button
          onClick={() => setIsCollapsed(false)}
          className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
          aria-label="Expand chat"
        >
          <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        
        {signals.length > 0 && (
          <div className="mt-4 px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
            {signals.length}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="w-96 flex flex-col h-full bg-white">
      {/* Chat Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <h3 className="text-sm font-medium text-gray-900">{contextLabel}</h3>
        {!hideCollapse && (
          <button
            onClick={() => setIsCollapsed(true)}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
            aria-label="Collapse chat"
          >
            <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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

        {/* Case suggestion prompt */}
        {showCaseSuggestion && onCreateCase && (
          <div className="mx-4 mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-900 mb-3">
              It seems you're exploring something substantial. Would you like to create a Case to organize your thinking?
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  onCreateCase();
                  setShowCaseSuggestion(false);
                }}
                className="px-3 py-1 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                Create Case
              </button>
              <button
                onClick={() => setShowCaseSuggestion(false)}
                className="px-3 py-1 text-blue-700 text-sm hover:bg-blue-100 rounded transition-colors"
              >
                Not now
              </button>
            </div>
          </div>
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
        <div className="border-t border-gray-200">
          <button
            onClick={() => setSignalsExpanded(!signalsExpanded)}
            className="w-full flex items-center justify-between px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
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
            <div className="px-4 py-3 max-h-48 overflow-y-auto bg-gray-50">
              <div className="space-y-2">
                {signals.map(signal => (
                  <div key={signal.id} className="text-xs p-2 bg-white border border-gray-200 rounded">
                    <span className="font-medium text-gray-700">{signal.signal_type}:</span>
                    <span className="text-gray-600 ml-1">{signal.content}</span>
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
