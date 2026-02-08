/**
 * PasteEvidenceForm
 *
 * Form for pasting evidence from external sources (Perplexity, ChatGPT, etc.).
 * Supports optional source metadata and auto-split by paragraph.
 */

'use client';

import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';

interface PasteEvidenceFormProps {
  onSubmit: (data: {
    items: Array<{
      text: string;
      source_url?: string;
      source_title?: string;
    }>;
    source_label?: string;
  }) => Promise<void>;
  isSubmitting: boolean;
}

export function PasteEvidenceForm({ onSubmit, isSubmitting }: PasteEvidenceFormProps) {
  const [text, setText] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [sourceTitle, setSourceTitle] = useState('');
  const [splitMode, setSplitMode] = useState(false);

  const items = useMemo(() => {
    if (!text.trim()) return [];

    if (splitMode) {
      // Split by double newline (paragraphs) or bullet points
      return text
        .split(/\n{2,}|(?=^[\-\*\u2022]\s)/m)
        .map(t => t.replace(/^[\-\*\u2022]\s*/, '').trim())
        .filter(t => t.length >= 10);
    }

    return [text.trim()];
  }, [text, splitMode]);

  const handleSubmit = async () => {
    if (items.length === 0) return;

    await onSubmit({
      items: items.map(t => ({
        text: t,
        source_url: sourceUrl || undefined,
        source_title: sourceTitle || undefined,
      })),
      source_label: sourceTitle || 'Pasted Evidence',
    });

    // Clear form on success
    setText('');
    setSourceUrl('');
    setSourceTitle('');
  };

  return (
    <div className="space-y-4">
      {/* Main text area */}
      <div className="space-y-1">
        <Label htmlFor="evidence-text">Evidence Text</Label>
        <Textarea
          id="evidence-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste findings from Perplexity, ChatGPT, research notes..."
          rows={8}
          className="font-mono text-sm"
        />
      </div>

      {/* Source metadata (collapsible) */}
      <div className="space-y-3 bg-neutral-50 dark:bg-neutral-900/50 rounded-lg p-3">
        <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
          Source (optional)
        </p>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <Label htmlFor="source-title">Title</Label>
            <Input
              id="source-title"
              value={sourceTitle}
              onChange={(e) => setSourceTitle(e.target.value)}
              placeholder="e.g. Market Research Report"
              className="text-sm"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="source-url">URL</Label>
            <Input
              id="source-url"
              type="url"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              placeholder="https://..."
              className="text-sm"
            />
          </div>
        </div>
      </div>

      {/* Split toggle + preview */}
      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400 cursor-pointer">
          <input
            type="checkbox"
            checked={splitMode}
            onChange={(e) => setSplitMode(e.target.checked)}
            className="rounded border-neutral-300 text-accent-600 focus:ring-accent-500"
          />
          Split into multiple items by paragraph
        </label>

        {items.length > 0 && (
          <span className="text-xs text-neutral-500 dark:text-neutral-400">
            {items.length} evidence item{items.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Preview when split */}
      {splitMode && items.length > 1 && (
        <div className="max-h-32 overflow-y-auto space-y-1.5 border border-neutral-200 dark:border-neutral-700 rounded-lg p-2">
          {items.map((item, i) => (
            <div
              key={i}
              className="text-xs text-neutral-600 dark:text-neutral-400 bg-white dark:bg-neutral-800 rounded px-2 py-1.5 border border-neutral-100 dark:border-neutral-700"
            >
              <span className="font-medium text-neutral-400 mr-1">#{i + 1}</span>
              {item.length > 120 ? `${item.slice(0, 120)}...` : item}
            </div>
          ))}
        </div>
      )}

      {/* Submit */}
      <Button
        onClick={handleSubmit}
        disabled={isSubmitting || items.length === 0}
        className="w-full"
      >
        {isSubmitting
          ? 'Ingesting...'
          : `Ingest ${items.length} Evidence Item${items.length !== 1 ? 's' : ''}`}
      </Button>
    </div>
  );
}
