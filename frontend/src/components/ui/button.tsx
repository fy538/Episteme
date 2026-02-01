/**
 * Button component - primary interactive element
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'ghost' | 'destructive' | 'success';
  size?: 'default' | 'sm' | 'lg' | 'icon';
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    return (
      <button
        className={cn(
          // Base styles
          'inline-flex items-center justify-center rounded-md font-medium transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2',
          'disabled:pointer-events-none disabled:opacity-50',
          // Variant styles
          {
            'bg-accent-600 text-white hover:bg-accent-700 shadow-sm': variant === 'default',
            'border border-primary-300 bg-white text-primary-700 hover:bg-primary-50': variant === 'outline',
            'text-primary-700 hover:bg-primary-100': variant === 'ghost',
            'bg-error-600 text-white hover:bg-error-700 shadow-sm': variant === 'destructive',
            'bg-success-600 text-white hover:bg-success-700 shadow-sm': variant === 'success',
          },
          // Size styles
          {
            'h-10 px-4 py-2 text-sm': size === 'default',
            'h-8 px-3 text-xs': size === 'sm',
            'h-12 px-6 text-base': size === 'lg',
            'h-9 w-9': size === 'icon',
          },
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);

Button.displayName = 'Button';

export { Button };
