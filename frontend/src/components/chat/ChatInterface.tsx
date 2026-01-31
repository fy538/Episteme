/**
 * Main chat interface component
 */

'use client';

import { useState, useEffect } from 'react';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { chatAPI } from '@/lib/api/chat';
import type { Message } from '@/lib/types/chat';

export function ChatInterface({ threadId }: { threadId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
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
    const interval = setInterval(async () => {
      try {
        const msgs = await chatAPI.getMessages(threadId);
        setMessages(msgs);
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [threadId]);

  async function handleSendMessage(content: string) {
    setIsLoading(true);
    setError(null); // Clear previous errors
    try {
      // Send message
      const userMessage = await chatAPI.sendMessage(threadId, content);
      
      // Add to list immediately (optimistic update)
      setMessages(prev => [...prev, userMessage]);
      
      // Assistant response will appear via polling
    } catch (error) {
      console.error('Failed to send message:', error);
      setError(error instanceof Error ? error.message : 'Failed to send message. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="border-b border-gray-200 p-4">
        <h1 className="text-lg font-semibold text-gray-900">Chat</h1>
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
      <MessageList messages={messages} />
      <MessageInput onSend={handleSendMessage} disabled={isLoading} />
    </div>
  );
}
