/**
 * Main chat interface component
 */

'use client';

import { useState, useEffect } from 'react';
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
    if (isStreaming) return;
    const interval = setInterval(async () => {
      try {
        const msgs = await chatAPI.getMessages(threadId);
        setMessages(msgs);
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
  }, [threadId, isStreaming, isWaitingForResponse, pendingSince]);

  async function handleSendMessage(content: string) {
    setIsLoading(true);
    setIsWaitingForResponse(true);
    setPendingSince(Date.now());
    setError(null); // Clear previous errors
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

      try {
        await chatAPI.sendMessageStream(
          threadId,
          content,
          (delta) => {
            setMessages(prev =>
              prev.map(msg =>
                msg.id === tempAssistantId
                  ? { ...msg, content: `${msg.content}${delta}` }
                  : msg
              )
            );
          },
          async () => {
            setIsWaitingForResponse(false);
            setIsStreaming(false);
            setPendingSince(null);
            const msgs = await chatAPI.getMessages(threadId);
            setMessages(msgs);
          }
        );
      } catch (streamError) {
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
      <MessageList messages={messages} isWaitingForResponse={isWaitingForResponse} />
      <MessageInput onSend={handleSendMessage} disabled={isLoading} isProcessing={isLoading || isWaitingForResponse} />
    </div>
  );
}
