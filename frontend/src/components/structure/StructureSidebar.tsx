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

  // Poll for signals
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
    loadSignals();
    const interval = setInterval(loadSignals, 3000);
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
