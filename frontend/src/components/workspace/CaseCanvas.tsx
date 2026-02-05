/**
 * CaseCanvas - Canvas-first case workspace
 *
 * The new primary view for cases that:
 * - Shows the decision graph by default
 * - Brief slides in from right when needed
 * - AI Copilot for gap analysis and suggestions
 * - Signals panel for viewing extracted signals
 * - Readiness panel for decision readiness
 * - Clean, minimal interface
 * - Focuses on graph thinking
 */

'use client';

import { useState, useCallback, useEffect } from 'react';
import {
  DecisionCanvas,
  BriefPanel,
  AICopilotPanel,
  AICopilotTrigger,
  SignalsPanel,
  ReadinessPanel,
} from '@/components/canvas';
import { useEvidenceLinks } from '@/hooks/useEvidenceLinks';
import { casesAPI } from '@/lib/api/cases';
import type { Case, CaseDocument, Inquiry } from '@/lib/types/case';

interface Signal {
  id: string;
  signal_type: string;
  content: string;
  inquiry_id?: string;
  strength?: number;
  validation_status?: string;
}

interface CaseCanvasProps {
  caseData: Case;
  brief: CaseDocument | null;
  inquiries: Inquiry[];
  signals?: Signal[];
  onInquiryClick: (inquiryId: string) => void;
  onAddInquiry: () => void;
  onEditBrief: () => void;
  onCreateInquiryFromText: (text: string) => void;
  onRefresh?: () => void;
}

export function CaseCanvas({
  caseData,
  brief,
  inquiries,
  signals = [],
  onInquiryClick,
  onAddInquiry,
  onEditBrief,
  onCreateInquiryFromText,
  onRefresh,
}: CaseCanvasProps) {
  const [briefOpen, setBriefOpen] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [signalsOpen, setSignalsOpen] = useState(false);
  const [readinessOpen, setReadinessOpen] = useState(false);

  // Evidence links for the brief panel
  const { claims, loadEvidenceLinks } = useEvidenceLinks({
    documentId: brief?.id || '',
  });

  // Open brief and load evidence links
  const handleOpenBrief = useCallback(() => {
    setBriefOpen(true);
    if (brief) {
      loadEvidenceLinks();
    }
  }, [brief, loadEvidenceLinks]);

  // Handle inquiry created from copilot
  const handleInquiryCreated = useCallback(() => {
    onRefresh?.();
  }, [onRefresh]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (isInputFocused()) return;

      switch (e.key.toLowerCase()) {
        case '?':
        case '/':
          e.preventDefault();
          setCopilotOpen((prev) => !prev);
          break;
        case 's':
          e.preventDefault();
          setSignalsOpen((prev) => !prev);
          break;
        case 'r':
          e.preventDefault();
          setReadinessOpen((prev) => !prev);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="relative w-full h-full">
      {/* Main canvas */}
      <DecisionCanvas
        caseData={caseData}
        inquiries={inquiries}
        signals={signals}
        onInquiryClick={onInquiryClick}
        onDecisionClick={handleOpenBrief}
        onAddInquiry={onAddInquiry}
        onOpenBrief={handleOpenBrief}
        onOpenSignals={() => setSignalsOpen(true)}
        onOpenReadiness={() => setReadinessOpen(true)}
      />

      {/* Brief slide-in panel */}
      <BriefPanel
        isOpen={briefOpen}
        onClose={() => setBriefOpen(false)}
        brief={brief}
        claims={claims}
        onEdit={onEditBrief}
        onCreateInquiry={onCreateInquiryFromText}
      />

      {/* AI Copilot panel */}
      <AICopilotPanel
        caseId={caseData.id}
        isOpen={copilotOpen}
        onClose={() => setCopilotOpen(false)}
        onInquiryCreated={handleInquiryCreated}
        onInquiryClick={onInquiryClick}
      />

      {/* Signals panel */}
      <SignalsPanel
        isOpen={signalsOpen}
        onClose={() => setSignalsOpen(false)}
        signals={signals.map((s) => ({
          id: s.id,
          type: mapSignalType(s.signal_type),
          text: s.content,
          strength: s.strength ?? 0.5,
          validation_status: mapValidationStatus(s.validation_status),
          inquiry_id: s.inquiry_id,
        }))}
        onSignalClick={(signal) => {
          if (signal.inquiry_id) {
            onInquiryClick(signal.inquiry_id);
          }
        }}
      />

      {/* Readiness panel */}
      <ReadinessPanel
        isOpen={readinessOpen}
        onClose={() => setReadinessOpen(false)}
        caseId={caseData.id}
        caseData={caseData}
        onReadyClick={() => {
          // User declared ready - could trigger decision flow
          setReadinessOpen(false);
        }}
        onCreateInquiry={(text) => {
          // Create inquiry from blind spot
          onCreateInquiryFromText(text);
          setReadinessOpen(false);
        }}
      />

      {/* AI Copilot trigger (when closed) */}
      {!copilotOpen && (
        <div className="absolute top-4 right-4 z-40">
          <AICopilotTrigger onClick={() => setCopilotOpen(true)} />
        </div>
      )}

      {/* Keyboard shortcuts hint */}
      <div className="absolute bottom-4 left-4 text-xs text-neutral-400">
        <span className="bg-white/80 backdrop-blur px-2 py-1 rounded">
          <kbd className="px-1 py-0.5 bg-neutral-100 rounded mx-1">B</kbd> Brief
          • <kbd className="px-1 py-0.5 bg-neutral-100 rounded mx-1">N</kbd> Inquiry
          • <kbd className="px-1 py-0.5 bg-neutral-100 rounded mx-1">?</kbd> Copilot
          • <kbd className="px-1 py-0.5 bg-neutral-100 rounded mx-1">S</kbd> Signals
          • <kbd className="px-1 py-0.5 bg-neutral-100 rounded mx-1">R</kbd> Readiness
        </span>
      </div>
    </div>
  );
}

// Helper
function isInputFocused(): boolean {
  const el = document.activeElement;
  return (
    el instanceof HTMLInputElement ||
    el instanceof HTMLTextAreaElement ||
    el?.getAttribute('contenteditable') === 'true'
  );
}

// Map API signal types to component expected types
function mapSignalType(
  type: string
): 'claim' | 'assumption' | 'evidence' | 'question' | 'constraint' | 'goal' {
  const typeMap: Record<string, 'claim' | 'assumption' | 'evidence' | 'question' | 'constraint' | 'goal'> = {
    claim: 'claim',
    assumption: 'assumption',
    evidence: 'evidence',
    evidence_mention: 'evidence',
    question: 'question',
    constraint: 'constraint',
    goal: 'goal',
    decision_intent: 'goal',
  };
  return typeMap[type.toLowerCase()] || 'claim';
}

// Map validation status from API to component
function mapValidationStatus(
  status?: string
): 'validated' | 'unvalidated' | 'contradicted' | 'pending' | undefined {
  if (!status) return undefined;
  const statusMap: Record<string, 'validated' | 'unvalidated' | 'contradicted' | 'pending'> = {
    validated: 'validated',
    unvalidated: 'unvalidated',
    contradicted: 'contradicted',
    pending: 'pending',
  };
  return statusMap[status.toLowerCase()];
}
