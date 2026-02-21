'use client';

import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { casesAPI } from '@/lib/api/cases';
import type { DecisionRecord, ResolutionType } from '@/lib/types/case';
import type { PlanAssumption } from '@/lib/types/plan';

interface DecisionSummaryViewProps {
  decision: DecisionRecord;
  assumptions?: PlanAssumption[];
  onAddOutcomeNote?: (note: string, sentiment: string) => Promise<void>;
}

// ── Resolution type display config ──────────────────────────

const RESOLUTION_HEADERS: Record<ResolutionType, { label: string; icon: string }> = {
  resolved: { label: 'Resolved', icon: '✓' },
  closed: { label: 'Closed', icon: '—' },
};

// ── Helpers ──────────────────────────────────────────────────

function sentimentIcon(sentiment: string): string {
  switch (sentiment) {
    case 'positive': return '✓';
    case 'negative': return '✗';
    default: return '·';
  }
}

function sentimentColor(sentiment: string): string {
  switch (sentiment) {
    case 'positive': return 'text-emerald-600 dark:text-emerald-400';
    case 'negative': return 'text-red-600 dark:text-red-400';
    default: return 'text-neutral-500 dark:text-neutral-400';
  }
}

function formatDate(isoString: string): string {
  try {
    return new Date(isoString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return isoString;
  }
}

function daysUntil(dateStr: string): number {
  const target = new Date(dateStr + 'T00:00:00');
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

// ── Inline-editable text field ──────────────────────────────

function EditableText({
  value,
  onSave,
  multiline = false,
  className = '',
}: {
  value: string;
  onSave: (newValue: string) => Promise<void>;
  multiline?: boolean;
  className?: string;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);

  const handleSave = async () => {
    if (draft.trim() === value) {
      setIsEditing(false);
      return;
    }
    setIsSaving(true);
    setSaveError(false);
    try {
      await onSave(draft.trim());
      setIsEditing(false);
    } catch {
      // Keep editing open with error indicator so user can retry
      setSaveError(true);
    } finally {
      setIsSaving(false);
    }
  };

  if (isEditing) {
    const Tag = multiline ? 'textarea' : 'input';
    return (
      <div className="space-y-1">
        <Tag
          value={draft}
          onChange={(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
            setDraft(e.target.value);
            setSaveError(false);
          }}
          onBlur={handleSave}
          onKeyDown={(e: React.KeyboardEvent) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSave();
            }
            if (e.key === 'Escape') {
              setDraft(value);
              setSaveError(false);
              setIsEditing(false);
            }
          }}
          disabled={isSaving}
          autoFocus
          className={`w-full px-2 py-1 text-sm rounded border bg-white dark:bg-neutral-900 focus:outline-none focus:ring-1 ${
            saveError
              ? 'border-red-400 dark:border-red-600 focus:ring-red-400'
              : 'border-accent-300 dark:border-accent-700 focus:ring-accent-400'
          } ${className}`}
          rows={multiline ? 3 : undefined}
        />
        {isSaving && (
          <p className="text-xs text-neutral-400">Saving...</p>
        )}
        {saveError && (
          <p className="text-xs text-red-500 dark:text-red-400">
            Save failed. Press Enter to retry or Escape to discard.
          </p>
        )}
      </div>
    );
  }

  return (
    <span
      onClick={() => { setDraft(value); setIsEditing(true); }}
      className={`cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded px-1 -mx-1 transition-colors ${className}`}
      title="Click to edit"
    >
      {value}
    </span>
  );
}

// ── Main Component ──────────────────────────────────────────

export function DecisionSummaryView({
  decision,
  assumptions = [],
  onAddOutcomeNote,
}: DecisionSummaryViewProps) {
  const [showNoteForm, setShowNoteForm] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [noteSentiment, setNoteSentiment] = useState<'positive' | 'neutral' | 'negative'>('neutral');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');

  // Local state for inline edits (optimistic)
  const [localDecision, setLocalDecision] = useState(decision);

  const resolutionType = localDecision.resolution_type || 'resolved';
  const header = RESOLUTION_HEADERS[resolutionType] || RESOLUTION_HEADERS.resolved;
  const showOutcomeTimeline = resolutionType !== 'closed';

  // Inline edit handlers
  const handleSaveField = useCallback(async (field: string, value: string | string[]) => {
    const updates: Record<string, unknown> = { [field]: value };
    const updated = await casesAPI.updateResolution(localDecision.case, updates as Parameters<typeof casesAPI.updateResolution>[1]);
    setLocalDecision(updated);
  }, [localDecision.case]);

  const handleSubmitNote = useCallback(async () => {
    if (!noteText.trim() || !onAddOutcomeNote) return;
    setIsSaving(true);
    setError('');
    try {
      await onAddOutcomeNote(noteText.trim(), noteSentiment);
      setNoteText('');
      setNoteSentiment('neutral');
      setShowNoteForm(false);
    } catch {
      setError('Failed to add note. Please try again.');
    } finally {
      setIsSaving(false);
    }
  }, [noteText, noteSentiment, onAddOutcomeNote]);

  // Build assumption cross-reference
  const linkedIds = new Set(localDecision.linked_assumption_ids);
  const validatedAssumptions = assumptions.filter((a) => linkedIds.has(a.id));
  const unvalidatedAssumptions = assumptions.filter((a) => !linkedIds.has(a.id));

  return (
    <div className="space-y-5">
      {/* Decision / Resolution Statement */}
      <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-5 bg-white dark:bg-neutral-900">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-3 flex items-center gap-1.5">
          <span>{header.icon}</span>
          {header.label}
        </h3>

        <div className="text-neutral-900 dark:text-neutral-100 leading-relaxed">
          <EditableText
            value={localDecision.decision_text}
            onSave={(v) => handleSaveField('decision_text', v)}
            multiline
          />
        </div>

        {/* Key Reasons */}
        {localDecision.key_reasons.length > 0 && (
          <div className="mt-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-2">
              Key Reasons
            </h4>
            <ol className="space-y-1.5">
              {localDecision.key_reasons.map((reason, i) => (
                <li key={i} className="flex gap-2 text-sm text-neutral-700 dark:text-neutral-300">
                  <span className="text-neutral-400 dark:text-neutral-500 shrink-0">{i + 1}.</span>
                  <EditableText
                    value={reason}
                    onSave={async (v) => {
                      const updated = [...localDecision.key_reasons];
                      updated[i] = v;
                      await handleSaveField('key_reasons', updated);
                    }}
                  />
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Resolution Profile (LLM narrative) */}
        {localDecision.resolution_profile && (
          <div className="mt-4 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-100 dark:border-neutral-700/50">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-1.5">
              Resolution Profile
            </h4>
            <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">
              {localDecision.resolution_profile}
            </p>
          </div>
        )}

        {/* Caveats */}
        {localDecision.caveats && (
          <div className="mt-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-1.5">
              Caveats
            </h4>
            <div className="text-sm text-neutral-600 dark:text-neutral-400 italic">
              <EditableText
                value={localDecision.caveats}
                onSave={(v) => handleSaveField('caveats', v)}
                multiline
              />
            </div>
          </div>
        )}

        {/* Assumptions validated */}
        {assumptions.length > 0 && (
          <div className="mt-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-2">
              Assumptions Validated
            </h4>
            <div className="space-y-1">
              {validatedAssumptions.map((a) => (
                <div key={a.id} className="flex items-start gap-2 text-sm">
                  <span className="text-emerald-500 mt-0.5 shrink-0">✓</span>
                  <span className="text-neutral-700 dark:text-neutral-300">{a.text}</span>
                </div>
              ))}
              {unvalidatedAssumptions.map((a) => (
                <div key={a.id} className="flex items-start gap-2 text-sm">
                  <span className="text-neutral-400 mt-0.5 shrink-0">✗</span>
                  <span className="text-neutral-400 dark:text-neutral-500">
                    {a.text}
                    <span className="ml-1 text-xs">(not validated)</span>
                  </span>
                </div>
              ))}
            </div>
            {linkedIds.size > 0 && (
              <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1.5">
                {validatedAssumptions.length} of {assumptions.length} assumptions validated
                {linkedIds.size > validatedAssumptions.length && (
                  <span>; {linkedIds.size - validatedAssumptions.length} no longer tracked</span>
                )}
              </p>
            )}
          </div>
        )}

        {/* Decided at */}
        <p className="mt-4 text-xs text-neutral-400 dark:text-neutral-500">
          {resolutionType === 'resolved' ? 'Resolved' : 'Closed'} on {formatDate(localDecision.decided_at)}
        </p>
      </div>

      {/* Outcome Timeline — hidden for closed cases */}
      {showOutcomeTimeline && (
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-5 bg-white dark:bg-neutral-900" data-outcome-timeline>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-3">
            Outcome Timeline
          </h3>

          {localDecision.outcome_notes.length > 0 ? (
            <div className="space-y-3">
              {localDecision.outcome_notes.map((note, i) => (
                <div key={i} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <span className={`text-sm font-medium ${sentimentColor(note.sentiment)}`}>
                      {sentimentIcon(note.sentiment)}
                    </span>
                    {i < localDecision.outcome_notes.length - 1 && (
                      <div className="w-px flex-1 bg-neutral-200 dark:bg-neutral-700 mt-1" />
                    )}
                  </div>
                  <div className="flex-1 pb-3">
                    <div className="flex items-baseline gap-2">
                      <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
                        {formatDate(note.date)}
                      </span>
                      <span className={`text-xs capitalize ${sentimentColor(note.sentiment)}`}>
                        {note.sentiment}
                      </span>
                    </div>
                    <p className="text-sm text-neutral-700 dark:text-neutral-300 mt-0.5">
                      {note.note}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-neutral-400 dark:text-neutral-500 italic">
              No outcome notes yet.
            </p>
          )}

          {/* Add Note Form */}
          {showNoteForm ? (
            <div className="mt-4 space-y-3 pt-3 border-t border-neutral-100 dark:border-neutral-800">
              <Textarea
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="How did it go? What happened?"
                className="resize-none"
                rows={2}
                autoFocus
              />
              <div className="flex items-center gap-3">
                <span className="text-xs text-neutral-500 dark:text-neutral-400">How&apos;s it going?</span>
                <div className="flex gap-1">
                  {(['positive', 'neutral', 'negative'] as const).map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => setNoteSentiment(s)}
                      className={`text-xs px-2.5 py-1 rounded-full border transition-colors capitalize ${
                        noteSentiment === s
                          ? s === 'positive'
                            ? 'bg-emerald-100 dark:bg-emerald-900/30 border-emerald-300 dark:border-emerald-700 text-emerald-700 dark:text-emerald-300'
                            : s === 'negative'
                            ? 'bg-red-100 dark:bg-red-900/30 border-red-300 dark:border-red-700 text-red-700 dark:text-red-300'
                            : 'bg-neutral-100 dark:bg-neutral-800 border-neutral-300 dark:border-neutral-600 text-neutral-700 dark:text-neutral-300'
                          : 'border-neutral-200 dark:border-neutral-700 text-neutral-400 dark:text-neutral-500 hover:border-neutral-300 dark:hover:border-neutral-600'
                      }`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
              {error && (
                <p className="text-xs text-red-500" role="alert">{error}</p>
              )}
              <div className="flex justify-end gap-2">
                <Button variant="ghost" size="sm" onClick={() => { setShowNoteForm(false); setNoteText(''); }}>
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={handleSubmitNote}
                  disabled={!noteText.trim() || isSaving}
                  isLoading={isSaving}
                >
                  {isSaving ? 'Adding...' : 'Add Note'}
                </Button>
              </div>
            </div>
          ) : onAddOutcomeNote ? (
            <button
              type="button"
              onClick={() => setShowNoteForm(true)}
              className="mt-3 text-sm text-accent-600 dark:text-accent-400 hover:text-accent-700 dark:hover:text-accent-300 transition-colors"
            >
              + Add Outcome Note
            </button>
          ) : null}

          {/* Next check date */}
          {localDecision.outcome_check_date && (
            <div className="mt-4 pt-3 border-t border-neutral-100 dark:border-neutral-800">
              {(() => {
                const days = daysUntil(localDecision.outcome_check_date);
                const isPast = days < 0;
                const isNear = days >= 0 && days <= 7;
                return (
                  <p className={`text-xs ${
                    isPast
                      ? 'text-red-500 dark:text-red-400'
                      : isNear
                      ? 'text-amber-600 dark:text-amber-400'
                      : 'text-neutral-400 dark:text-neutral-500'
                  }`}>
                    {isPast
                      ? `⏰ Outcome check was due ${formatDate(localDecision.outcome_check_date)} (${Math.abs(days)} days ago)`
                      : days === 0
                      ? '⏰ Outcome check is due today'
                      : `📅 Next check: ${formatDate(localDecision.outcome_check_date)} (in ${days} days)`
                    }
                  </p>
                );
              })()}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
