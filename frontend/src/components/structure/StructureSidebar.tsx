/**
 * Structure sidebar - shows signals, inquiries, and suggestions
 */

'use client';

import { useEffect, useRef, useState } from 'react';
import { SignalsList } from './SignalsList';
import { InquirySuggestions } from './InquirySuggestions';
import { CaseCard } from './CaseCard';
import { signalsAPI } from '@/lib/api/signals';
import { casesAPI } from '@/lib/api/cases';
import { Button } from '@/components/ui/button';
import type { Signal, InquirySuggestion } from '@/lib/types/signal';

export function StructureSidebar({ 
  threadId, 
  caseId,
  onCaseCreated 
}: { 
  threadId: string; 
  caseId?: string;
  onCaseCreated?: (caseId: string) => void;
}) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [suggestions, setSuggestions] = useState<InquirySuggestion[]>([]);
  const [creatingCase, setCreatingCase] = useState(false);
  const [signalsExpanded, setSignalsExpanded] = useState(false);
  const pollCountRef = useRef(0);
  const signalsCountRef = useRef(0);

  // Poll for signals with smart backoff
  const loadSignals = async () => {
    if (threadId) {
      try {
        const sigs = await signalsAPI.getByThread(threadId);
        setSignals(prev => {
          const sameLength = prev.length === sigs.length;
          const sameIds =
            sameLength &&
            prev.every((signal, idx) => signal.id === sigs[idx]?.id);
          if (sameIds) return prev;
          signalsCountRef.current = sigs.length;
          return sigs;
        });
      } catch (error) {
        console.error('Failed to load signals:', error);
      }
    }
  };

  useEffect(() => {
    pollCountRef.current = 0;
    signalsCountRef.current = 0;
    loadSignals(); // Initial load

    let interval: NodeJS.Timeout;

    const startPolling = () => {
      // Smart polling with exponential backoff
      const getPollInterval = () => {
        if (signalsCountRef.current === 0) {
          // No signals yet - poll more frequently (first 5 attempts)
          if (pollCountRef.current < 5) return 3000; // 3s for first 15s
          if (pollCountRef.current < 10) return 5000; // 5s for next 25s
          return 10000; // 10s after 40s
        } else {
          // Have signals - poll less frequently
          return 15000; // 15s when signals exist
        }
      };

      const poll = async () => {
        await loadSignals();
        pollCountRef.current += 1;

        // Stop polling after 20 attempts with no signals (1 minute)
        if (signalsCountRef.current === 0 && pollCountRef.current > 20) {
          console.log('[Signals] No signals after 20 polls, stopping');
          clearInterval(interval);
          return;
        }

        // Restart with new interval
        clearInterval(interval);
        interval = setInterval(poll, getPollInterval());
      };

      interval = setInterval(poll, getPollInterval());
    };

    startPolling();

    return () => clearInterval(interval);
  }, [threadId]);

  // Poll for inquiry suggestions
  useEffect(() => {
    async function loadSuggestions() {
      if (caseId) {
        try {
          const sugs = await signalsAPI.getPromotionSuggestions(caseId);
          setSuggestions(sugs);
        } catch (error) {
          console.error('Failed to load suggestions:', error);
        }
      }
    }

    if (caseId) {
      loadSuggestions();
      const interval = setInterval(loadSuggestions, 5000);
      return () => clearInterval(interval);
    }
  }, [caseId]);

  async function handleCreateCase() {
    setCreatingCase(true);
    try {
      const result = await casesAPI.createCase('Untitled Case');
      onCaseCreated?.(result.case.id);
    } catch (error) {
      console.error('Failed to create case:', error);
    } finally {
      setCreatingCase(false);
    }
  }

  return (
    <div className="w-80 border-l border-gray-200 p-4 overflow-y-auto bg-gray-50 flex flex-col">
      <div className="flex-1 space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Structure
          </h2>
          
          {/* Always show Create Case button */}
          <Button
            onClick={handleCreateCase}
            disabled={creatingCase || !!caseId}
            className="w-full mb-4"
            size="sm"
          >
            {creatingCase ? 'Creating...' : caseId ? 'Case Created' : 'Create Case'}
          </Button>
        </div>

        {/* Case Card */}
        {caseId && <CaseCard caseId={caseId} />}
        
        {/* Inquiry Suggestions */}
        {suggestions.length > 0 && (
          <InquirySuggestions 
            suggestions={suggestions}
            onInquiryCreated={() => {
              setSuggestions([]);
            }}
          />
        )}
      </div>

      {/* Collapsible Signals - Bottom Right */}
      {signals.length > 0 && (
        <div className="mt-auto pt-4 border-t border-gray-200">
          <button
            onClick={() => setSignalsExpanded(!signalsExpanded)}
            className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded transition-colors"
          >
            <span className="flex items-center gap-2">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"/>
                <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd"/>
              </svg>
              Signals ({signals.length})
            </span>
            <svg
              className={`w-4 h-4 transition-transform ${signalsExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {signalsExpanded && (
            <div className="mt-2 max-h-96 overflow-y-auto">
              <SignalsList signals={signals} onRefresh={loadSignals} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
