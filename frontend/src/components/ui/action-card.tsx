/**
 * ActionCard - Card with colored left border for inline actions
 *
 * Used for inline action prompts in chat (case creation, evidence suggestion, etc.)
 * Provides semantic color variants that follow the design system.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

type ActionCardVariant = 'default' | 'success' | 'warning' | 'info' | 'error' | 'accent';

const variantStyles: Record<ActionCardVariant, string> = {
  default: cn(
    'border-l-neutral-500',
    'bg-neutral-50 dark:bg-neutral-900/50',
    'border-neutral-200 dark:border-neutral-800'
  ),
  success: cn(
    'border-l-success-500',
    'bg-success-50 dark:bg-success-900/20',
    'border-success-200 dark:border-success-800'
  ),
  warning: cn(
    'border-l-warning-500',
    'bg-warning-50 dark:bg-warning-900/20',
    'border-warning-200 dark:border-warning-800'
  ),
  info: cn(
    'border-l-info-500',
    'bg-info-50 dark:bg-info-900/20',
    'border-info-200 dark:border-info-800'
  ),
  error: cn(
    'border-l-error-500',
    'bg-error-50 dark:bg-error-900/20',
    'border-error-200 dark:border-error-800'
  ),
  accent: cn(
    'border-l-accent-500',
    'bg-accent-50 dark:bg-accent-900/20',
    'border-accent-200 dark:border-accent-800'
  ),
};

const variantTextStyles: Record<ActionCardVariant, { primary: string; secondary: string }> = {
  default: {
    primary: 'text-neutral-700 dark:text-neutral-300',
    secondary: 'text-neutral-600 dark:text-neutral-400',
  },
  success: {
    primary: 'text-success-700 dark:text-success-300',
    secondary: 'text-success-600 dark:text-success-400',
  },
  warning: {
    primary: 'text-warning-700 dark:text-warning-300',
    secondary: 'text-warning-600 dark:text-warning-400',
  },
  info: {
    primary: 'text-info-700 dark:text-info-300',
    secondary: 'text-info-600 dark:text-info-400',
  },
  error: {
    primary: 'text-error-700 dark:text-error-300',
    secondary: 'text-error-600 dark:text-error-400',
  },
  accent: {
    primary: 'text-accent-700 dark:text-accent-300',
    secondary: 'text-accent-600 dark:text-accent-400',
  },
};

interface ActionCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: ActionCardVariant;
}

const ActionCard = React.forwardRef<HTMLDivElement, ActionCardProps>(
  ({ className, variant = 'default', ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'border-l-4 rounded-md border p-4',
        variantStyles[variant],
        className
      )}
      {...props}
    />
  )
);
ActionCard.displayName = 'ActionCard';

interface ActionCardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
}

const ActionCardHeader = React.forwardRef<HTMLDivElement, ActionCardHeaderProps>(
  ({ className, icon, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex items-start gap-3', className)}
      {...props}
    >
      {icon && <span className="text-lg flex-shrink-0">{icon}</span>}
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  )
);
ActionCardHeader.displayName = 'ActionCardHeader';

interface ActionCardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  variant?: ActionCardVariant;
}

const ActionCardTitle = React.forwardRef<HTMLHeadingElement, ActionCardTitleProps>(
  ({ className, variant = 'default', ...props }, ref) => (
    <h4
      ref={ref}
      className={cn(
        'font-medium text-sm',
        'text-neutral-900 dark:text-neutral-100',
        className
      )}
      {...props}
    />
  )
);
ActionCardTitle.displayName = 'ActionCardTitle';

interface ActionCardDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {
  variant?: ActionCardVariant;
}

const ActionCardDescription = React.forwardRef<HTMLParagraphElement, ActionCardDescriptionProps>(
  ({ className, variant = 'default', ...props }, ref) => (
    <p
      ref={ref}
      className={cn(
        'text-sm mt-1',
        'text-neutral-600 dark:text-neutral-400',
        className
      )}
      {...props}
    />
  )
);
ActionCardDescription.displayName = 'ActionCardDescription';

interface ActionCardContentProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: ActionCardVariant;
}

const ActionCardContent = React.forwardRef<HTMLDivElement, ActionCardContentProps>(
  ({ className, variant = 'default', ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'mt-2 p-2 rounded text-sm',
        variant !== 'default' && cn(
          variantStyles[variant].replace('border-l-', 'bg-').split(' ')[0] + '/50',
        ),
        className
      )}
      {...props}
    />
  )
);
ActionCardContent.displayName = 'ActionCardContent';

const ActionCardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex items-center gap-2 mt-4', className)}
    {...props}
  />
));
ActionCardFooter.displayName = 'ActionCardFooter';

// Export variant text styles for custom text coloring
export { variantTextStyles };

export {
  ActionCard,
  ActionCardHeader,
  ActionCardTitle,
  ActionCardDescription,
  ActionCardContent,
  ActionCardFooter,
  type ActionCardVariant,
};
