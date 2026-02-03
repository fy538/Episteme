/**
 * Assembly animation - shows case being built
 * Creates anticipation and celebrates AI work
 */

'use client';

import { useState, useEffect } from 'react';

interface CaseAssemblyAnimationProps {
  onComplete: () => void;
}

export function CaseAssemblyAnimation({ onComplete }: CaseAssemblyAnimationProps) {
  const [step, setStep] = useState(0);

  const steps = [
    { label: 'Created brief from conversation', icon: '📝' },
    { label: 'Extracted questions as inquiries', icon: '🔍' },
    { label: 'Flagged assumptions for validation', icon: '⚠️' },
    { label: 'Ready to research!', icon: '✨' },
  ];

  useEffect(() => {
    const timer = setInterval(() => {
      setStep((prev) => {
        if (prev >= steps.length - 1) {
          clearInterval(timer);
          setTimeout(onComplete, 800);
          return prev;
        }
        return prev + 1;
      });
    }, 600);

    return () => clearInterval(timer);
  }, [onComplete]);

  return (
    <div className="fixed inset-0 bg-white z-50 flex items-center justify-center">
      <div className="text-center max-w-md px-4">
        <h3 className="text-2xl tracking-tight font-semibold text-neutral-900 mb-8">
          Creating your decision workspace...
        </h3>

        <div className="space-y-4">
          {steps.map((s, idx) => (
            <div
              key={idx}
              className={`flex items-center gap-4 p-4 rounded-lg transition-all duration-500 transform ${
                idx <= step
                  ? 'bg-green-50 border-2 border-green-200 scale-100'
                  : 'bg-neutral-50 border border-neutral-200 opacity-50 scale-95'
              }`}
            >
              <span className="text-3xl">{s.icon}</span>
              <span
                className={`font-medium text-lg flex-1 text-left ${
                  idx <= step ? 'text-green-900' : 'text-neutral-500'
                }`}
              >
                {s.label}
              </span>
              {idx <= step && (
                <svg
                  className="w-6 h-6 text-green-600 animate-bounce"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </div>
          ))}
        </div>

        {/* Progress indicator */}
        <div className="mt-8">
          <div className="text-sm text-neutral-500 mb-2">
            {Math.min(((step + 1) / steps.length) * 100, 100).toFixed(0)}% complete
          </div>
          <div className="w-full bg-neutral-200 rounded-full h-2 overflow-hidden">
            <div
              className="bg-gradient-to-r from-accent-500 to-success-500 h-2 transition-all duration-600"
              style={{ width: `${Math.min(((step + 1) / steps.length) * 100, 100)}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
