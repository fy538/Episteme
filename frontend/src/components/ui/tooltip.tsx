/**
 * Tooltip component - hover information
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  side?: 'top' | 'right' | 'bottom' | 'left';
}

export function Tooltip({ content, children, side = 'top' }: TooltipProps) {
  const [isVisible, setIsVisible] = React.useState(false);

  return (
    <div className="relative inline-block">
      <div
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onFocus={() => setIsVisible(true)}
        onBlur={() => setIsVisible(false)}
      >
        {children}
      </div>

      {isVisible && (
        <div
          className={cn(
            'absolute z-50 px-3 py-2 text-sm text-white bg-primary-900 rounded-md shadow-lg whitespace-nowrap animate-fade-in',
            {
              'bottom-full left-1/2 -translate-x-1/2 mb-2': side === 'top',
              'top-full left-1/2 -translate-x-1/2 mt-2': side === 'bottom',
              'left-full top-1/2 -translate-y-1/2 ml-2': side === 'right',
              'right-full top-1/2 -translate-y-1/2 mr-2': side === 'left',
            }
          )}
        >
          {content}
          {/* Arrow */}
          <div
            className={cn('absolute w-2 h-2 bg-primary-900 transform rotate-45', {
              'top-full left-1/2 -translate-x-1/2 -mt-1': side === 'top',
              'bottom-full left-1/2 -translate-x-1/2 -mb-1': side === 'bottom',
              'top-1/2 right-full -translate-y-1/2 -mr-1': side === 'right',
              'top-1/2 left-full -translate-y-1/2 -ml-1': side === 'left',
            })}
          />
        </div>
      )}
    </div>
  );
}
