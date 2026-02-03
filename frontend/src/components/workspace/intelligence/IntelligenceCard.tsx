/**
 * Base Intelligence Card Component
 * Wrapper for all intelligence feed cards
 */

import { ReactNode } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface IntelligenceCardProps {
  icon: ReactNode;
  title: string;
  description: string;
  actions?: ReactNode;
  variant?: 'success' | 'info' | 'warning' | 'error' | 'neutral';
  children?: ReactNode;
}

const variantStyles = {
  success: 'border-l-success-500 bg-success-50 dark:bg-success-900/10',
  info: 'border-l-accent-500 bg-accent-50 dark:bg-accent-900/10',
  warning: 'border-l-warning-500 bg-warning-50 dark:bg-warning-900/10',
  error: 'border-l-error-500 bg-error-50 dark:bg-error-900/10',
  neutral: 'border-l-neutral-500 bg-neutral-50 dark:bg-neutral-800',
};

export function IntelligenceCard({
  icon,
  title,
  description,
  actions,
  variant = 'neutral',
  children,
}: IntelligenceCardProps) {
  return (
    <Card className={cn('border-l-4', variantStyles[variant])}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          {icon}
          {title}
        </CardTitle>
        <p className="text-sm text-neutral-700 dark:text-neutral-300 mt-1">
          {description}
        </p>
      </CardHeader>
      
      {(children || actions) && (
        <CardContent className="space-y-3">
          {children}
          {actions && (
            <div className="flex gap-2 pt-2 border-t border-neutral-200 dark:border-neutral-700">
              {actions}
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
