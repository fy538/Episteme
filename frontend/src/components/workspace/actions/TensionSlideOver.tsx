/**
 * Tension Slide Over
 *
 * A slide-over panel for resolving tensions.
 * Keeps user in context while providing space for side-by-side comparison.
 */

'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { TensionData } from '@/lib/types/intelligence';

interface TensionSlideOverProps {
  tension: TensionData;
  title: string;
  caseName?: string;
  inquiryName?: string;
  isOpen: boolean;
  onClose: () => void;
  onResolve: (choice: 'A' | 'B' | 'neither') => void;
  onDismiss: () => void;
}

export function TensionSlideOver({
  tension,
  title,
  caseName,
  inquiryName,
  isOpen,
  onClose,
  onResolve,
  onDismiss,
}: TensionSlideOverProps) {
  const [chatInput, setChatInput] = useState('');
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
  const [selectedSource, setSelectedSource] = useState<'A' | 'B' | null>(null);
  const [isVisible, setIsVisible] = useState(false);

  // Handle open/close animation
  useEffect(() => {
    if (isOpen) {
      // Small delay to trigger animation
      requestAnimationFrame(() => setIsVisible(true));
    } else {
      setIsVisible(false);
    }
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, onClose]);

  const handleSendMessage = () => {
    if (!chatInput.trim()) return;

    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: chatInput }]);

    // Simulate AI response
    setTimeout(() => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `I understand you're trying to resolve the tension about "${title}". Looking at both sources, the key difference seems to be in how they interpret the underlying data. Would you like me to analyze the implications of each approach in more detail?`
      }]);
    }, 1000);

    setChatInput('');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        className={cn(
          'absolute inset-0 bg-black/30 backdrop-blur-sm transition-opacity duration-300',
          isVisible ? 'opacity-100' : 'opacity-0'
        )}
        onClick={onClose}
      />

      {/* Slide-over panel */}
      <div
        className={cn(
          'absolute top-0 right-0 h-full w-full max-w-3xl bg-white dark:bg-neutral-900 shadow-2xl transition-transform duration-300 ease-out flex flex-col',
          isVisible ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        {/* Header */}
        <header className="flex items-center justify-between p-4 border-b border-neutral-200 dark:border-neutral-800 shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="p-1 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded"
            >
              <CloseIcon className="w-5 h-5 text-neutral-500" />
            </button>
            <div>
              <h1 className="font-semibold text-primary-900 dark:text-primary-50">
                Resolve Tension
              </h1>
              <p className="text-sm text-neutral-500 dark:text-neutral-400">
                {[caseName, inquiryName].filter(Boolean).join(' · ')}
              </p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={onDismiss}>
            Note as Unresolved
          </Button>
        </header>

        {/* Tension Title */}
        <div className="p-4 bg-warning-50 dark:bg-warning-900/10 border-b border-warning-200 dark:border-warning-800 shrink-0">
          <div className="flex items-start gap-2">
            <TensionIcon className="w-5 h-5 text-warning-600 dark:text-warning-400 shrink-0 mt-0.5" />
            <div>
              <h2 className="font-medium text-warning-900 dark:text-warning-100">
                {title}
              </h2>
              {tension.impact && (
                <p className="text-sm text-warning-700 dark:text-warning-300 mt-1">
                  Impact: {tension.impact}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Sources Comparison */}
          <div className="flex-1 overflow-auto p-4">
            <div className="grid grid-cols-2 gap-4 h-full">
              {/* Source A */}
              <SourceCard
                source={tension.sourceA}
                label="Source A"
                isSelected={selectedSource === 'A'}
                onSelect={() => setSelectedSource('A')}
                onAccept={() => onResolve('A')}
              />

              {/* Source B */}
              <SourceCard
                source={tension.sourceB}
                label="Source B"
                isSelected={selectedSource === 'B'}
                onSelect={() => setSelectedSource('B')}
                onAccept={() => onResolve('B')}
              />
            </div>
          </div>

          {/* Chat Panel */}
          <div className="w-72 border-l border-neutral-200 dark:border-neutral-800 flex flex-col shrink-0">
            <div className="p-3 border-b border-neutral-200 dark:border-neutral-800 shrink-0">
              <h3 className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
                Discuss
              </h3>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-auto p-3 space-y-3">
              {messages.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-sm text-neutral-500 dark:text-neutral-400">
                    Ask questions to help resolve this tension
                  </p>
                  <div className="mt-4 space-y-2">
                    <SuggestedQuestion
                      question="Why do these sources disagree?"
                      onClick={() => {
                        setChatInput("Why do these sources disagree?");
                        handleSendMessage();
                      }}
                    />
                    <SuggestedQuestion
                      question="What's the impact of each interpretation?"
                      onClick={() => {
                        setChatInput("What's the impact of each interpretation?");
                        handleSendMessage();
                      }}
                    />
                    <SuggestedQuestion
                      question="Is there a way to reconcile these?"
                      onClick={() => {
                        setChatInput("Is there a way to reconcile these?");
                        handleSendMessage();
                      }}
                    />
                  </div>
                </div>
              )}
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={cn(
                    'text-sm p-3 rounded-lg',
                    msg.role === 'user'
                      ? 'bg-accent-100 dark:bg-accent-900/30 ml-4'
                      : 'bg-neutral-100 dark:bg-neutral-800 mr-4'
                  )}
                >
                  {msg.content}
                </div>
              ))}
            </div>

            {/* Input */}
            <div className="p-3 border-t border-neutral-200 dark:border-neutral-800 shrink-0">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="Ask about this tension..."
                  className="flex-1 text-sm px-3 py-2 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-900 focus:outline-none focus:ring-2 focus:ring-accent-500"
                />
                <Button size="sm" onClick={handleSendMessage}>
                  Send
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Footer with resolution options */}
        <div className="p-4 border-t border-neutral-200 dark:border-neutral-800 flex items-center justify-between shrink-0">
          <Button variant="ghost" onClick={() => onResolve('neither')}>
            Neither source is correct
          </Button>
          <div className="flex items-center gap-2">
            <Button
              variant={selectedSource === 'A' ? 'default' : 'outline'}
              onClick={() => onResolve('A')}
            >
              Accept Source A
            </Button>
            <Button
              variant={selectedSource === 'B' ? 'default' : 'outline'}
              onClick={() => onResolve('B')}
            >
              Accept Source B
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Suggested question button
function SuggestedQuestion({ question, onClick }: { question: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left text-xs px-3 py-2 bg-neutral-100 dark:bg-neutral-800 rounded-lg text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700 transition-colors"
    >
      {question}
    </button>
  );
}

// Source card component
interface SourceCardProps {
  source: TensionData['sourceA'];
  label: string;
  isSelected: boolean;
  onSelect: () => void;
  onAccept: () => void;
}

function SourceCard({ source, label, isSelected, onSelect, onAccept }: SourceCardProps) {
  return (
    <div
      className={cn(
        'flex flex-col p-4 rounded-xl border-2 transition-colors cursor-pointer h-fit',
        isSelected
          ? 'border-accent-500 bg-accent-50/50 dark:bg-accent-900/10'
          : 'border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600'
      )}
      onClick={onSelect}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide">
          {label}
        </span>
        {isSelected && (
          <div className="w-5 h-5 rounded-full bg-accent-500 flex items-center justify-center">
            <CheckIcon className="w-3 h-3 text-white" />
          </div>
        )}
      </div>

      {/* Source Name */}
      <h4 className="font-medium text-primary-900 dark:text-primary-50 mb-2">
        {source.name}
      </h4>

      {/* Content */}
      <p className="text-sm text-neutral-600 dark:text-neutral-400">
        "{source.content}"
      </p>

      {/* Implication */}
      {source.implication && (
        <div className="mt-3 pt-3 border-t border-neutral-200 dark:border-neutral-700">
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            <span className="font-medium">Implication:</span> {source.implication}
          </p>
        </div>
      )}
    </div>
  );
}

// Icons
function CloseIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function TensionIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 9v4M12 17h.01" strokeLinecap="round" />
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
    </svg>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default TensionSlideOver;
