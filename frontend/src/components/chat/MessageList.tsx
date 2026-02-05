/**
 * Message list component - displays chat messages with inline action cards
 */

import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import type { Message as MessageType, InlineActionCard } from '@/lib/types/chat';
import type { CardAction } from '@/lib/types/cards';
import { Streamdown } from 'streamdown';
import remarkGfm from 'remark-gfm';
import { SignalHighlighter, type HighlightedSignal } from './SignalHighlighter';
import { useSignalsForMessage, useDismissSignal } from '@/hooks/useSignals';
import { useUserPreferences } from '@/hooks/usePreferences';
import { CardRenderer } from './cards/CardRenderer';
import { InlineActionCardRenderer, type InlineCardActions } from './cards/InlineActionCardRenderer';
import { MessageListSkeleton } from '@/components/ui/skeleton';
import { useReducedMotion } from '@/hooks/useReducedMotion';

// Separate Message component to call hooks at top level
function Message({ 
  message, 
  onAddToBrief, 
  onCreateEvidence,
  onCardAction,
  index,
}: { 
  message: MessageType;
  onAddToBrief?: (messageId: string, content: string) => void;
  onCreateEvidence?: (content: string) => void;
  onCardAction?: (action: CardAction, messageId: string) => void;
  index: number;
}) {
  const prefersReducedMotion = useReducedMotion();
  const isStreamingMsg = message.metadata?.streaming === true;
  const isRichMessage = message.is_rich_content && message.structured_content;
  const showActions = message.role === 'assistant' && !isStreamingMsg && !isRichMessage && message.content.length > 20;
  
  // Fetch signals for this message (hook at top level)
  const { data: signals = [] } = useSignalsForMessage(
    message.id,
    message.role === 'assistant' && !isStreamingMsg
  );

  const { data: userPreferences } = useUserPreferences();
  const dismissSignal = useDismissSignal();

  // Check if signal highlighting is enabled
  const highlightSignals = 
    message.role === 'assistant' &&
    !isStreamingMsg &&
    userPreferences && 
    signals.length > 0 &&
    (userPreferences.highlight_assumptions ||
     userPreferences.highlight_questions ||
     userPreferences.highlight_evidence);

  const handleDismissSignal = (signalId: string) => {
    dismissSignal.mutate(signalId);
  };

  const handleCardAction = (action: CardAction) => {
    if (onCardAction) {
      onCardAction(action, message.id);
    }
  };

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
          ) : highlightSignals ? (
            <SignalHighlighter
              content={message.content}
              signals={signals.map(s => ({
                id: s.id,
                text: s.text,
                type: s.type as any,
                start: s.span?.start || 0,
                end: s.span?.end || 0,
                confidence: s.confidence
              }))}
              onDismiss={handleDismissSignal}
            />
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
                className="text-xs px-2 py-1 bg-accent-50 text-accent-700 rounded hover:bg-accent-100 transition-colors dark:bg-accent-900 dark:text-accent-200"
              >
                Add to Brief
              </button>
            )}
            {onCreateEvidence && (
              <button
                onClick={() => onCreateEvidence(message.content)}
                className="text-xs px-2 py-1 bg-success-50 text-success-700 rounded hover:bg-success-100 transition-colors dark:bg-success-900 dark:text-success-200"
              >
                Create Evidence
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
        delay: index < 3 ? index * 0.1 : 0, // Only stagger first 3 messages
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
  onCreateEvidence,
  onCardAction,
  isLoading,
  inlineCards = [],
  inlineCardActions = {},
}: {
  messages: MessageType[];
  isWaitingForResponse?: boolean;
  isStreaming?: boolean;
  ttft?: number | null;
  onAddToBrief?: (messageId: string, content: string) => void;
  onCreateEvidence?: (content: string) => void;
  onCardAction?: (action: CardAction, messageId: string) => void;
  isLoading?: boolean;
  /** Inline action cards to display after messages */
  inlineCards?: InlineActionCard[];
  /** Actions for inline cards */
  inlineCardActions?: InlineCardActions;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isWaitingForResponse]);

  // Show skeleton during initial load
  if (isLoading) {
    return <MessageListSkeleton />;
  }

  if (messages.length === 0) {
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

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {messages.map((message, index) => (
        <div key={message.id}>
          <Message
            message={message}
            index={index}
            onAddToBrief={onAddToBrief}
            onCreateEvidence={onCreateEvidence}
            onCardAction={onCardAction}
          />

          {/* Inline action cards after this message */}
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
