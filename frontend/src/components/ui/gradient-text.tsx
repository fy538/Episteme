/**
 * Gradient Text Component
 * Beautiful gradient text effects
 */

import { cn } from '@/lib/utils';

interface GradientTextProps extends React.HTMLAttributes<HTMLSpanElement> {
  gradient?: 'accent' | 'success' | 'rainbow';
}

export function GradientText({
  children,
  className,
  gradient = 'accent',
  ...props
}: GradientTextProps) {
  const gradients = {
    accent: 'from-accent-600 via-accent-500 to-accent-700',
    success: 'from-success-600 via-success-500 to-success-700',
    rainbow: 'from-accent-600 via-purple-500 to-pink-600',
  };

  return (
    <span
      className={cn(
        'bg-gradient-to-r bg-clip-text text-transparent',
        gradients[gradient],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
