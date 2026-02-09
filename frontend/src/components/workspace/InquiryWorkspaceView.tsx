/**
 * Inquiry workspace - research environment for specific questions
 * Tabs: Objections, Brief
 */

'use client';

import { useState, useEffect } from 'react';
import { Streamdown } from 'streamdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { DiffViewer } from '@/components/ui/DiffViewer';
import { inquiriesAPI } from '@/lib/api/inquiries';
import { documentsAPI } from '@/lib/api/documents';
import type { Inquiry, WorkingDocument } from '@/lib/types/case';
import type { Objection } from '@/lib/types/inquiry';

interface InquiryWorkspaceViewProps {
  caseId: string;
  inquiry: Inquiry;
  onBack: () => void;
  onRefresh: () => void;
  briefId?: string;
  briefContent?: string;
}

type TabType = 'objections' | 'brief';

export function InquiryWorkspaceView({
  caseId,
  inquiry,
  onBack,
  onRefresh,
  briefId,
  briefContent = '',
}: InquiryWorkspaceViewProps) {
  const [activeTab, setActiveTab] = useState<TabType>('objections');
  const [objections, setObjections] = useState<Objection[]>([]);
  const [brief, setBrief] = useState<WorkingDocument | null>(null);
  const [isResolving, setIsResolving] = useState(false);
  const [conclusion, setConclusion] = useState('');
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [briefUpdateSuggestion, setBriefUpdateSuggestion] = useState<any>(null);

  useEffect(() => {
    loadInquiryData();
    setTitleDraft(inquiry.title);
  }, [inquiry.id, inquiry.title]);

  async function loadInquiryData() {
    try {
      // Load objections
      const obj = await fetch(`/api/objections/?inquiry=${inquiry.id}`).then(r => r.json());
      setObjections(obj);

      // Load inquiry brief if it exists
      if (inquiry.brief) {
        const briefDoc = await documentsAPI.get(inquiry.brief);
        setBrief(briefDoc);
      }
    } catch (err) {
      console.error('Failed to load inquiry data:', err);
      setError('Failed to load inquiry data. Please try again.');
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
    } catch (err) {
      console.error('Failed to resolve inquiry:', err);
      setError('Failed to resolve inquiry. Please try again.');
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
    } catch (err) {
      console.error('Failed to update inquiry title:', err);
      setError('Failed to update title. Please try again.');
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
    } catch (err) {
      console.error('Failed to delete inquiry:', err);
      setError('Failed to delete inquiry. Please try again.');
      setDeleting(false);
    }
  }

  return (
    <div className="max-w-5xl mx-auto p-8">
      {/* Error banner */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between">
          <p className="text-sm text-red-700">{error}</p>
          <button
            onClick={() => setError(null)}
            className="text-red-500 hover:text-red-700 text-sm font-medium"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Inquiry Header */}
      <div className="mb-6">
        <button
          onClick={onBack}
          className="text-sm text-accent-600 hover:text-accent-700 mb-3 flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Case
        </button>

        {isEditingTitle ? (
          <div className="flex items-center gap-2 mb-3">
            <Input
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
              aria-label="Edit inquiry title"
              className="text-3xl tracking-tight font-bold text-neutral-900 border-b-2 border-accent-500 bg-transparent outline-none flex-1 h-auto py-0"
            />
          </div>
        ) : (
          <button
            onClick={() => setIsEditingTitle(true)}
            className="text-3xl tracking-tight font-bold text-neutral-900 hover:text-accent-600 transition-colors mb-3 text-left"
          >
            {inquiry.title}
          </button>
        )}

        {inquiry.description && (
          <p className="text-neutral-600 mb-4">{inquiry.description}</p>
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
          </div>

          {/* Delete button */}
          <Button
            onClick={handleDelete}
            disabled={deleting}
            size="sm"
            variant="outline"
            className="text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
          >
            {deleting ? 'Deleting...' : 'Delete Inquiry'}
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-neutral-200 dark:border-neutral-800 mb-6">
        <div className="flex gap-6">
          <button
            onClick={() => setActiveTab('objections')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'objections'
                ? 'border-accent-600 text-accent-600'
                : 'border-transparent text-neutral-500 hover:text-neutral-700'
            }`}
          >
            Objections ({objections.length})
          </button>
          <button
            onClick={() => setActiveTab('brief')}
            className={`pb-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'brief'
                ? 'border-accent-600 text-accent-600'
                : 'border-transparent text-neutral-500 hover:text-neutral-700'
            }`}
          >
            Brief
          </button>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'objections' && (
        <div>
          <h3 className="text-lg font-semibold text-neutral-900 mb-4">
            Challenges & Alternatives
          </h3>
          {objections.length === 0 ? (
            <p className="text-neutral-500 italic">No objections raised yet</p>
          ) : (
            <div className="space-y-3">
              {objections.map(obj => (
                <div key={obj.id} className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="font-medium text-neutral-900 mb-2">{obj.content}</p>
                  {obj.response && (
                    <div className="mt-3 pt-3 border-t border-yellow-200">
                      <p className="text-sm text-neutral-700">
                        <span className="font-medium">Response:</span> {obj.response}
                      </p>
                    </div>
                  )}
                  <div className="mt-2 flex gap-2">
                    <span className={`text-xs px-2 py-1 rounded ${
                      obj.status === 'addressed'
                        ? 'bg-green-100 text-green-700'
                        : obj.status === 'dismissed'
                        ? 'bg-neutral-100 text-neutral-600'
                        : 'bg-yellow-100 text-yellow-700'
                    }`}>
                      {obj.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Resolve section */}
          {inquiry.status !== 'resolved' && (
            <div className="mt-8 p-6 bg-accent-50 border border-accent-200 rounded-lg">
              <h3 className="text-lg font-semibold text-accent-900 mb-3">
                Ready to conclude?
              </h3>
              <Textarea
                value={conclusion}
                onChange={(e) => setConclusion(e.target.value)}
                placeholder="What's your conclusion for this inquiry?"
                aria-label="Inquiry conclusion"
                className="mb-3"
                rows={3}
              />
              <Button
                onClick={handleResolve}
                disabled={isResolving || !conclusion.trim()}
              >
                {isResolving ? 'Resolving...' : 'Resolve Inquiry'}
              </Button>
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
              <p className="text-neutral-500 italic">No inquiry brief yet. Resolve the inquiry to generate one.</p>
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
