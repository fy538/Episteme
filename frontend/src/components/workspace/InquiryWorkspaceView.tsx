/**
 * Inquiry workspace - research environment for specific questions
 * Tabs: Evidence, Objections, Brief
 */

'use client';

import { useState, useEffect } from 'react';
import { Streamdown } from 'streamdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { EvidenceList } from '@/components/evidence/EvidenceList';
import { DiffViewer } from '@/components/ui/DiffViewer';
import { inquiriesAPI } from '@/lib/api/inquiries';
import { documentsAPI } from '@/lib/api/documents';
import type { Inquiry, CaseDocument } from '@/lib/types/case';
import type { InquiryEvidence, Objection } from '@/lib/types/inquiry';

interface InquiryWorkspaceViewProps {
  caseId: string;
  inquiry: Inquiry;
  onBack: () => void;
  onRefresh: () => void;
  briefId?: string;
  briefContent?: string;
}

type TabType = 'evidence' | 'objections' | 'brief';

export function InquiryWorkspaceView({
  caseId,
  inquiry,
  onBack,
  onRefresh,
  briefId,
  briefContent = '',
}: InquiryWorkspaceViewProps) {
  const [activeTab, setActiveTab] = useState<TabType>('evidence');
  const [evidence, setEvidence] = useState<InquiryEvidence[]>([]);
  const [objections, setObjections] = useState<Objection[]>([]);
  const [brief, setBrief] = useState<CaseDocument | null>(null);
  const [isResolvingopen, setIsResolving] = useState(false);
  const [conclusion, setConclusion] = useState('');
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [briefUpdateSuggestion, setBriefUpdateSuggestion] = useState<any>(null);

  useEffect(() => {
    loadInquiryData();
    setTitleDraft(inquiry.title);
  }, [inquiry.id, inquiry.title]);

  async function loadInquiryData() {
    try {
      // Load evidence, objections, and brief in parallel
      const [evd, obj] = await Promise.all([
        fetch(`/api/evidence/?inquiry=${inquiry.id}`).then(r => r.json()),
        fetch(`/api/objections/?inquiry=${inquiry.id}`).then(r => r.json()),
      ]);
      
      setEvidence(evd);
      setObjections(obj);
      
      // Load inquiry brief if it exists
      if (inquiry.brief) {
        const briefDoc = await documentsAPI.get(inquiry.brief);
        setBrief(briefDoc);
      }
    } catch (error) {
      console.error('Failed to load inquiry data:', error);
    }
  }

  async function handleResolve() {
    if (!conclusion.trim()) return;
    
    setIsResolving(true);
    try {
      // 1. Resolve inquiry
      await inquiriesAPI.resolve(inquiry.id, conclusion);
      
      // 2. Generate brief update suggestion if brief exists
      if (briefId) {
        const suggestion = await inquiriesAPI.generateBriefUpdate(
          inquiry.id,
          briefId
        );
        setBriefUpdateSuggestion(suggestion);
      } else {
        // No brief update, just go back
        onRefresh();
        onBack();
      }
    } catch (error) {
      console.error('Failed to resolve inquiry:', error);
    } finally {
      setIsResolving(false);
    }
  }

  async function handleSaveTitle() {
    if (!titleDraft.trim() || titleDraft === inquiry.title) {
      setIsEditingTitle(false);
      return;
    }

    try {
      await inquiriesAPI.update(inquiry.id, { title: titleDraft });
      setIsEditingTitle(false);
      onRefresh();
    } catch (error) {
      console.error('Failed to update inquiry title:', error);
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete inquiry "${inquiry.title}"? This cannot be undone.`)) {
      return;
    }

    setDeleting(true);
    try {
      await inquiriesAPI.delete(inquiry.id);
      onBack();
      onRefresh();
    } catch (error) {
      console.error('Failed to delete inquiry:', error);
      setDeleting(false);
    }
  }

  const supportingEvidence = evidence.filter(e => e.direction === 'supporting');
  const contradictingEvidence = evidence.filter(e => e.direction === 'contradicting');

  return (
    <div className="max-w-5xl mx-auto p-8">
      {/* Inquiry Header */}
      <div className="mb-6">
        <button
          onClick={onBack}
          className="text-sm text-blue-600 hover:text-blue-700 mb-3 flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Case
        </button>

        {isEditingTitle ? (
          <div className="flex items-center gap-2 mb-3">
            <input
              type="text"
              value={titleDraft}
              onChange={(e) => setTitleDraft(e.target.value)}
              onBlur={handleSaveTitle}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveTitle();
                if (e.key === 'Escape') {
                  setTitleDraft(inquiry.title);
                  setIsEditingTitle(false);
                }
              }}
              autoFocus
              className="text-3xl font-bold text-gray-900 border-b-2 border-blue-500 bg-transparent outline-none flex-1"
            />
          </div>
        ) : (
          <button
            onClick={() => setIsEditingTitle(true)}
            className="text-3xl font-bold text-gray-900 hover:text-blue-600 transition-colors mb-3 text-left"
          >
            {inquiry.title}
          </button>
        )}
        
        {inquiry.description && (
          <p className="text-gray-600 mb-4">{inquiry.description}</p>
        )}

        {/* Status and actions */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              inquiry.status === 'resolved' 
                ? 'bg-green-100 text-green-700'
                : 'bg-purple-100 text-purple-700'
            }`}>
              {inquiry.status}
            </span>
            
            {inquiry.status !== 'resolved' && (
              <Button onClick={() => setActiveTab('evidence')} size="sm" variant="outline">
                Resolve Inquiry
              </Button>
            )}
          </div>

          {/* Delete button */}
          <Button
            onClick={handleDelete}
            disabled={deleting}
            size="sm"
            variant="outline"
            className="text-red-600 hover:bg-red-50"
          >
            {deleting ? 'Deleting...' : 'Delete Inquiry'}
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <div className="flex gap-6">
          <button
            onClick={() => setActiveTab('evidence')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'evidence'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Evidence ({evidence.length})
          </button>
          <button
            onClick={() => setActiveTab('objections')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'objections'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Objections ({objections.length})
          </button>
          <button
            onClick={() => setActiveTab('brief')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'brief'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Brief
          </button>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'evidence' && (
        <div className="space-y-6">
          {/* Supporting Evidence */}
          <div>
            <h3 className="text-lg font-semibold text-green-900 mb-3">
              Supporting ({supportingEvidence.length})
            </h3>
            {supportingEvidence.length === 0 ? (
              <p className="text-gray-500 italic">No supporting evidence yet</p>
            ) : (
              <div className="space-y-3">
                {supportingEvidence.map(e => (
                  <div key={e.id} className="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-gray-800">{e.content}</p>
                    {e.source && (
                      <p className="text-xs text-gray-600 mt-2">Source: {e.source}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Contradicting Evidence */}
          <div>
            <h3 className="text-lg font-semibold text-red-900 mb-3">
              Contradicting ({contradictingEvidence.length})
            </h3>
            {contradictingEvidence.length === 0 ? (
              <p className="text-gray-500 italic">No contradicting evidence yet</p>
            ) : (
              <div className="space-y-3">
                {contradictingEvidence.map(e => (
                  <div key={e.id} className="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-gray-800">{e.content}</p>
                    {e.source && (
                      <p className="text-xs text-gray-600 mt-2">Source: {e.source}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Resolve section */}
          {inquiry.status !== 'resolved' && evidence.length > 0 && (
            <div className="mt-8 p-6 bg-blue-50 border border-blue-200 rounded-lg">
              <h3 className="text-lg font-semibold text-blue-900 mb-3">
                Ready to conclude?
              </h3>
              <textarea
                value={conclusion}
                onChange={(e) => setConclusion(e.target.value)}
                placeholder="Based on the evidence, what's your conclusion?"
                className="w-full px-4 py-3 border border-blue-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 mb-3"
                rows={3}
              />
              <Button 
                onClick={handleResolve}
                disabled={isResolvingopen || !conclusion.trim()}
              >
                {isResolvingopen ? 'Resolving...' : 'Resolve Inquiry'}
              </Button>
            </div>
          )}
        </div>
      )}

      {activeTab === 'objections' && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Challenges & Alternatives
          </h3>
          {objections.length === 0 ? (
            <p className="text-gray-500 italic">No objections raised yet</p>
          ) : (
            <div className="space-y-3">
              {objections.map(obj => (
                <div key={obj.id} className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="font-medium text-gray-900 mb-2">{obj.content}</p>
                  {obj.response && (
                    <div className="mt-3 pt-3 border-t border-yellow-200">
                      <p className="text-sm text-gray-700">
                        <span className="font-medium">Response:</span> {obj.response}
                      </p>
                    </div>
                  )}
                  <div className="mt-2 flex gap-2">
                    <span className={`text-xs px-2 py-1 rounded ${
                      obj.status === 'addressed' 
                        ? 'bg-green-100 text-green-700'
                        : obj.status === 'dismissed'
                        ? 'bg-gray-100 text-gray-600'
                        : 'bg-yellow-100 text-yellow-700'
                    }`}>
                      {obj.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'brief' && (
        <div>
          {brief ? (
            <div className="prose prose-lg max-w-none">
              <Streamdown remarkPlugins={[remarkGfm]}>
                {brief.content_markdown || ''}
              </Streamdown>
            </div>
          ) : (
            <div className="text-center py-12">
              <p className="text-gray-500 mb-4">No inquiry brief yet</p>
              <Button size="sm" variant="outline">
                Generate Inquiry Brief
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Brief Update Suggestion Modal */}
      {briefUpdateSuggestion && briefId && (
        <DiffViewer
          original={briefContent}
          proposed={briefUpdateSuggestion.updated_content}
          title="Update Brief with Inquiry Conclusion"
          onAccept={async (content) => {
            await documentsAPI.update(briefId, { content_markdown: content });
            setBriefUpdateSuggestion(null);
            onRefresh();
            onBack();
          }}
          onReject={() => {
            setBriefUpdateSuggestion(null);
            onRefresh();
            onBack();
          }}
          onClose={() => setBriefUpdateSuggestion(null)}
        />
      )}
    </div>
  );
}
