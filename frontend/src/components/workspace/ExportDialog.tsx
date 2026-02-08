/**
 * ExportDialog — Modal with two export options: Markdown and Structured JSON.
 *
 * Markdown: Uses existing client-side `exportBriefMarkdown()` -> downloads .md
 * Structured JSON: Calls `casesAPI.exportJSON()` -> downloads .json
 */

'use client';

import { useState, useCallback, useEffect } from 'react';
import { Dialog } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { casesAPI } from '@/lib/api/cases';
import { cn } from '@/lib/utils';

interface ExportDialogProps {
  caseId: string;
  caseTitle: string;
  isOpen: boolean;
  onClose: () => void;
}

type ExportFormat = 'markdown' | 'json';

export function ExportDialog({ caseId, caseTitle, isOpen, onClose }: ExportDialogProps) {
  const [exporting, setExporting] = useState<ExportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Reset error & exporting state when dialog opens
  useEffect(() => {
    if (isOpen) {
      setError(null);
      setExporting(null);
    }
  }, [isOpen]);

  const sanitizeFilename = (title: string) =>
    title.replace(/[^a-zA-Z0-9_\- ]/g, '').replace(/\s+/g, '_').slice(0, 60) || 'brief';

  const downloadBlob = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    // Delay revoke so the browser has time to start the download
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const handleExportMarkdown = useCallback(async () => {
    setExporting('markdown');
    setError(null);
    try {
      const markdown = await casesAPI.exportBriefMarkdown(caseId);
      downloadBlob(markdown, `${sanitizeFilename(caseTitle)}.md`, 'text/markdown');
      onClose();
    } catch (err: any) {
      setError(err.message || 'Export failed');
    } finally {
      setExporting(null);
    }
  }, [caseId, caseTitle, onClose]);

  const handleExportJSON = useCallback(async () => {
    setExporting('json');
    setError(null);
    try {
      const data = await casesAPI.exportJSON(caseId);
      const json = JSON.stringify(data, null, 2);
      downloadBlob(json, `${sanitizeFilename(caseTitle)}_IR.json`, 'application/json');
      onClose();
    } catch (err: any) {
      setError(err.message || 'Export failed');
    } finally {
      setExporting(null);
    }
  }, [caseId, caseTitle, onClose]);

  return (
    <Dialog isOpen={isOpen} onClose={onClose} title="Export Brief" size="md">
      <div className="flex flex-col gap-4 py-2">
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          Choose an export format for your brief.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" role="group" aria-label="Export formats">
          {/* Markdown */}
          <button
            onClick={handleExportMarkdown}
            disabled={!!exporting}
            aria-label="Export as Markdown"
            className={cn(
              'flex flex-col items-start gap-2 p-4 rounded-xl border text-left transition-all',
              'border-neutral-200 dark:border-neutral-800',
              'hover:border-accent-300 dark:hover:border-accent-700',
              'hover:bg-accent-50/30 dark:hover:bg-accent-900/10',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-400',
              'disabled:opacity-50 disabled:pointer-events-none',
            )}
          >
            <div className="flex items-center gap-2">
              <MarkdownIcon className="w-5 h-5 text-neutral-600 dark:text-neutral-400" />
              <span className="text-sm font-medium text-neutral-800 dark:text-neutral-200">
                Markdown
              </span>
            </div>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 leading-relaxed">
              Human-readable document with sections, assumptions, and criteria. Great for sharing.
            </p>
            {exporting === 'markdown' && (
              <span className="text-[10px] text-accent-500 dark:text-accent-400" role="status">Exporting...</span>
            )}
          </button>

          {/* Structured JSON */}
          <button
            onClick={handleExportJSON}
            disabled={!!exporting}
            aria-label="Export as Structured JSON"
            className={cn(
              'flex flex-col items-start gap-2 p-4 rounded-xl border text-left transition-all',
              'border-neutral-200 dark:border-neutral-800',
              'hover:border-accent-300 dark:hover:border-accent-700',
              'hover:bg-accent-50/30 dark:hover:bg-accent-900/10',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-400',
              'disabled:opacity-50 disabled:pointer-events-none',
            )}
          >
            <div className="flex items-center gap-2">
              <JSONIcon className="w-5 h-5 text-neutral-600 dark:text-neutral-400" />
              <span className="text-sm font-medium text-neutral-800 dark:text-neutral-200">
                Structured JSON
              </span>
            </div>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 leading-relaxed">
              Full reasoning graph (claims, evidence, grounding scores). For slides, memos, or integrations.
            </p>
            {exporting === 'json' && (
              <span className="text-[10px] text-accent-500 dark:text-accent-400" role="status">Exporting...</span>
            )}
          </button>
        </div>

        {error && (
          <p className="text-xs text-red-500 text-center" role="alert">{error}</p>
        )}

        <div className="flex justify-end">
          <Button variant="ghost" size="sm" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

// -- Icons --

function MarkdownIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M7 15V9l2.5 3L12 9v6M17 15v-6l-2 3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function JSONIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <path d="M8 3H6a2 2 0 00-2 2v2m0 6v2a2 2 0 002 2h2m8-14h2a2 2 0 012 2v2m0 6v2a2 2 0 01-2 2h-2" strokeLinecap="round" />
      <path d="M9 12h1.5m3 0H15M9 9h6M9 15h6" strokeLinecap="round" />
    </svg>
  );
}

export default ExportDialog;
