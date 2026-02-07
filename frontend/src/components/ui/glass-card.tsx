/**
 * Glass Card Component
 * Glassmorphism effect cards for modern UI
 */

'use client';

import { cn } from '@/lib/utils';

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'strong' | 'subtle';
}

export function GlassCard({
  className,
  variant = 'default',
  ...props
}: GlassCardProps) {
  return (
    <div
      className={cn(
        'rounded-md border shadow-sm',
        {
          'backdrop-blur-md bg-white/80 dark:bg-primary-900/80 border-white/20 dark:border-neutral-700/30':
            variant === 'default',
          'backdrop-blur-lg bg-white/90 dark:bg-primary-900/90 border-white/30 dark:border-neutral-700/40':
            variant === 'strong',
          'backdrop-blur-sm bg-white/60 dark:bg-primary-900/60 border-white/10 dark:border-neutral-700/20':
            variant === 'subtle',
        },
        className
      )}
      {...props}
    />
  );
}

export function GlassCardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('flex flex-col space-y-1.5 p-6', className)}
      {...props}
    />
  );
}

export function GlassCardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={cn(
        'font-display text-2xl tracking-tight font-semibold leading-none tracking-tight',
        className
      )}
      {...props}
    />
  );
}

export function GlassCardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('p-6 pt-0', className)} {...props} />;
}
