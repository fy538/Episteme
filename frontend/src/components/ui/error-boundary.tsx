/**
 * Error Boundary Component
 * Catches React errors and shows graceful fallback UI
 */

'use client';

import React, { Component, ReactNode } from 'react';
import { Button } from './button';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <ErrorFallback
          error={this.state.error}
          reset={() => this.setState({ hasError: false, error: null })}
        />
      );
    }

    return this.props.children;
  }
}

function ErrorFallback({ error, reset }: { error: Error | null; reset: () => void }) {
  return (
    <div className="flex min-h-[400px] items-center justify-center p-8">
      <div className="text-center max-w-md">
        <div className="mb-4 flex justify-center">
          <div className="rounded-full bg-error-100 dark:bg-error-900/30 p-3">
            <svg
              className="h-8 w-8 text-error-600 dark:text-error-400"
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

        <h2 className="text-xl font-display font-semibold tracking-tight text-neutral-900 dark:text-neutral-100 mb-2">
          Something went wrong
        </h2>

        <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-6">
          {error?.message || 'An unexpected error occurred'}
        </p>

        <div className="flex items-center justify-center gap-3">
          <Button onClick={reset}>Try Again</Button>
          <Button variant="outline" onClick={() => window.location.reload()}>
            Reload Page
          </Button>
        </div>

        {process.env.NODE_ENV === 'development' && error && (
          <details className="mt-6 text-left">
            <summary className="cursor-pointer text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Error Details (dev only)
            </summary>
            <pre className="mt-2 overflow-auto rounded bg-neutral-900 p-4 text-xs text-neutral-100">
              {error.stack}
            </pre>
          </details>
        )}
      </div>
    </div>
  );
}

export function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
  showReload = true,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
  showReload?: boolean;
}) {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="text-center max-w-md">
        <div className="mb-4 flex justify-center">
          <div className="rounded-full bg-error-100 dark:bg-error-900/30 p-3">
            <svg
              className="h-6 w-6 text-error-600 dark:text-error-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
        </div>

        <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
          {title}
        </h3>

        {message && (
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-6">
            {message}
          </p>
        )}

        <div className="flex items-center justify-center gap-3">
          {onRetry && (
            <Button onClick={onRetry} size="sm">
              Try Again
            </Button>
          )}
          {showReload && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.location.reload()}
            >
              Reload
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
