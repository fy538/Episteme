/**
 * Smart Action Bar - Context-aware action suggestions
 * 
 * Replaces static "Create Case" with dynamic suggestions based on
 * detected signals and conversation state.
 */

import { useMemo } from 'react';
import { Button } from '@/components/ui/Button';
import type { ChatThread } from '@/lib/types/chat';

interface Signal {
  id: string;
  type: 'assumption' | 'question' | 'evidence' | 'claim';
  text: string;
}

interface SmartActionBarProps {
  thread: ChatThread | null;
  signals: Signal[];
  onCreateCase: () => void;
  onCreateInquiriesFromAssumptions?: () => void;
  onOrganizeEvidence?: () => void;
}

interface SuggestedAction {
  id: string;
  priority: 'high' | 'medium' | 'low';
  icon: string;
  title: string;
  description: string;
  action: () => void;
  count?: number;
}

export function SmartActionBar({
  thread,
  signals,
  onCreateCase,
  onCreateInquiriesFromAssumptions,
  onOrganizeEvidence
}: SmartActionBarProps) {
  const suggestedActions = useMemo<SuggestedAction[]>(() => {
    const actions: SuggestedAction[] = [];
    
    // Count signals by type
    const assumptions = signals.filter(s => s.type === 'assumption');
    const questions = signals.filter(s => s.type === 'question');
    const evidence = signals.filter(s => s.type === 'evidence');
    
    // Only suggest for threads without a case
    const hasCase = thread?.primary_case;
    
    if (!hasCase) {
      // High priority: Validate assumptions (if 2+)
      if (assumptions.length >= 2 && onCreateInquiriesFromAssumptions) {
        actions.push({
          id: 'validate-assumptions',
          priority: 'high',
          icon: '⚠️',
          title: `Validate ${assumptions.length} Assumptions`,
          description: 'Create inquiries to test these assumptions',
          action: onCreateInquiriesFromAssumptions,
          count: assumptions.length
        });
      }
      
      // Medium priority: Organize evidence (if 3+)
      if (evidence.length >= 3 && onOrganizeEvidence) {
        actions.push({
          id: 'organize-evidence',
          priority: 'medium',
          icon: '📁',
          title: 'Organize Evidence',
          description: 'Track this research in a case',
          action: onOrganizeEvidence,
          count: evidence.length
        });
      }
      
      // Medium priority: Structure questions (if 3+)
      if (questions.length >= 3) {
        actions.push({
          id: 'structure-questions',
          priority: 'medium',
          icon: '🔍',
          title: `Structure ${questions.length} Questions`,
          description: 'Create a research case to investigate',
          action: onCreateCase,
          count: questions.length
        });
      }
    }
    
    // Sort by priority
    const priorityOrder = { high: 0, medium: 1, low: 2 };
    return actions.sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]);
  }, [thread, signals, onCreateCase, onCreateInquiriesFromAssumptions, onOrganizeEvidence]);

  const getPriorityStyles = (priority: 'high' | 'medium' | 'low') => {
    switch (priority) {
      case 'high':
        return 'border-warning-300 dark:border-warning-700 bg-warning-50 dark:bg-warning-900/20';
      case 'medium':
        return 'border-accent-300 dark:border-accent-700 bg-accent-50 dark:bg-accent-900/20';
      case 'low':
        return 'border-neutral-300 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900/20';
    }
  };

  return (
    <div className="space-y-3">
      {/* Dynamic suggested actions */}
      {suggestedActions.map(action => (
        <div
          key={action.id}
          className={`border rounded-lg p-4 ${getPriorityStyles(action.priority)} transition-all hover:shadow-md`}
        >
          <div className="flex items-start gap-3">
            <span className="text-2xl shrink-0">{action.icon}</span>
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-neutral-900 dark:text-neutral-100 text-sm flex items-center gap-2">
                {action.title}
                {action.count !== undefined && (
                  <span className="inline-flex items-center justify-center w-6 h-6 text-xs font-bold bg-white dark:bg-neutral-800 rounded-full">
                    {action.count}
                  </span>
                )}
              </h3>
              <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">
                {action.description}
              </p>
              <Button
                onClick={action.action}
                variant={action.priority === 'high' ? 'primary' : 'secondary'}
                className="mt-3 w-full"
                size="sm"
              >
                {action.priority === 'high' ? 'Recommended' : 'Create'}
              </Button>
            </div>
          </div>
        </div>
      ))}
      
      {/* Fallback: Manual creation always available */}
      <div className="pt-2">
        <Button
          onClick={onCreateCase}
          variant="ghost"
          className="w-full justify-center"
        >
          + Create Case Manually
        </Button>
      </div>
      
      {/* Help text when no suggestions */}
      {suggestedActions.length === 0 && !thread?.primary_case && (
        <div className="text-center py-4">
          <p className="text-sm text-neutral-500 dark:text-neutral-400">
            Keep chatting to detect decision patterns
          </p>
          <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
            I'll suggest when to create structure
          </p>
        </div>
      )}
    </div>
  );
}
