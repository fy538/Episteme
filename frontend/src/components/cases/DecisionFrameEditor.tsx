/**
 * DecisionFrameEditor - Edit decision question, constraints, success criteria, stakeholders
 *
 * Provides a focused interface for defining the decision frame of a case.
 */

'use client';

import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  PlusIcon,
  XMarkIcon,
  SparklesIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from '@heroicons/react/24/outline';
import type { Case, Constraint, SuccessCriterion, Stakeholder } from '@/lib/types/case';

interface DecisionFrameEditorProps {
  caseData: Case;
  onSave: (updates: {
    decision_question?: string;
    constraints?: Constraint[];
    success_criteria?: SuccessCriterion[];
    stakeholders?: Stakeholder[];
  }) => Promise<void>;
  onSuggest?: () => Promise<{
    constraints?: Constraint[];
    success_criteria?: SuccessCriterion[];
    stakeholders?: Stakeholder[];
  }>;
  isLoading?: boolean;
  compact?: boolean;
}

export function DecisionFrameEditor({
  caseData,
  onSave,
  onSuggest,
  isLoading = false,
  compact = false,
}: DecisionFrameEditorProps) {
  const [decisionQuestion, setDecisionQuestion] = useState(caseData.decision_question || '');
  const [constraints, setConstraints] = useState<Constraint[]>(caseData.constraints || []);
  const [successCriteria, setSuccessCriteria] = useState<SuccessCriterion[]>(
    caseData.success_criteria || []
  );
  const [stakeholders, setStakeholders] = useState<Stakeholder[]>(caseData.stakeholders || []);

  const [expandedSection, setExpandedSection] = useState<string | null>(
    compact ? null : 'question'
  );
  const [saving, setSaving] = useState(false);
  const [suggesting, setSuggesting] = useState(false);

  // Track if there are unsaved changes
  const hasChanges =
    decisionQuestion !== (caseData.decision_question || '') ||
    JSON.stringify(constraints) !== JSON.stringify(caseData.constraints || []) ||
    JSON.stringify(successCriteria) !== JSON.stringify(caseData.success_criteria || []) ||
    JSON.stringify(stakeholders) !== JSON.stringify(caseData.stakeholders || []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      await onSave({
        decision_question: decisionQuestion,
        constraints,
        success_criteria: successCriteria,
        stakeholders,
      });
    } finally {
      setSaving(false);
    }
  }, [decisionQuestion, constraints, successCriteria, stakeholders, onSave]);

  const handleSuggest = useCallback(async () => {
    if (!onSuggest) return;
    setSuggesting(true);
    try {
      const suggestions = await onSuggest();
      if (suggestions.constraints?.length) {
        setConstraints((prev) => [...prev, ...suggestions.constraints!]);
      }
      if (suggestions.success_criteria?.length) {
        setSuccessCriteria((prev) => [...prev, ...suggestions.success_criteria!]);
      }
      if (suggestions.stakeholders?.length) {
        setStakeholders((prev) => [...prev, ...suggestions.stakeholders!]);
      }
    } finally {
      setSuggesting(false);
    }
  }, [onSuggest]);

  // Constraint handlers
  const addConstraint = () => {
    setConstraints([...constraints, { type: '', description: '' }]);
  };

  const updateConstraint = (index: number, field: keyof Constraint, value: string) => {
    const updated = [...constraints];
    updated[index] = { ...updated[index], [field]: value };
    setConstraints(updated);
  };

  const removeConstraint = (index: number) => {
    setConstraints(constraints.filter((_, i) => i !== index));
  };

  // Success criteria handlers
  const addCriterion = () => {
    setSuccessCriteria([...successCriteria, { criterion: '', measurable: '' }]);
  };

  const updateCriterion = (index: number, field: keyof SuccessCriterion, value: string) => {
    const updated = [...successCriteria];
    updated[index] = { ...updated[index], [field]: value };
    setSuccessCriteria(updated);
  };

  const removeCriterion = (index: number) => {
    setSuccessCriteria(successCriteria.filter((_, i) => i !== index));
  };

  // Stakeholder handlers
  const addStakeholder = () => {
    setStakeholders([...stakeholders, { name: '', interest: '', influence: 'medium' }]);
  };

  const updateStakeholder = (index: number, field: keyof Stakeholder, value: string) => {
    const updated = [...stakeholders];
    updated[index] = { ...updated[index], [field]: value } as Stakeholder;
    setStakeholders(updated);
  };

  const removeStakeholder = (index: number) => {
    setStakeholders(stakeholders.filter((_, i) => i !== index));
  };

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  const SectionHeader = ({
    title,
    section,
    count,
  }: {
    title: string;
    section: string;
    count?: number;
  }) => (
    <button
      onClick={() => toggleSection(section)}
      className="flex items-center justify-between w-full py-2 text-left text-sm font-medium text-neutral-700 hover:text-neutral-900"
    >
      <span className="flex items-center gap-2">
        {title}
        {count !== undefined && count > 0 && (
          <Badge variant="neutral" className="text-xs">
            {count}
          </Badge>
        )}
      </span>
      {expandedSection === section ? (
        <ChevronUpIcon className="w-4 h-4" />
      ) : (
        <ChevronDownIcon className="w-4 h-4" />
      )}
    </button>
  );

  return (
    <div className="space-y-4">
      {/* Decision Question - Always visible */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-neutral-700">Decision Question</label>
        <Textarea
          value={decisionQuestion}
          onChange={(e) => setDecisionQuestion(e.target.value)}
          placeholder="What core question are you trying to answer? (e.g., 'Should we acquire CompanyX?' or 'Which database should we use?')"
          className="min-h-[60px] text-base"
          disabled={isLoading}
        />
        <p className="text-xs text-neutral-500">
          Frame this as a clear, answerable question that captures the essence of your decision.
        </p>
      </div>

      {/* Constraints Section */}
      <div className="border-t pt-3">
        <SectionHeader title="Constraints" section="constraints" count={constraints.length} />
        {expandedSection === 'constraints' && (
          <div className="mt-2 space-y-2">
            {constraints.map((constraint, index) => (
              <div key={index} className="flex gap-2 items-start">
                <Input
                  value={constraint.type}
                  onChange={(e) => updateConstraint(index, 'type', e.target.value)}
                  placeholder="Type (e.g., budget, timeline)"
                  className="w-32 text-sm"
                  disabled={isLoading}
                />
                <Input
                  value={constraint.description}
                  onChange={(e) => updateConstraint(index, 'description', e.target.value)}
                  placeholder="Description (e.g., Must stay under $50k)"
                  className="flex-1 text-sm"
                  disabled={isLoading}
                />
                <button
                  onClick={() => removeConstraint(index)}
                  className="p-2 text-neutral-400 hover:text-error-500"
                  disabled={isLoading}
                >
                  <XMarkIcon className="w-4 h-4" />
                </button>
              </div>
            ))}
            <Button
              variant="ghost"
              size="sm"
              onClick={addConstraint}
              disabled={isLoading}
              className="text-neutral-600"
            >
              <PlusIcon className="w-4 h-4 mr-1" />
              Add Constraint
            </Button>
          </div>
        )}
      </div>

      {/* Success Criteria Section */}
      <div className="border-t pt-3">
        <SectionHeader
          title="Success Criteria"
          section="criteria"
          count={successCriteria.length}
        />
        {expandedSection === 'criteria' && (
          <div className="mt-2 space-y-2">
            {successCriteria.map((criterion, index) => (
              <div key={index} className="flex gap-2 items-start">
                <Input
                  value={criterion.criterion}
                  onChange={(e) => updateCriterion(index, 'criterion', e.target.value)}
                  placeholder="What success looks like"
                  className="flex-1 text-sm"
                  disabled={isLoading}
                />
                <Input
                  value={criterion.measurable || ''}
                  onChange={(e) => updateCriterion(index, 'measurable', e.target.value)}
                  placeholder="How to measure it"
                  className="flex-1 text-sm"
                  disabled={isLoading}
                />
                <button
                  onClick={() => removeCriterion(index)}
                  className="p-2 text-neutral-400 hover:text-error-500"
                  disabled={isLoading}
                >
                  <XMarkIcon className="w-4 h-4" />
                </button>
              </div>
            ))}
            <Button
              variant="ghost"
              size="sm"
              onClick={addCriterion}
              disabled={isLoading}
              className="text-neutral-600"
            >
              <PlusIcon className="w-4 h-4 mr-1" />
              Add Criterion
            </Button>
          </div>
        )}
      </div>

      {/* Stakeholders Section */}
      <div className="border-t pt-3">
        <SectionHeader title="Stakeholders" section="stakeholders" count={stakeholders.length} />
        {expandedSection === 'stakeholders' && (
          <div className="mt-2 space-y-2">
            {stakeholders.map((stakeholder, index) => (
              <div key={index} className="flex gap-2 items-start">
                <Input
                  value={stakeholder.name}
                  onChange={(e) => updateStakeholder(index, 'name', e.target.value)}
                  placeholder="Name/Role"
                  className="w-32 text-sm"
                  disabled={isLoading}
                />
                <Input
                  value={stakeholder.interest}
                  onChange={(e) => updateStakeholder(index, 'interest', e.target.value)}
                  placeholder="Their interest/concern"
                  className="flex-1 text-sm"
                  disabled={isLoading}
                />
                <select
                  value={stakeholder.influence}
                  onChange={(e) =>
                    updateStakeholder(index, 'influence', e.target.value as Stakeholder['influence'])
                  }
                  className="w-24 h-10 px-2 text-sm border rounded-md border-primary-300"
                  disabled={isLoading}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
                <button
                  onClick={() => removeStakeholder(index)}
                  className="p-2 text-neutral-400 hover:text-error-500"
                  disabled={isLoading}
                >
                  <XMarkIcon className="w-4 h-4" />
                </button>
              </div>
            ))}
            <Button
              variant="ghost"
              size="sm"
              onClick={addStakeholder}
              disabled={isLoading}
              className="text-neutral-600"
            >
              <PlusIcon className="w-4 h-4 mr-1" />
              Add Stakeholder
            </Button>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between pt-4 border-t">
        <div className="flex gap-2">
          {onSuggest && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSuggest}
              disabled={isLoading || suggesting}
            >
              <SparklesIcon className="w-4 h-4 mr-1" />
              {suggesting ? 'Suggesting...' : 'AI Suggest'}
            </Button>
          )}
        </div>
        <div className="flex gap-2">
          {hasChanges && (
            <span className="text-xs text-neutral-500 self-center mr-2">Unsaved changes</span>
          )}
          <Button onClick={handleSave} disabled={isLoading || saving || !hasChanges} size="sm">
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>
    </div>
  );
}

/**
 * Compact version of the decision frame display (read-only)
 */
export function DecisionFrameSummary({ caseData }: { caseData: Case }) {
  if (!caseData.decision_question && !caseData.constraints?.length) {
    return null;
  }

  return (
    <div className="bg-accent-50 border border-accent-200 rounded-lg p-4 space-y-3">
      {caseData.decision_question && (
        <div>
          <p className="text-xs font-medium text-accent-700 uppercase tracking-wide mb-1">
            Decision Question
          </p>
          <p className="text-sm text-neutral-800">{caseData.decision_question}</p>
        </div>
      )}

      {caseData.constraints && caseData.constraints.length > 0 && (
        <div>
          <p className="text-xs font-medium text-accent-700 uppercase tracking-wide mb-1">
            Constraints
          </p>
          <div className="flex flex-wrap gap-2">
            {caseData.constraints.map((c, i) => (
              <Badge key={i} variant="outline" className="text-xs">
                {c.type}: {c.description}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {caseData.success_criteria && caseData.success_criteria.length > 0 && (
        <div>
          <p className="text-xs font-medium text-accent-700 uppercase tracking-wide mb-1">
            Success Criteria
          </p>
          <ul className="text-sm text-neutral-700 space-y-1">
            {caseData.success_criteria.map((sc, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-success-500 mt-0.5">&#10003;</span>
                <span>
                  {sc.criterion}
                  {sc.measurable && (
                    <span className="text-neutral-500"> ({sc.measurable})</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
