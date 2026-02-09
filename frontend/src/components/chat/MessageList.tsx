/**
 * Message list component - displays chat messages with inline action cards
 *
 * Supports two variants:
 * - default (panel): Compact chat bubbles for sidebar
 * - full: Claude-style layout — no box around AI messages, user messages
 *   have a subtle background, smaller font, messages pushed to bottom
 */

import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import type { Message as MessageType, InlineActionCard } from '@/lib/types/chat';
import type { CardAction } from '@/lib/types/cards';
import { Streamdown } from 'streamdown';
import remarkGfm from 'remark-gfm';
import { CardRenderer } from './cards/CardRenderer';
import { InlineActionCardRenderer, type InlineCardActions } from './cards/InlineActionCardRenderer';
import { MessageListSkeleton } from '@/components/ui/skeleton';
import { useReducedMotion } from '@/hooks/useReducedMotion';

// Separate Message component to call hooks at top level
function Message({
  message,
  onAddToBrief,
  onCardAction,
  index,
  variant = 'default',
}: {
  message: MessageType;
  onAddToBrief?: (messageId: string, content: string) => void;
  onCardAction?: (action: CardAction, messageId: string) => void;
  index: number;
  variant?: 'default' | 'full';
}) {
  const prefersReducedMotion = useReducedMotion();
  const isStreamingMsg = message.metadata?.streaming === true;
  const isRichMessage = message.is_rich_content && message.structured_content;
  const showActions = message.role === 'assistant' && !isStreamingMsg && !isRichMessage && message.content.length > 20;
  const isFull = variant === 'full';

  const handleCardAction = (action: CardAction) => {
    if (onCardAction) {
      onCardAction(action, message.id);
    }
  };

  // --- Full variant (Claude-style) ---
  if (isFull) {
    const messageContent = (
      <div className={`group ${message.role === 'user' ? 'flex justify-end' : ''}`}>
        {message.role === 'user' ? (
          // User message: right-aligned, subtle rounded rectangle
          <div className="max-w-[85%] rounded-lg px-4 py-2.5 bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100">
            <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{message.content}</p>
          </div>
        ) : isRichMessage ? (
          // Rich card: full width, no box
          <div className="w-full">
            <CardRenderer
              card={message.structured_content!}
              onAction={handleCardAction}
            />
          </div>
        ) : (
          // Assistant message: no box, just text, left-aligned
          <div className="w-full">
            {message.content.trim() === '' && isStreamingMsg ? (
              <div className="flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400 py-1">
                <span className="inline-flex gap-1">
                  <span className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '-0.2s' }} />
                  <span className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce" />
                  <span className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                </span>
              </div>
            ) : (
              <div className="prose prose-sm max-w-none dark:prose-invert text-[15px] leading-relaxed text-neutral-800 dark:text-neutral-200 prose-p:text-[15px] prose-p:leading-relaxed prose-p:text-neutral-800 dark:prose-p:text-neutral-200 prose-headings:text-neutral-900 dark:prose-headings:text-neutral-100 prose-li:text-[15px] prose-code:text-[13px] prose-pre:text-[13px]">
                <Streamdown
                  remarkPlugins={[remarkGfm]}
                  parseIncompleteMarkdown={isStreamingMsg}
                  isAnimating={isStreamingMsg}
                  shikiTheme={['min-light', 'min-dark']}
                >
                  {message.content}
                </Streamdown>
              </div>
            )}

            {/* Action buttons (show on hover) */}
            {showActions && (
              <div className="opacity-0 group-hover:opacity-100 transition-opacity mt-2 flex gap-2">
                {onAddToBrief && (
                  <button
                    onClick={() => onAddToBrief(message.id, message.content)}
                    className="text-xs px-2 py-1 text-neutral-500 hover:text-accent-600 hover:bg-accent-50 rounded transition-colors dark:text-neutral-400 dark:hover:text-accent-400 dark:hover:bg-accent-900/30"
                  >
                    Add to Brief
                  </button>
                )}
                <button
                  onClick={() => navigator.clipboard.writeText(message.content)}
                  className="text-xs px-2 py-1 text-neutral-500 hover:text-neutral-700 hover:bg-neutral-100 rounded transition-colors dark:text-neutral-400 dark:hover:text-neutral-300 dark:hover:bg-neutral-800"
                >
                  Copy
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    );

    if (prefersReducedMotion) return messageContent;

    return (
      <motion.div
        key={message.id}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{
          duration: 0.25,
          delay: index < 3 ? index * 0.08 : 0,
          ease: [0.22, 1, 0.36, 1],
        }}
      >
        {messageContent}
      </motion.div>
    );
  }

  // --- Default variant (panel/sidebar) ---
  const messageContent = (
    <div className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} group`}>
      <div
        className={`${isRichMessage ? 'w-full max-w-3xl' : 'max-w-2xl'} rounded-lg ${isRichMessage ? '' : 'px-4 py-3'} ${
          message.role === 'user'
            ? 'bg-accent-600 text-white'
            : isRichMessage
            ? ''  // No background for rich cards
            : 'bg-neutral-100 text-neutral-900 dark:bg-primary-800 dark:text-primary-50'
        }`}
      >
        {message.role === 'assistant' && isRichMessage ? (
          <CardRenderer
            card={message.structured_content!}
            onAction={handleCardAction}
          />
        ) : message.role === 'assistant' ? (
          message.content.trim() === '' && isStreamingMsg ? (
            <div className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400">
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
        {showActions && (
          <div className="opacity-0 group-hover:opacity-100 transition-opacity mt-2 flex gap-2">
            {onAddToBrief && (
              <button
                onClick={() => onAddToBrief(message.id, message.content)}
                className="text-xs px-2 py-1 bg-accent-50 text-accent-700 rounded hover:bg-accent-100 transition-colors dark:bg-accent-900 dark:text-accent-200"
              >
                Add to Brief
              </button>
            )}
            <button
              onClick={() => navigator.clipboard.writeText(message.content)}
              className="text-xs px-2 py-1 bg-neutral-50 text-neutral-700 rounded hover:bg-neutral-100 transition-colors dark:bg-neutral-800 dark:text-neutral-300"
            >
              Copy
            </button>
          </div>
        )}
      </div>
    </div>
  );

  // Skip animation for reduced motion
  if (prefersReducedMotion) {
    return messageContent;
  }

  // Stagger animation for new messages
  return (
    <motion.div
      key={message.id}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.3,
        delay: index < 3 ? index * 0.1 : 0,
        ease: [0.22, 1, 0.36, 1],
      }}
    >
      {messageContent}
    </motion.div>
  );
}

export function MessageList({
  messages,
  isWaitingForResponse,
  isStreaming,
  ttft,
  onAddToBrief,
  onCardAction,
  isLoading,
  inlineCards = [],
  inlineCardActions = {},
  variant = 'default',
}: {
  messages: MessageType[];
  isWaitingForResponse?: boolean;
  isStreaming?: boolean;
  ttft?: number | null;
  onAddToBrief?: (messageId: string, content: string) => void;
  onCardAction?: (action: CardAction, messageId: string) => void;
  isLoading?: boolean;
  inlineCards?: InlineActionCard[];
  inlineCardActions?: InlineCardActions;
  variant?: 'default' | 'full';
}) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const isFull = variant === 'full';

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isWaitingForResponse]);

  // Show skeleton during initial load
  if (isLoading) {
    return <MessageListSkeleton />;
  }

  if (messages.length === 0 && !isFull) {
    return (
      <div className="flex-1 flex items-center justify-center text-neutral-500 dark:text-neutral-400">
        <p>Start a conversation...</p>
      </div>
    );
  }

  // Get cards for a specific message
  const getCardsForMessage = (messageId: string) => {
    return inlineCards.filter(
      (card) => card.afterMessageId === messageId && !card.dismissed
    );
  };

  // Full variant: use flex-col with spacer to push messages to bottom when few
  if (isFull) {
    return (
      <div className="flex flex-col min-h-full">
        {/* Spacer: pushes messages toward bottom when there are few */}
        <div className="flex-1" />

        {/* Messages */}
        <div className="space-y-5 py-6">
          {messages.length === 0 && (
            <div className="flex items-center justify-center py-20 text-neutral-400 dark:text-neutral-500">
              <p className="text-sm">Start a conversation...</p>
            </div>
          )}
          {messages.map((message, index) => (
            <div key={message.id}>
              <Message
                message={message}
                index={index}
                onAddToBrief={onAddToBrief}
                onCardAction={onCardAction}
                variant="full"
              />
              {getCardsForMessage(message.id).map((card) => (
                <InlineActionCardRenderer
                  key={card.id}
                  card={card}
                  actions={inlineCardActions}
                />
              ))}
            </div>
          ))}
          {isWaitingForResponse && !isStreaming && (
            <div className="flex items-center gap-2 text-sm text-neutral-500 py-1">
              <span className="inline-flex gap-1">
                <span className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '-0.2s' }} />
                <span className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce" />
                <span className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
              </span>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>
    );
  }

  // Default (panel) variant
  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {messages.map((message, index) => (
        <div key={message.id}>
          <Message
            message={message}
            index={index}
            onAddToBrief={onAddToBrief}
            onCardAction={onCardAction}
            variant="default"
          />
          {getCardsForMessage(message.id).map((card) => (
            <InlineActionCardRenderer
              key={card.id}
              card={card}
              actions={inlineCardActions}
            />
          ))}
        </div>
      ))}
      {isWaitingForResponse && !isStreaming && (
        <div className="flex justify-start">
          <div className="max-w-2xl rounded-lg px-4 py-3 bg-neutral-100 text-neutral-900">
            <div className="flex items-center gap-2 text-sm text-neutral-600">
              <span className="inline-flex gap-1">
                <span className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '-0.2s' }} />
                <span className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce" />
                <span className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
              </span>
            </div>
          </div>
        </div>
      )}
      {isStreaming && ttft !== null && (
        <div className="text-xs text-neutral-400 py-1">
          TTFT: {ttft}ms
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
