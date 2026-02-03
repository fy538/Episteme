/**
 * Status Indicators
 * Animated status badges, progress rings, live indicators
 */

'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useReducedMotion } from '@/hooks/useReducedMotion';

interface StatusIndicatorProps {
  status: 'active' | 'idle' | 'warning' | 'error' | 'success';
  label?: string;
  showPulse?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

const STATUS_COLORS = {
  active: {
    bg: 'bg-accent-500',
    ring: 'bg-accent-400',
    text: 'text-accent-700 dark:text-accent-300',
  },
  idle: {
    bg: 'bg-neutral-400',
    ring: 'bg-neutral-300',
    text: 'text-neutral-600 dark:text-neutral-400',
  },
  warning: {
    bg: 'bg-warning-500',
    ring: 'bg-warning-400',
    text: 'text-warning-700 dark:text-warning-300',
  },
  error: {
    bg: 'bg-error-500',
    ring: 'bg-error-400',
    text: 'text-error-700 dark:text-error-300',
  },
  success: {
    bg: 'bg-success-500',
    ring: 'bg-success-400',
    text: 'text-success-700 dark:text-success-300',
  },
};

const SIZES = {
  sm: 'h-2 w-2',
  md: 'h-3 w-3',
  lg: 'h-4 w-4',
};

export function StatusIndicator({
  status,
  label,
  showPulse = true,
  size = 'md',
}: StatusIndicatorProps) {
  const prefersReducedMotion = useReducedMotion();
  const colors = STATUS_COLORS[status];

  return (
    <div className="inline-flex items-center gap-2">
      <span className="relative flex">
        {showPulse && !prefersReducedMotion && (status === 'active' || status === 'warning') && (
          <span
            className={cn(
              'absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping',
              colors.ring
            )}
          />
        )}
        <span className={cn('relative inline-flex rounded-full', SIZES[size], colors.bg)} />
      </span>
      {label && <span className={cn('text-sm font-medium', colors.text)}>{label}</span>}
    </div>
  );
}

interface CircularProgressProps {
  value: number; // 0-100
  size?: 'sm' | 'md' | 'lg';
  color?: 'accent' | 'success' | 'warning' | 'error';
  showLabel?: boolean;
  thickness?: number;
}

export function CircularProgress({
  value,
  size = 'md',
  color = 'accent',
  showLabel = true,
  thickness = 4,
}: CircularProgressProps) {
  const sizes = {
    sm: 40,
    md: 60,
    lg: 80,
  };

  const colors = {
    accent: 'stroke-accent-600',
    success: 'stroke-success-600',
    warning: 'stroke-warning-600',
    error: 'stroke-error-600',
  };

  const dimension = sizes[size];
  const radius = (dimension - thickness * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={dimension} height={dimension} className="transform -rotate-90">
        {/* Background circle */}
        <circle
          cx={dimension / 2}
          cy={dimension / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={thickness}
          fill="none"
          className="text-neutral-200 dark:text-neutral-800"
        />
        {/* Progress circle */}
        <circle
          cx={dimension / 2}
          cy={dimension / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={thickness}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={cn(colors[color], 'transition-all duration-500 ease-out')}
        />
      </svg>
      {showLabel && (
        <span className="absolute text-sm font-semibold text-neutral-900 dark:text-neutral-100">
          {Math.round(value)}%
        </span>
      )}
    </div>
  );
}

interface ProgressBarProps {
  value: number; // 0-100
  color?: 'accent' | 'success' | 'warning' | 'error';
  showLabel?: boolean;
  label?: string;
  className?: string;
}

export function ProgressBar({
  value,
  color = 'accent',
  showLabel = false,
  label,
  className,
}: ProgressBarProps) {
  const colors = {
    accent: 'bg-accent-600',
    success: 'bg-success-600',
    warning: 'bg-warning-600',
    error: 'bg-error-600',
  };

  return (
    <div className={className}>
      {(showLabel || label) && (
        <div className="flex items-center justify-between mb-2">
          {label && (
            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
              {label}
            </span>
          )}
          {showLabel && (
            <span className="text-sm text-neutral-600 dark:text-neutral-400">
              {Math.round(value)}%
            </span>
          )}
        </div>
      )}
      <div className="h-2 w-full rounded-full bg-neutral-200 dark:bg-neutral-800 overflow-hidden">
        <motion.div
          className={cn('h-full rounded-full', colors[color])}
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}
