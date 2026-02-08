/**
 * Chat Landing Page
 *
 * Route: /chat
 * Shows a centered hero input for starting a new conversation.
 * The conversation list lives in the left sidebar panel — no duplication here.
 * When user sends a message, creates a thread and navigates to /chat/[threadId].
 */

'use client';

import { MessageInput } from '@/components/chat/MessageInput';
import { useHomeState } from '@/hooks/useHomeState';
import { cn } from '@/lib/utils';

export default function ChatLandingPage() {
  const state = useHomeState();

  return (
    <div className="flex flex-col h-full bg-white dark:bg-neutral-950">
      <div
        className={cn(
          'flex-1 flex flex-col items-center justify-center px-6 transition-all duration-200 ease-out',
          state.isTransitioning ? 'opacity-0 scale-[0.98] blur-[2px]' : 'opacity-100 scale-100'
        )}
      >
        <div className="w-full max-w-2xl space-y-4">
          {/* Welcome text */}
          <div className="text-center mb-2">
            <h1 className="text-2xl font-semibold text-neutral-900 dark:text-neutral-100 tracking-tight">
              What would you like to explore?
            </h1>
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-2">
              Start a conversation, or pick one from the sidebar.
            </p>
          </div>

          {/* Hero input */}
          <div className="rounded-lg border border-neutral-200/60 dark:border-neutral-700/50 overflow-hidden">
            <MessageInput
              variant="hero"
              onSend={state.handleHeroSend}
              placeholder={state.currentPlaceholder}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
