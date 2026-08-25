import * as React from 'react';
import { cn } from '../../lib/utils';

export interface RadioOption<T extends string | number> {
  value: T;
  label: React.ReactNode;
  description?: React.ReactNode;
  badge?: React.ReactNode;
  icon?: React.ReactNode;
  disabled?: boolean;
}

export interface RadioGroupProps<T extends string | number> {
  options: RadioOption<T>[];
  value: T;
  onChange: (value: T) => void;
  variant?: 'inline' | 'cards';
  className?: string;
}

export function RadioGroup<T extends string | number>({
  options,
  value,
  onChange,
  variant = 'cards',
  className,
}: RadioGroupProps<T>) {
  if (variant === 'inline') {
    return (
      <div className={cn('flex items-center space-x-4 flex-wrap gap-y-2', className)}>
        {options.map((opt) => {
          const isSelected = opt.value === value;
          return (
            <label
              key={String(opt.value)}
              className={cn(
                'inline-flex items-center space-x-2 cursor-pointer select-none',
                opt.disabled && 'opacity-50 pointer-events-none'
              )}
            >
              <button
                type="button"
                role="radio"
                aria-checked={isSelected}
                disabled={opt.disabled}
                onClick={() => onChange(opt.value)}
                className={cn(
                  'w-4 h-4 rounded-full border flex items-center justify-center transition-all',
                  isSelected
                    ? 'border-[#7367F0] bg-[#7367F0]'
                    : 'border-slate-300 dark:border-white/[0.15] bg-white dark:bg-white/[0.04]'
                )}
              >
                {isSelected && <span className="w-1.5 h-1.5 rounded-full bg-white" />}
              </button>
              <span className="text-xs font-bold text-slate-700 dark:text-slate-200">
                {opt.label}
              </span>
            </label>
          );
        })}
      </div>
    );
  }

  return (
    <div className={cn('grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3', className)}>
      {options.map((opt) => {
        const isSelected = opt.value === value;
        return (
          <div
            key={String(opt.value)}
            onClick={() => !opt.disabled && onChange(opt.value)}
            className={cn(
              'p-4 rounded-xl border text-left transition-all duration-200 cursor-pointer select-none flex flex-col justify-between space-y-2',
              opt.disabled && 'opacity-50 pointer-events-none cursor-not-allowed',
              isSelected
                ? 'border-[#7367F0] bg-[#7367F0]/10 ring-1 ring-[#7367F0]/50 shadow-sm'
                : 'border-slate-200 dark:border-white/[0.08] bg-slate-50/50 dark:bg-white/[0.02] hover:bg-slate-100/70 dark:hover:bg-white/[0.04]'
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center space-x-2 font-bold text-xs text-slate-800 dark:text-white">
                {opt.icon}
                <span>{opt.label}</span>
              </div>
              {opt.badge}
            </div>

            {opt.description && (
              <p className="text-[11px] text-slate-500 dark:text-[#7E7F96] leading-relaxed">
                {opt.description}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
