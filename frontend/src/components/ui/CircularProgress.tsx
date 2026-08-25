import * as React from 'react';
import { cn } from '../../lib/utils';

export interface CircularProgressProps {
  value: number; // 0 to 100
  size?: number; // diameter in px (default 64)
  strokeWidth?: number; // stroke width in px (default 6)
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'info';
  showLabel?: boolean;
  className?: string;
}

export const CircularProgress: React.FC<CircularProgressProps> = ({
  value,
  size = 64,
  strokeWidth = 6,
  variant = 'primary',
  showLabel = true,
  className,
}) => {
  const clampedValue = Math.max(0, Math.min(100, value));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (clampedValue / 100) * circumference;

  const colorClasses = {
    primary: 'text-[#7367F0]',
    success: 'text-[#28C76F]',
    warning: 'text-[#FF9F43]',
    danger: 'text-[#EA5455]',
    info: 'text-[#00CFE8]',
  };

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Track Background */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          stroke="currentColor"
          fill="transparent"
          className="text-slate-100 dark:text-white/[0.08]"
        />
        {/* Animated Progress Arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          stroke="currentColor"
          fill="transparent"
          className={cn('transition-all duration-700 ease-out', colorClasses[variant])}
        />
      </svg>

      {showLabel && (
        <span className="absolute font-mono font-extrabold text-xs text-slate-800 dark:text-white select-none">
          %{Math.round(clampedValue)}
        </span>
      )}
    </div>
  );
};
