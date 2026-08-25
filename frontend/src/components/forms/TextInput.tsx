import * as React from 'react';
import { LucideIcon, X } from 'lucide-react';
import { cn, renderIcon } from '../../lib/utils';

export interface TextInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  leftIcon?: LucideIcon | React.ReactNode;
  rightIcon?: LucideIcon | React.ReactNode;
  onClear?: () => void;
  error?: boolean;
}

export const TextInput = React.forwardRef<HTMLInputElement, TextInputProps>(
  ({ className, leftIcon: LeftIcon, rightIcon: RightIcon, onClear, error, value, ...props }, ref) => {
    const showClear = onClear && value && String(value).length > 0;

    return (
      <div className="relative flex items-center w-full">
        {LeftIcon && (
          <div className="absolute left-3 text-slate-400 pointer-events-none flex items-center justify-center">
            {renderIcon(LeftIcon, 'w-4 h-4')}
          </div>
        )}

        <input
          ref={ref}
          value={value}
          className={cn(
            'w-full py-2 text-xs font-medium rounded-lg vuexy-input transition-all',
            LeftIcon ? 'pl-9' : 'pl-3',
            showClear || RightIcon ? 'pr-9' : 'pr-3',
            error && 'border-[#EA5455] focus:border-[#EA5455] focus:ring-[#EA5455]/20',
            className
          )}
          {...props}
        />

        {showClear ? (
          <button
            type="button"
            onClick={onClear}
            className="absolute right-2.5 p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-white transition-colors cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        ) : RightIcon ? (
          <div className="absolute right-3 text-slate-400 pointer-events-none flex items-center justify-center">
            {renderIcon(RightIcon, 'w-4 h-4')}
          </div>
        ) : null}
      </div>
    );
  }
);

TextInput.displayName = 'TextInput';
