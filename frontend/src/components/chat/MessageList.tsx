/**
 * Message list component - displays chat messages
 */

import { useEffect, useRef } from 'react';
import type { Message } from '@/lib/types/chat';
import { Streamdown } from 'streamdown';
import remarkGfm from 'remark-gfm';

export function MessageList({
  messages,
  isWaitingForResponse,
  isStreaming,
  ttft,
  onAddToBrief,
  onCreateEvidence,
}: {
  messages: Message[];
  isWaitingForResponse?: boolean;
  isStreaming?: boolean;
  ttft?: number | null;
  onAddToBrief?: (messageId: string, content: string) => void;
  onCreateEvidence?: (content: string) => void;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isWaitingForResponse]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-neutral-500">
        <p>Start a conversation...</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {messages.map(message => {
        const isStreamingMsg = message.metadata?.streaming === true;
        const showActions = message.role === 'assistant' && !isStreamingMsg && message.content.length > 20;
        
        return (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} group`}
          >
            <div
              className={`max-w-2xl rounded-lg px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-accent-600 text-white'
                  : 'bg-neutral-100 text-neutral-900'
              }`}
            >
              {message.role === 'assistant' ? (
                message.content.trim() === '' && isStreamingMsg ? (
                  <div className="flex items-center gap-2 text-sm text-neutral-600">
                    <span className="inline-flex gap-1">
                      <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '-0.2s' }} />
                      <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" />
                      <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                    </span>
                    <span>Thinking...</span>
                  </div>
                ) : (
                  <div className="prose prose-sm max-w-none dark:prose-invert">
                    <Streamdown
                      remarkPlugins={[remarkGfm]}
                      parseIncompleteMarkdown={isStreamingMsg}
                      isAnimating={isStreamingMsg}
                      shikiTheme={['min-light', 'min-dark']}
                    >
                      {message.content}
                    </Streamdown>
                  </div>
                )
              ) : (
                <p className="whitespace-pre-wrap">{message.content}</p>
              )}
              
              {/* Action buttons (show on hover) */}
              {showActions && (onAddToBrief || onCreateEvidence) && (
                <div className="opacity-0 group-hover:opacity-100 transition-opacity mt-2 flex gap-2">
                  {onAddToBrief && (
                    <button
                      onClick={() => onAddToBrief(message.id, message.content)}
                      className="text-xs px-2 py-1 bg-blue-50 text-blue-700 rounded hover:bg-blue-100 transition-colors"
                    >
                      Add to Brief
                    </button>
                  )}
                  {onCreateEvidence && (
                    <button
                      onClick={() => onCreateEvidence(message.content)}
                      className="text-xs px-2 py-1 bg-success-50 text-success-700 rounded hover:bg-success-100 transition-colors"
                    >
                      Create Evidence
                    </button>
                  )}
                  <button
                    onClick={() => navigator.clipboard.writeText(message.content)}
                    className="text-xs px-2 py-1 bg-neutral-50 text-neutral-700 rounded hover:bg-neutral-100 transition-colors"
                  >
                    Copy
                  </button>
                </div>
              )}
            </div>
          </div>
        );
      })}
      {isWaitingForResponse && !isStreaming && (
        <div className="flex justify-start">
          <div className="max-w-2xl rounded-lg px-4 py-3 bg-neutral-100 text-neutral-900">
            <div className="flex items-center gap-2 text-sm text-neutral-600">
              <span className="inline-flex gap-1">
                <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '-0.2s' }} />
                <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" />
                <span className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
              </span>
              <span>Waiting for response...</span>
            </div>
          </div>
        </div>
      )}
      {isStreaming && ttft !== null && (
        <div className="text-xs text-neutral-400 px-4 py-1">
          Streaming (TTFT: {ttft}ms)
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
