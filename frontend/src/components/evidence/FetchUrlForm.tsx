/**
 * FetchUrlForm
 *
 * Form for fetching a URL, extracting its content, and ingesting as evidence.
 * The backend fetches the page, creates a Document, and processes it
 * through the standard document pipeline.
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface FetchUrlFormProps {
  onSubmit: (url: string) => Promise<void>;
  isSubmitting: boolean;
}

export function FetchUrlForm({ onSubmit, isSubmitting }: FetchUrlFormProps) {
  const [url, setUrl] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const isValidUrl = (() => {
    if (!url.trim()) return false;
    try {
      const parsed = new URL(url.startsWith('http') ? url : `https://${url}`);
      return parsed.hostname.includes('.');
    } catch {
      return false;
    }
  })();

  const handleSubmit = async () => {
    if (!isValidUrl) return;
    const normalizedUrl = url.startsWith('http') ? url : `https://${url}`;
    await onSubmit(normalizedUrl);
    setSubmitted(true);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && isValidUrl && !isSubmitting) {
      handleSubmit();
    }
  };

  if (submitted && !isSubmitting) {
    return (
      <div className="text-center py-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-900/30 mb-3">
          <svg className="w-6 h-6 text-emerald-600 dark:text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
            <polyline points="20 6 9 17 4 12" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
          URL queued for processing
        </p>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
          Content will be fetched, extracted, and evidence will appear shortly.
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={() => { setUrl(''); setSubmitted(false); }}
          className="mt-4"
        >
          Fetch Another URL
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <Label htmlFor="fetch-url">Web Page URL</Label>
        <Input
          id="fetch-url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="https://example.com/article"
          className="text-sm"
          autoFocus
        />
        <p className="text-xs text-neutral-500 dark:text-neutral-400">
          The page content will be fetched, text extracted, and processed as a document with automatic evidence extraction.
        </p>
      </div>

      {/* URL preview */}
      {isValidUrl && (
        <div className="flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400 bg-neutral-50 dark:bg-neutral-900/50 rounded-lg px-3 py-2">
          <svg className="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
            <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="truncate">
            {(() => {
              try {
                const parsed = new URL(url.startsWith('http') ? url : `https://${url}`);
                return parsed.hostname;
              } catch {
                return url;
              }
            })()}
          </span>
        </div>
      )}

      <Button
        onClick={handleSubmit}
        disabled={isSubmitting || !isValidUrl}
        className="w-full"
      >
        {isSubmitting ? (
          <span className="flex items-center gap-2">
            <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
              <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
              <path d="M12 2a10 10 0 019.17 6" strokeLinecap="round" />
            </svg>
            Fetching...
          </span>
        ) : (
          'Fetch & Extract Evidence'
        )}
      </Button>
    </div>
  );
}
