/**
 * Welcome Empty State
 *
 * Shown when a new user has zero projects.
 * Provides a friendly introduction to Episteme with clear next steps.
 */

'use client';

import { Button } from '@/components/ui/button';
import { NoProjectsIllustration } from '@/components/illustrations/EmptyStateIllustrations';

interface WelcomeEmptyProps {
  onCreateProject: () => void;
}

export function WelcomeEmpty({ onCreateProject }: WelcomeEmptyProps) {
  return (
    <div className="max-w-md mx-auto text-center py-8 animate-fade-in">
      {/* Illustration */}
      <div className="mb-6 flex justify-center">
        <NoProjectsIllustration />
      </div>

      {/* Welcome message */}
      <h2 className="text-2xl font-bold text-primary-900 dark:text-primary-50 mb-3">
        Welcome to Episteme
      </h2>
      <p className="text-neutral-600 dark:text-neutral-400 mb-6">
        Make better decisions by structuring your thinking,
        gathering evidence, and testing assumptions.
      </p>

      {/* How it works */}
      <div className="text-left bg-neutral-100 dark:bg-neutral-800/50 rounded-xl p-5 mb-6">
        <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-3">
          How it works:
        </p>
        <ol className="text-sm text-neutral-600 dark:text-neutral-400 space-y-3">
          <li className="flex gap-3">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent-100 dark:bg-accent-900/50 text-accent-600 dark:text-accent-400 text-xs font-medium flex items-center justify-center">
              1
            </span>
            <span>Start a conversation about any decision you're facing</span>
          </li>
          <li className="flex gap-3">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent-100 dark:bg-accent-900/50 text-accent-600 dark:text-accent-400 text-xs font-medium flex items-center justify-center">
              2
            </span>
            <span>I'll help you identify key questions and assumptions</span>
          </li>
          <li className="flex gap-3">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent-100 dark:bg-accent-900/50 text-accent-600 dark:text-accent-400 text-xs font-medium flex items-center justify-center">
              3
            </span>
            <span>Build evidence until you're ready to decide</span>
          </li>
        </ol>
      </div>

      {/* CTA */}
      <Button onClick={onCreateProject} size="lg" className="w-full sm:w-auto">
        Create Your First Project
      </Button>

      {/* Or just chat hint */}
      <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-4">
        Or just start chatting below — I'll help you get organized
      </p>
    </div>
  );
}

export default WelcomeEmpty;
