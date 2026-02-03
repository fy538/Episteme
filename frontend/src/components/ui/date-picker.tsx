/**
 * Date Picker Component
 * Simple date selection input
 */

'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';

interface DatePickerProps {
  value?: Date;
  onChange: (date: Date) => void;
  min?: Date;
  max?: Date;
  className?: string;
  placeholder?: string;
}

export function DatePicker({
  value,
  onChange,
  min,
  max,
  className,
  placeholder = 'Select date',
}: DatePickerProps) {
  const [inputValue, setInputValue] = useState(
    value ? value.toISOString().split('T')[0] : ''
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setInputValue(newValue);

    if (newValue) {
      const date = new Date(newValue);
      if (!isNaN(date.getTime())) {
        onChange(date);
      }
    }
  };

  return (
    <input
      type="date"
      value={inputValue}
      onChange={handleChange}
      min={min?.toISOString().split('T')[0]}
      max={max?.toISOString().split('T')[0]}
      placeholder={placeholder}
      className={cn(
        'flex h-10 w-full rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-primary-900 px-3 py-2 text-sm',
        'focus:outline-none focus:ring-2 focus:ring-accent-500 focus:ring-offset-2',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'text-neutral-900 dark:text-neutral-100',
        className
      )}
    />
  );
}
