import * as React from 'react';
import { LucideIcon } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface SliderProps {
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  label?: React.ReactNode;
  icon?: LucideIcon | React.ReactNode;
  helperText?: React.ReactNode;
  unit?: string;
  disabled?: boolean;
  className?: string;
}

export const Slider: React.FC<SliderProps> = ({
  value,
  onChange,
  min,
  max,
  step = 1,
  label,
  icon: Icon,
  helperText,
  unit = '',
  disabled = false,
  className,
}) => {
  return (
    <div
      className={cn(
        'p-4 rounded-xl bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] space-y-2.5 shadow-sm hover:border-[#7367F0]/30 transition-all',
        disabled && 'opacity-50 pointer-events-none',
        className
      )}
    >
      {/* Label and Live Bubble Value */}
      <div className="flex items-center justify-between">
        {label && (
          <label className="text-xs font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5 select-none">
            {Icon && (typeof Icon === 'function' ? <Icon className="w-3.5 h-3.5 text-[#7367F0]" /> : Icon)}
            <span>{label}</span>
          </label>
        )}
        <span className="text-xs font-extrabold font-mono text-[#7367F0] bg-[#7367F0]/10 px-2.5 py-0.5 rounded-lg border border-[#7367F0]/20 select-none">
          {value}{unit}
        </span>
      </div>

      {/* Native Track Slider */}
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[#7367F0] cursor-pointer h-2 rounded-lg bg-slate-200 dark:bg-white/[0.1] transition-all"
      />

      {helperText && (
        <p className="text-[11px] text-slate-400 dark:text-[#7E7F96] leading-normal select-none">
          {helperText}
        </p>
      )}
    </div>
  );
};
