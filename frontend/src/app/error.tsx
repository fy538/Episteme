/**
 * Global Error Page
 * Catches unhandled errors in app router
 */

'use client';

import { useEffect } from 'react';
import { Button } from '@/components/ui/button';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('App error:', error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-50 dark:bg-primary-950 p-4">
      <div className="text-center max-w-md">
        <div className="mb-6 flex justify-center">
          <div className="rounded-full bg-error-100 dark:bg-error-900/30 p-4">
            <svg
              className="h-12 w-12 text-error-600 dark:text-error-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
        </div>

        <h2 className="text-2xl tracking-tight font-semibold text-neutral-900 dark:text-neutral-100 mb-3">
          Something went wrong
        </h2>

        <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-8">
          {error.message || 'An unexpected error occurred. Please try again.'}
        </p>

        <div className="flex items-center justify-center gap-3">
          <Button onClick={reset}>Try Again</Button>
          <Button variant="outline" onClick={() => window.location.href = '/'}>
            Go Home
          </Button>
        </div>

        {process.env.NODE_ENV === 'development' && (
          <details className="mt-8 text-left">
            <summary className="cursor-pointer text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
              Error Details
            </summary>
            <pre className="overflow-auto rounded bg-neutral-900 p-4 text-xs text-neutral-100 max-h-64">
              {error.stack}
            </pre>
            {error.digest && (
              <p className="mt-2 text-xs text-neutral-500">
                Error ID: {error.digest}
              </p>
            )}
          </details>
        )}
      </div>
    </div>
  );
}
