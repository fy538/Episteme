/**
 * Message input component
 *
 * Features:
 * - Context-aware placeholder text based on mode
 * - Character limit with progressive visual feedback
 * - Distinct states: idle, processing, waiting, streaming
 */

import { useState, KeyboardEvent, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { UI } from '@/lib/constants';
import { cn } from '@/lib/utils';

type ChatMode = 'casual' | 'case' | 'inquiry_focus';

interface MessageInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  isProcessing?: boolean;
  isStreaming?: boolean;
  isWaitingForFirstToken?: boolean;
  onStop?: () => void;
  mode?: ChatMode;
  placeholder?: string;
}

// Get context-aware placeholder text
function getPlaceholder(mode?: ChatMode, isStreaming?: boolean, isWaiting?: boolean): string {
  if (isStreaming) return 'Waiting for response...';
  if (isWaiting) return 'Thinking...';
  switch (mode) {
    case 'case':
      return "What's your next question about this case?";
    case 'inquiry_focus':
      return 'Add evidence or thoughts about this inquiry...';
    default:
      return 'What would you like to explore?';
  }
}

// Get character limit class based on usage
function getCharLimitClass(charCount: number, maxChars: number): string {
  const ratio = charCount / maxChars;
  if (ratio > 1) return 'text-error-500 font-medium';
  if (ratio > 0.9) return 'text-warning-500';
  if (ratio > 0.8) return 'text-warning-400';
  return 'text-neutral-400';
}

export function MessageInput({
  onSend,
  disabled,
  isProcessing,
  isStreaming,
  isWaitingForFirstToken,
  onStop,
  mode,
  placeholder: customPlaceholder,
}: MessageInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  function doSubmit() {
    if (input.trim() && !disabled) {
      onSend(input);
      setInput('');
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    doSubmit();
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    // Submit on Enter (without shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      doSubmit();
    }
  }

  // Character count
  const charCount = input.length;
  const maxChars = UI.MAX_MESSAGE_LENGTH;
  const isOverLimit = charCount > maxChars;
  const isApproachingLimit = charCount > maxChars * 0.8;

  // Placeholder text
  const placeholderText = customPlaceholder || getPlaceholder(mode, isStreaming, isWaitingForFirstToken);

  // Disable send when streaming, processing, waiting, or over limit
  const canSend = !disabled && !isStreaming && !isProcessing && !isWaitingForFirstToken && input.trim() && !isOverLimit;

  return (
    <form onSubmit={handleSubmit} className="border-t border-neutral-200 dark:border-neutral-700 p-4 bg-white dark:bg-neutral-900">
      <div className="flex gap-2 items-end">
        <div className="flex-1">
          <Label htmlFor="message" className="sr-only">Message</Label>
          <Textarea
            id="message"
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholderText}
            disabled={disabled || isStreaming || isWaitingForFirstToken}
            rows={1}
            className={cn(
              'resize-none overflow-hidden min-h-[42px] max-h-[200px]',
              isOverLimit && 'border-error-300 dark:border-error-700 focus:ring-error-500'
            )}
          />
          {/* Character count - show when approaching limit or typing */}
          {(isApproachingLimit || charCount > 0) && (
            <div className={cn('text-xs mt-1 text-right', getCharLimitClass(charCount, maxChars))}>
              {charCount.toLocaleString()}
              {isApproachingLimit && ` / ${maxChars.toLocaleString()}`}
              {isOverLimit && ' (over limit)'}
            </div>
          )}
        </div>
        {isStreaming && onStop ? (
          <Button type="button" onClick={onStop} variant="outline">
            <span className="inline-flex items-center gap-2">
              <span className="w-3 h-3 bg-error-500 rounded-sm" />
              Stop
            </span>
          </Button>
        ) : (
          <Button type="submit" disabled={!canSend}>
            {isWaitingForFirstToken ? (
              <span className="inline-flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white/60 border-t-white rounded-full animate-spin" />
                Thinking...
              </span>
            ) : isProcessing ? (
              <span className="inline-flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white/60 border-t-white rounded-full animate-spin" />
                Sending
              </span>
            ) : (
              'Send'
            )}
          </Button>
        )}
      </div>
    </form>
  );
}
