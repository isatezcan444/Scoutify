import * as React from 'react';
import { cn } from '../../lib/utils';

export interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: React.ReactNode;
  description?: React.ReactNode;
  disabled?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const Switch: React.FC<SwitchProps> = ({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  size = 'md',
  className,
}) => {
  const switchSizes = {
    sm: 'w-8 h-4',
    md: 'w-10 h-5',
    lg: 'w-12 h-6',
  };

  const knobSizes = {
    sm: 'w-3 h-3 translate-x-4',
    md: 'w-3.5 h-3.5 translate-x-5',
    lg: 'w-4.5 h-4.5 translate-x-6',
  };

  return (
    <label
      className={cn(
        'inline-flex items-center justify-between cursor-pointer select-none group',
        disabled && 'opacity-50 pointer-events-none cursor-not-allowed',
        className
      )}
    >
      {(label || description) && (
        <div className="mr-3 space-y-0.5">
          {label && <div className="text-xs font-bold text-slate-800 dark:text-slate-200">{label}</div>}
          {description && (
            <div className="text-[11px] text-slate-400 dark:text-[#7E7F96]">{description}</div>
          )}
        </div>
      )}

      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative inline-flex shrink-0 p-0.5 rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-[#7367F0]/30',
          switchSizes[size],
          checked ? 'bg-[#7367F0]' : 'bg-slate-300 dark:bg-white/[0.12]'
        )}
      >
        <span
          className={cn(
            'pointer-events-none inline-block rounded-full bg-white shadow-md transform ring-0 transition duration-200 ease-in-out',
            checked ? knobSizes[size] : 'translate-x-0',
            size === 'sm' ? 'w-3 h-3' : size === 'md' ? 'w-4 h-4' : 'w-5 h-5'
          )}
        />
      </button>
    </label>
  );
};
