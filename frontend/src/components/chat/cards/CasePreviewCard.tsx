/**
 * CasePreviewCard - Rich preview of a structured case ready for creation
 *
 * Shown after the analyze_for_case API returns results. Displays the
 * suggested title, key questions, and assumptions. User can edit all
 * fields before creating the case, turning AI analysis into a
 * collaborative refinement step.
 */

'use client';

import { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import {
  ActionCard,
  ActionCardHeader,
  ActionCardTitle,
  ActionCardFooter,
} from '@/components/ui/action-card';
import type { InlineActionCard, CasePreviewData } from '@/lib/types/chat';
import { CompanionTransferIndicator } from './CompanionTransferIndicator';

interface CasePreviewCardProps {
  card: InlineActionCard;
  onCreateCase: (
    analysis: Record<string, unknown>,
    title: string,
    userEdits?: Record<string, unknown>
  ) => void;
  onAdjust: () => void;
  onDismiss: () => void;
  isCreating?: boolean;
}

// ── Inline editable text ────────────────────────────────────────

function EditableText({
  value,
  onChange,
  className = '',
  multiline = false,
  placeholder = '',
}: {
  value: string;
  onChange: (v: string) => void;
  className?: string;
  multiline?: boolean;
  placeholder?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const commit = useCallback(() => {
    const trimmed = draft.trim();
    if (trimmed && trimmed !== value) onChange(trimmed);
    else setDraft(value);
    setEditing(false);
  }, [draft, value, onChange]);

  if (!editing) {
    return (
      <span
        role="button"
        tabIndex={0}
        onClick={() => { setDraft(value); setEditing(true); }}
        onKeyDown={(e) => { if (e.key === 'Enter') { setDraft(value); setEditing(true); } }}
        className={`cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded px-0.5 -mx-0.5 transition-colors ${className}`}
        title="Click to edit"
      >
        {value}
      </span>
    );
  }

  if (multiline) {
    return (
      <textarea
        ref={inputRef as React.RefObject<HTMLTextAreaElement>}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => { if (e.key === 'Escape') { setDraft(value); setEditing(false); } }}
        placeholder={placeholder}
        rows={2}
        className={`w-full bg-white dark:bg-neutral-800 border border-accent-300 dark:border-accent-600 rounded px-1.5 py-0.5 text-xs text-neutral-800 dark:text-neutral-200 focus:outline-none focus:ring-1 focus:ring-accent-400 resize-none ${className}`}
      />
    );
  }

  return (
    <input
      ref={inputRef as React.RefObject<HTMLInputElement>}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === 'Enter') commit();
        if (e.key === 'Escape') { setDraft(value); setEditing(false); }
      }}
      placeholder={placeholder}
      className={`w-full bg-white dark:bg-neutral-800 border border-accent-300 dark:border-accent-600 rounded px-1.5 py-0.5 text-sm text-neutral-800 dark:text-neutral-200 focus:outline-none focus:ring-1 focus:ring-accent-400 ${className}`}
    />
  );
}

// ── Editable list section ───────────────────────────────────────

function EditableListSection({
  label,
  items,
  onUpdate,
  icon,
  iconClass,
  placeholder = 'New item...',
}: {
  label: string;
  items: string[];
  onUpdate: (items: string[]) => void;
  icon: string;
  iconClass: string;
  placeholder?: string;
}) {
  const [addingNew, setAddingNew] = useState(false);
  const [newValue, setNewValue] = useState('');
  const newInputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (addingNew) newInputRef.current?.focus();
  }, [addingNew]);

  if (!items || items.length === 0) return null;

  return (
    <div className="mt-3">
      <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
        {label}
        <span className="text-[10px] text-neutral-400 dark:text-neutral-500 normal-case tracking-normal font-normal">
          (click to edit)
        </span>
      </div>
      <div className="space-y-1">
        {items.map((item, i) => (
          <div
            key={i}
            className="group text-xs text-neutral-700 dark:text-neutral-300 flex items-start gap-1.5"
          >
            <span className={`${iconClass} mt-px shrink-0`}>{icon}</span>
            <EditableText
              value={item}
              onChange={(v) => {
                const next = [...items];
                next[i] = v;
                onUpdate(next);
              }}
              multiline
              className="flex-1"
            />
            <button
              onClick={() => onUpdate(items.filter((_, j) => j !== i))}
              className="opacity-0 group-hover:opacity-100 text-neutral-400 hover:text-error-500 transition-opacity shrink-0 mt-px"
              title="Remove"
              aria-label={`Remove ${item}`}
            >
              &times;
            </button>
          </div>
        ))}
      </div>

      {addingNew ? (
        <div className="mt-1.5 flex items-start gap-1.5">
          <span className={`${iconClass} mt-px shrink-0 opacity-50`}>{icon}</span>
          <textarea
            ref={newInputRef}
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            onBlur={() => {
              if (newValue.trim()) {
                onUpdate([...items, newValue.trim()]);
              }
              setNewValue('');
              setAddingNew(false);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (newValue.trim()) {
                  onUpdate([...items, newValue.trim()]);
                }
                setNewValue('');
                setAddingNew(false);
              }
              if (e.key === 'Escape') {
                setNewValue('');
                setAddingNew(false);
              }
            }}
            placeholder={placeholder}
            rows={1}
            className="flex-1 bg-white dark:bg-neutral-800 border border-accent-300 dark:border-accent-600 rounded px-1.5 py-0.5 text-xs text-neutral-800 dark:text-neutral-200 focus:outline-none focus:ring-1 focus:ring-accent-400 resize-none"
          />
        </div>
      ) : (
        <button
          onClick={() => setAddingNew(true)}
          className="mt-1 text-[10px] text-accent-500 hover:text-accent-600 dark:text-accent-400 dark:hover:text-accent-300 transition-colors"
        >
          + Add
        </button>
      )}
    </div>
  );
}

// ── Editable criteria section ───────────────────────────────────

function EditableCriteriaSection({
  criteria,
  onUpdate,
}: {
  criteria: Array<{ criterion: string; measurable?: string }>;
  onUpdate: (criteria: Array<{ criterion: string; measurable?: string }>) => void;
}) {
  const [addingNew, setAddingNew] = useState(false);
  const [newCriterion, setNewCriterion] = useState('');
  const [newMeasurable, setNewMeasurable] = useState('');
  const newCriterionRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (addingNew) newCriterionRef.current?.focus();
  }, [addingNew]);

  if (!criteria || criteria.length === 0) return null;

  return (
    <div className="mt-3">
      <div className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
        Decision criteria
        <span className="text-[10px] text-neutral-400 dark:text-neutral-500 normal-case tracking-normal font-normal">
          (click to edit)
        </span>
      </div>
      <div className="space-y-1">
        {criteria.map((c, i) => (
          <div
            key={i}
            className="group text-xs text-neutral-700 dark:text-neutral-300 flex items-start gap-1.5"
          >
            <span className="text-success-500 mt-px shrink-0">&#x2713;</span>
            <span className="flex-1">
              <EditableText
                value={c.criterion}
                onChange={(v) => {
                  const next = criteria.map((item, j) =>
                    j === i ? { ...item, criterion: v } : item
                  );
                  onUpdate(next);
                }}
              />
              {c.measurable && (
                <span className="text-neutral-400 dark:text-neutral-500 ml-1">
                  (<EditableText
                    value={c.measurable}
                    onChange={(v) => {
                      const next = criteria.map((item, j) =>
                        j === i ? { ...item, measurable: v } : item
                      );
                      onUpdate(next);
                    }}
                  />)
                </span>
              )}
            </span>
            <button
              onClick={() => onUpdate(criteria.filter((_, j) => j !== i))}
              className="opacity-0 group-hover:opacity-100 text-neutral-400 hover:text-error-500 transition-opacity shrink-0 mt-px"
              title="Remove"
              aria-label={`Remove ${c.criterion}`}
            >
              &times;
            </button>
          </div>
        ))}
      </div>

      {addingNew ? (
        <div className="mt-1.5 space-y-1">
          <div className="flex items-start gap-1.5">
            <span className="text-success-500 mt-px shrink-0 opacity-50">&#x2713;</span>
            <input
              ref={newCriterionRef}
              value={newCriterion}
              onChange={(e) => setNewCriterion(e.target.value)}
              placeholder="Criterion..."
              className="flex-1 bg-white dark:bg-neutral-800 border border-accent-300 dark:border-accent-600 rounded px-1.5 py-0.5 text-xs text-neutral-800 dark:text-neutral-200 focus:outline-none focus:ring-1 focus:ring-accent-400"
            />
          </div>
          <div className="flex items-center gap-1.5 ml-4">
            <input
              value={newMeasurable}
              onChange={(e) => setNewMeasurable(e.target.value)}
              placeholder="Measurable (optional)..."
              onKeyDown={(e) => {
                if (e.key === 'Enter' && newCriterion.trim()) {
                  onUpdate([
                    ...criteria,
                    {
                      criterion: newCriterion.trim(),
                      ...(newMeasurable.trim() ? { measurable: newMeasurable.trim() } : {}),
                    },
                  ]);
                  setNewCriterion('');
                  setNewMeasurable('');
                  setAddingNew(false);
                }
                if (e.key === 'Escape') {
                  setNewCriterion('');
                  setNewMeasurable('');
                  setAddingNew(false);
                }
              }}
              onBlur={() => {
                if (newCriterion.trim()) {
                  onUpdate([
                    ...criteria,
                    {
                      criterion: newCriterion.trim(),
                      ...(newMeasurable.trim() ? { measurable: newMeasurable.trim() } : {}),
                    },
                  ]);
                }
                setNewCriterion('');
                setNewMeasurable('');
                setAddingNew(false);
              }}
              className="flex-1 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded px-1.5 py-0.5 text-xs text-neutral-600 dark:text-neutral-400 focus:outline-none focus:ring-1 focus:ring-accent-400"
            />
          </div>
        </div>
      ) : (
        <button
          onClick={() => setAddingNew(true)}
          className="mt-1 text-[10px] text-accent-500 hover:text-accent-600 dark:text-accent-400 dark:hover:text-accent-300 transition-colors"
        >
          + Add criterion
        </button>
      )}
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────

export function CasePreviewCard({
  card,
  onCreateCase,
  onAdjust,
  onDismiss,
  isCreating = false,
}: CasePreviewCardProps) {
  const data = card.data as unknown as CasePreviewData;

  // Editable local state — initialized from AI analysis
  const [editedTitle, setEditedTitle] = useState(data.suggestedTitle);
  const [editedQuestions, setEditedQuestions] = useState<string[]>([...data.keyQuestions]);
  const [editedAssumptions, setEditedAssumptions] = useState<string[]>([...data.assumptions]);
  const [editedCriteria, setEditedCriteria] = useState(
    [...(data.decisionCriteria || [])].map(c => ({ ...c }))
  );

  const hasEdits = useMemo(() => {
    return (
      editedTitle !== data.suggestedTitle ||
      JSON.stringify(editedQuestions) !== JSON.stringify(data.keyQuestions) ||
      JSON.stringify(editedAssumptions) !== JSON.stringify(data.assumptions) ||
      JSON.stringify(editedCriteria) !== JSON.stringify(data.decisionCriteria)
    );
  }, [editedTitle, editedQuestions, editedAssumptions, editedCriteria, data]);

  const handleCreate = useCallback(() => {
    const userEdits: Record<string, unknown> = { title: editedTitle };
    if (hasEdits) {
      userEdits.key_questions = editedQuestions;
      userEdits.assumptions = editedAssumptions;
      userEdits.decision_criteria = editedCriteria;
    }
    onCreateCase(data.analysis, editedTitle, userEdits);
  }, [editedTitle, editedQuestions, editedAssumptions, editedCriteria, hasEdits, data.analysis, onCreateCase]);

  return (
    <div className="my-3">
      <ActionCard variant="accent">
        <ActionCardHeader>
          <div className="flex items-center gap-2">
            <ActionCardTitle>Case Preview</ActionCardTitle>
            {hasEdits && (
              <span className="text-[10px] bg-accent-100 dark:bg-accent-900/40 text-accent-600 dark:text-accent-400 px-1.5 py-0.5 rounded-full font-medium">
                Edited
              </span>
            )}
          </div>

          {/* Editable title */}
          <div className="mt-3 text-sm font-medium text-neutral-900 dark:text-neutral-100">
            <EditableText
              value={editedTitle}
              onChange={setEditedTitle}
              placeholder="Case title"
            />
          </div>

          {/* Editable key questions */}
          <EditableListSection
            label="Questions to investigate"
            items={editedQuestions}
            onUpdate={setEditedQuestions}
            icon="?"
            iconClass="text-accent-500"
            placeholder="New question..."
          />

          {/* Editable assumptions */}
          <EditableListSection
            label="Assumptions to test"
            items={editedAssumptions}
            onUpdate={setEditedAssumptions}
            icon="&middot;"
            iconClass="text-neutral-400"
            placeholder="New assumption..."
          />

          {/* Editable decision criteria */}
          <EditableCriteriaSection
            criteria={editedCriteria}
            onUpdate={setEditedCriteria}
          />
        </ActionCardHeader>

        {/* Transfer indicator */}
        <CompanionTransferIndicator analysis={data.analysis} />

        <ActionCardFooter>
          <Button
            size="sm"
            onClick={handleCreate}
            disabled={isCreating}
          >
            {isCreating ? (
              <span className="inline-flex items-center gap-2">
                <Spinner size="xs" />
                Creating...
              </span>
            ) : (
              'Create This Case'
            )}
          </Button>
          <Button variant="ghost" size="sm" onClick={onAdjust} disabled={isCreating}>
            Adjust
          </Button>
          <Button variant="ghost" size="sm" onClick={onDismiss} disabled={isCreating}>
            Dismiss
          </Button>
        </ActionCardFooter>
      </ActionCard>
    </div>
  );
}
