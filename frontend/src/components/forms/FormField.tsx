import * as React from 'react';
import { cn } from '../../lib/utils';

export interface FormFieldProps {
  label?: React.ReactNode;
  required?: boolean;
  helperText?: React.ReactNode;
  error?: string;
  children: React.ReactNode;
  className?: string;
}

export const FormField: React.FC<FormFieldProps> = ({
  label,
  required,
  helperText,
  error,
  children,
  className,
}) => {
  return (
    <div className={cn('space-y-1.5', className)}>
      {label && (
        <label className="text-xs font-bold text-slate-700 dark:text-slate-200 block select-none">
          {label}
          {required && <span className="text-[#EA5455] ml-1">*</span>}
        </label>
      )}

      {children}

      {error ? (
        <p className="text-[11px] font-bold text-[#EA5455] animate-fade-in">{error}</p>
      ) : helperText ? (
        <p className="text-[11px] text-slate-400 dark:text-[#7E7F96]">{helperText}</p>
      ) : null}
    </div>
  );
};
