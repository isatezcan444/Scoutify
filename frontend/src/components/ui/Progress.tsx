import * as React from 'react';
import { cn } from '../../lib/utils';

export interface ProgressProps {
  value: number; // 0 to 100
  variant?: 'primary' | 'success' | 'warning' | 'info' | 'gradient';
  size?: 'xs' | 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  label?: string;
  animated?: boolean;
  className?: string;
}

export const Progress: React.FC<ProgressProps> = ({
  value,
  variant = 'primary',
  size = 'md',
  showLabel = false,
  label,
  animated = true,
  className,
}) => {
  const clampedValue = Math.min(Math.max(value, 0), 100);

  const sizeClasses = {
    xs: 'h-1.5',
    sm: 'h-2',
    md: 'h-2.5',
    lg: 'h-3.5',
  };

  const variantBarClasses = {
    primary: 'bg-[#7367F0]',
    success: 'bg-[#28C76F]',
    warning: 'bg-[#FF9F43]',
    info: 'bg-[#00CFE8]',
    gradient: 'bg-gradient-to-r from-[#7367F0] via-[#867BFF] to-[#00CFE8]',
  };

  return (
    <div className={cn('w-full space-y-1.5', className)}>
      {(showLabel || label) && (
        <div className="flex justify-between items-center text-xs font-bold text-slate-700 dark:text-slate-200">
          <span>{label || 'Progress'}</span>
          <span className="font-mono text-[#7367F0] dark:text-[#A59DF8]">{Math.round(clampedValue)}%</span>
        </div>
      )}

      <div className={cn('w-full bg-slate-200/80 dark:bg-white/[0.08] rounded-full overflow-hidden p-0.5', sizeClasses[size])}>
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500 ease-out',
            variantBarClasses[variant],
            animated && 'animate-pulse-subtle'
          )}
          style={{ width: `${clampedValue}%` }}
        />
      </div>
    </div>
  );
};
