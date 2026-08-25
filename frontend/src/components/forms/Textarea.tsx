import * as React from 'react';
import { cn } from '../../lib/utils';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  maxLength?: number;
  showCount?: boolean;
  error?: boolean;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, maxLength, showCount = false, error, value, onChange, ...props }, ref) => {
    const currentLength = value ? String(value).length : 0;

    return (
      <div className="relative w-full space-y-1">
        <textarea
          ref={ref}
          value={value}
          maxLength={maxLength}
          onChange={onChange}
          className={cn(
            'w-full p-3 rounded-lg vuexy-input text-xs font-medium leading-relaxed transition-all resize-y min-h-[90px]',
            error && 'border-[#EA5455] focus:border-[#EA5455] focus:ring-[#EA5455]/20',
            className
          )}
          {...props}
        />

        {showCount && maxLength && (
          <div className="flex justify-end text-[10px] font-mono text-slate-400">
            <span>
              {currentLength} / {maxLength}
            </span>
          </div>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
