import React, { useState, useEffect } from 'react';
import { Search, X, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface SearchInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  value?: string;
  onChange?: (value: string) => void;
  onClear?: () => void;
  debounceMs?: number;
  loading?: boolean;
  sizeVariant?: 'sm' | 'md' | 'lg';
}

export const SearchInput = React.forwardRef<HTMLInputElement, SearchInputProps>(
  (
    {
      value: controlledValue,
      onChange,
      onClear,
      debounceMs = 300,
      loading = false,
      sizeVariant = 'md',
      placeholder = 'Search...',
      className,
      ...props
    },
    ref
  ) => {
    const [localValue, setLocalValue] = useState(controlledValue || '');

    useEffect(() => {
      if (controlledValue !== undefined) {
        setLocalValue(controlledValue);
      }
    }, [controlledValue]);

    useEffect(() => {
      const handler = setTimeout(() => {
        if (onChange) {
          onChange(localValue);
        }
      }, debounceMs);
      return () => clearTimeout(handler);
    }, [localValue, debounceMs, onChange]);

    const handleClear = () => {
      setLocalValue('');
      if (onChange) onChange('');
      if (onClear) onClear();
    };

    const sizeClasses = {
      sm: 'h-8 text-[11px] pl-8 pr-7',
      md: 'h-10 text-xs pl-9 pr-8',
      lg: 'h-11 text-sm pl-10 pr-9',
    };

    const iconSizes = {
      sm: 'w-3.5 h-3.5 left-2.5',
      md: 'w-4 h-4 left-3',
      lg: 'w-4.5 h-4.5 left-3.5',
    };

    return (
      <div className="relative flex items-center w-full">
        <Search
          className={cn(
            'text-slate-400 absolute pointer-events-none transition-colors',
            iconSizes[sizeVariant]
          )}
        />

        <input
          ref={ref}
          type="text"
          value={localValue}
          onChange={(e) => setLocalValue(e.target.value)}
          placeholder={placeholder}
          className={cn(
            'w-full rounded-lg vuexy-input font-medium transition-all',
            sizeClasses[sizeVariant],
            className
          )}
          {...props}
        />

        <div className="absolute right-2.5 flex items-center space-x-1">
          {loading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin text-[#7367F0]" />
          ) : localValue ? (
            <button
              type="button"
              onClick={handleClear}
              className="p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-white transition-colors cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          ) : null}
        </div>
      </div>
    );
  }
);

SearchInput.displayName = 'SearchInput';
