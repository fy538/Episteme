/**
 * Message input component
 */

import { useState, KeyboardEvent, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';

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

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSend(input);
      setInput('');
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    // Submit on Enter (without shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-neutral-200 p-4 bg-white">
      <div className="flex gap-2 items-end">
        <div className="flex-1">
          <Label htmlFor="message" className="sr-only">Message</Label>
          <Textarea
            id="message"
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            disabled={disabled}
            rows={1}
            className="resize-none overflow-hidden min-h-[42px] max-h-[200px]"
          />
        </div>
        {isStreaming && onStop ? (
          <Button type="button" onClick={onStop} variant="outline">
            <span className="inline-flex items-center gap-2">
              <span className="w-3 h-3 bg-error-500 rounded-sm" />
              Stop
            </span>
          </Button>
        ) : (
          <Button type="submit" disabled={disabled || !input.trim()}>
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
