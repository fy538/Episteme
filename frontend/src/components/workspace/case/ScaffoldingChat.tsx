/**
 * ScaffoldingChat — Guided conversation that scaffolds a new case.
 *
 * Uses the real chat agent with a scaffolding system prompt (Socratic
 * interviewer mode) for adaptive, context-aware follow-up questions.
 *
 * Flow:
 * 1. Creates a thread with metadata: { mode: 'scaffolding' }
 * 2. Sends an initial system greeting via the LLM (adaptive first question)
 * 3. User describes their decision; LLM responds with Socratic follow-ups
 * 4. User can click "Create Case" at any point (or continue chatting)
 * 5. Scaffolding runs (LLM extraction + case creation)
 * 6. Redirect to the new case overview
 *
 * Also supports "Skip scaffolding" to create a blank case.
 */

'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { chatAPI } from '@/lib/api/chat';
import { casesAPI } from '@/lib/api/cases';
import { SkillPicker } from './SkillPicker';

interface ScaffoldingChatProps {
  projectId: string;
  /** Optional thread ID if scaffolding from an existing conversation */
  existingThreadId?: string;
  /** Called when case is created */
  onCaseCreated?: (caseId: string) => void;
  /** Called when user cancels */
  onCancel?: () => void;
  className?: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
}

type ScaffoldingPhase = 'picking' | 'initializing' | 'chatting' | 'scaffolding' | 'complete' | 'error';

// Initial greeting — shown while the thread is being created
const INITIAL_GREETING = "What decision are you working through? I'll ask a few quick questions to understand the context, then scaffold a structured case for you.";

export function ScaffoldingChat({
  projectId,
  existingThreadId,
  onCaseCreated,
  onCancel,
  className,
}: ScaffoldingChatProps) {
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  // Start at 'picking' unless we're resuming from an existing thread
  const [phase, setPhase] = useState<ScaffoldingPhase>(
    existingThreadId ? 'initializing' : 'picking'
  );
  const [isSending, setIsSending] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [threadError, setThreadError] = useState<string | null>(null);
  const [createdCaseId, setCreatedCaseId] = useState<string | null>(null);
  const [threadId, setThreadId] = useState<string | null>(existingThreadId || null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when phase changes to chatting
  useEffect(() => {
    if (phase === 'chatting' && inputRef.current) {
      inputRef.current.focus();
    }
  }, [phase]);

  // ── Initialize thread (runs when phase transitions to 'initializing') ──

  useEffect(() => {
    if (phase !== 'initializing') return;

    let mounted = true;

    async function initThread() {
      try {
        if (existingThreadId) {
          // Use existing thread — show greeting and move to chatting
          setThreadId(existingThreadId);
          setMessages([{
            id: 'greeting',
            role: 'assistant',
            content: INITIAL_GREETING,
          }]);
          if (mounted) setPhase('chatting');
          return;
        }

        // Create a new thread with scaffolding mode metadata
        let thread;
        try {
          thread = await chatAPI.createThread(projectId, { mode: 'scaffolding' });
        } catch (threadErr: any) {
          if (!mounted) return;
          // Thread creation is critical — show error and disable chat
          setThreadError(threadErr.message || 'Failed to connect to the chat service');
          setPhase('chatting'); // Show UI but with error banner
          return;
        }

        if (!mounted) return;
        setThreadId(thread.id);
        setThreadError(null);

        // Send an initial "greeting" message via the LLM to get an adaptive first question
        // We use a sentinel user message that the scaffolding prompt knows to handle
        const greetingMsg: ChatMessage = {
          id: 'greeting-stream',
          role: 'assistant',
          content: '',
          isStreaming: true,
        };
        setMessages([greetingMsg]);

        let accumulated = '';
        await chatAPI.sendUnifiedStream(
          thread.id,
          '[User has opened the scaffolding flow. Greet them and ask your first question.]',
          {
            onResponseChunk: (delta) => {
              if (!mounted) return;
              accumulated += delta;
              setMessages([{
                id: 'greeting-stream',
                role: 'assistant',
                content: accumulated,
                isStreaming: true,
              }]);
            },
            onResponseComplete: (content) => {
              if (!mounted) return;
              setMessages([{
                id: 'greeting',
                role: 'assistant',
                content: content || accumulated,
                isStreaming: false,
              }]);
            },
            onDone: () => {
              if (mounted) setPhase('chatting');
            },
            onError: (error) => {
              if (!mounted) return;
              // LLM greeting failed — non-critical, fall back to static greeting
              setMessages([{
                id: 'greeting',
                role: 'assistant',
                content: INITIAL_GREETING,
              }]);
              setPhase('chatting');
            },
          }
        );
      } catch (err: any) {
        if (!mounted) return;
        // LLM stream failed but thread exists — fall back to static greeting
        if (threadId) {
          setMessages([{
            id: 'greeting',
            role: 'assistant',
            content: INITIAL_GREETING,
          }]);
          setPhase('chatting');
        } else {
          // No thread — show error
          setThreadError(err.message || 'Failed to initialize');
          setPhase('chatting');
        }
      }
    }

    initThread();

    return () => {
      mounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  // ── Retry thread creation ────────────────────────────────────
  const retryInit = useCallback(async () => {
    setThreadError(null);
    setPhase('initializing');
    setMessages([]);
    try {
      const thread = await chatAPI.createThread(projectId, { mode: 'scaffolding' });
      setThreadId(thread.id);
      setMessages([{
        id: 'greeting',
        role: 'assistant',
        content: INITIAL_GREETING,
      }]);
      setPhase('chatting');
    } catch (err: any) {
      setThreadError(err.message || 'Failed to connect to the chat service');
      setPhase('chatting');
    }
  }, [projectId]);

  // ── Send a message ────────────────────────────────────────────

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || phase !== 'chatting' || !threadId || isSending) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text.trim(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setIsSending(true);

    // Create a streaming assistant message placeholder
    const assistantMsgId = `assistant-${Date.now()}`;
    setMessages(prev => [...prev, {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      isStreaming: true,
    }]);

    let accumulated = '';
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      await chatAPI.sendUnifiedStream(
        threadId,
        text.trim(),
        {
          onResponseChunk: (delta) => {
            accumulated += delta;
            setMessages(prev => prev.map(m =>
              m.id === assistantMsgId
                ? { ...m, content: accumulated }
                : m
            ));
          },
          onResponseComplete: (content) => {
            setMessages(prev => prev.map(m =>
              m.id === assistantMsgId
                ? { ...m, content: content || accumulated, isStreaming: false }
                : m
            ));
          },
          onDone: () => {
            setIsSending(false);
            abortControllerRef.current = null;
          },
          onError: (error) => {
            setMessages(prev => prev.map(m =>
              m.id === assistantMsgId
                ? { ...m, content: accumulated || 'Sorry, something went wrong. Please try again.', isStreaming: false }
                : m
            ));
            setIsSending(false);
            abortControllerRef.current = null;
          },
        },
        controller.signal
      );
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setMessages(prev => prev.map(m =>
          m.id === assistantMsgId
            ? { ...m, content: accumulated || 'Sorry, something went wrong. Please try again.', isStreaming: false }
            : m
        ));
      }
      setIsSending(false);
      abortControllerRef.current = null;
    }
  }, [phase, threadId, isSending]);

  // ── Scaffold the case ─────────────────────────────────────────

  const handleScaffold = useCallback(async () => {
    // Abort any in-flight stream
    abortControllerRef.current?.abort();
    setPhase('scaffolding');

    try {
      if (threadId) {
        // Scaffold from the real thread — this sends the full transcript to the LLM
        const result = await casesAPI.scaffoldFromChat(projectId, threadId);
        setCreatedCaseId(result.case.id);
        setPhase('complete');
        onCaseCreated?.(result.case.id);
      } else {
        // No thread (shouldn't happen in normal flow) — minimal scaffold
        const result = await casesAPI.scaffoldMinimal(projectId, 'New Case');
        setCreatedCaseId(result.case.id);
        setPhase('complete');
        onCaseCreated?.(result.case.id);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to scaffold case');
      setPhase('error');
    }
  }, [threadId, projectId, onCaseCreated]);

  // ── Skill Picker handlers ────────────────────────────────────

  const handleSelectPack = useCallback(async (slug: string) => {
    // Skip the chat interview — scaffold immediately with pack template
    setPhase('scaffolding');
    try {
      const result = await casesAPI.scaffoldMinimal(projectId, 'New Case', undefined, { packSlug: slug });
      setCreatedCaseId(result.case.id);
      setPhase('complete');
      onCaseCreated?.(result.case.id);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to scaffold with pack');
      setPhase('error');
    }
  }, [projectId, onCaseCreated]);

  const handleSelectSkill = useCallback(async (skillId: string) => {
    // Scaffold immediately using the skill
    setPhase('scaffolding');
    try {
      const result = await casesAPI.scaffoldMinimal(projectId, 'New Case', undefined, { skillId });
      setCreatedCaseId(result.case.id);
      setPhase('complete');
      onCaseCreated?.(result.case.id);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to scaffold with skill');
      setPhase('error');
    }
  }, [projectId, onCaseCreated]);

  const handleSkipPicker = useCallback(() => {
    // Move from picking → initializing (starts the Socratic interview)
    setPhase('initializing');
  }, []);

  // ── Create blank case ─────────────────────────────────────────

  const handleCreateBlank = useCallback(async () => {
    abortControllerRef.current?.abort();
    setPhase('scaffolding');
    try {
      const result = await casesAPI.scaffoldMinimal(projectId, 'New Case');
      setCreatedCaseId(result.case.id);
      setPhase('complete');
      onCaseCreated?.(result.case.id);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to create case');
      setPhase('error');
    }
  }, [projectId, onCaseCreated]);

  // ── Navigate to created case ──────────────────────────────────

  const handleGoToCase = useCallback(() => {
    if (createdCaseId) {
      router.push(`/cases/${createdCaseId}/overview`);
    }
  }, [createdCaseId, router]);

  // ── Handle input submit ───────────────────────────────────────

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(inputValue);
  }, [inputValue, sendMessage]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputValue);
    }
  }, [inputValue, sendMessage]);

  const canScaffold = messages.filter(m => m.role === 'user').length >= 1;
  const userMessageCount = messages.filter(m => m.role === 'user').length;

  // ── Render ────────────────────────────────────────────────────

  return (
    <div className={cn(
      'flex flex-col h-full max-w-2xl mx-auto',
      className
    )}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-800">
        <div>
          <h2 className="text-sm font-semibold text-primary-900 dark:text-primary-50">
            Scaffold a New Case
          </h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">
            Tell me about your decision — I'll help structure it
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCreateBlank}
            className="text-xs text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300"
            disabled={phase !== 'chatting'}
          >
            Skip — blank case
          </button>
          {onCancel && (
            <Button variant="ghost" size="sm" onClick={onCancel} className="h-7 text-xs">
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Skill Picker — shown before the chat */}
      {phase === 'picking' && (
        <div className="flex-1 overflow-y-auto">
          <SkillPicker
            onSelectPack={handleSelectPack}
            onSelectSkill={handleSelectSkill}
            onSkip={handleSkipPicker}
          />
        </div>
      )}

      {/* Messages */}
      {phase !== 'picking' && (
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {/* Initializing state */}
        {phase === 'initializing' && messages.length === 0 && (
          <div className="flex justify-start">
            <div className="max-w-[80%] px-3 py-2 rounded-xl text-sm bg-neutral-100 dark:bg-neutral-800">
              <div className="flex items-center gap-2 text-neutral-500 dark:text-neutral-400">
                <TypingIndicator />
              </div>
            </div>
          </div>
        )}

        {/* Thread creation failure banner */}
        {threadError && (
          <div className="mx-auto max-w-md p-3 border border-red-200 dark:border-red-900/40 rounded-xl bg-red-50/50 dark:bg-red-900/10 text-center">
            <p className="text-xs font-medium text-red-600 dark:text-red-400">
              Couldn't connect to the chat service
            </p>
            <p className="text-xs text-red-500 dark:text-red-400/80 mt-0.5">
              {threadError}
            </p>
            <button
              onClick={retryInit}
              className="mt-2 px-3 py-1 text-xs font-medium text-red-600 dark:text-red-400 border border-red-300 dark:border-red-700 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              'flex',
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            )}
          >
            <div
              className={cn(
                'max-w-[80%] px-3 py-2 rounded-xl text-sm whitespace-pre-wrap',
                msg.role === 'user'
                  ? 'bg-accent-100 dark:bg-accent-900/30 text-accent-900 dark:text-accent-100'
                  : 'bg-neutral-100 dark:bg-neutral-800 text-primary-900 dark:text-primary-50'
              )}
            >
              {msg.content || (msg.isStreaming ? <TypingIndicator /> : null)}
              {msg.isStreaming && msg.content && (
                <span className="inline-block w-1.5 h-4 ml-0.5 bg-current opacity-50 animate-pulse" />
              )}
            </div>
          </div>
        ))}

        {/* Scaffolding state */}
        {phase === 'scaffolding' && (
          <div className="flex justify-center py-6">
            <div className="flex items-center gap-3 px-4 py-3 bg-accent-50 dark:bg-accent-900/20 border border-accent-200 dark:border-accent-800 rounded-xl">
              <LoadingSpinner className="w-5 h-5 text-accent-500" />
              <div>
                <p className="text-sm font-medium text-accent-700 dark:text-accent-300">
                  Scaffolding your case...
                </p>
                <p className="text-xs text-accent-500 dark:text-accent-400 mt-0.5">
                  Creating brief, inquiries, and structure
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Complete state */}
        {phase === 'complete' && (
          <div className="flex justify-center py-6">
            <div className="text-center px-6 py-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-xl">
              <CheckIcon className="w-8 h-8 mx-auto text-emerald-500 mb-2" />
              <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">
                Case scaffolded successfully!
              </p>
              <p className="text-xs text-emerald-500 dark:text-emerald-400 mt-1 mb-3">
                Your brief, inquiries, and structure are ready
              </p>
              <Button size="sm" onClick={handleGoToCase}>
                Open Case →
              </Button>
            </div>
          </div>
        )}

        {/* Error state */}
        {phase === 'error' && (
          <div className="flex justify-center py-6" role="alert">
            <div className="text-center px-6 py-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
              <p className="text-sm font-medium text-red-700 dark:text-red-300">
                Something went wrong
              </p>
              <p className="text-xs text-red-500 dark:text-red-400 mt-1 mb-3">
                {errorMessage}
              </p>
              <div className="flex items-center justify-center gap-2">
                {!existingThreadId && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setErrorMessage('');
                      setPhase('picking');
                    }}
                  >
                    Back to templates
                  </Button>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setPhase('chatting')}
                >
                  Try Again
                </Button>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
      )}

      {/* Scaffolding nudge — shown after 2+ user messages */}
      {phase === 'chatting' && userMessageCount >= 2 && !isSending && !threadError && (
        <div className="px-4 pb-2">
          <div className="flex items-center gap-2 p-2 rounded-lg bg-accent-50/50 dark:bg-accent-900/10 border border-accent-200/50 dark:border-accent-800/50">
            <SparklesIcon className="w-3.5 h-3.5 text-accent-500 flex-shrink-0" />
            <span className="text-xs text-accent-600 dark:text-accent-400 flex-1">
              Ready to create your case? You can keep chatting or scaffold now.
            </span>
          </div>
        </div>
      )}

      {/* Input area */}
      {phase === 'chatting' && !threadError && (
        <div className="px-4 pb-4">
          <form onSubmit={handleSubmit} className="flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Describe your decision..."
                rows={1}
                disabled={isSending}
                aria-label="Describe your decision"
                className="w-full px-3 py-2 text-sm border border-neutral-300 dark:border-neutral-700 rounded-xl bg-white dark:bg-neutral-900 text-primary-900 dark:text-primary-50 resize-none outline-none focus:ring-1 focus:ring-accent-400 dark:focus:ring-accent-600 disabled:opacity-50"
              />
            </div>
            <div className="flex items-center gap-1.5">
              <Button
                type="submit"
                size="sm"
                variant="ghost"
                className="h-9"
                disabled={!inputValue.trim() || isSending}
              >
                {isSending ? (
                  <LoadingSpinner className="w-4 h-4" />
                ) : (
                  <SendIcon className="w-4 h-4" />
                )}
              </Button>
              {canScaffold && (
                <Button
                  size="sm"
                  className="h-9"
                  disabled={isSending}
                  onClick={(e) => {
                    e.preventDefault();
                    handleScaffold();
                  }}
                >
                  <SparklesIcon className="w-3.5 h-3.5 mr-1" />
                  Create Case
                </Button>
              )}
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="w-1.5 h-1.5 rounded-full bg-neutral-400 dark:bg-neutral-500 animate-bounce [animation-delay:0ms]" />
      <span className="w-1.5 h-1.5 rounded-full bg-neutral-400 dark:bg-neutral-500 animate-bounce [animation-delay:150ms]" />
      <span className="w-1.5 h-1.5 rounded-full bg-neutral-400 dark:bg-neutral-500 animate-bounce [animation-delay:300ms]" />
    </span>
  );
}

// ── Icons ────────────────────────────────────────────────────────

function LoadingSpinner({ className }: { className?: string }) {
  return (
    <svg className={cn(className, 'animate-spin')} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
      <path d="M12 2a10 10 0 019.17 6" strokeLinecap="round" />
    </svg>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SendIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}

function SparklesIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5L12 3zM5 19l.5 1.5L7 21l-1.5.5L5 23l-.5-1.5L3 21l1.5-.5L5 19zM19 10l.5 1.5L21 12l-1.5.5L19 14l-.5-1.5L17 12l1.5-.5L19 10z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default ScaffoldingChat;
