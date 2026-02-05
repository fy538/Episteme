/**
 * Message input component
 */

import { useState, KeyboardEvent, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { UI } from '@/lib/constants';

export function MessageInput({ 
  onSend, 
  disabled,
  isProcessing,
  isStreaming,
  onStop,
}: { 
  onSend: (content: string) => void;
  disabled?: boolean;
  isProcessing?: boolean;
  isStreaming?: boolean;
  onStop?: () => void;
}) {
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

  // Disable send when streaming, processing, or over limit
  const canSend = !disabled && !isStreaming && !isProcessing && input.trim() && !isOverLimit;

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
            placeholder={isStreaming ? "Wait for response..." : "Type your message..."}
            disabled={disabled || isStreaming}
            rows={1}
            className="resize-none overflow-hidden min-h-[42px] max-h-[200px]"
          />
          {/* Character count */}
          {charCount > 0 && (
            <div className={`text-xs mt-1 text-right ${isOverLimit ? 'text-error-500' : 'text-neutral-400'}`}>
              {charCount.toLocaleString()}{isOverLimit && ` / ${maxChars.toLocaleString()} max`}
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
            {isProcessing ? (
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
