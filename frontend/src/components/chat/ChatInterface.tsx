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

  // Load messages on mount
  useEffect(() => {
    async function loadMessages() {
      try {
        const msgs = await chatAPI.getMessages(threadId);
        setMessages(msgs);
      } catch (error) {
        console.error('Failed to load messages:', error);
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
    try {
      // Send message
      const userMessage = await chatAPI.sendMessage(threadId, content);
      
      // Add to list immediately (optimistic update)
      setMessages(prev => [...prev, userMessage]);
      
      // Assistant response will appear via polling
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="border-b border-gray-200 p-4">
        <h1 className="text-lg font-semibold text-gray-900">Chat</h1>
      </div>
      <MessageList messages={messages} />
      <MessageInput onSend={handleSendMessage} disabled={isLoading} />
    </div>
  );
}
