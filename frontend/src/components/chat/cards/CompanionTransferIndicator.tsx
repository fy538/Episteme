/**
 * CompanionTransferIndicator - Shows what data transfers from conversation to case
 *
 * Displayed below the CasePreviewCard content to give users confidence
 * about what context will carry over when they create a case.
 */

'use client';

interface CompanionTransferIndicatorProps {
  analysis: Record<string, unknown>;
}

export function CompanionTransferIndicator({ analysis }: CompanionTransferIndicatorProps) {
  const companionState = analysis?.companion_state as
    | { structure_type?: string; research_count?: number }
    | undefined;
  const hasStructure = !!companionState?.structure_type;
  const researchCount = companionState?.research_count ?? 0;

  const items = [
    { label: 'Conversation context', present: true },
    { label: `Research results (${researchCount})`, present: researchCount > 0 },
    { label: `Companion structure (${companionState?.structure_type || ''})`, present: hasStructure },
  ].filter(item => item.present);

  // Don't show if only basic context transfers
  if (items.length <= 1) return null;

  return (
    <div className="mx-4 mb-2 px-3 py-2 rounded-md bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200/50 dark:border-neutral-800/50">
      <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-1.5 font-medium">
        Transfers to case:
      </p>
      <div className="space-y-0.5">
        {items.map((item, i) => (
          <div key={i} className="text-xs text-neutral-600 dark:text-neutral-300 flex items-center gap-1.5">
            <span className="text-success-500">&#x2713;</span>
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
