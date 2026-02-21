/**
 * Heading components - standardized typography hierarchy
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

interface HeadingProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode;
}

/** Page-level title (h1) - used once per page */
export function PageTitle({ className, children, ...props }: HeadingProps) {
  return (
    <h1
      className={cn(
        'text-2xl font-display font-bold tracking-tight text-neutral-900 dark:text-neutral-100',
        className
      )}
      {...props}
    >
      {children}
    </h1>
  );
}

/** Major section heading (h2) */
export function SectionTitle({ className, children, ...props }: HeadingProps) {
  return (
    <h2
      className={cn(
        'text-base font-semibold text-neutral-800 dark:text-neutral-100',
        className
      )}
      {...props}
    >
      {children}
    </h2>
  );
}

/** Card/subsection heading (h3) */
export function SubsectionTitle({ className, children, ...props }: HeadingProps) {
  return (
    <h3
      className={cn(
        'text-sm font-semibold text-neutral-800 dark:text-neutral-100',
        className
      )}
      {...props}
    >
      {children}
    </h3>
  );
}

/** Small label heading (h4) - uppercase tracking */
export function LabelHeading({ className, children, ...props }: HeadingProps) {
  return (
    <h4
      className={cn(
        'text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400',
        className
      )}
      {...props}
    >
      {children}
    </h4>
  );
}
