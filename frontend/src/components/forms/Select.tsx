import * as React from 'react';
import { ChevronDown, LucideIcon } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface SelectOption {
  value: string | number;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  options: SelectOption[];
  leftIcon?: LucideIcon | React.ReactNode;
  error?: boolean;
  sizeVariant?: 'sm' | 'md' | 'lg';
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, options, leftIcon: LeftIcon, error, sizeVariant = 'md', ...props }, ref) => {
    const sizeClasses = {
      sm: 'h-8 text-[11px] py-1',
      md: 'h-10 text-xs py-2',
      lg: 'h-11 text-sm py-2.5',
    };

    return (
      <div className="relative flex items-center w-full">
        {LeftIcon && (
          <div className="absolute left-3 text-slate-400 pointer-events-none flex items-center justify-center">
            {typeof LeftIcon === 'function' ? <LeftIcon className="w-4 h-4" /> : LeftIcon}
          </div>
        )}

        <select
          ref={ref}
          className={cn(
            'w-full font-bold rounded-lg vuexy-input cursor-pointer appearance-none transition-all pr-8',
            LeftIcon ? 'pl-9' : 'pl-3',
            sizeClasses[sizeVariant],
            error && 'border-[#EA5455] focus:border-[#EA5455] focus:ring-[#EA5455]/20',
            className
          )}
          {...props}
        >
          {options.map((opt) => (
            <option key={String(opt.value)} value={opt.value} disabled={opt.disabled}>
              {opt.label}
            </option>
          ))}
        </select>

        <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-3 pointer-events-none transition-colors" />
      </div>
    );
  }
);

Select.displayName = 'Select';
