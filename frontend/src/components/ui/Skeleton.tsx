import * as React from 'react';
import { cn } from '../../lib/utils';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'rectangular' | 'circular';
  width?: string | number;
  height?: string | number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className,
  variant = 'rectangular',
  width,
  height,
  style,
  ...props
}) => {
  const variantClasses = {
    text: 'h-4 w-full rounded-md',
    rectangular: 'rounded-xl',
    circular: 'rounded-full',
  };

  return (
    <div
      className={cn(
        'animate-pulse bg-slate-200/80 dark:bg-white/[0.06]',
        variantClasses[variant],
        className
      )}
      style={{
        width,
        height,
        ...style,
      }}
      {...props}
    />
  );
};
