import * as React from 'react';
import { Check } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface CheckboxProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: React.ReactNode;
  description?: React.ReactNode;
  disabled?: boolean;
  className?: string;
  size?: 'sm' | 'md';
}

export const Checkbox: React.FC<CheckboxProps> = ({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  className,
  size = 'md',
}) => {
  const boxSizes = {
    sm: 'w-4 h-4 rounded',
    md: 'w-4.5 h-4.5 rounded-md',
  };

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
  };

  return (
    <label
      className={cn(
        'inline-flex items-start space-x-2.5 cursor-pointer select-none group',
        disabled && 'opacity-50 pointer-events-none cursor-not-allowed',
        className
      )}
    >
      <button
        type="button"
        role="checkbox"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          'flex items-center justify-center border transition-all duration-200 mt-0.5 shrink-0',
          boxSizes[size],
          checked
            ? 'bg-[#7367F0] border-[#7367F0] text-white shadow-sm shadow-[#7367F0]/30'
            : 'border-slate-300 dark:border-white/[0.15] bg-white dark:bg-white/[0.04] group-hover:border-[#7367F0]'
        )}
      >
        {checked && <Check className={cn('stroke-[3]', iconSizes[size])} />}
      </button>

      {(label || description) && (
        <div className="space-y-0.5 min-w-0">
          {label && (
            <span className="text-xs font-bold text-slate-800 dark:text-slate-200 block leading-tight">
              {label}
            </span>
          )}
          {description && (
            <span className="text-[11px] text-slate-400 dark:text-[#7E7F96] block leading-normal">
              {description}
            </span>
          )}
        </div>
      )}
    </label>
  );
};
