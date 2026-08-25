import * as React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface SpinnerProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'primary' | 'success' | 'danger' | 'warning' | 'white' | 'muted';
  className?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  variant = 'primary',
  className,
}) => {
  const sizeClasses = {
    xs: 'w-3 h-3',
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
    xl: 'w-10 h-10',
  };

  const variantClasses = {
    primary: 'text-[#7367F0]',
    success: 'text-[#28C76F]',
    danger: 'text-[#EA5455]',
    warning: 'text-[#FF9F43]',
    white: 'text-white',
    muted: 'text-slate-400',
  };

  return (
    <Loader2
      className={cn('animate-spin', sizeClasses[size], variantClasses[variant], className)}
    />
  );
};
