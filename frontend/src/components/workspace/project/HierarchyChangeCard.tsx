/**
 * HierarchyChangeCard — shows what changed since the last hierarchy build.
 *
 * Displays new documents, new/expanded/merged themes, and change stats
 * in a dismissible card at the top of the landscape view (Plan 6).
 */

'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import type { HierarchyDiff } from '@/lib/types/hierarchy';

// ── Props ────────────────────────────────────────────────────────

interface HierarchyChangeCardProps {
  diff: HierarchyDiff;
  summary: string;
  version: number;
  projectId: string;
  onDismiss: () => void;
}

// ── Persistence ──────────────────────────────────────────────────

function getDismissKey(projectId: string, version: number) {
  return `hierarchy_change_dismissed:${projectId}:v${version}`;
}

function isDismissed(projectId: string, version: number): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem(getDismissKey(projectId, version)) === '1';
}

function markDismissed(projectId: string, version: number) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(getDismissKey(projectId, version), '1');

  // Clean up dismiss keys from older versions to prevent localStorage bloat.
  const prefix = `hierarchy_change_dismissed:${projectId}:v`;
  const keysToRemove: string[] = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key?.startsWith(prefix)) {
      const v = parseInt(key.slice(prefix.length), 10);
      if (!isNaN(v) && v < version) {
        keysToRemove.push(key);
      }
    }
  }
  keysToRemove.forEach(k => localStorage.removeItem(k));
}

// ── Component ────────────────────────────────────────────────────

export function HierarchyChangeCard({
  diff,
  summary,
  version,
  projectId,
  onDismiss,
}: HierarchyChangeCardProps) {
  const [dismissed, setDismissed] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (isDismissed(projectId, version)) {
      setDismissed(true);
    }
  }, [projectId, version]);

  if (dismissed) return null;

  const totalChanges =
    (diff.new_documents?.length ?? 0) +
    (diff.new_themes?.length ?? 0) +
    (diff.expanded_themes?.length ?? 0) +
    (diff.merged_themes?.length ?? 0);

  if (totalChanges === 0) return null;

  const handleDismiss = () => {
    markDismissed(projectId, version);
    setDismissed(true);
    onDismiss();
  };

  return (
    <AnimatePresence>
      {!dismissed && (
        <motion.div
          initial={{ opacity: 0, y: -12, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -8, scale: 0.98 }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
          className={cn(
            'rounded-lg border p-4',
            'border-accent-200/80 dark:border-accent-800/60',
            'bg-accent-50/50 dark:bg-accent-950/20',
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-2">
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-2 text-sm font-medium text-primary-900 dark:text-primary-100 hover:text-accent-700 dark:hover:text-accent-300 transition-colors"
            >
              <span className="text-base">&#x1f504;</span>
              <span>Knowledge base updated (v{version})</span>
              <span className="text-xs text-neutral-400">
                {expanded ? '\u25B2' : '\u25BC'}
              </span>
            </button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDismiss}
              className="text-xs h-6 w-6 p-0 text-neutral-400 hover:text-neutral-600"
              aria-label="Dismiss change notification"
            >
              &#x2715;
            </Button>
          </div>

          {/* Change summary lines */}
          <div className="space-y-1">
            {diff.new_documents?.length > 0 && (
              <ChangeLine
                icon={'\ud83d\udcc4'}
                text={`${diff.new_documents.length} new document${diff.new_documents.length > 1 ? 's' : ''}: ${diff.new_documents.map(d => d.document_title).slice(0, 3).join(', ')}${diff.new_documents.length > 3 ? '...' : ''}`}
              />
            )}
            {diff.new_themes?.length > 0 && (
              <ChangeLine
                icon={'\ud83c\udf3f'}
                text={`${diff.new_themes.length} new theme${diff.new_themes.length > 1 ? 's' : ''}: ${diff.new_themes.map(t => t.label).slice(0, 3).join(', ')}${diff.new_themes.length > 3 ? '...' : ''}`}
              />
            )}
            {diff.expanded_themes?.length > 0 && (
              <ChangeLine
                icon={'\ud83d\udcc8'}
                text={`${diff.expanded_themes.length} theme${diff.expanded_themes.length > 1 ? 's' : ''} expanded: ${diff.expanded_themes.map(t => t.label).slice(0, 3).join(', ')}${diff.expanded_themes.length > 3 ? '...' : ''}`}
              />
            )}
            {diff.merged_themes?.length > 0 && (
              <ChangeLine
                icon={'\ud83d\udd17'}
                text={`${diff.merged_themes.length} theme${diff.merged_themes.length > 1 ? 's' : ''} merged: ${diff.merged_themes.map(t => `"${t.old_label}" \u2192 "${t.merged_into}"`).slice(0, 2).join(', ')}${diff.merged_themes.length > 2 ? '...' : ''}`}
              />
            )}
            {diff.removed_themes?.length > 0 && (
              <ChangeLine
                icon={'\ud83d\uddd1'}
                text={`${diff.removed_themes.length} theme${diff.removed_themes.length > 1 ? 's' : ''} removed`}
              />
            )}
          </div>

          {/* Expanded details */}
          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="mt-3 pt-3 border-t border-accent-200/60 dark:border-accent-800/40 space-y-2">
                  {/* Chunk stats */}
                  <div className="flex items-center gap-4 text-xs text-neutral-500 dark:text-neutral-400">
                    {diff.chunks_added > 0 && (
                      <span className="text-emerald-600 dark:text-emerald-400">
                        +{diff.chunks_added} passages
                      </span>
                    )}
                    {diff.chunks_removed > 0 && (
                      <span className="text-red-500 dark:text-red-400">
                        -{diff.chunks_removed} passages
                      </span>
                    )}
                    <span>
                      {diff.themes_before} &rarr; {diff.themes_after} themes
                    </span>
                  </div>

                  {/* Detailed new themes */}
                  {diff.new_themes?.length > 0 && (
                    <div className="space-y-1">
                      <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                        New themes
                      </span>
                      {diff.new_themes.map((theme, i) => (
                        <div
                          key={i}
                          className="text-xs text-neutral-600 dark:text-neutral-400 pl-3 border-l-2 border-emerald-300 dark:border-emerald-700"
                        >
                          <span className="font-medium">{theme.label}</span>
                          {theme.summary && (
                            <span className="text-neutral-400 dark:text-neutral-500">
                              {' '}&mdash; {theme.summary.slice(0, 100)}{theme.summary.length > 100 ? '...' : ''}
                            </span>
                          )}
                          <span className="text-neutral-400 ml-1">
                            ({theme.chunk_count} passages)
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Detailed expanded themes */}
                  {diff.expanded_themes?.length > 0 && (
                    <div className="space-y-1">
                      <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
                        Expanded themes
                      </span>
                      {diff.expanded_themes.map((theme, i) => (
                        <div
                          key={i}
                          className="text-xs text-neutral-600 dark:text-neutral-400 pl-3 border-l-2 border-blue-300 dark:border-blue-700"
                        >
                          <span className="font-medium">{theme.label}</span>
                          <span className="text-blue-600 dark:text-blue-400 ml-1">
                            +{theme.growth} passages ({theme.old_chunk_count} &rarr; {theme.new_chunk_count})
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ── Helpers ──────────────────────────────────────────────────────

function ChangeLine({ icon, text }: { icon: string; text: string }) {
  return (
    <div className="flex items-start gap-2 text-xs text-neutral-600 dark:text-neutral-400">
      <span className="shrink-0 mt-0.5">{icon}</span>
      <span>{text}</span>
    </div>
  );
}
