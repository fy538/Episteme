/**
 * Case brief view - living document at the heart of case workspace
 * Cursor-inspired editable document with AI suggestions
 */

'use client';

import { useState, useEffect } from 'react';
import { Streamdown } from 'streamdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { BriefEditor } from '@/components/editor/BriefEditor';
import { CaseOnboarding } from '@/components/onboarding/CaseOnboarding';
import { AssumptionHighlighter } from '@/components/onboarding/AssumptionHighlighter';
import { documentsAPI } from '@/lib/api/documents';
import { inquiriesAPI } from '@/lib/api/inquiries';
import type { Case, CaseDocument, Inquiry } from '@/lib/types/case';

interface CaseBriefViewProps {
  caseData: Case;
  brief: CaseDocument | null;
  inquiries: Inquiry[];
  onStartInquiry: () => void;
  onOpenInquiry: (inquiryId: string) => void;
  onViewDashboard?: () => void;
  onRefresh: () => void;
}

export function CaseBriefView({
  caseData,
  brief,
  inquiries,
  onStartInquiry,
  onOpenInquiry,
  onViewDashboard,
  onRefresh,
}: CaseBriefViewProps) {
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState('');
  const [assumptions, setAssumptions] = useState<any[]>([]);
  const [detectingAssumptions, setDetectingAssumptions] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(true);
  const [hasInteracted, setHasInteracted] = useState(false);

  useEffect(() => {
    setTitleDraft(caseData.title);
  }, [caseData.title]);

  // Determine if should show onboarding
  useEffect(() => {
    // Show onboarding if:
    // 1. Case is new (has inquiries but no activity yet)
    // 2. User hasn't dismissed it
    // 3. Brief exists but hasn't been edited much
    const shouldShow = 
      !hasInteracted &&
      showOnboarding &&
      (inquiries.length > 0 || (brief && brief.ai_structure?.assumptions));
    
    setShowOnboarding(shouldShow);
  }, [hasInteracted, inquiries.length, brief]);

  async function detectAssumptions() {
    if (!brief) return;
    
    setDetectingAssumptions(true);
    try {
      const detected = await documentsAPI.detectAssumptions(brief.id);
      setAssumptions(detected);
      console.log('Detected assumptions:', detected);
      // TODO: Apply TipTap marks to highlight text
    } catch (error) {
      console.error('Failed to detect assumptions:', error);
    } finally {
      setDetectingAssumptions(false);
    }
  }

  async function handleSaveTitle() {
    if (!titleDraft.trim() || titleDraft === caseData.title) {
      setIsEditingTitle(false);
      return;
    }

    try {
      const { casesAPI } = await import('@/lib/api/cases');
      await casesAPI.updateCase(caseData.id, { title: titleDraft });
      setIsEditingTitle(false);
      onRefresh();
    } catch (error) {
      console.error('Failed to update case title:', error);
    }
  }

  const activeInquiries = inquiries.filter(i => i.status === 'open' || i.status === 'investigating');
  const resolvedInquiries = inquiries.filter(i => i.status === 'resolved');

  return (
    <div className="max-w-4xl mx-auto p-8">
      {/* Brief Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          {isEditingTitle ? (
            <div className="flex items-center gap-2 flex-1">
              <Input
                type="text"
                value={titleDraft}
                onChange={(e) => setTitleDraft(e.target.value)}
                onBlur={handleSaveTitle}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSaveTitle();
                  if (e.key === 'Escape') {
                    setTitleDraft(caseData.title);
                    setIsEditingTitle(false);
                  }
                }}
                autoFocus
                aria-label="Edit case title"
                className="text-3xl font-bold text-neutral-900 border-b-2 border-accent-500 bg-transparent outline-none flex-1 h-auto py-0"
              />
            </div>
          ) : (
            <button
              onClick={() => setIsEditingTitle(true)}
              className="text-3xl font-bold text-neutral-900 hover:text-accent-600 transition-colors"
            >
              {caseData.title}
            </button>
          )}
        </div>

        {/* Case metadata */}
        <div className="flex items-center gap-4 text-sm text-neutral-600">
          <span className="px-2 py-1 bg-neutral-100 rounded">{caseData.status}</span>
          <span className="px-2 py-1 bg-orange-100 text-orange-700 rounded">
            {caseData.stakes} stakes
          </span>
          {caseData.confidence != null && (
            <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded">
              {Math.round(caseData.confidence * 100)}% confidence
            </span>
          )}
        </div>
      </div>

      {/* Onboarding (for new cases) */}
      {showOnboarding && (
        <CaseOnboarding
          caseId={caseData.id}
          onStartInquiry={(inquiryId) => {
            setHasInteracted(true);
            onOpenInquiry(inquiryId);
          }}
          onDismiss={() => {
            setShowOnboarding(false);
            setHasInteracted(true);
          }}
        />
      )}

      {/* Assumption Highlighter */}
      {brief && brief.ai_structure?.assumptions && brief.ai_structure.assumptions.length > 0 && (
        <div className="mb-6">
          <AssumptionHighlighter
            assumptions={brief.highlighted_assumptions || brief.ai_structure.assumptions.map((text: string) => ({
              text,
              has_inquiry: false,
              inquiry_id: null,
              inquiry_title: null,
              inquiry_status: null,
              related_signals_count: 0,
              validated: false,
            }))}
            caseId={caseData.id}
            onInquiryCreated={(inquiryId) => {
              onRefresh();
            }}
            onViewInquiry={(inquiryId) => {
              onOpenInquiry(inquiryId);
            }}
          />
        </div>
      )}

      {/* Brief Content - Rich Editor */}
      <div className="mb-8">
        {brief ? (
          <BriefEditor
            document={brief}
            onSave={() => onRefresh()}
            onCreateInquiry={async (selectedText) => {
              // 1. Generate AI title from selected text
              const { title } = await inquiriesAPI.generateTitle(selectedText);
              
              // 2. Create inquiry with origin tracking
              const inquiry = await inquiriesAPI.create({
                case: caseData.id,
                title,
                description: `Validate: "${selectedText}"`,
                origin_text: selectedText,
                origin_document: brief.id,
                status: 'open',
              });
              
              // 3. Navigate to inquiry
              onOpenInquiry(inquiry.id);
            }}
            onMarkAssumption={(selectedText) => {
              console.log('Mark assumption:', selectedText);
            }}
          />
        ) : (
          <div className="p-8 text-center text-neutral-500">
            <p className="mb-4">No brief found for this case.</p>
            <p className="text-sm">A brief will be auto-generated when the case is created.</p>
          </div>
        )}
      </div>

      {/* Active Inquiries */}
      {activeInquiries.length > 0 && (
        <div className="mb-8 p-4 bg-purple-50 border border-purple-200 rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-purple-900">
              Active Inquiries ({activeInquiries.length})
            </h3>
            {onViewDashboard && (
              <Button size="sm" variant="outline" onClick={onViewDashboard}>
                View Dashboard
              </Button>
            )}
          </div>
          <div className="space-y-2">
            {activeInquiries.map(inquiry => (
              <button
                key={inquiry.id}
                onClick={() => onOpenInquiry(inquiry.id)}
                className="w-full text-left px-4 py-3 bg-white border border-purple-200 rounded-lg hover:border-purple-400 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-neutral-900">{inquiry.title}</span>
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
                {inquiry.description && (
                  <p className="text-sm text-neutral-600 mt-1">{inquiry.description}</p>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Resolved Inquiries */}
      {resolvedInquiries.length > 0 && (
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-neutral-900 mb-3">
            Resolved Inquiries ({resolvedInquiries.length})
          </h3>
          <div className="space-y-2">
            {resolvedInquiries.map(inquiry => (
              <button
                key={inquiry.id}
                onClick={() => onOpenInquiry(inquiry.id)}
                className="w-full text-left px-4 py-3 bg-green-50 border border-green-200 rounded-lg hover:border-green-400 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-neutral-900">{inquiry.title}</span>
                  <span className="text-xs text-green-700 font-medium">Resolved</span>
                </div>
                {inquiry.conclusion && (
                  <p className="text-sm text-neutral-700 mt-2 italic">"{inquiry.conclusion}"</p>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Detected Assumptions Summary */}
      {assumptions.length > 0 && (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <h3 className="text-lg font-semibold text-yellow-900 mb-2">
            Detected Assumptions ({assumptions.length})
          </h3>
          <div className="space-y-2 text-sm">
            {assumptions.map((assumption, idx) => (
              <div key={idx} className="flex items-start gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                  assumption.status === 'untested'
                    ? 'bg-yellow-200 text-yellow-800'
                    : assumption.status === 'investigating'
                    ? 'bg-purple-200 text-purple-800'
                    : 'bg-green-200 text-green-800'
                }`}>
                  {assumption.status}
                </span>
                <span className="text-neutral-800">"{assumption.text}"</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="flex gap-3">
        <Button onClick={onStartInquiry} variant="outline">
          + Start New Inquiry
        </Button>
        <Button 
          onClick={detectAssumptions} 
          variant="outline"
          disabled={detectingAssumptions || !brief}
        >
          {detectingAssumptions ? 'Detecting...' : 'Detect Assumptions'}
        </Button>
        <Button variant="outline">
          Generate Research
        </Button>
      </div>
    </div>
  );
}
