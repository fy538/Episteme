/**
 * Multi-Select Component
 * Select multiple items from a list
 */

'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Badge } from './badge';
import { useReducedMotion } from '@/hooks/useReducedMotion';

interface MultiSelectProps {
  options: Array<{ value: string; label: string }>;
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
  className?: string;
}

export function MultiSelect({
  options,
  value,
  onChange,
  placeholder = 'Select items...',
  className,
}: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const prefersReducedMotion = useReducedMotion();

  const selectedLabels = value.map(
    (v) => options.find((o) => o.value === v)?.label || v
  );

  const toggleOption = (optionValue: string) => {
    if (value.includes(optionValue)) {
      onChange(value.filter((v) => v !== optionValue));
    } else {
      onChange([...value, optionValue]);
    }
  };

  const removeValue = (valueToRemove: string) => {
    onChange(value.filter((v) => v !== valueToRemove));
  };

  return (
    <div className={cn('relative', className)}>
      {/* Selected badges */}
      <div
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'min-h-[40px] w-full rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-primary-900 px-3 py-2',
          'focus-within:outline-none focus-within:ring-2 focus-within:ring-accent-500 focus-within:ring-offset-2',
          'cursor-pointer'
        )}
      >
        {value.length === 0 ? (
          <span className="text-sm text-neutral-500 dark:text-neutral-400">
            {placeholder}
          </span>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {selectedLabels.map((label, index) => (
              <Badge
                key={value[index]}
                variant="neutral"
                className="cursor-pointer hover:bg-neutral-200 dark:hover:bg-neutral-700"
                onClick={(e) => {
                  e.stopPropagation();
                  removeValue(value[index]);
                }}
              >
                {label}
                <span className="ml-1.5 text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300">
                  ×
                </span>
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={prefersReducedMotion ? {} : { opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={prefersReducedMotion ? {} : { opacity: 0, y: -10 }}
            transition={{ duration: 0.15 }}
            className="absolute z-50 mt-2 w-full rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-primary-900 shadow-lg max-h-64 overflow-y-auto"
          >
            {options.map((option) => (
              <button
                key={option.value}
                onClick={() => toggleOption(option.value)}
                className={cn(
                  'flex w-full items-center justify-between px-4 py-2 text-left text-sm transition-colors',
                  value.includes(option.value)
                    ? 'bg-accent-50 dark:bg-accent-900/20 text-accent-900 dark:text-accent-100'
                    : 'text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800'
                )}
              >
                <span>{option.label}</span>
                {value.includes(option.value) && (
                  <svg
                    className="h-4 w-4 text-accent-600 dark:text-accent-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                )}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
