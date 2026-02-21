/**
 * Message input component
 *
 * Claude-style input box with:
 * - Textarea at top
 * - Bottom toolbar: mode dropdown (left), model selector (center-left), send button (far right)
 *
 * Variants:
 * - default: Standard chat input with border-top separator (sidebar panels)
 * - hero: Borderless input for the home page hero area
 * - full: Claude-style input with bottom toolbar for full-screen chat
 */

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Spinner } from '@/components/ui/spinner';
import { UI } from '@/lib/constants';
import { cn } from '@/lib/utils';
import { ArrowUpIcon, StopIcon, ChatBubbleIcon as ModeIcon, ChevronDownIcon as ChevronIcon } from '@/components/ui/icons';

type ChatMode = 'casual' | 'case' | 'inquiry_focus' | 'graph' | 'orientation';

interface MessageInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  isProcessing?: boolean;
  isStreaming?: boolean;
  isWaitingForFirstToken?: boolean;
  onStop?: () => void;
  mode?: ChatMode;
  onModeChange?: (mode: ChatMode) => void;
  placeholder?: string;
  /** Variant: "default" (standard), "hero" (borderless home), "full" (Claude-style) */
  variant?: 'default' | 'hero' | 'full';
  /** Pre-fill the input with this value (e.g., from deep-linking). Input is set once when value changes. */
  prefillValue?: string | null;
  /** Called after prefillValue has been consumed (set into input) */
  onPrefillConsumed?: () => void;
}

const MODE_LABELS: Record<ChatMode, string> = {
  casual: 'Chat',
  case: 'Case',
  inquiry_focus: 'Inquiry',
  graph: 'Graph',
  orientation: 'Orientation',
};

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
  mode = 'casual',
  onModeChange,
  placeholder: customPlaceholder,
  variant = 'default',
  prefillValue,
  onPrefillConsumed,
}: MessageInputProps) {
  const [input, setInput] = useState('');
  const [showModeMenu, setShowModeMenu] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const modeMenuRef = useRef<HTMLDivElement>(null);

  // Handle prefill from deep-linking (e.g., chat-about buttons)
  // Appends to existing input (on a new line) if user has already typed something
  useEffect(() => {
    if (prefillValue) {
      setInput(prev => {
        if (prev.trim()) {
          return `${prev}\n\n${prefillValue}`;
        }
        return prefillValue;
      });
      onPrefillConsumed?.();
      // Focus the textarea so user can immediately edit/send
      requestAnimationFrame(() => textareaRef.current?.focus());
    }
  }, [prefillValue]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  // Close mode menu on click outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (modeMenuRef.current && !modeMenuRef.current.contains(e.target as Node)) {
        setShowModeMenu(false);
      }
    }
    if (showModeMenu) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showModeMenu]);

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

  const isHero = variant === 'hero';
  const isFull = variant === 'full';

  // ─── Hero variant (home page) ──────────────────────────────────
  if (isHero) {
    return (
      <form onSubmit={handleSubmit} className="p-0 bg-transparent">
        <div className="flex flex-col">
          <div className="px-3 pt-2 pb-1">
            <Label htmlFor="message" className="sr-only">Message</Label>
            <textarea
              id="message"
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholderText}
              disabled={disabled || isStreaming || isWaitingForFirstToken}
              rows={1}
              className="w-full resize-none overflow-hidden min-h-[38px] max-h-[200px] border-0 bg-transparent text-sm placeholder:text-neutral-400 dark:placeholder:text-neutral-500 dark:text-neutral-100 focus:outline-none focus:ring-0 px-1 py-1"
            />
          </div>
          {/* Bottom toolbar */}
          <div className="flex items-center justify-between px-3 py-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-neutral-400">Chat</span>
            </div>
            <Button
              type="submit"
              variant="ghost"
              size="icon"
              disabled={!canSend}
              className={cn(
                'w-7 h-7 rounded flex items-center justify-center transition-colors',
                canSend
                  ? 'bg-neutral-900 dark:bg-neutral-100 text-white dark:text-neutral-900 hover:bg-neutral-800 dark:hover:bg-neutral-200'
                  : 'bg-neutral-200 dark:bg-neutral-700 text-neutral-400 dark:text-neutral-500 cursor-not-allowed'
              )}
            >
              <ArrowUpIcon className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </form>
    );
  }

  // ─── Default variant (sidebar panel) ───────────────────────────
  if (!isFull) {
    return (
      <form onSubmit={handleSubmit} className="border-t border-neutral-200 dark:border-neutral-700 p-4 bg-white dark:bg-neutral-900">
        <div className="flex gap-2 items-end">
          <div className="flex-1">
            <Label htmlFor="message" className="sr-only">Message</Label>
            <textarea
              id="message"
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholderText}
              disabled={disabled || isStreaming || isWaitingForFirstToken}
              rows={1}
              className="w-full resize-none overflow-hidden min-h-[42px] max-h-[200px] rounded-md border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-accent-500 focus:border-transparent"
            />
            {(isApproachingLimit || charCount > 0) && (
              <div className={cn('text-xs mt-1 text-right', getCharLimitClass(charCount, maxChars))}>
                {charCount.toLocaleString()}
                {isApproachingLimit && ` / ${maxChars.toLocaleString()}`}
                {isOverLimit && ' (over limit)'}
              </div>
            )}
          </div>
          {isStreaming && onStop ? (
            <Button type="button" variant="outline" size="sm" onClick={onStop}>
              <span className="inline-flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-error-500 rounded-sm" />
                Stop
              </span>
            </Button>
          ) : (
            <Button
              type="submit"
              variant="default"
              size="sm"
              disabled={!canSend}
            >
              Send
            </Button>
          )}
        </div>
      </form>
    );
  }

  // ─── Full variant (Claude-style) ──────────────────────────────
  return (
    <form onSubmit={handleSubmit} className="bg-transparent">
      <div className="rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 overflow-hidden focus-within:border-neutral-300 dark:focus-within:border-neutral-600 transition-colors">
        {/* Textarea area */}
        <div className="px-4 pt-3 pb-1">
          <Label htmlFor="message-full" className="sr-only">Message</Label>
          <textarea
            id="message-full"
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholderText}
            disabled={disabled || isStreaming || isWaitingForFirstToken}
            rows={1}
            className="w-full resize-none overflow-hidden min-h-[36px] max-h-[200px] border-0 bg-transparent text-sm leading-relaxed placeholder:text-neutral-400 dark:placeholder:text-neutral-500 dark:text-neutral-100 focus:outline-none focus:ring-0 p-0"
          />
        </div>

        {/* Bottom toolbar */}
        <div className="flex items-center justify-between px-3 py-2">
          {/* Left side: mode + model */}
          <div className="flex items-center gap-1">
            {/* Mode dropdown */}
            <div className="relative" ref={modeMenuRef}>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setShowModeMenu(!showModeMenu)}
                className="gap-1 px-2 py-1 text-xs text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300"
              >
                <ModeIcon className="w-3.5 h-3.5" />
                <span>{MODE_LABELS[mode]}</span>
                <ChevronIcon className="w-3 h-3" />
              </Button>

              {/* Dropdown menu (opens upward) */}
              {showModeMenu && (
                <div className="absolute bottom-full left-0 mb-1 w-36 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-lg py-1 z-50">
                  {(Object.keys(MODE_LABELS) as ChatMode[]).map((m) => (
                    <Button
                      key={m}
                      type="button"
                      variant="ghost"
                      size="sm"
                      className={cn(
                        'w-full justify-start rounded-none px-3 py-1.5 text-xs transition-colors',
                        m === mode
                          ? 'bg-neutral-100 dark:bg-neutral-700 text-neutral-900 dark:text-neutral-100'
                          : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-50 dark:hover:bg-neutral-750'
                      )}
                      onClick={() => {
                        onModeChange?.(m);
                        setShowModeMenu(false);
                      }}
                    >
                      {MODE_LABELS[m]}
                    </Button>
                  ))}
                </div>
              )}
            </div>

            {/* Model indicator */}
            <span className="px-2 py-1 text-xs text-neutral-400 dark:text-neutral-500">
              Default
            </span>
          </div>

          {/* Right side: char count + send/stop */}
          <div className="flex items-center gap-2">
            {(isApproachingLimit || isOverLimit) && (
              <span className={cn('text-xs', getCharLimitClass(charCount, maxChars))}>
                {charCount.toLocaleString()}/{maxChars.toLocaleString()}
              </span>
            )}

            {isStreaming && onStop ? (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={onStop}
                className="w-7 h-7 rounded bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 transition-colors"
              >
                <StopIcon className="w-3 h-3 text-neutral-600 dark:text-neutral-300" />
              </Button>
            ) : (
              <Button
                type="submit"
                variant="ghost"
                size="icon"
                disabled={!canSend}
                className={cn(
                  'w-7 h-7 rounded flex items-center justify-center transition-colors',
                  canSend
                    ? 'bg-neutral-900 dark:bg-neutral-100 text-white dark:text-neutral-900 hover:bg-neutral-800 dark:hover:bg-neutral-200'
                    : 'bg-neutral-200 dark:bg-neutral-700 text-neutral-400 dark:text-neutral-500 cursor-not-allowed'
                )}
              >
                {(isWaitingForFirstToken || isProcessing) ? (
                  <Spinner size="sm" />
                ) : (
                  <ArrowUpIcon className="w-3.5 h-3.5" />
                )}
              </Button>
            )}
          </div>
        </div>
      </div>
    </form>
  );
}

