/**
 * WordDiff - Word-level diff visualization for document changes.
 *
 * Uses a simple LCS-based diff algorithm to produce red strikethrough
 * for removed words and green highlights for added words.
 * Context lines (unchanged) are shown in gray and can be collapsed.
 */

'use client';

import { useMemo, useState } from 'react';

interface WordDiffProps {
  oldText: string;
  newText: string;
  /** Maximum context words to show around changes (default: 30) */
  contextWords?: number;
}

type DiffOp = 'equal' | 'insert' | 'delete';

interface DiffChunk {
  op: DiffOp;
  text: string;
}

/**
 * Simple word-level diff using longest common subsequence.
 * Good enough for document diffs — for production, consider diff-match-patch.
 */
function computeWordDiff(oldText: string, newText: string): DiffChunk[] {
  const oldWords = oldText.split(/(\s+)/);
  const newWords = newText.split(/(\s+)/);

  // LCS table
  const m = oldWords.length;
  const n = newWords.length;

  // For very large texts, fall back to a simpler approach
  if (m * n > 500000) {
    return simpleDiff(oldText, newText);
  }

  const dp: number[][] = Array.from({ length: m + 1 }, () =>
    Array(n + 1).fill(0)
  );

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (oldWords[i - 1] === newWords[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  // Backtrack to build diff
  const chunks: DiffChunk[] = [];
  let i = m;
  let j = n;

  const result: DiffChunk[] = [];

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && oldWords[i - 1] === newWords[j - 1]) {
      result.push({ op: 'equal', text: oldWords[i - 1] });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      result.push({ op: 'insert', text: newWords[j - 1] });
      j--;
    } else {
      result.push({ op: 'delete', text: oldWords[i - 1] });
      i--;
    }
  }

  result.reverse();

  // Merge consecutive same-op chunks
  const merged: DiffChunk[] = [];
  for (const chunk of result) {
    if (merged.length > 0 && merged[merged.length - 1].op === chunk.op) {
      merged[merged.length - 1].text += chunk.text;
    } else {
      merged.push({ ...chunk });
    }
  }

  return merged;
}

/**
 * Simple fallback for very large texts: just show old as delete, new as insert.
 */
function simpleDiff(oldText: string, newText: string): DiffChunk[] {
  const chunks: DiffChunk[] = [];
  if (oldText) chunks.push({ op: 'delete', text: oldText });
  if (newText) chunks.push({ op: 'insert', text: newText });
  return chunks;
}

export function WordDiff({ oldText, newText, contextWords = 30 }: WordDiffProps) {
  const [expanded, setExpanded] = useState(false);

  const chunks = useMemo(
    () => computeWordDiff(oldText, newText),
    [oldText, newText]
  );

  const hasChanges = chunks.some((c) => c.op !== 'equal');

  if (!hasChanges) {
    return (
      <div className="text-sm text-neutral-500 italic p-3 bg-neutral-50 rounded">
        No changes detected.
      </div>
    );
  }

  // Stats
  const deletedWords = chunks
    .filter((c) => c.op === 'delete')
    .reduce((acc, c) => acc + c.text.split(/\s+/).filter(Boolean).length, 0);
  const insertedWords = chunks
    .filter((c) => c.op === 'insert')
    .reduce((acc, c) => acc + c.text.split(/\s+/).filter(Boolean).length, 0);

  return (
    <div className="space-y-2">
      {/* Stats bar */}
      <div className="flex items-center gap-3 text-xs text-neutral-500">
        {deletedWords > 0 && (
          <span className="text-red-600">-{deletedWords} words</span>
        )}
        {insertedWords > 0 && (
          <span className="text-green-600">+{insertedWords} words</span>
        )}
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-accent-600 hover:underline ml-auto"
        >
          {expanded ? 'Collapse context' : 'Expand all'}
        </button>
      </div>

      {/* Diff content */}
      <div className="text-sm leading-relaxed p-3 bg-neutral-50 rounded-lg border border-neutral-200 max-h-80 overflow-auto whitespace-pre-wrap font-mono">
        {chunks.map((chunk, idx) => {
          if (chunk.op === 'equal') {
            // Show context words only if not expanded
            if (!expanded && chunk.text.split(/\s+/).length > contextWords * 2) {
              const words = chunk.text.split(/(\s+)/);
              const contextStart = words.slice(0, contextWords * 2).join('');
              const contextEnd = words.slice(-contextWords * 2).join('');
              return (
                <span key={idx}>
                  <span className="text-neutral-600">{contextStart}</span>
                  <span className="text-neutral-400 bg-neutral-100 px-1 rounded mx-1">
                    ···
                  </span>
                  <span className="text-neutral-600">{contextEnd}</span>
                </span>
              );
            }
            return (
              <span key={idx} className="text-neutral-600">
                {chunk.text}
              </span>
            );
          }

          if (chunk.op === 'delete') {
            return (
              <span
                key={idx}
                className="bg-red-100 text-red-700 line-through decoration-red-400"
              >
                {chunk.text}
              </span>
            );
          }

          if (chunk.op === 'insert') {
            return (
              <span key={idx} className="bg-green-100 text-green-800">
                {chunk.text}
              </span>
            );
          }

          return null;
        })}
      </div>
    </div>
  );
}

/**
 * Per-change diff view for individual agentic task changes.
 */
export function ChangeDiff({
  change,
  onAccept,
  onReject,
}: {
  change: { step_id: string; type: string; description: string; before: string; after: string };
  onAccept?: (change: any) => void;
  onReject?: (change: any) => void;
}) {
  return (
    <div className="border border-neutral-200 rounded-lg overflow-hidden">
      <div className="px-3 py-2 bg-neutral-50 border-b flex items-center justify-between">
        <div>
          <span className="text-xs font-medium text-neutral-700">{change.description}</span>
          <span className="text-xs text-neutral-400 ml-2">({change.type})</span>
        </div>
        {(onAccept || onReject) && (
          <div className="flex items-center gap-1.5">
            {onReject && (
              <button
                onClick={() => onReject(change)}
                className="text-xs px-2 py-0.5 rounded border border-neutral-300 text-neutral-600 hover:bg-red-50 hover:border-red-300 hover:text-red-600"
              >
                Skip
              </button>
            )}
            {onAccept && (
              <button
                onClick={() => onAccept(change)}
                className="text-xs px-2 py-0.5 rounded border border-green-300 text-green-700 bg-green-50 hover:bg-green-100"
              >
                Accept
              </button>
            )}
          </div>
        )}
      </div>
      <div className="p-3">
        <WordDiff oldText={change.before} newText={change.after} />
      </div>
    </div>
  );
}
