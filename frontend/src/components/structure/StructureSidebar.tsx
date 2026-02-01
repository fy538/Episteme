/**
 * Structure sidebar - shows signals, inquiries, and suggestions
 */

'use client';

import { useEffect, useState } from 'react';
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

  // Poll for signals with smart backoff
  const loadSignals = async () => {
    if (threadId) {
      try {
        const sigs = await signalsAPI.getByThread(threadId);
        setSignals(sigs);
      } catch (error) {
        console.error('Failed to load signals:', error);
      }
    }
  };

  useEffect(() => {
    loadSignals(); // Initial load
    
    let pollCount = 0;
    let interval: NodeJS.Timeout;
    
    const startPolling = () => {
      // Smart polling with exponential backoff
      const getPollInterval = () => {
        if (signals.length === 0) {
          // No signals yet - poll more frequently (first 5 attempts)
          if (pollCount < 5) return 3000;   // 3s for first 15s
          if (pollCount < 10) return 5000;  // 5s for next 25s
          return 10000; // 10s after 40s
        } else {
          // Have signals - poll less frequently
          return 15000; // 15s when signals exist
        }
      };
      
      const poll = async () => {
        await loadSignals();
        pollCount++;
        
        // Stop polling after 20 attempts with no signals (1 minute)
        if (signals.length === 0 && pollCount > 20) {
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
  }, [threadId, signals.length]);

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
    <div className="w-80 border-l border-gray-200 p-4 overflow-y-auto bg-gray-50">
      <div className="space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Structure
          </h2>
          
          {!caseId && signals.length > 0 && (
            <Button
              onClick={handleCreateCase}
              disabled={creatingCase}
              className="w-full mb-4"
              size="sm"
            >
              {creatingCase ? 'Creating...' : 'Create Case'}
            </Button>
          )}
        </div>

        {caseId && <CaseCard caseId={caseId} />}
        
        {suggestions.length > 0 && (
          <InquirySuggestions 
            suggestions={suggestions}
            onInquiryCreated={() => {
              // Refresh suggestions
              setSuggestions([]);
            }}
          />
        )}
        
        <SignalsList signals={signals} onRefresh={loadSignals} />
      </div>
    </div>
  );
}
