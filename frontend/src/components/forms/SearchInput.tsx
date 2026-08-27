import React, { useState, useEffect, useRef } from 'react';
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
    const onChangeRef = useRef(onChange);
    const onClearRef = useRef(onClear);
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
      onChangeRef.current = onChange;
      onClearRef.current = onClear;
    });

    // Sync from parent if controlledValue changed from outside
    useEffect(() => {
      if (controlledValue !== undefined && controlledValue !== localValue) {
        setLocalValue(controlledValue);
      }
    }, [controlledValue]);

    // Clean up timer on unmount
    useEffect(() => {
      return () => {
        if (timerRef.current) clearTimeout(timerRef.current);
      };
    }, []);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = e.target.value;
      setLocalValue(newValue);

      if (timerRef.current) clearTimeout(timerRef.current);

      if (debounceMs <= 0) {
        onChangeRef.current?.(newValue);
      } else {
        timerRef.current = setTimeout(() => {
          onChangeRef.current?.(newValue);
        }, debounceMs);
      }
    };

    const handleClear = () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      setLocalValue('');
      onChangeRef.current?.('');
      onClearRef.current?.();
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
