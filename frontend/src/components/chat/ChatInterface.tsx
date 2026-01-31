/**
 * Main chat interface component
 */

'use client';

import { useState, useEffect, startTransition } from 'react';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { chatAPI } from '@/lib/api/chat';
import type { Message } from '@/lib/types/chat';

export function ChatInterface({
  threadId,
  onToggleLeft,
  onToggleRight,
  leftCollapsed,
  rightCollapsed,
  projects,
  projectId,
  onProjectChange,
}: {
  threadId: string;
  onToggleLeft?: () => void;
  onToggleRight?: () => void;
  leftCollapsed?: boolean;
  rightCollapsed?: boolean;
  projects?: { id: string; title: string }[];
  projectId?: string | null;
  onProjectChange?: (projectId: string | null) => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [pendingSince, setPendingSince] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [ttft, setTtft] = useState<number | null>(null);

  // Load messages on mount
  useEffect(() => {
    async function loadMessages() {
      try {
        const msgs = await chatAPI.getMessages(threadId);
        setMessages(msgs);
        setError(null); // Clear any previous errors
      } catch (error) {
        console.error('Failed to load messages:', error);
        setError(error instanceof Error ? error.message : 'Failed to load messages');
      }
    }
    loadMessages();
  }, [threadId]);

  // Poll for new messages (assistant responses)
  useEffect(() => {
    // Pause polling during streaming or when loading (optimistic messages active)
    if (isStreaming || isLoading) return;
    
    const interval = setInterval(async () => {
      try {
        const msgs = await chatAPI.getMessages(threadId);
        
        // Deduplicate: only update if we got new messages
        setMessages(prev => {
          const existingIds = new Set(prev.map(m => m.id));
          const newMessages = msgs.filter(m => !existingIds.has(m.id));
          
          if (newMessages.length === 0 && prev.length === msgs.length) {
            return prev; // No changes, skip update
          }
          
          return msgs; // Full replace only if there are real changes
        });
        
        if (isWaitingForResponse && pendingSince) {
          const hasNewAssistant = msgs.some(
            msg =>
              msg.role === 'assistant' &&
              new Date(msg.created_at).getTime() > pendingSince
          );
          if (hasNewAssistant) {
            setIsWaitingForResponse(false);
            setPendingSince(null);
          }
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [threadId, isStreaming, isLoading, isWaitingForResponse, pendingSince]);

  async function handleSendMessage(content: string) {
    setIsLoading(true);
    setIsWaitingForResponse(true);
    const requestStart = Date.now();
    setPendingSince(requestStart);
    setError(null);
    setTtft(null);
    
    // Create AbortController for cancellation
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
            // Track TTFT (time to first token)
            if (!firstTokenReceived) {
              const ttftMs = Date.now() - requestStart;
              setTtft(ttftMs);
              console.log(`[Chat] TTFT: ${ttftMs}ms`);
              firstTokenReceived = true;
            }
            
            // Use startTransition to batch rapid token updates (non-urgent)
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
            
            // Replace temp IDs with real message ID (no refetch needed)
            if (messageId) {
              setMessages(prev =>
                prev.map(msg => {
                  if (msg.id === tempAssistantId) {
                    return { ...msg, id: messageId, metadata: { ...msg.metadata, streaming: false } };
                  }
                  if (msg.id === tempUserId) {
                    // User message is already saved, just keep optimistic for now
                    // Polling will eventually replace it with real ID
                    return msg;
                  }
                  return msg;
                })
              );
            }
          },
          controller.signal
        );
      } catch (streamError) {
        // Check if aborted by user
        if (streamError instanceof Error && streamError.name === 'AbortError') {
          console.log('[Chat] Stream aborted by user');
          setIsStreaming(false);
          setIsWaitingForResponse(false);
          setPendingSince(null);
          return; // Don't fallback, user cancelled
        }
        
        // Fallback to non-streaming if stream isn't available
        console.warn('Streaming unavailable, falling back to polling.', streamError);
        setIsStreaming(false);

        setMessages(prev =>
          prev.filter(msg => msg.id !== tempAssistantId && msg.id !== tempUserId)
        );

        const userMessage = await chatAPI.sendMessage(threadId, content);
        setMessages(prev => [...prev, userMessage]);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setError(error instanceof Error ? error.message : 'Failed to send message. Please try again.');
      setIsWaitingForResponse(false);
      setIsStreaming(false);
      setPendingSince(null);
    } finally {
      setIsLoading(false);
      setAbortController(null);
    }
  }

  function handleStopGeneration() {
    if (abortController) {
      console.log('[Chat] Aborting stream');
      abortController.abort();
      setAbortController(null);
      setIsStreaming(false);
      setIsWaitingForResponse(false);
      setIsLoading(false);
      
      // Clean up optimistic assistant message
      setMessages(prev =>
        prev.filter(msg => msg.metadata?.streaming !== true)
      );
    }
  }

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="border-b border-gray-200 p-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-gray-900">Chat</h1>
          {projects && onProjectChange && (
            <label className="text-xs text-gray-600 flex items-center gap-2">
              Project
              <select
                value={projectId || ''}
                onChange={(e) => onProjectChange(e.target.value || null)}
                className="text-xs border border-gray-300 rounded px-2 py-1"
              >
                <option value="">No Project</option>
                {projects.map(project => (
                  <option key={project.id} value={project.id}>
                    {project.title}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        <div className="flex items-center gap-2">
          {onToggleLeft && (
            <button
              onClick={onToggleLeft}
              className="text-xs px-2 py-1 border rounded hover:bg-gray-50"
            >
              {leftCollapsed ? 'Show Conversations' : 'Hide Conversations'}
            </button>
          )}
          {onToggleRight && (
            <button
              onClick={onToggleRight}
              className="text-xs px-2 py-1 border rounded hover:bg-gray-50"
            >
              {rightCollapsed ? 'Show Structure' : 'Hide Structure'}
            </button>
          )}
        </div>
      </div>
      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 mx-4 mt-4">
          <div className="flex">
            <div className="flex-1">
              <p className="text-sm text-red-700">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="ml-4 text-red-700 hover:text-red-900"
            >
              ✕
            </button>
          </div>
        </div>
      )}
      <MessageList 
        messages={messages} 
        isWaitingForResponse={isWaitingForResponse}
        isStreaming={isStreaming}
        ttft={ttft}
      />
      <MessageInput 
        onSend={handleSendMessage} 
        disabled={isLoading} 
        isProcessing={isLoading || isWaitingForResponse}
        isStreaming={isStreaming}
        onStop={handleStopGeneration}
      />
    </div>
  );
}
